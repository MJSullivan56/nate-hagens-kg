#!/usr/bin/env python3
"""patch_md.py — write the data fetched from the episode pages back into the
hand-enriched .md files, in place.

    python extraction/shape/patch_md.py                 # dry run: report only
    python extraction/shape/patch_md.py --diff          # dry run + unified diffs
    python extraction/shape/patch_md.py --apply         # actually edit the files

Four edits, each independently switchable with --no-<name>:

  nul        Strip stray NUL (0x00) bytes. 24 files carry them as an artifact of
             copy-pasting out of the source PDFs. Python reads them fine, but
             they make grep classify the file as binary and skip it silently —
             which is exactly how 24 of these 57 files went missing from the
             first survey of this corpus. Pure deletion, no text changes.

  labels     Normalize the header metadata lines to one spelling (WEBPAGE:,
             YOUTUBE:) and add whichever are missing. The corpus currently uses
             WEBPAGE:/Webpage:/WEBSITE: interchangeably, and 'Video:' for what
             is really the YouTube link.

  shownotes  Fill in external links on show-notes rows that have none. Eight
             files had their timestamps and topics transcribed by hand but the
             site's hyperlinks were never copied across (444 rows). Rows are
             matched to the page BY TIMESTAMP so the hand-typed topic wording is
             preserved untouched — only links are added, in the indented-bullet
             style already used by Frankly-020.

  meta       Add the label / publish-date / recorded-date / keywords block for
             files that are missing it entirely.

Nothing that the .md already states is ever overwritten: this only fills blanks
and unifies label spelling. Where the page disagrees with an existing .md value,
the .md wins and the disagreement is reported instead (see the shape file's
conflict policy).
"""

from __future__ import annotations

import argparse
import difflib
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import shape_lib as SL  # noqa: E402

HERE = Path(__file__).resolve().parent
CACHE = HERE / "site_cache"
VALUES = CACHE / "site_values.json"

BANNER = "The Great Simplification"
LABEL_ORDER = ["TITLE", "WEBPAGE", "YOUTUBE"]
LABEL_ALIASES = {
    "TITLE": ["TITLE"],
    "WEBPAGE": ["WEBPAGE", "WEBSITE", "PAGE", "URL", "LINK"],
    "YOUTUBE": ["YOUTUBE", "VIDEO"],
}


def load_site() -> dict:
    return json.loads(VALUES.read_text(encoding="utf-8")) if VALUES.exists() else {}


# --------------------------------------------------------------------------
# edit 1: NUL bytes
# --------------------------------------------------------------------------

def edit_nul(text: str) -> tuple[str, list[str]]:
    n = text.count("\x00")
    if not n:
        return text, []
    return text.replace("\x00", ""), [f"stripped {n} NUL byte(s)"]


# --------------------------------------------------------------------------
# edit 2: header label lines
# --------------------------------------------------------------------------

def edit_labels(text: str, rec: dict, site: dict,
                md_only: dict | None = None) -> tuple[str, list[str]]:
    """Normalize label spelling and add missing WEBPAGE:/YOUTUBE: lines.

    The lines are placed immediately after the 'The Great Simplification'
    banner where one exists (the convention in most of the corpus), otherwise
    at the very top.
    """
    lines = text.split("\n")
    notes: list[str] = []

    wanted = {
        "WEBPAGE": rec.get("webpage_url") or site.get("webpage_url"),
        "YOUTUBE": rec.get("youtube_url") or SL.n_youtube_canonical(site.get("youtube_url"), None),
    }
    # Only write a TITLE: line where the .md cannot yield the title on its own.
    # Franklys already fuse it into their label line ("Frankly 151 | Real
    # Title"); RR/TGS carry a bare label ("Reality Roundtable 19") with the
    # title living only on the webpage. `md_only` is the record built without
    # any site input, so an empty title there means the .md genuinely lacks one.
    if site.get("title") and not (md_only or {}).get("title"):
        wanted["TITLE"] = site["title"]

    # Rewrite existing label lines to the canonical spelling; drop duplicates.
    present: set[str] = set()
    out: list[str] = []
    for line in lines:
        m = re.match(r"^\s*([A-Za-z][A-Za-z ]{2,20}?)\s*:\s*(\S.*)?$", line)
        canon = None
        if m:
            key = re.sub(r"\s+", " ", m.group(1).strip()).upper()
            for c, aliases in LABEL_ALIASES.items():
                if key in aliases:
                    canon = c
                    break
        if canon is None:
            out.append(line)
            continue

        val = (m.group(2) or "").strip()
        # A 'Video:'/'VIDEO:' line only counts as YOUTUBE if it really is one.
        if canon == "YOUTUBE" and val and not SL.youtube_id(val):
            out.append(line)
            continue
        if canon == "WEBPAGE" and val and SL.youtube_id(val) and rec.get("series") == "video":
            # The animated-series files legitimately point WEBPAGE: at YouTube.
            out.append(line)
            present.add("WEBPAGE")
            continue

        target = wanted.get(canon) or val
        if canon in present or not target:
            if not target:
                notes.append(f"dropped empty {canon}: line")
            continue
        newline = f"{canon}: {target}"
        if newline != line:
            notes.append(f"{canon}: normalized/filled")
        out.append(newline)
        present.add(canon)

    # Insert any still-missing labels after the banner.
    missing = [c for c in LABEL_ORDER if c not in present and wanted.get(c)]
    if missing:
        # Prefer to sit directly below the label lines already present, so the
        # block reads WEBPAGE then YOUTUBE; otherwise fall in below the banner.
        anchor = None
        for i, l in enumerate(out[:12]):
            if re.match(rf"^({'|'.join(LABEL_ORDER)}):", l):
                anchor = i
        if anchor is None:
            anchor = next((i for i, l in enumerate(out) if l.strip() == BANNER), None)
        if anchor is None:
            anchor = next((i for i, l in enumerate(out) if l.strip()), 0) - 1
        ins = anchor + 1
        for c in missing:
            out.insert(ins, f"{c}: {wanted[c]}")
            ins += 1
            notes.append(f"added {c}: line")

    return "\n".join(out), notes


# --------------------------------------------------------------------------
# edit 3: show-notes links
# --------------------------------------------------------------------------

def _site_rows_by_seconds(site: dict) -> dict[int, dict]:
    idx: dict[int, dict] = {}
    for r in site.get("show_notes") or []:
        if r.get("seconds") is not None:
            idx.setdefault(r["seconds"], r)
    return idx


def _match(sec: int | None, idx: dict[int, dict], tol: int = 3) -> dict | None:
    """Match a hand-typed timestamp to a page row, exact first then within
    `tol` seconds (hand transcription is occasionally a second or two off)."""
    if sec is None:
        return None
    if sec in idx:
        return idx[sec]
    near = [s for s in idx if abs(s - sec) <= tol]
    return idx[min(near, key=lambda s: abs(s - sec))] if near else None


def edit_shownotes(text: str, rec: dict, site: dict) -> tuple[str, list[str]]:
    """Append links to linkless show-notes lines, matched by timestamp.

    Only touches the plain-line layouts ('MM:SS - topic'). Markdown-table
    layouts are left alone: those were curated by hand and, per the conflict
    policy, the .md wins there.
    """
    if rec.get("show_notes_layout") not in ("lines-only", "lines+links"):
        return text, []
    idx = _site_rows_by_seconds(site)
    if not idx:
        return text, []

    lines = text.split("\n")
    out: list[str] = []
    filled = unmatched = 0
    i = 0
    while i < len(lines):
        line = lines[i]
        out.append(line)
        m = SL.TS_RE.match(line)
        if not m or line.lstrip().startswith("|") or line.startswith(("    ", "\t")):
            i += 1
            continue

        # Collect the block of continuation lines that belong to this row.
        j = i + 1
        block: list[str] = []
        while j < len(lines) and lines[j].strip() and not SL.TS_RE.match(lines[j]):
            block.append(lines[j])
            j += 1

        row = _match(SL.ts_to_seconds(m.group(1)), idx)

        # Dedupe on the RENDERED LINE, not on a parsed URL. The URL regexes stop
        # at the first ")", so a link like
        # ".../wiki/Coupling_(physics)" round-trips as a truncated string and a
        # URL-based check would think it absent — making --apply re-append the
        # same bullet on every run. Comparing the exact line is exact.
        present_lines = {l.strip() for l in block}
        present_urls = set(SL.BARE_URL_RE.findall(line + "\n" + "\n".join(block)))
        add = []
        for l in (row or {}).get("links", []):
            rendered = f"      - [{l.get('label') or 'link'}]({l['url']})"
            if rendered.strip() in present_lines or l["url"] in present_urls:
                continue
            present_lines.add(rendered.strip())
            add.append(rendered)

        out.extend(block)
        if row is None:
            unmatched += 1
        elif add:
            out.extend(add)
            filled += 1
        i = j

    notes = []
    if filled:
        notes.append(f"added links to {filled} show-notes row(s)")
    if unmatched:
        notes.append(f"{unmatched} row(s) had no matching timestamp on the page")
    return "\n".join(out), notes


# --------------------------------------------------------------------------
# edit 4: missing meta block
# --------------------------------------------------------------------------

def edit_meta(text: str, rec: dict, site: dict) -> tuple[str, list[str]]:
    """Add the label/date/recorded/keywords block when a file lacks it.

    Written in the same visual form the rest of the corpus uses (which is what
    a copy-paste off the page's .post_meta panel produces), so these files end
    up looking like their siblings rather than carrying a new convention.
    """
    # Idempotence guard: bail if this file already carries either form of the
    # metadata (a "Recorded on" block, or the PUBLISHED: line written below).
    # Without the PUBLISHED: half of this check, re-running --apply appends a
    # second identical line to the video files every time.
    if re.search(r"(?i)recorded\s+on", text) or re.search(r"(?im)^PUBLISHED\s*:", text):
        return text, []
    if not site:
        return text, []

    label = rec.get("episode_label") or site.get("episode_label")
    pub = site.get("published_date")
    recd = site.get("recorded_date")
    kws = site.get("keywords") or []
    if not (label or pub or recd or kws):
        return text, []

    if not label and not recd and not kws and pub:
        # Only a publish date is available and there is no episode label to
        # anchor it (the animated video series). A bare floating date above the
        # transcript would read as noise, so label it and put it in the header
        # block with the other metadata lines instead.
        lines = text.split("\n")
        anchor = None
        for i, l in enumerate(lines[:12]):
            if re.match(rf"^({'|'.join(LABEL_ORDER)}):", l):
                anchor = i
        if anchor is None:
            anchor = next((i for i, l in enumerate(lines) if l.strip() == BANNER), 0)
        lines.insert(anchor + 1, f"PUBLISHED: {pub}")
        return "\n".join(lines), ["added PUBLISHED: line"]

    block = []
    if label:
        block.append(label)
    if pub:
        block.append(pub)
    if recd:
        block += ["", "Recorded on:", recd]
    if kws:
        block.append("KEYWORDS: " + ", ".join(kws))

    # Place it just above the transcript marker, where the corpus puts it.
    marks = list(SL.TRANSCRIPT_RE.finditer(text))
    ins_at = marks[-1].start() if marks else len(text)
    patched = text[:ins_at].rstrip("\n") + "\n\n" + "\n".join(block) + "\n\n" + text[ins_at:]
    return patched, [f"added meta block ({len(block)} line(s))"]


# --------------------------------------------------------------------------

EDITS = ["nul", "labels", "shownotes", "meta"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="write changes to disk")
    ap.add_argument("--diff", action="store_true", help="print unified diffs")
    ap.add_argument("--only", help="substring filter on filename")
    for e in EDITS:
        ap.add_argument(f"--no-{e}", action="store_true", help=f"skip the '{e}' edit")
    args = ap.parse_args()

    shape = SL.load_shape()
    manifest = SL.load_manifest()
    site_all = load_site()
    enabled = [e for e in EDITS if not getattr(args, f"no_{e}")]

    files = sorted(p for p in SL.MD_DIR.glob("*.md")
                   if not args.only or args.only.lower() in p.name.lower())
    changed = 0
    total_notes: list[tuple[str, list[str]]] = []

    for p in files:
        site = site_all.get(p.stem, {})
        rec = SL.build_record(p, shape, manifest, site=site)
        # Same record built with no site input, so the patcher can tell what the
        # .md can already produce unaided from what only the webpage supplies.
        md_only = SL.build_record(p, shape, manifest)
        original = p.read_bytes().decode("utf-8")
        text = original
        notes: list[str] = []

        if "nul" in enabled:
            text, n = edit_nul(text)
            notes += n
        if "labels" in enabled:
            text, n = edit_labels(text, rec, site, md_only)
            notes += n
        if "shownotes" in enabled:
            text, n = edit_shownotes(text, rec, site)
            notes += n
        if "meta" in enabled:
            text, n = edit_meta(text, rec, site)
            notes += n

        if text == original:
            continue
        changed += 1
        total_notes.append((p.name, notes))

        if args.diff:
            print(f"\n{'='*78}\n{p.name}\n{'='*78}")
            for dl in difflib.unified_diff(
                    original.split("\n"), text.split("\n"),
                    fromfile=f"a/{p.name}", tofile=f"b/{p.name}", lineterm="", n=1):
                print(dl)
        if args.apply:
            p.write_text(text, encoding="utf-8")

    print(f"\n{'APPLIED' if args.apply else 'DRY RUN'} — {changed}/{len(files)} files "
          f"would change (edits enabled: {', '.join(enabled)})")
    for name, notes in total_notes:
        print(f"  {name[:56]:56} {'; '.join(notes)}")
    if not args.apply and changed:
        print("\nre-run with --apply to write these changes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
