#!/usr/bin/env python3
"""build_episodes.py — turn the hand-enriched .md transcripts into shaped
YAML/JSON records, and report what is still missing.

    python extraction/shape/build_episodes.py --report
    python extraction/shape/build_episodes.py --out extraction/shape/out --format yaml
    python extraction/shape/build_episodes.py --out ... --with-transcript

Only .md files are read; the .txt files in transcripts_text_cache/ are
un-enriched raw dumps and are deliberately ignored.

If site_cache/ holds pages fetched by fetch_episode_pages.py, their values are
merged in to fill gaps — the .md always wins on conflict (see the shape's
conflict policy).
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import shape_lib as SL  # noqa: E402

REQUIRED_ORDER = ["title", "webpage_url", "youtube_url", "published_date", "description"]


def load_site_cache(cache_dir: Path) -> dict:
    f = cache_dir / "site_values.json"
    if not f.exists():
        return {}
    return json.loads(f.read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--md-dir", type=Path, default=SL.MD_DIR)
    ap.add_argument("--shape", type=Path, default=SL.SHAPE_PATH)
    ap.add_argument("--site-cache", type=Path, default=Path(__file__).resolve().parent / "site_cache")
    ap.add_argument("--out", type=Path, help="directory to write shaped records into")
    ap.add_argument("--format", choices=["yaml", "json"], default="yaml")
    ap.add_argument("--with-transcript", action="store_true",
                    help="include full transcript text and parsed speaker turns")
    ap.add_argument("--report", action="store_true", help="print the gap report")
    ap.add_argument("--gap-csv", type=Path, help="write the gap report as CSV")
    ap.add_argument("--only", help="substring filter on filename")
    args = ap.parse_args()

    shape = SL.load_shape(args.shape)
    manifest = SL.load_manifest()
    site_all = load_site_cache(args.site_cache)

    files = sorted(p for p in args.md_dir.glob("*.md")
                   if not args.only or args.only.lower() in p.name.lower())
    if not files:
        print(f"no .md files matched under {args.md_dir}", file=sys.stderr)
        return 1

    records, gap_rows = [], []
    for p in files:
        site = site_all.get(p.stem, {})
        rec = SL.build_record(p, shape, manifest, site=site)
        records.append(rec)
        gap_rows.append({
            "record_id": rec.get("record_id"),
            "series": rec.get("series"),
            "episode_number": rec.get("episode_number"),
            "missing_required": ";".join(rec.get("_gaps", [])),
            "show_notes_rows": len(rec.get("show_notes") or []),
            "show_notes_layout": rec.get("show_notes_layout") or "",
            "show_notes_rows_without_links": sum(
                1 for r in (rec.get("show_notes") or []) if not r.get("links")),
            "guests": len(rec.get("guests") or []),
            "keywords": ";".join(rec.get("keywords") or []),
            "transcript_turns": len(rec.get("transcript_turns") or []),
            "had_nul_bytes": rec.get("had_nul_bytes"),
            "site_divergence": ";".join((rec.get("_site_divergence") or {}).keys()),
            "confirmed_absent": ";".join((rec.get("_confirmed_absent") or {}).keys()),
        })

    if args.out:
        args.out.mkdir(parents=True, exist_ok=True)
        ext = "yaml" if args.format == "yaml" else "json"
        for rec in records:
            (args.out / f"{rec['record_id']}.{ext}").write_text(
                SL.emit(rec, args.format, args.with_transcript), encoding="utf-8")
        print(f"wrote {len(records)} records to {args.out} as .{ext}")

    if args.gap_csv:
        args.gap_csv.parent.mkdir(parents=True, exist_ok=True)
        with open(args.gap_csv, "w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(gap_rows[0].keys()))
            w.writeheader()
            w.writerows(gap_rows)
        print(f"wrote gap report to {args.gap_csv}")

    if args.report:
        print_report(records, gap_rows)
    return 0


def print_report(records, gap_rows) -> None:
    n = len(records)
    print(f"\n{'='*78}\nSHAPED {n} MARKDOWN EPISODE RECORDS\n{'='*78}")

    print("\nField coverage (required fields first):")
    fieldnames = [f for f in REQUIRED_ORDER] + [
        "episode_label", "recorded_date", "keywords", "guests", "show_notes",
        "transcript", "spotify_url", "transcript_pdf_url",
    ]
    for f in fieldnames:
        have = sum(1 for r in records if r.get(f))
        bar = "#" * round(28 * have / n)
        flag = "  <-- GAP" if f in REQUIRED_ORDER and have < n else ""
        print(f"  {f:22} {have:2}/{n}  {bar:<28}{flag}")

    absent = [g for g in gap_rows if g["confirmed_absent"]]
    print(f"\nFields CONFIRMED ABSENT at the source (checked, genuinely not there): {len(absent)}")
    for g in absent:
        print(f"  {g['record_id'][:52]:52} {g['confirmed_absent']}")

    print("\nRecords with missing REQUIRED fields (still open):")
    any_gap = False
    for g in gap_rows:
        if g["missing_required"]:
            any_gap = True
            print(f"  {g['record_id'][:52]:52} {g['missing_required']}")
    if not any_gap:
        print("  (none)")

    print("\nShow-notes layout distribution:")
    from collections import Counter
    for lay, c in Counter(g["show_notes_layout"] or "(none)" for g in gap_rows).most_common():
        print(f"  {lay:14} {c:3} files")

    print("\nShow-notes rows lacking any external link (the link gap):")
    tot = 0
    for g in sorted(gap_rows, key=lambda x: -x["show_notes_rows_without_links"]):
        if g["show_notes_rows_without_links"]:
            tot += g["show_notes_rows_without_links"]
            print(f"  {g['record_id'][:52]:52} {g['show_notes_rows_without_links']:3}"
                  f" of {g['show_notes_rows']:3}  [{g['show_notes_layout']}]")
    print(f"  TOTAL linkless rows: {tot}")

    nul = [g["record_id"] for g in gap_rows if g["had_nul_bytes"]]
    print(f"\nFiles containing stray NUL bytes: {len(nul)}")
    print("  (harmless to Python, but makes grep treat them as binary and skip them)")

    div = [g for g in gap_rows if g["site_divergence"]]
    print(f"\nRecords where the site disagrees with the .md: {len(div)}")
    for g in div:
        print(f"  {g['record_id'][:52]:52} {g['site_divergence']}")


if __name__ == "__main__":
    raise SystemExit(main())
