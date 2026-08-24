#!/usr/bin/env python3
"""fetch_episode_pages.py — fill the gaps in the hand-enriched .md files from
their canonical source: the episode page on thegreatsimplification.com.

    python extraction/shape/fetch_episode_pages.py --catalog     # refresh catalog
    python extraction/shape/fetch_episode_pages.py --fetch       # fetch missing pages
    python extraction/shape/fetch_episode_pages.py --extract     # (re)parse cached HTML

Two stages, deliberately separate so the slow one runs once:

  1. CATALOG. The site is WordPress and exposes its REST API, so the full
     episode list can be pulled as JSON from two post types — `episode`
     (interviews + Reality Roundtables) and `frankly-original` (Franklys).
     This is what makes URL resolution reliable: slugs are NOT guessable.
     Episode 1 is at /episode/01-dickgephardt (zero-padded), episode 220 at
     /episode/220-art-berman (not padded), and roundtable 19 at
     /episode/reality-roundtable-19. Pattern-guessing those would fail; the
     catalog just tells us.

  2. FETCH + EXTRACT. Each page is downloaded once into site_cache/ and parsed
     locally, so re-running the extraction costs nothing and does not re-hit the
     site. The site's robots.txt asks for Crawl-delay: 10 and this honors it.

What the pages give us that the .md files lack:
  - youtube_url            from a#ep_lnk_yt  (47 of 57 files were missing this)
  - spotify/apple/podlink  from a#ep_lnk_{sp,am,pl}
  - transcript_pdf_url     from a#dl_transcript
  - title                  from h1           (RR/TGS .md files never carried it)
  - episode_label          from p#epi_label
  - published/recorded     from .post_meta
  - keywords               from .post_tags .pill
  - show_notes with links  from div#epi_notes (444 hand-typed rows have no links)

IMPORTANT on the YouTube link: episode pages contain many youtube.com URLs
inside their show notes (RR-19 alone has three). A bare regex over the page
picks the wrong one. The `id="ep_lnk_yt"` anchor is the only unambiguous
signal, so that is what this uses.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import html as html_mod
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import shape_lib as SL  # noqa: E402

HERE = Path(__file__).resolve().parent
CACHE = HERE / "site_cache"
CATALOG = CACHE / "catalog.json"
VALUES = CACHE / "site_values.json"

BASE = "https://www.thegreatsimplification.com"
REST = {
    "episode": f"{BASE}/wp-json/wp/v2/episode",
    "frankly-original": f"{BASE}/wp-json/wp/v2/frankly-original",
}
UA = "nate-hagens-kg/1.0 (research; contact michael@haywood-sullivan.com)"
CRAWL_DELAY = 10  # honors the site's robots.txt Crawl-delay directive


def get(url: str, timeout: int = 45) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read()
    return raw.decode("utf-8", errors="replace")


# --------------------------------------------------------------------------
# stage 1: catalog
# --------------------------------------------------------------------------

def build_catalog() -> dict:
    entries = []
    for ptype, base in REST.items():
        page = 1
        while True:
            url = (f"{base}?per_page=100&page={page}"
                   f"&orderby=date&order=asc&_fields=id,slug,link,title,date")
            try:
                data = json.loads(get(url))
            except urllib.error.HTTPError as e:
                if e.code == 400:  # past the last page
                    break
                raise
            if not isinstance(data, list) or not data:
                break
            for e in data:
                entries.append({
                    "post_type": ptype,
                    "id": e["id"],
                    "slug": e["slug"],
                    "link": e["link"],
                    "title": html_mod.unescape(e["title"]["rendered"]),
                    "date": e.get("date"),
                })
            print(f"  {ptype} page {page}: {len(data)}")
            if len(data) < 100:
                break
            page += 1
            time.sleep(1)

    cat = {"entries": entries, "index": _index(entries)}
    CACHE.mkdir(parents=True, exist_ok=True)
    CATALOG.write_text(json.dumps(cat, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"catalog: {len(entries)} entries -> {CATALOG}")
    return cat


def _index(entries: list[dict]) -> dict:
    """Map 'series:number' -> canonical URL.

    Slug numbering is inconsistent across the catalog's history (zero-padded
    early episodes, un-padded later ones, plus 'archive-' prefixed re-posts),
    so every leading-number form is indexed and 'archive-' duplicates lose to
    the canonical entry.
    """
    idx: dict[str, str] = {}

    def add(key, link, weak=False):
        if key not in idx or (not weak and "archive-" in idx[key]):
            idx[key] = link

    for e in entries:
        slug, link = e["slug"], e["link"]
        weak = slug.startswith("archive-")
        s = slug[len("archive-"):] if weak else slug
        if e["post_type"] == "frankly-original":
            m = re.match(r"^0*(\d+)\b", s)
            if m:
                add(f"frankly:{int(m.group(1))}", link, weak)
        else:
            m = re.match(r"^reality-roundtable-0*(\d+)\b", s)
            if m:
                add(f"roundtable:{int(m.group(1))}", link, weak)
                continue
            m = re.match(r"^rr-?0*(\d+)\b", s)
            if m:
                add(f"roundtable:{int(m.group(1))}", link, weak)
                continue
            m = re.match(r"^0*(\d+)\b", s)
            if m:
                add(f"interview:{int(m.group(1))}", link, weak)
    return idx


def load_catalog() -> dict:
    if not CATALOG.exists():
        raise SystemExit("no catalog; run with --catalog first")
    return json.loads(CATALOG.read_text(encoding="utf-8"))


# --------------------------------------------------------------------------
# stage 2: fetch
# --------------------------------------------------------------------------

def resolve_url(rec: dict, catalog: dict) -> str | None:
    if rec.get("webpage_url") and "thegreatsimplification.com" in rec["webpage_url"]:
        return rec["webpage_url"]
    num, series = rec.get("episode_number"), rec.get("series")
    if num is not None and series:
        return catalog["index"].get(f"{series}:{num}")
    return None


def fetch_all(records: list[dict], catalog: dict, force: bool = False) -> None:
    CACHE.mkdir(parents=True, exist_ok=True)
    todo = []
    for rec in records:
        rid = rec["record_id"]
        # The 4 animated videos are YouTube-only; they have no episode page.
        if rec.get("series") == "video":
            continue
        url = resolve_url(rec, catalog)
        if not url:
            print(f"  UNRESOLVED {rid}")
            continue
        dest = CACHE / f"{rid}.html"
        if dest.exists() and not force:
            continue
        todo.append((rid, url, dest))

    print(f"{len(todo)} pages to fetch (crawl-delay {CRAWL_DELAY}s)")
    for i, (rid, url, dest) in enumerate(todo, 1):
        try:
            html = get(url)
            dest.write_text(html, encoding="utf-8")
            print(f"  [{i}/{len(todo)}] {rid} <- {url} ({len(html)} bytes)")
        except Exception as e:  # noqa: BLE001 - keep going, report at the end
            print(f"  [{i}/{len(todo)}] FAILED {rid} {url}: {e}")
        if i < len(todo):
            time.sleep(CRAWL_DELAY)


# --------------------------------------------------------------------------
# stage 3: extract from cached HTML
# --------------------------------------------------------------------------

def _anchor(html: str, anchor_id: str) -> str | None:
    m = re.search(rf'<a[^>]*\bid="{anchor_id}"[^>]*\bhref="([^"]+)"', html)
    if m:
        return html_mod.unescape(m.group(1))
    m = re.search(rf'<a[^>]*\bhref="([^"]+)"[^>]*\bid="{anchor_id}"', html)
    return html_mod.unescape(m.group(1)) if m else None


def _div(html: str, attr: str, value: str) -> str | None:
    """Return the inner HTML of the first element whose `attr` equals `value`.

    Walks nested same-tag opens/closes so a container with child <div>s is not
    truncated at the first </div>.
    """
    m = re.search(rf'<(\w+)[^>]*\b{attr}="(?:[^"]*\s)?{re.escape(value)}(?:\s[^"]*)?"[^>]*>', html)
    if not m:
        return None
    tag, pos, depth = m.group(1), m.end(), 1
    for t in re.finditer(rf"</?{tag}\b[^>]*>", html[pos:]):
        depth += -1 if t.group(0).startswith("</") else 1
        if depth == 0:
            return html[pos: pos + t.start()]
    return html[pos:]


def _links_from_html(frag: str) -> list[dict]:
    out = []
    for m in re.finditer(r'<a[^>]*\bhref="([^"]+)"[^>]*>(.*?)</a>', frag, re.S | re.I):
        url = html_mod.unescape(m.group(1)).strip()
        if not url.startswith("http"):
            continue
        # Collapse ALL whitespace, newlines included. n_collapse_ws only folds
        # spaces and tabs, so a label spanning two source lines kept its newline
        # and produced a multi-line "bullet" when written back into the .md —
        # which then never compared equal to itself on the next run.
        label = re.sub(r"\s+", " ", SL.strip_tags(m.group(2))).strip()
        out.append({"label": label or None, "url": url})
    return out


def parse_show_notes(frag: str) -> list[dict]:
    """Parse the #epi_notes block into {timestamp, seconds, topic, links[]} rows.

    The block is loose HTML: a timestamp appears as text ("07:04 – ") and the
    links for it follow, either inline in the same <p> or as <li> children of a
    following <ul>. So rather than trusting the markup, this splits the whole
    fragment on timestamp tokens and attributes every <a> in each span to the
    timestamp that opened it.
    """
    if not frag:
        return []
    # Preserve list-item boundaries as newlines before flattening tags.
    frag = re.sub(r"(?i)</(li|p|ul|div|h\d)>", "\n", frag)
    frag = re.sub(r"(?i)<li[^>]*>", "\n", frag)

    # The separator between a timestamp and its dash may contain markup, not
    # just whitespace: older pages wrap them in separate <span>s
    # ("<span>02:57 </span><span>– </span>"). Allowing tags in between is what
    # makes those pages split into rows instead of collapsing into one.
    # The trailing ':?' covers rows typed as "09:50: – topic" rather than
    # "09:50 – topic"; without it that timestamp stays buried in the previous
    # row's topic text and its links are attributed to the wrong row.
    ts_tok = re.compile(
        r"((?:\d{1,2}:)?\d{1,2}:\d{2}):?(?:<[^>]*>|&nbsp;|\s)*"
        r"(?:&#8211;|&ndash;|&#8212;|–|—|-|&#45;)")
    marks = list(ts_tok.finditer(frag))
    rows = []
    for i, m in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(frag)
        span = frag[m.end(): end]
        links = _links_from_html(span)
        topic = _clean_topic(SL.strip_tags(span))
        ts = m.group(1)
        rows.append({
            "timestamp": ts,
            "seconds": SL.ts_to_seconds(ts),
            "topic": topic,
            "links": links,
        })
    return rows


def _clean_topic(text: str) -> str | None:
    """Tidy a topic string recovered from HTML.

    A single timestamp on the page often heads several <li> bullets, so the
    span for one row spans multiple list items; flattening it leaves embedded
    newlines. Stripping tags also inserts a space on both sides of every
    former element boundary, which shows up as " ," and " :".
    """
    t = re.sub(r"\s+", " ", text)
    t = re.sub(r"\s+([,;:.)\]])", r"\1", t)
    t = re.sub(r"([(\[])\s+", r"\1", t)
    t = re.sub(r"[,;]\s*(?=[,;])", "", t)
    return t.strip(" ,;:–—-") or None


DATE_TOK = (r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)\w*\.?\s+\d{1,2},?\s+\d{4}")


# Chrome that lives in the same region as the prose and must never be mistaken
# for it: player buttons, the channel banner, download links.
BOILERPLATE = {
    "check out this podcast", "listen now", "the great simplification",
    "download transcript", "watch", "youtube", "spotify", "apple music",
    "apple podcasts", "show notes", "view show notes", "share", "subscribe",
}


def _paragraphs(frag: str, min_len: int = 0) -> str:
    """Flatten prose blocks in a fragment into newline-separated plain text.

    Collects <h3> as well as <p>: some older pages put the whole episode
    description in an <h3> with no <p> anywhere near it (episode 46, Vandana
    Shiva). Boilerplate is dropped, because those pages also carry player
    buttons as real <p> elements — without filtering, "Check out this podcast /
    Listen now" wins and becomes the description.
    """
    paras = []
    for m in re.finditer(r"(?is)<(p|h3)[^>]*>(.*?)</\1>", frag):
        t = re.sub(r"\s+", " ", SL.strip_tags(m.group(2))).strip()
        if not t or t.lower().strip(" :.") in BOILERPLATE or len(t) < min_len:
            continue
        paras.append(t)
    if not paras:
        t = re.sub(r"\s+", " ", SL.strip_tags(frag)).strip()
        if t and len(t) >= min_len:
            paras.append(t)
    return "\n".join(paras)


def extract_prose(html: str) -> dict:
    """Pull the Description and the "About <Name>" bios out of a page.

    Essential for the .txt batch: those files contain nothing but transcript, so
    unlike the hand-enriched .md files there is no local description or guest bio
    to fall back on — the page is the only source.

    The body is a flat sequence of <h2 class="wp-block-heading"> sections, so
    each heading's content runs until the next heading.
    """
    out: dict = {}

    # Window the search between the page title and the show-notes heading, so
    # nav and footer prose can never be mistaken for a description. Three page
    # layouts occur and all three must work:
    #   a. <h2 class="wp-block-heading">Description</h2> then paragraphs
    #   b. a plain <h2>Description</h2> with no class      (Frankly 96)
    #   c. no Description heading at all — the prose simply precedes the first
    #      "About <Name>" heading                          (TGS 212)
    start = 0
    m = re.search(r"</h1>", html, re.I)
    if m:
        start = m.end()
    end = len(html)
    m = re.search(r'(?is)<h2[^>]*>\s*Show\s+Notes|id="notes_stop"|id="epi_notes"',
                  html[start:])
    if m:
        end = start + m.start()
    region = html[start:end]

    heads = list(re.finditer(r"(?is)<h2[^>]*>(.*?)</h2>", region))
    bios = []
    # min_len filters residual chrome out of the unlabeled lead section.
    lead = _paragraphs(region[: heads[0].start()] if heads else region, min_len=60)

    for i, h in enumerate(heads):
        label = re.sub(r"\s+", " ", SL.strip_tags(h.group(1))).strip()
        body = region[h.end(): heads[i + 1].start() if i + 1 < len(heads) else len(region)]
        text = _paragraphs(body)
        if not text:
            continue
        # Trailing colon is optional: the older pages write "Show Summary:" and
        # "About DJ White:" where the newer ones write "Description" and
        # "About John Cook". Requiring an exact match missed 12 descriptions.
        label = label.rstrip(":  ")
        if re.match(r"(?i)^(description|show\s+summary|summary|show\s+notes\s+summary)$",
                    label):
            out["description"] = text
        else:
            m = re.match(r"(?i)^about\s+(?:dr\.?\s+)?(.+)$", label)
            if m:
                # Some headings append the episode title to the name, e.g.
                # 'About Arthur Berman: "Shale Oil, the Slurping Sound"'. Cut at
                # the first colon or dash so the name is a name — otherwise the
                # title gets split on its own comma and becomes phantom guests.
                name = re.sub(r"\s+", " ", m.group(1)).strip()
                name = re.split(r"\s*[:–—]\s*|\s+[-–—]\s+", name)[0]
                # The site writes both "About Arthur Berman" and
                # "About Arthur Berman:"; keeping the colon would split one
                # person into two identities.
                name = name.strip().rstrip(":;,.- ").strip('"“”')
                if name:
                    bios.append({"name": name, "bio": text})
    if bios:
        out["guest_bios"] = bios
    # Layout (c): no Description heading, so fall back to the prose that ran
    # before the first heading. Require some length so a stray caption or
    # button label does not become the description.
    if "description" not in out and len(lead) >= 120:
        out["description"] = lead
    return out


def extract_page(html: str) -> dict:
    out: dict = {}
    out.update(extract_prose(html))

    m = re.search(r"<h1[^>]*>(.*?)</h1>", html, re.S | re.I)
    if m:
        out["title"] = SL.n_collapse_ws(SL.strip_tags(m.group(1)), None) or None

    m = re.search(r'<p[^>]*\bid="epi_label"[^>]*>(.*?)</p>', html, re.S | re.I)
    if m:
        out["episode_label"] = SL.n_collapse_ws(SL.strip_tags(m.group(1)), None) or None

    for key, aid in (("youtube_url", "ep_lnk_yt"), ("spotify_url", "ep_lnk_sp"),
                     ("apple_podcasts_url", "ep_lnk_am"), ("podlink_url", "ep_lnk_pl"),
                     ("transcript_pdf_url", "dl_transcript")):
        v = _anchor(html, aid)
        if v:
            out[key] = v

    m = re.search(r'<link[^>]*rel="canonical"[^>]*href="([^"]+)"', html)
    if m:
        out["webpage_url"] = html_mod.unescape(m.group(1))

    meta = _div(html, "class", "post_meta")
    if meta:
        text = SL.strip_tags(meta)
        rm = re.search(rf"(?i)recorded\s+on\s*:?\s*({DATE_TOK})", text)
        if rm:
            out["recorded_date"] = rm.group(1).strip()
        # The publish date is the first date that is NOT the recorded-on one.
        for dm in re.finditer(DATE_TOK, text):
            pre = text[max(0, dm.start() - 30): dm.start()]
            if not re.search(r"(?i)recorded\s+on\s*:?\s*$", pre):
                out["published_date"] = dm.group(0).strip()
                break
        gm = re.search(r"<h3[^>]*>(.*?)</h3>", meta, re.S | re.I)
        if gm:
            g = SL.n_collapse_ws(SL.strip_tags(gm.group(1)), None)
            if g:
                out["guests"] = [g]

    tags = _div(html, "class", "post_tags")
    if tags:
        pills = [SL.n_collapse_ws(SL.strip_tags(p), None)
                 for p in re.findall(r"<span[^>]*>(.*?)</span>", tags, re.S | re.I)]
        pills = [p for p in pills if p]
        if pills:
            out["keywords"] = pills

    notes = _div(html, "id", "epi_notes")
    if notes:
        rows = parse_show_notes(notes)
        if rows:
            out["show_notes"] = rows

    return out


def extract_all() -> dict:
    values = {}
    for f in sorted(CACHE.glob("*.html")):
        values[f.stem] = extract_page(f.read_text(encoding="utf-8"))
    for f in sorted(CACHE.glob("*.yt.json")):
        values.setdefault(f.stem[:-3], {}).update(json.loads(f.read_text(encoding="utf-8")))
    VALUES.write_text(json.dumps(values, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"extracted {len(values)} records -> {VALUES}")
    return values


# --------------------------------------------------------------------------
# stage 2b: YouTube watch pages
# --------------------------------------------------------------------------

YT_MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
             "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def extract_youtube(html: str) -> dict:
    """Pull publish date, title, and duration off a YouTube watch page.

    Needed for the 4-part animated video series, which lives only on YouTube —
    those files have no episode page on thegreatsimplification.com and so no
    other source for a publication date. Duration is picked up for every
    episode because it is free here and useful to have in the database.
    """
    out: dict = {}
    m = re.search(r'"uploadDate":"([0-9]{4})-([0-9]{2})-([0-9]{2})', html)
    if m:
        y, mo, d = m.group(1), int(m.group(2)), int(m.group(3))
        out["published_date"] = f"{YT_MONTHS[mo - 1]} {d}, {y}"
        out["published_date_iso"] = f"{y}-{mo:02d}-{d:02d}"
    m = re.search(r"<title>(.*?)</title>", html, re.S)
    if m:
        t = html_mod.unescape(m.group(1)).strip()
        t = re.sub(r"\s*-\s*YouTube\s*$", "", t)
        if t:
            out["youtube_title"] = t
    m = re.search(r'"lengthSeconds":"(\d+)"', html)
    if m:
        out["duration_seconds"] = int(m.group(1))
    return out


# Title conventions the channel has used for each series, over the years. The
# interview series alone appears as "The Great Simplification #25", "TGS #25",
# and "TGS 211" depending on era, so all forms are checked.
SERIES_TITLE_TOKEN = {
    "interview": ["the great simplification episode", "the great simplification", "tgs"],
    "frankly": ["frankly"],
    "roundtable": ["reality roundtable", "roundtable", "rr"],
}


def _search_candidates(query: str) -> list[tuple[str, str]]:
    """Return [(video_id, title)] from a YouTube search results page."""
    html = get("https://www.youtube.com/results?search_query="
               + urllib.parse.quote_plus(query))
    out: list[tuple[str, str]] = []
    seen: set[str] = set()
    # The title is a JSON string, so it may contain escaped quotes (\") and
    # \uXXXX escapes. Matching [^"]* would truncate at the first escaped quote
    # and silently lop the "| The Great Simplification #24" suffix off exactly
    # the titles being matched on — so consume escapes properly and json-decode.
    pat = re.compile(
        r'"videoId":"([A-Za-z0-9_-]{11})".{0,400}?"text":"((?:[^"\\]|\\.){10,240})"', re.S)
    for m in pat.finditer(html):
        vid, raw = m.group(1), m.group(2)
        try:
            title = json.loads(f'"{raw}"')
        except json.JSONDecodeError:
            title = raw
        if vid not in seen:
            seen.add(vid)
            out.append((vid, title))
    return out


def _within_days(iso_a: str, iso_b: str, days: int) -> bool:
    """True if two ISO dates are within `days` of each other."""
    try:
        a = _dt.date.fromisoformat(iso_a[:10])
        b = _dt.date.fromisoformat(iso_b[:10])
    except (ValueError, TypeError):
        return False
    return abs((a - b).days) <= days


def _title_matches(title: str, series: str, num: int) -> bool:
    """Require the episode number to appear in the video title.

    Guest-name matching alone is not enough: several guests appear on multiple
    episodes and on roundtables too, so a name search happily returns the wrong
    video. The channel's titles carry an explicit '#N' for every series, which
    makes the number the reliable discriminator.
    """
    t = re.sub(r"\s+", " ", title.lower())
    for prefix in SERIES_TITLE_TOKEN.get(series, []):
        # The trailing (?!\d) matters: a plain substring test would let
        # "TGS 240" satisfy a search for episode 24.
        if re.search(rf"\b{re.escape(prefix)}\s*#?\s*0*{num}(?!\d)", t):
            return True
    return False


def search_youtube(records: list[dict], force: bool = False) -> None:
    """Find YouTube videos for episodes whose page carries no YouTube link.

    The older episode pages (roughly TGS 10-27) embed a Libsyn audio player and
    never link the video, so `a#ep_lnk_yt` does not exist there. For those the
    video is located by search and then VERIFIED against the watch page: the
    title must contain the episode number and the channel must be Nate Hagens.
    A candidate that fails either check is discarded rather than guessed at.
    """
    todo = [r for r in records
            if not r.get("youtube_video_id")
            and r.get("episode_number") is not None
            and r.get("series") in SERIES_TITLE_TOKEN
            and (force or not (CACHE / f"{r['record_id']}.yt.json").exists())]
    print(f"{len(todo)} records need a YouTube search")

    for i, rec in enumerate(todo, 1):
        rid, num, series = rec["record_id"], rec["episode_number"], rec["series"]
        guests = " ".join(rec.get("guests") or [])
        label = {"interview": "The Great Simplification", "frankly": "Frankly",
                 "roundtable": "Reality Roundtable"}[series]
        # A ladder of progressively broader queries. The narrow forms come
        # first; the long title-bearing form is last because extra words
        # dilute the query and can push the right video off the first page.
        queries = [
            f"Nate Hagens {label} #{num} {guests}".strip(),
            f"{guests} {label} #{num}".strip(),
            f"Nate Hagens TGS #{num} {guests}".strip(),
            f"Nate Hagens {label} #{num} {guests} {rec.get('title') or ''}".strip(),
        ]
        cands: list = []
        for qi, query in enumerate(queries):
            try:
                cands = _search_candidates(query)
            except Exception as e:  # noqa: BLE001
                print(f"  [{i}/{len(todo)}] SEARCH FAILED {rid}: {e}")
                break
            if any(_title_matches(t, series, num) for _, t in cands):
                break
            if qi < len(queries) - 1:
                time.sleep(2)

        # Rank candidates: an episode-numbered title first, then any title
        # carrying a guest surname. The older episodes (roughly TGS 5-56) title
        # their videos "<Name> on <Topic>" with NO episode number at all, so
        # requiring the number rejected many correct matches outright.
        surnames = [w.lower() for g in (rec.get("guests") or [])
                    for w in re.findall(r"[A-Za-z]{4,}", g)]
        numbered = [(v, t) for v, t in cands if _title_matches(t, series, num)]
        named = [(v, t) for v, t in cands
                 if (v, t) not in numbered
                 and surnames and any(s in t.lower() for s in surnames)]
        expect = rec.get("published_date")

        accepted = None
        for vid, vtitle in (numbered + named)[:6]:
            time.sleep(2)
            try:
                page = get(f"https://www.youtube.com/watch?v={vid}")
            except Exception as e:  # noqa: BLE001
                print(f"       verify fetch failed for {vid}: {e}")
                continue
            # Which key carries the channel varies between served page variants,
            # so check all three rather than relying on any one being present.
            chan = next((m.group(1) for m in (
                re.search(r'"ownerChannelName":"([^"]+)"', page),
                re.search(r'"channelName":"([^"]+)"', page),
                re.search(r'"author":"([^"]+)"', page),
            ) if m), None)
            if not chan or "hagens" not in chan.lower():
                continue

            vals = extract_youtube(page)
            if (vid, vtitle) in numbered:
                how = "search+number"
            else:
                # No number in the title, so corroborate with the publish date
                # the episode page already told us. A guest can have several
                # episodes (Berman has six), and the date is what separates
                # them; without it, a name-only match could pick the wrong one.
                got = vals.get("published_date_iso")
                if not (expect and got and _within_days(got, expect, 14)):
                    continue
                how = "search+name+date"

            vals["youtube_url"] = f"https://www.youtube.com/watch?v={vid}"
            vals["youtube_resolved_by"] = how
            (CACHE / f"{rid}.yt.json").write_text(
                json.dumps(vals, indent=1, ensure_ascii=False), encoding="utf-8")
            print(f"  [{i}/{len(todo)}] {rid} -> {vid} [{how}] | {vtitle[:44]} "
                  f"| {vals.get('published_date_iso')}")
            accepted = vid
            break

        if not accepted:
            print(f"  [{i}/{len(todo)}] NO CONFIDENT MATCH {rid} "
                  f"({len(numbered)} numbered / {len(named)} named candidates; "
                  f"top: {cands[0][1][:44] if cands else 'none'})")
        if i < len(todo):
            time.sleep(2)


def fetch_youtube(records: list[dict], force: bool = False) -> None:
    CACHE.mkdir(parents=True, exist_ok=True)
    todo = []
    for rec in records:
        vid = rec.get("youtube_video_id")
        if not vid:
            continue
        dest = CACHE / f"{rec['record_id']}.yt.json"
        if dest.exists() and not force:
            continue
        todo.append((rec["record_id"], vid, dest))

    print(f"{len(todo)} YouTube pages to fetch")
    for i, (rid, vid, dest) in enumerate(todo, 1):
        try:
            html = get(f"https://www.youtube.com/watch?v={vid}")
            vals = extract_youtube(html)
            dest.write_text(json.dumps(vals, indent=1, ensure_ascii=False), encoding="utf-8")
            print(f"  [{i}/{len(todo)}] {rid} {vid} -> "
                  f"{vals.get('published_date_iso')} {vals.get('duration_seconds')}s")
        except Exception as e:  # noqa: BLE001
            print(f"  [{i}/{len(todo)}] FAILED {rid} {vid}: {e}")
        if i < len(todo):
            time.sleep(2)


# --------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--catalog", action="store_true", help="refresh the REST catalog")
    ap.add_argument("--fetch", action="store_true", help="download missing episode pages")
    ap.add_argument("--youtube", action="store_true",
                    help="download YouTube watch pages for publish date and duration")
    ap.add_argument("--youtube-search", action="store_true",
                    help="find videos by search for episodes whose page has no YouTube link")
    ap.add_argument("--extract", action="store_true", help="parse cached HTML into site_values.json")
    ap.add_argument("--force", action="store_true", help="re-download pages already cached")
    ap.add_argument("--only", help="substring filter on record id")
    args = ap.parse_args()

    if not any((args.catalog, args.fetch, args.youtube, args.youtube_search, args.extract)):
        ap.error("pick at least one of --catalog / --fetch / --youtube / "
                 "--youtube-search / --extract")

    if args.catalog:
        build_catalog()

    def records():
        shape, manifest = SL.load_shape(), SL.load_manifest()
        site_all = json.loads(VALUES.read_text(encoding="utf-8")) if VALUES.exists() else {}
        out = []
        for p in sorted(SL.MD_DIR.glob("*.md")):
            if args.only and args.only.lower() not in p.name.lower():
                continue
            out.append(SL.build_record(p, shape, manifest, site=site_all.get(p.stem, {})))
        return out

    if args.fetch:
        fetch_all(records(), load_catalog(), force=args.force)

    if args.youtube:
        fetch_youtube(records(), force=args.force)

    if args.youtube_search:
        search_youtube(records(), force=args.force)

    if args.extract:
        extract_all()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
