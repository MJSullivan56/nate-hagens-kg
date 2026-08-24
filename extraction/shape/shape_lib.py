"""shape_lib.py — shape-driven extraction of episode records from the
hand-enriched Markdown transcripts in extraction/transcripts_text_cache/.

The field list, source priority, and normalization rules all live in
`episode_shape.yaml`. This module supplies the machinery that file names:
block segmentation, the named `extract:` routines, and the named `normalize:`
transforms. Adding a field to the shape needs no edit here unless it requires a
genuinely new extractor.

Why this is more than a regex script: the corpus is 57 files hand-assembled
over several weeks by copy-pasting from episode webpages, so essentially every
field has 2-4 spelling or layout variants (WEBPAGE/Webpage/WEBSITE,
KEYWORDS/Keywords/KEYWOREDS, three different show-notes layouts, meta blocks
that are sometimes five lines and sometimes one). The variants are enumerated in
the shape file rather than discovered at runtime, so an unrecognized variant
shows up as an explicit gap instead of being silently dropped.
"""

from __future__ import annotations

import csv
import datetime as dt
import hashlib
import html as html_mod
import json
import re
from dataclasses import dataclass, field as dc_field
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
EXTRACTION = HERE.parent
REPO = EXTRACTION.parent
MD_DIR = EXTRACTION / "transcripts_text_cache"
MANIFEST = EXTRACTION / "download_manifest.csv"
SHAPE_PATH = HERE / "episode_shape.yaml"
ABSENT_PATH = HERE / "known_absent.yaml"

TRANSCRIPT_RE = re.compile(r"(?im)^\#*\s*TRANSCRIPT\s*:?\s*$")
SHOWNOTES_RE = re.compile(r"(?im)^\#*\s*SHOW\s+NOTES\s*:?\s*$")
DATE_RE = re.compile(
    r"^\s*("
    r"Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec"
    r"|January|February|March|April|June|July|August|September|October|November|December"
    r")\w*\.?\s+(\d{1,2}),?\s+(\d{4})\s*$"
)
MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6, "jul": 7,
    "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}
TS_RE = re.compile(r"^\s*\(?((?:\d{1,2}:)?\d{1,2}:\d{2})\)?\s*[–—\-−:]+\s*(.*)$")
MD_LINK_RE = re.compile(r"\[([^\]]*)\]\((https?://[^)\s]+)\)")
BARE_URL_RE = re.compile(r"https?://[^\s<>\)\]\"',]+")
# "About Foo", "## About Foo", "About Foo:" — the guest-bio heading, all variants.
ABOUT_RE = re.compile(r"(?im)^\#*\s*About\s+(?:Dr\.?\s+)?([A-Z][^\n:#]{1,60}?)\s*:?\s*$")
# Two transcript conventions exist across the corpus, in roughly equal numbers:
#   A. "Nate Hagens [00:12]: text"   -> SPEAKER_RE   (speaker first)
#   B. "[00:00:00] Nate Hagens: text" -> TS_SPEAKER_RE (timestamp first)
# Both must be handled, and B must be tested BEFORE the bare-timestamp
# continuation form or "[00:00:00] Nate Hagens: ..." parses as a continuation
# whose text happens to begin with a name.
SPEAKER_RE = re.compile(r"^([A-Z][A-Za-z.'’\- ]{1,40})\s*\[((?:\d{1,2}:)?\d{1,2}:\d{2})\]\s*:\s*(.*)$")
TS_SPEAKER_RE = re.compile(
    r"^\[((?:\d{1,2}:)?\d{1,2}:\d{2})\]\s*([A-Z][A-Za-z.'’\-]*(?:\s+[A-Z][A-Za-z.'’\-]*){0,3})\s*:\s*(.*)$")
# Third convention, dominant in the .txt batch (115 of 301 files):
#   "Nate Hagens (00:00:02):"  with the spoken text starting on the NEXT line,
#   and bare "(00:00:33):" markers continuing the same speaker.
PAREN_SPEAKER_RE = re.compile(
    r"^([A-Z][A-Za-z.'’\-]*(?:\s+[A-Z][A-Za-z.'’\-]*){0,3})\s*\(((?:\d{1,2}:)?\d{1,2}:\d{2})\)\s*:\s*(.*)$")
PAREN_TS_RE = re.compile(r"^\(((?:\d{1,2}:)?\d{1,2}:\d{2})\)\s*:?\s*(.*)$")
# Fourth variant: "Nate Hagens: (00:02)" — speaker, colon, then the timestamp
# in parentheses. Same shape as PAREN_SPEAKER_RE with the colon moved.
SPEAKER_PAREN_RE = re.compile(
    r"^([A-Z][A-Za-z.'’\-]*(?:\s+[A-Z][A-Za-z.'’\-]*){0,3})\s*:\s*\(((?:\d{1,2}:)?\d{1,2}:\d{2})\)\s*(.*)$")
# Boilerplate at the top of a .txt: the channel banner and the auto-generation
# notice. Neither is transcript content.
TXT_BOILERPLATE_RE = re.compile(
    r"(?is)^\s*(?:\*?\s*The Great Simplification\s*)?"
    r"(?:\*?\s*PLEASE NOTE:.*?info@thegreatsimplification\.com\.?\s*\*?)?\s*")


# --------------------------------------------------------------------------
# shape loading
# --------------------------------------------------------------------------

def load_shape(path: Path = SHAPE_PATH) -> dict:
    with open(path, encoding="utf-8") as fh:
        return yaml.safe_load(fh)["shape"]


def load_known_absent(path: Path = ABSENT_PATH) -> dict:
    """Fields confirmed absent at the source (see known_absent.yaml)."""
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


# --------------------------------------------------------------------------
# normalizers  (referenced by name from the shape's `normalize:` lists)
# --------------------------------------------------------------------------

def n_collapse_ws(v, ctx):
    return re.sub(r"[ \t]+", " ", v).strip() if isinstance(v, str) else v


def n_unescape_html(v, ctx):
    return html_mod.unescape(v) if isinstance(v, str) else v


def n_collapse_blank_lines(v, ctx):
    return re.sub(r"\n{3,}", "\n\n", v).strip() if isinstance(v, str) else v


def n_strip_trailing_slash(v, ctx):
    return v.rstrip("/") if isinstance(v, str) else v


def n_to_iso_date(v, ctx):
    if not isinstance(v, str):
        return v
    m = DATE_RE.match(v.strip())
    if not m:
        # Return None rather than passing the raw string through: an unparseable
        # date should surface as a gap in the report, not as junk in the record.
        return None
    mon = MONTHS.get(m.group(1)[:3].lower())
    return f"{int(m.group(3)):04d}-{mon:02d}-{int(m.group(2)):02d}" if mon else None


def n_youtube_canonical(v, ctx):
    """Normalize every YouTube spelling to https://www.youtube.com/watch?v=<id>."""
    vid = youtube_id(v)
    return f"https://www.youtube.com/watch?v={vid}" if vid else (v or None)


def n_split_keyword_vocabulary(v, ctx):
    """Undo the run-together tag artifact.

    The episode page renders topic tags as adjacent <span class="pill"> elements
    with no separator between them, so a copy-paste yields
    "Economics And MonetarySystems ScienceGeopolitics". Recovering the three
    real tags is only possible against the known vocabulary, which the shape
    supplies. Comma-separated input is handled the same way, so the two styles
    converge on one result.
    """
    vocab = sorted(ctx["shape"]["keyword_vocabulary"], key=len, reverse=True)
    items = v if isinstance(v, list) else [v or ""]
    out = []
    for item in items:
        for chunk in re.split(r"[,;/]", str(item)):
            chunk = chunk.strip()
            if not chunk:
                continue
            rest, found = chunk, []
            # Greedily peel known vocabulary terms off the concatenated blob.
            while rest:
                for term in vocab:
                    if rest.lower().startswith(term.lower()):
                        found.append(term)
                        rest = rest[len(term):].lstrip(" ,;/")
                        break
                else:
                    break
            if found:
                out.extend(found)
                if rest.strip():
                    out.append(rest.strip())  # unknown remainder, kept visible
            else:
                out.append(chunk)
    return out


def n_split_names(v, ctx):
    items = v if isinstance(v, list) else [v or ""]
    out = []
    for item in items:
        for part in re.split(r"\s*(?:,| and | & )\s*", str(item)):
            part = part.strip()
            if part:
                out.append(part)
    return out


def n_dedupe(v, ctx):
    if not isinstance(v, list):
        return v
    seen, out = set(), []
    for x in v:
        k = x.lower() if isinstance(x, str) else json.dumps(x, sort_keys=True)
        if k not in seen:
            seen.add(k)
            out.append(x)
    return out


NORMALIZERS = {
    "collapse_ws": n_collapse_ws,
    "unescape_html": n_unescape_html,
    "collapse_blank_lines": n_collapse_blank_lines,
    "strip_trailing_slash": n_strip_trailing_slash,
    "to_iso_date": n_to_iso_date,
    "youtube_canonical": n_youtube_canonical,
    "split_keyword_vocabulary": n_split_keyword_vocabulary,
    "split_names": n_split_names,
    "dedupe": n_dedupe,
}


# --------------------------------------------------------------------------
# small helpers
# --------------------------------------------------------------------------

def youtube_id(url: str | None) -> str | None:
    if not url:
        return None
    m = re.search(
        r"(?:youtube(?:-nocookie)?\.com/(?:watch\?(?:.*&)?v=|embed/|shorts/|live/)|youtu\.be/)"
        r"([A-Za-z0-9_-]{11})",
        url,
    )
    return m.group(1) if m else None


def ts_to_seconds(ts: str) -> int | None:
    parts = ts.split(":")
    try:
        nums = [int(p) for p in parts]
    except ValueError:
        return None
    if len(nums) == 2:
        return nums[0] * 60 + nums[1]
    if len(nums) == 3:
        return nums[0] * 3600 + nums[1] * 60 + nums[2]
    return None


def strip_tags(h: str) -> str:
    h = re.sub(r"(?is)<(script|style).*?</\1>", " ", h)
    h = re.sub(r"(?i)<br\s*/?>", "\n", h)
    h = re.sub(r"<[^>]+>", " ", h)
    return re.sub(r"[ \t]+", " ", html_mod.unescape(h))


# --------------------------------------------------------------------------
# document segmentation
# --------------------------------------------------------------------------

@dataclass
class MdDoc:
    """A segmented view of one hand-enriched .md file."""
    path: Path
    raw_bytes: bytes
    text: str
    had_nul: bool
    header: str = ""
    transcript: str = ""
    labels: dict = dc_field(default_factory=dict)
    meta: dict = dc_field(default_factory=dict)
    warnings: list = dc_field(default_factory=list)
    is_txt: bool = False


def read_md(path: Path) -> MdDoc:
    raw = path.read_bytes()
    had_nul = b"\x00" in raw
    text = raw.decode("utf-8", errors="replace").replace("\x00", "").replace("\r\n", "\n")
    doc = MdDoc(path=path, raw_bytes=raw, text=text, had_nul=had_nul)

    # A .txt is transcript ONLY — no enriched header, no show notes, no meta
    # block. Everything except the transcript has to come from the episode page,
    # so there is no header to segment and attempting to would misread the
    # opening paragraphs of speech as a description.
    if path.suffix.lower() == ".txt":
        doc.is_txt = True
        doc.header = ""
        doc.transcript = TXT_BOILERPLATE_RE.sub("", text).strip()
        return doc

    # Split on the LAST '# TRANSCRIPT' marker, not the first. Frankly-154 has a
    # stray premature marker sitting above its disclaimer and show-notes table,
    # so splitting on the first one would bury the show notes inside the
    # transcript. Show notes always precede the transcript, so last-marker wins.
    marks = list(TRANSCRIPT_RE.finditer(text))
    if marks:
        m = marks[-1]
        doc.header, doc.transcript = text[: m.start()], text[m.end():].strip()
        if len(marks) > 1:
            doc.warnings.append(
                f"{len(marks)} '# TRANSCRIPT' markers found; split on the last one")
    else:
        doc.header, doc.transcript = text, ""
        doc.warnings.append("no '# TRANSCRIPT' marker; whole file treated as header")

    doc.labels = _parse_labels(doc.header)
    doc.meta = _parse_meta_block(doc.header)
    return doc


def _parse_labels(header: str) -> dict:
    """Collect 'LABEL: value' lines, keyed by uppercased label.

    Restricted to a short whitelist of known label words so that prose
    containing a colon (very common in the description paragraphs) is not
    mistaken for a metadata line.
    """
    known = {
        "WEBPAGE", "WEBSITE", "PAGE", "URL", "LINK",
        "YOUTUBE", "VIDEO", "KEYWORDS", "KEYWOREDS", "KEYWORD",
        "RECORDED ON", "SPOTIFY", "APPLE", "PUBLISHED", "PUBLISHED ON", "TITLE",
    }
    out: dict[str, list[str]] = {}
    for line in header.split("\n"):
        m = re.match(r"^\s*([A-Za-z][A-Za-z ]{2,20}?)\s*:\s*(.*)$", line)
        if not m:
            continue
        key = re.sub(r"\s+", " ", m.group(1).strip()).upper()
        if key in known:
            out.setdefault(key, []).append(m.group(2).strip())
    return {k: v for k, v in out.items()}


def _parse_meta_block(header: str) -> dict:
    """Locate and parse the 5-ish line block copied off the page's .post_meta.

    Canonical layout on the webpage (and so in most .md files):

        <guest byline>            e.g. "Nate Hagens"        (optional)
        <episode label>           e.g. "Reality Roundtable 19"
        <publish date>            e.g. "Sep 17, 2025"
        Recorded on:
        <recorded date>           e.g. "Jul 22, 2025"
        <keywords>                e.g. "Human Behavior"     (optional)

    RR-26 collapses this onto two inline lines instead
    ("Reality Roundtable #26, Jun 10, 2026" / "Recorded on: Apr 22, 2026"), so
    both forms are handled. Anchoring on "Recorded on" rather than on position
    is what makes this work across all the variants.
    """
    lines = header.split("\n")
    meta: dict = {}

    rec_i = next((i for i, l in enumerate(lines) if re.search(r"(?i)recorded\s+on", l)), None)
    if rec_i is not None:
        # "Recorded on: Apr 22, 2026" (inline) and "Recorded on:" followed by the
        # date on the next line are both common. `[\s:]*` eats the separator so
        # the bare-label form yields an empty capture rather than a stray ":".
        inline = re.search(r"(?i)recorded\s+on\b[\s:]*(.*)$", lines[rec_i])
        val = inline.group(1).strip() if inline else ""
        if not val:
            val = next((l.strip() for l in lines[rec_i + 1: rec_i + 4] if l.strip()), "")
        if DATE_RE.match(val):
            meta["recorded_date"] = val

        # Walk backwards for publish date, then the label line above it.
        prev = [(i, lines[i].strip()) for i in range(rec_i - 1, max(-1, rec_i - 7), -1)
                if lines[i].strip()]
        label_i = None
        for i, val in prev:
            if DATE_RE.match(val):
                meta["published_date"] = val
                label_i = i
                break
        if label_i is not None:
            above = next((lines[j].strip() for j in range(label_i - 1, max(-1, label_i - 4), -1)
                          if lines[j].strip()), "")
            if above and not DATE_RE.match(above):
                meta["episode_label"] = above
        else:
            # No separate publish-date line: it may be fused with the label,
            # as in RR-26's "Reality Roundtable #26, Jun 10, 2026".
            for i, val in prev:
                dm = re.search(
                    r"^(.*?),\s*((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\.?\s+\d{1,2},?\s+\d{4})\s*$",
                    val,
                )
                if dm:
                    meta["episode_label"] = dm.group(1).strip()
                    meta["published_date"] = dm.group(2).strip()
                    break

        # Keywords: the line after the recorded date, if it is vocabulary-ish.
        tail = [l.strip() for l in lines[rec_i + 1: rec_i + 6] if l.strip()]
        for cand in tail:
            if DATE_RE.match(cand):
                continue
            km = re.match(r"(?i)^(?:KEYWO?RE?DS?|Keywords?)\s*:\s*(.+)$", cand)
            if km:
                meta["keywords"] = km.group(1).strip()
                break
            if re.match(r"(?i)^(?:Energy|Human|Economic|Systems|Geopolit)", cand) and len(cand) < 120:
                meta["keywords"] = cand
                break
    return meta


# --------------------------------------------------------------------------
# block extractors
# --------------------------------------------------------------------------

def label_value(doc: MdDoc, names: list[str]) -> tuple[str | None, str | None]:
    """First non-empty value among the given header-label spellings."""
    for key in names:
        for v in doc.labels.get(key, []):
            if v.strip():
                return v.strip(), f"md_label:{key}"
    return None, None


def block_description(doc: MdDoc) -> str | None:
    """Prose between the SHOW NOTES / Description heading and the first
    'About <Name>' bio or the meta block, whichever comes first."""
    h = doc.header
    start = 0
    dm = re.search(r"(?im)^\#*\s*(?:Description|Show\s+Summary)\s*:?\s*$", h)
    if dm:
        start = dm.end()
    else:
        sm = SHOWNOTES_RE.search(h)
        if sm:
            start = sm.end()

    ends = []
    am = ABOUT_RE.search(h, start)
    if am:
        ends.append(am.start())
    # The meta block starts at the episode-label line; cut there if we found it.
    lbl = doc.meta.get("episode_label")
    if lbl:
        i = h.find(lbl, start)
        if i > start:
            ends.append(i)
    pd = doc.meta.get("published_date")
    if pd:
        i = h.find(pd, start)
        if i > start:
            ends.append(i)
    km = re.search(r"(?im)^\s*(?:KEYWO?RE?DS?|Keywords?)\s*:", h[start:])
    if km:
        ends.append(start + km.start())
    dis = re.search(r"(?i)The TGS team puts together", h[start:])
    if dis:
        ends.append(start + dis.start())

    body = h[start: min(ends)] if ends else h[start:]
    # Drop residual label lines and headings that slipped into the range.
    keep = [
        l for l in body.split("\n")
        if not re.match(r"(?i)^\s*(?:WEBPAGE|WEBSITE|PAGE|YOUTUBE|VIDEO|KEYWO?RE?DS?|Keywords?|URL|LINK)\s*:", l)
        and not re.match(r"^\s*\#", l)
        and l.strip() != "The Great Simplification"
    ]
    out = n_collapse_blank_lines("\n".join(keep), None)
    return out or None


def block_disclaimer(doc: MdDoc) -> str | None:
    m = re.search(r"(?is)(The TGS team puts together.*?own informed conclusions\.)", doc.header)
    return n_collapse_ws(re.sub(r"\s*\n\s*", " ", m.group(1)), None) if m else None


def _about_sections(doc: MdDoc) -> list[dict]:
    h = doc.header
    hits = list(ABOUT_RE.finditer(h))
    out = []
    for i, m in enumerate(hits):
        name = n_collapse_ws(m.group(1), None)
        # Reject false positives: prose sentences that happen to start "About ..."
        if not re.match(r"^[A-Z][\w.'’\-]*(?:\s+[A-Z][\w.'’\-]*){0,4}$", name):
            continue
        end = hits[i + 1].start() if i + 1 < len(hits) else len(h)
        body = h[m.end(): end]
        # Stop the bio at the meta block if it runs into it.
        for stop in (doc.meta.get("episode_label"), doc.meta.get("published_date")):
            if stop:
                j = body.find(stop)
                if j > 0:
                    body = body[:j]
        bio = n_collapse_blank_lines("\n".join(
            l for l in body.split("\n") if not re.match(r"^\s*\#", l)
        ), None)
        out.append({"name": name, "bio": bio or None})
    return out


def block_about_names(doc: MdDoc) -> list[str]:
    return [s["name"] for s in _about_sections(doc)]


def block_about_bios(doc: MdDoc) -> list[dict]:
    return _about_sections(doc)


def block_credits(doc: MdDoc) -> list[dict] | None:
    m = re.search(r"(?im)^\#*\s*Credits\s*:?\s*$", doc.header)
    if not m:
        return None
    body = doc.header[m.end():]
    stop = re.search(r"(?im)^\#+\s", body)
    if stop:
        body = body[: stop.start()]
    out = []
    for line in body.split("\n"):
        line = line.strip()
        if not line:
            continue
        rm = re.match(r"^[-*•]\s*([^:]{2,60}?)\s*:\s*(.+)$", line)
        if rm:
            for name in re.split(r"\s*(?:,| and | & )\s*", rm.group(2)):
                if name.strip():
                    out.append({"role": rm.group(1).strip(), "name": name.strip()})
        elif not line.startswith(("-", "*", "•")) and len(line) < 60 and ":" not in line:
            out.append({"role": "organization", "name": line})
        elif line.lower().startswith("thanks"):
            out.append({"role": "acknowledgement", "name": line})
    return out or None


def block_show_notes(doc: MdDoc) -> tuple[list[dict], str | None]:
    """Parse the timestamped show-notes index in any of its three layouts.

    Returns (rows, layout) where layout is 'table', 'lines+links',
    'lines-only', or None. 'lines-only' is the gap case: the timestamps and
    topics were transcribed by hand but the site's hyperlinks were never
    copied, so those rows need filling from the episode page.
    """
    h = doc.header
    rows: list[dict] = []

    # ---- Layout A: markdown table ----
    table_rows = [l for l in h.split("\n") if l.lstrip().startswith("|")]
    body_rows = [l for l in table_rows if not re.match(r"^\s*\|[\s|:\-]+\|?\s*$", l)]
    for line in body_rows:
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 2:
            continue
        if re.match(r"(?i)^\s*time", cells[0]):  # header row
            continue
        tsm = re.match(r"^\(?((?:\d{1,2}:)?\d{1,2}:\d{2})\)?$", cells[0])
        if not tsm:
            continue
        topic = cells[1]
        linkcell = cells[2] if len(cells) > 2 else ""
        links = [{"label": n_collapse_ws(lb, None) or None, "url": u}
                 for lb, u in MD_LINK_RE.findall(linkcell)]
        seen = {l["url"] for l in links}
        links += [{"label": None, "url": u} for u in BARE_URL_RE.findall(
            MD_LINK_RE.sub(" ", linkcell)) if u not in seen]
        rows.append({
            "timestamp": tsm.group(1),
            "seconds": ts_to_seconds(tsm.group(1)),
            "topic": n_collapse_ws(MD_LINK_RE.sub(r"\1", topic), None) or None,
            "links": links,
        })
    if rows:
        return rows, "table"

    # ---- Layouts B/C: plain "MM:SS - topic" lines, links (if any) below ----
    lines = h.split("\n")
    cur = None
    for line in lines:
        if line.lstrip().startswith("|"):
            continue
        m = TS_RE.match(line)
        if m and not line.startswith(("    ", "\t")):
            ts = m.group(1)
            topic = m.group(2).strip()
            links = [{"label": n_collapse_ws(lb, None) or None, "url": u}
                     for lb, u in MD_LINK_RE.findall(topic)]
            topic_clean = MD_LINK_RE.sub(r"\1", topic)
            for u in BARE_URL_RE.findall(topic_clean):
                links.append({"label": None, "url": u})
                topic_clean = topic_clean.replace(u, "")
            cur = {
                "timestamp": ts,
                "seconds": ts_to_seconds(ts),
                "topic": n_collapse_ws(topic_clean.strip(" -–—,"), None) or None,
                "links": links,
            }
            rows.append(cur)
        elif cur is not None:
            # Continuation: indented bullet or bare URL belonging to the row above.
            for lb, u in MD_LINK_RE.findall(line):
                cur["links"].append({"label": n_collapse_ws(lb, None) or None, "url": u})
            for u in BARE_URL_RE.findall(MD_LINK_RE.sub(" ", line)):
                cur["links"].append({"label": None, "url": u})
            if not line.strip():
                cur = None

    if not rows:
        return [], None
    layout = "lines+links" if any(r["links"] for r in rows) else "lines-only"
    return rows, layout


def guests_from_title(title: str | None) -> list[str]:
    """Pull featured-guest names out of a title's "with <Name>" suffix.

    This channel names a featured guest in the title itself — "Staying Warm
    Data with Nora Bateson", "Reclaiming Food Sovereignty through Farming Clubs?
    with Jason Bradford". It is the ONLY guest signal for such episodes: the
    page's byline heading reads just "Nate Hagens" regardless, and a Frankly
    with a guest carries no "About <Name>" bio block either.

    Requiring two-or-more capitalized tokens is what keeps this from firing on
    ordinary prose ("...with a Framework for Action", "...with Nature").
    """
    if not title:
        return []
    m = re.search(
        r"\bwith\s+((?:[A-Z][\w.'’\-]*)(?:\s+[A-Z][\w.'’\-]*){1,2}"
        r"(?:\s*(?:,|and|&)\s*(?:[A-Z][\w.'’\-]*)(?:\s+[A-Z][\w.'’\-]*){1,2})*)",
        title)
    if not m:
        return []
    stop = {"The", "A", "An", "Part", "How", "What", "Why", "Our", "This",
            "Framework", "Series", "Nate", "Hagens"}
    out = []
    for name in re.split(r"\s*(?:,|and|&)\s*", m.group(1)):
        toks = name.split()
        if len(toks) >= 2 and not (set(toks) & stop):
            out.append(name.strip())
    return out


def is_non_person_speaker(label: str | None, shape: dict) -> bool:
    """True if a speaker label names something other than a person.

    "Voiceover" and "Outro" are labels for audio, not speakers, so they must not
    land in transcript_speakers (a person index). The turn itself is kept — the
    text is real content. The vocabulary lives in the shape file; a trailing
    number is ignored so "Speaker 2" matches "Speaker".
    """
    if not label:
        return True
    v = re.sub(r"[\s_-]*\d+$", "", str(label)).strip().lower()
    return v in {x.strip().lower() for x in shape.get("non_person_speakers") or []}


def block_transcript_chapters(transcript: str) -> list[dict]:
    """Extract "## Chapter N: Title" style headings from a transcript.

    A handful of transcripts (Frankly 80/151, RR-13, Frankly-047) carry no
    speaker labels at all — continuous prose broken up by chapter headings
    instead. Those yield no speaker turns, so these headings are the only
    structure available for navigating them.
    """
    out = []
    for m in re.finditer(r"(?m)^\s*\#{2,}\s*(.+?)\s*$", transcript):
        title = n_collapse_ws(m.group(1), None)
        if not title:
            continue
        num = re.match(r"(?i)^chapter\s+(\d+)\s*[:.\-]?\s*(.*)$", title)
        out.append({
            "index": int(num.group(1)) if num else len(out) + 1,
            "title": (num.group(2).strip() or title) if num else title,
            "heading": title,
        })
    return out


def block_transcript_turns(transcript: str) -> list[dict]:
    """Parse 'Speaker [MM:SS]: text' turns; returns [] for other conventions."""
    turns: list[dict] = []
    cur = None
    for line in transcript.split("\n"):
        if set(line.strip()) == {"-"} or not line.strip():
            continue
        m = SPEAKER_RE.match(line.strip())
        m2 = None if m else TS_SPEAKER_RE.match(line.strip())
        m3 = None if (m or m2) else PAREN_SPEAKER_RE.match(line.strip())
        if not (m or m2 or m3):
            m3 = SPEAKER_PAREN_RE.match(line.strip())
        if m3:
            cur = {
                "speaker": n_collapse_ws(m3.group(1), None),
                "timestamp": m3.group(2),
                "seconds": ts_to_seconds(m3.group(2)),
                "text": m3.group(3).strip(),
            }
            turns.append(cur)
        elif m:
            cur = {
                "speaker": n_collapse_ws(m.group(1), None),
                "timestamp": m.group(2),
                "seconds": ts_to_seconds(m.group(2)),
                "text": m.group(3).strip(),
            }
            turns.append(cur)
        elif m2:
            cur = {
                "speaker": n_collapse_ws(m2.group(2), None),
                "timestamp": m2.group(1),
                "seconds": ts_to_seconds(m2.group(1)),
                "text": m2.group(3).strip(),
            }
            turns.append(cur)
        else:
            tsonly = re.match(r"^\[((?:\d{1,2}:)?\d{1,2}:\d{2})\]\s*:?\s*(.*)$", line.strip())
            if not tsonly:
                tsonly = PAREN_TS_RE.match(line.strip())
            if tsonly:
                # speaker=None when nothing has named one yet. 24 of the .txt
                # files are solo Franklys timestamped as "[00:00:00] text" with
                # no speaker label anywhere. Keeping the timestamped
                # segmentation is worth having; guessing at the speaker is not,
                # so attribution is left to the caller (the episode's host is
                # recorded separately).
                cur = {
                    "speaker": cur["speaker"] if cur else None,
                    "timestamp": tsonly.group(1),
                    "seconds": ts_to_seconds(tsonly.group(1)),
                    "text": tsonly.group(2).strip(),
                }
                turns.append(cur)
            elif cur:
                cur["text"] = (cur["text"] + " " + line.strip()).strip()
    for t in turns:
        t["text"] = n_collapse_ws(t["text"], None)
    return turns


# --------------------------------------------------------------------------
# manifest
# --------------------------------------------------------------------------

def load_manifest(path: Path = MANIFEST) -> list[dict]:
    if not path.exists():
        return []
    with open(path, encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def manifest_lookup(rows: list[dict], series: str, number: int | None,
                    guest_hint: str = "") -> dict | None:
    """Find the manifest row for a series+number.

    URL slugs differ by series: Franklys live at /frankly-original/<n>-<slug>,
    roundtables at /episode/reality-roundtable-<n> (with a handful of older
    /episode/rr<nn>-<names> forms), interviews at /episode/<n>-<slug>.
    """
    if number is None:
        return None
    pats = {
        "frankly": [rf"/frankly-original/{number}-", rf"/frankly/{number}-"],
        "roundtable": [rf"/episode/reality-roundtable-{number}$",
                       rf"/episode/rr-?0*{number}-"],
        "interview": [rf"/episode/{number}-"],
    }.get(series, [])
    for pat in pats:
        for r in rows:
            if re.search(pat, r.get("episode_url", "")):
                return r
    return None


# --------------------------------------------------------------------------
# record assembly
# --------------------------------------------------------------------------

def build_record(path: Path, shape: dict, manifest: list[dict],
                 site: dict | None = None) -> dict:
    """Extract one episode record from a .md file, per the shape.

    `site` is an optional dict of values scraped from the episode webpage (see
    fetch_episode_pages.py). Per the shape's conflict policy the .md always
    wins; site values only fill fields the .md left empty, and any disagreement
    on a field the .md did supply is recorded under `_site_divergence`.
    """
    doc = read_md(path)
    site = site or {}
    ctx = {"shape": shape, "doc": doc}

    # Path.stem only strips the last suffix, leaving ".docx" on the many
    # ".docx.txt" transcripts. Strip every transcript-ish extension so the
    # record_id is clean and matches the resolver's own stem.
    stem = re.sub(r"(?i)(\.txt|\.docx|\.pdf|\.doc)+$", "", path.name)
    prefix = next((p for p in ("Frankly", "RR", "TGS", "Video") if stem.startswith(p)), None)
    series_cfg = shape["series"].get(prefix, {})
    series = series_cfg.get("kind")

    rec: dict = {}
    prov: dict = {}
    gaps: list[str] = []
    diverge: dict = {}

    def put(name, value, source):
        if value is None or value == [] or value == "":
            return False
        rec[name] = value
        prov[name] = source
        return True

    # ---- identity ----
    put("record_id", stem, "md_filename")
    put("series", series, "md_filename")
    put("source_file", path.name, "md_filename")

    # episode number: prefer the label line inside the file, fall back to filename
    num = None
    lbl = doc.meta.get("episode_label") or ""
    if series_cfg.get("label_pattern"):
        m = re.search(series_cfg["label_pattern"], lbl)
        if m:
            num = int(m.group(1))
            put("episode_number", num, "md_block:meta")
    if num is None:
        m = re.match(r"^(?:Frankly|RR|TGS)-(\d+)", stem)
        if m:
            num = int(m.group(1))
            put("episode_number", num, "md_filename")
    if series == "video":
        m = re.search(r"Part\s*(\d+)\s*of\s*(\d+)", stem)
        if m:
            put("part_number", int(m.group(1)), "md_filename")
            put("part_total", int(m.group(2)), "md_filename")

    if lbl:
        put("episode_label", n_collapse_ws(lbl, ctx), "md_block:meta")
    elif site.get("episode_label"):
        put("episode_label", site["episode_label"], "site:#epi_label")

    # ---- title ----
    # Franklys fuse label and title on one line ("Frankly 151 | Real Title");
    # RR/TGS carry only a bare label, so their title comes from the page <h1>.
    title = None
    if lbl and "|" in lbl:
        title = lbl.split("|", 1)[1].strip()
        src = "md_block:meta"
    if not title:
        # A "TITLE:" header line is what patch_md.py writes for RR/TGS files,
        # whose meta block carries only a bare label ("Reality Roundtable 19")
        # with the real title living solely on the webpage.
        title, src = label_value(doc, ["TITLE"])
    if not title and series == "video":
        first = next((l.strip() for l in doc.header.split("\n") if l.strip()), "")
        title = re.sub(r"(?i)^Video\s+Ser[it]+es\s*:\s*", "", first).strip() or None
        src = "md_block:first_line"
    if not title and site.get("title"):
        title, src = site["title"], "site:h1"
    if not title:
        mrow = manifest_lookup(manifest, series, num)
        if mrow and mrow.get("title"):
            title, src = mrow["title"], "manifest:title"
    if title:
        for nm in ("collapse_ws", "unescape_html"):
            title = NORMALIZERS[nm](title, ctx)
        put("title", title, src)

    # ---- links ----
    def from_labels(names):
        return label_value(doc, names)

    wp, wsrc = from_labels(["WEBPAGE", "WEBSITE", "PAGE", "URL", "LINK"])
    if not wp:
        mrow = manifest_lookup(manifest, series, num)
        if mrow:
            wp, wsrc = mrow.get("episode_url"), "manifest:episode_url"
    if not wp and site.get("webpage_url"):
        wp, wsrc = site["webpage_url"], "site:canonical"
    if wp:
        put("webpage_url", n_strip_trailing_slash(wp, ctx), wsrc)

    yt, ysrc = from_labels(["YOUTUBE", "VIDEO"])
    if yt and not youtube_id(yt):
        yt = None  # a "Video:" label that isn't actually a YouTube link
    if not yt and site.get("youtube_url"):
        yt, ysrc = site["youtube_url"], "site:a#ep_lnk_yt"
    if series == "video" and not yt:
        # The animated-series files put the YouTube URL in the WEBPAGE slot.
        if youtube_id(rec.get("webpage_url", "")):
            yt, ysrc = rec["webpage_url"], "md_label:WEBPAGE"
    if yt:
        put("youtube_url", n_youtube_canonical(yt, ctx), ysrc)
        put("youtube_video_id", youtube_id(yt), "derived:youtube_url")

    for fld, key in (("spotify_url", "spotify_url"),
                     ("apple_podcasts_url", "apple_podcasts_url"),
                     ("podlink_url", "podlink_url"),
                     ("transcript_pdf_url", "transcript_pdf_url"),
                     ("duration_seconds", "duration_seconds")):
        if site.get(key):
            put(fld, site[key], f"site:{key}")
    if "transcript_pdf_url" not in rec:
        mrow = manifest_lookup(manifest, series, num)
        if mrow and mrow.get("transcript_url"):
            put("transcript_pdf_url", mrow["transcript_url"], "manifest:transcript_url")

    # ---- dates ----
    for fld, sitekey, labels in (
            ("published_date", "published_date", ["PUBLISHED", "PUBLISHED ON"]),
            ("recorded_date", "recorded_date", ["RECORDED ON"])):
        v, src = doc.meta.get(fld), "md_block:meta"
        if not v:
            # A "PUBLISHED:" header line is what patch_md.py writes for records
            # with no meta block to anchor a bare date (the animated videos).
            v, src = from_labels(labels)
        if not v and site.get(sitekey):
            v, src = site[sitekey], "site:.post_meta"
        if v:
            put(fld, n_to_iso_date(v, ctx), src)

    # ---- keywords ----
    kw, ksrc = None, None
    if doc.meta.get("keywords"):
        kw, ksrc = doc.meta["keywords"], "md_block:meta"
    else:
        v, s = from_labels(["KEYWORDS", "KEYWOREDS", "KEYWORD"])
        if v:
            kw, ksrc = v, s
    if not kw and site.get("keywords"):
        kw, ksrc = site["keywords"], "site:.post_tags"
    if kw:
        vals = n_dedupe(n_split_keyword_vocabulary(kw, ctx), ctx)
        put("keywords", vals, ksrc)

    # ---- people ----
    rec["host"] = shape["fields"][next(
        i for i, f in enumerate(shape["fields"]) if f["name"] == "host")].get("default")
    prov["host"] = "shape_default"

    # Guests are gathered from every available signal and merged, because no
    # single one covers the whole corpus: "About <Name>" bios exist on most
    # interviews/roundtables but never on a Frankly, while the "with <Name>"
    # title convention is the only signal for a guest-featuring Frankly.
    # Any name equal to the host is dropped — the page byline reads
    # "Nate Hagens" on many episodes, and he is not his own guest.
    host = (rec.get("host") or "").lower()
    bios = block_about_bios(doc)
    if bios:
        put("guest_bios", bios, "md_block:about")
    elif site.get("guest_bios"):
        bios = site["guest_bios"]
        put("guest_bios", bios, "site:about-sections")

    cand: list[tuple[str, str]] = []
    for b in bios:
        cand.append((b["name"], "md_block:about"))
    for b in (site.get("guest_bios") or []):
        cand.append((b["name"], "site:about-sections"))
    for g in n_split_names(site.get("guests") or [], ctx):
        cand.append((g, "site:.post_meta h3"))
    for g in guests_from_title(rec.get("title")):
        cand.append((g, "derived:title"))

    names, srcs, seen = [], [], set()
    for name, src in cand:
        key = name.lower()
        if key == host or key in seen or not name:
            continue
        seen.add(key)
        names.append(name)
        srcs.append(src)
    if names:
        put("guests", names, "+".join(sorted(set(srcs))))

    creds = block_credits(doc)
    if creds:
        put("credits", creds, "md_block:credits")

    # ---- prose ----
    desc = None if doc.is_txt else block_description(doc)
    if not desc and site.get("description"):
        desc, dsrc = site["description"], "site:.wp-block-paragraph"
    else:
        dsrc = "md_block:description"
    if desc:
        put("description", desc, dsrc)

    dis = block_disclaimer(doc)
    if dis:
        put("disclaimer", dis, "md_block:disclaimer")

    # ---- show notes ----
    rows, layout = block_show_notes(doc)
    if rows:
        put("show_notes", rows, "md_block:show_notes")
        put("show_notes_layout", layout, "derived:show_notes")
    elif site.get("show_notes"):
        put("show_notes", site["show_notes"], "site:#epi_notes")
        put("show_notes_layout", "site", "site:#epi_notes")

    # ---- transcript ----
    if doc.transcript:
        rec["transcript"] = doc.transcript
        prov["transcript"] = "md_block:transcript"
        chapters = block_transcript_chapters(doc.transcript)
        if chapters:
            put("transcript_chapters", chapters, "derived:transcript")
        turns = block_transcript_turns(doc.transcript)
        if turns:
            rec["transcript_turns"] = turns
            prov["transcript_turns"] = "derived:transcript"
            put("transcript_speakers",
                n_dedupe([t["speaker"] for t in turns
                          if not is_non_person_speaker(t["speaker"], shape)], ctx),
                "derived:transcript_turns")

    # ---- integrity ----
    put("source_sha256", hashlib.sha256(doc.raw_bytes).hexdigest(), "derived")
    rec["had_nul_bytes"] = doc.had_nul
    prov["had_nul_bytes"] = "derived"

    # ---- gap + divergence report ----
    # A field recorded in known_absent.yaml has been checked and found genuinely
    # missing at the source, so it is reported separately from an open gap.
    absent = (load_known_absent().get(stem) or {})
    for f in shape["fields"]:
        name = f["name"]
        if f.get("required") and not rec.get(name):
            if name in absent:
                rec.setdefault("_confirmed_absent", {})[name] = absent[name]
            else:
                gaps.append(name)

    for key, fld in (("title", "title"), ("published_date", "published_date"),
                     ("recorded_date", "recorded_date"), ("youtube_url", "youtube_url"),
                     ("webpage_url", "webpage_url")):
        sv = site.get(key)
        if not sv or fld not in rec:
            continue
        a, b = rec[fld], sv
        if fld.endswith("_date"):
            b = n_to_iso_date(b, ctx)
        if fld == "youtube_url":
            b = n_youtube_canonical(b, ctx)
        if str(a).strip().lower() != str(b).strip().lower():
            diverge[fld] = {"md": a, "site": b}

    rec["_provenance"] = prov
    rec["_gaps"] = gaps
    if diverge:
        rec["_site_divergence"] = diverge
    if doc.warnings:
        rec["_warnings"] = doc.warnings
    return rec


def emit(rec: dict, fmt: str = "yaml", with_transcript: bool = False) -> str:
    out = dict(rec)
    if not with_transcript:
        out.pop("transcript", None)
        out.pop("transcript_turns", None)
    if fmt == "json":
        # PyYAML turns an unquoted `2026-08-21` (as in known_absent.yaml) into a
        # datetime.date, which json.dumps rejects outright. Emit any such value
        # as its ISO string so both output formats stay in step.
        return json.dumps(out, indent=2, ensure_ascii=False,
                          default=lambda o: o.isoformat()
                          if isinstance(o, (dt.date, dt.datetime)) else str(o))
    return yaml.safe_dump(out, sort_keys=False, allow_unicode=True, width=100)
