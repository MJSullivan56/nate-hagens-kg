#!/usr/bin/env python3
"""txt_pipeline.py — build episode records from the transcript-only .txt files.

    # 1. resolve filenames to episode pages (offline, instant, no network)
    python extraction/shape/txt_pipeline.py --resolve-report
    python extraction/shape/txt_pipeline.py --resolve-csv extraction/shape/txt_resolution.csv

    # 2. pilot: pick a reproducible random sample and run it end to end
    python extraction/shape/txt_pipeline.py --pilot 10 --seed 20260821 --run

    # 3. the whole batch, once the pilot looks right
    python extraction/shape/txt_pipeline.py --all --run

How this differs from the .md pipeline, and why the scripts needed revising:

  * A .txt has NO metadata — no URL, title, date, keyword, show note, or guest.
    Everything except the transcript must come from the episode page, so the
    "the .md wins, the site fills gaps" conflict policy has nothing to arbitrate
    here: the site is the only source. The one thing the file does carry is the
    transcript, and that stays authoritative.

  * The .md files told us their own URL. A .txt does not, so the filename has to
    be matched against the site catalog — and the filename's episode number is
    wrong often enough that matching needs real care. See resolve.py.

  * Description and guest bios now have to be scraped from the page (they were
    read out of the .md before), which is why fetch_episode_pages.extract_prose
    exists.

The pilot exists because resolution is the risky part. Ten fetched pages let you
check that the resolver picked the right episode before committing to 301
requests at a 10-second crawl delay (roughly 50 minutes).
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import fetch_episode_pages as FP  # noqa: E402
import resolve as RS  # noqa: E402
import shape_lib as SL  # noqa: E402

CACHE = FP.CACHE
TXT_VALUES = CACHE / "txt_site_values.json"
TXT_RESOLUTION = CACHE / "txt_resolution.json"


def txt_files(md_dir: Path = SL.MD_DIR) -> list[Path]:
    return sorted(md_dir.glob("*.txt"))


# --------------------------------------------------------------------------
# stage 1: resolution (offline)
# --------------------------------------------------------------------------

def resolve_all(files: list[Path]) -> list[RS.Resolution]:
    catalog = FP.load_catalog()
    index = RS.build_index(catalog)
    overrides = RS.load_overrides()
    res = [RS.resolve(str(f), catalog, index, overrides) for f in files]
    # Two transcripts must never claim the same episode page.
    return RS.resolve_collisions(res, catalog, index)


def resolution_report(res: list[RS.Resolution]) -> None:
    from collections import Counter
    n = len(res)
    print(f"\n{'='*78}\nRESOLVED {n} TRANSCRIPT-ONLY .txt FILES TO EPISODE PAGES\n{'='*78}")
    print("\nconfidence:", dict(Counter(r.confidence for r in res)))
    print("method    :", dict(Counter(r.method for r in res)))

    flagged = [r for r in res if r.notes]
    print(f"\nFlagged for review ({len(flagged)}). Anything wrong here should go "
          f"into manual_overrides.yaml:")
    for r in flagged:
        print(f"\n  {r.parsed.filename}")
        print(f"    -> {r.slug or '(unresolved)'}  [{r.method}/{r.confidence}]")
        for note in r.notes:
            print(f"       {note}")


def resolution_csv(res: list[RS.Resolution], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["filename", "filename_series", "filename_number", "filename_name",
                    "resolved_slug", "resolved_number", "resolved_title",
                    "method", "confidence", "score", "url", "notes"])
        for r in res:
            w.writerow([r.parsed.filename, r.parsed.series, r.parsed.number,
                        r.parsed.name_part, r.slug, r.catalog_number, r.catalog_title,
                        r.method, r.confidence, r.score, r.url, " | ".join(r.notes)])
    print(f"wrote {len(res)} rows to {path}")


# --------------------------------------------------------------------------
# stage 2: fetch + extract
# --------------------------------------------------------------------------

def fetch_for(res: list[RS.Resolution], force: bool = False) -> None:
    """Fetch each resolved episode page into the shared HTML cache.

    Cached under the transcript's own stem so a .txt and a .md that happen to
    cover the same episode do not collide, and so a re-run of the pilot costs
    nothing.
    """
    CACHE.mkdir(parents=True, exist_ok=True)
    todo = []
    for r in res:
        if not r.url:
            print(f"  SKIP (unresolved) {r.parsed.filename}")
            continue
        dest = CACHE / f"txt__{r.parsed.stem}.html"
        if dest.exists() and not force:
            # The cache is keyed by TRANSCRIPT, not by URL, so a changed
            # resolution (a new manual override, or collision re-resolution)
            # would otherwise keep serving the page for the OLD episode
            # indefinitely. Compare the cached page's canonical URL and re-fetch
            # when it no longer matches.
            cached = FP.extract_page(dest.read_text(encoding="utf-8")).get("webpage_url")
            if not cached or cached.rstrip("/") == r.url.rstrip("/"):
                continue
            print(f"  STALE {r.parsed.filename[:44]:44} cached {cached.rsplit('/', 1)[-1]}"
                  f" != resolved {r.slug} — re-fetching")
            # Any YouTube data was derived from the wrong page too.
            (CACHE / f"txt__{r.parsed.stem}.yt.json").unlink(missing_ok=True)
        todo.append((r, dest))

    print(f"{len(todo)} pages to fetch (crawl-delay {FP.CRAWL_DELAY}s "
          f"— about {len(todo) * FP.CRAWL_DELAY // 60} min)")
    for i, (r, dest) in enumerate(todo, 1):
        try:
            dest.write_text(FP.get(r.url), encoding="utf-8")
            print(f"  [{i}/{len(todo)}] {r.parsed.filename[:46]:46} <- {r.slug}")
        except Exception as e:  # noqa: BLE001
            print(f"  [{i}/{len(todo)}] FAILED {r.parsed.filename}: {e}")
        if i < len(todo):
            import time
            time.sleep(FP.CRAWL_DELAY)


def extract_for(res: list[RS.Resolution]) -> dict:
    """Parse cached HTML into site_values, MERGING into what is already there.

    Must merge, not replace: `res` is whatever the current invocation was scoped
    to, so a filtered run (`--only`, `--pilot`) would otherwise truncate the
    shared file down to its own handful of records and silently strip the rest.
    """
    values = (json.loads(TXT_VALUES.read_text(encoding="utf-8"))
              if TXT_VALUES.exists() else {})
    before = len(values)
    for r in res:
        f = CACHE / f"txt__{r.parsed.stem}.html"
        if not f.exists():
            continue
        v = FP.extract_page(f.read_text(encoding="utf-8"))
        yt = CACHE / f"txt__{r.parsed.stem}.yt.json"
        if yt.exists():
            v.update(json.loads(yt.read_text(encoding="utf-8")))
        v["_resolved_slug"] = r.slug
        v["_resolved_by"] = f"{r.method}/{r.confidence}"
        values[r.parsed.filename] = v
    TXT_VALUES.write_text(json.dumps(values, indent=1, ensure_ascii=False),
                          encoding="utf-8")
    print(f"extracted {len(res)} pages; site_values now holds "
          f"{len(values)} records (was {before}) -> {TXT_VALUES}")
    return values


def fetch_youtube_for(res: list[RS.Resolution], values: dict, force: bool = False) -> None:
    """Fetch each episode's YouTube page for publish date and duration.

    Where the page carries no video link at all — true of the older episodes,
    which embed a Libsyn audio player instead — fall back to the verified search
    used for the .md batch: locate by search, then confirm the video's title
    carries the episode number and the channel is Nate Hagens.
    """
    import time
    todo, need_search = [], []
    for r in res:
        v = values.get(r.parsed.filename) or {}
        dest = CACHE / f"txt__{r.parsed.stem}.yt.json"
        if dest.exists() and not force:
            continue
        vid = SL.youtube_id(v.get("youtube_url"))
        if vid:
            todo.append((r, vid, dest))
        elif r.catalog_number is not None:
            need_search.append((r, dest))

    print(f"{len(todo)} YouTube pages to fetch, {len(need_search)} needing search")
    for i, (r, vid, dest) in enumerate(todo, 1):
        try:
            vals = FP.extract_youtube(FP.get(f"https://www.youtube.com/watch?v={vid}"))
            dest.write_text(json.dumps(vals, indent=1, ensure_ascii=False),
                            encoding="utf-8")
            print(f"  [{i}/{len(todo)}] {r.parsed.filename[:44]:44} {vid} "
                  f"{vals.get('duration_seconds')}s")
        except Exception as e:  # noqa: BLE001
            print(f"  [{i}/{len(todo)}] FAILED {r.parsed.filename}: {e}")
        if i < len(todo):
            time.sleep(2)

    for i, (r, dest) in enumerate(need_search, 1):
        v = values.get(r.parsed.filename) or {}
        series = r.parsed.series or "interview"
        # Reuse the .md batch's verified-search path by handing it a record-like
        # dict; it re-verifies title number and channel before accepting.
        # published_date lets the searcher corroborate a name-only title match
        # (the older videos carry no episode number in their titles).
        fake = {"record_id": f"txt__{r.parsed.stem}", "series": series,
                "episode_number": r.catalog_number, "title": v.get("title"),
                "guests": ([b["name"] for b in (v.get("guest_bios") or [])]
                           or v.get("guests") or []),
                "published_date": SL.n_to_iso_date(v.get("published_date"), None)}
        FP.search_youtube([fake], force=force)


def _merge_searched_yt(res: list[RS.Resolution]) -> None:
    """search_youtube writes to <record_id>.yt.json; it already uses the
    txt__ prefix here, so nothing to move — this just reports what landed."""
    found = sum(1 for r in res if (CACHE / f"txt__{r.parsed.stem}.yt.json").exists())
    print(f"YouTube data present for {found}/{len(res)} pilot records")


# --------------------------------------------------------------------------
# stage 3: build records
# --------------------------------------------------------------------------

def build(res: list[RS.Resolution], values: dict, out: Path | None,
          fmt: str = "yaml", with_transcript: bool = False) -> list[dict]:
    shape = SL.load_shape()
    manifest = SL.load_manifest()
    overrides = RS.load_overrides()
    records = []
    for r in res:
        site = dict(values.get(r.parsed.filename) or {})
        # The resolver, not the file, is what knows this transcript's URL.
        if r.url:
            site.setdefault("webpage_url", r.url)
        # A hand-supplied YouTube URL wins over anything scraped or searched.
        # Needed because ~27 older episodes have no video link on their page and
        # cannot be found by search: the channel hosts several short CLIPS per
        # episode, uploaded months later, which crowd out the full episode. The
        # date check correctly refuses those, so a human supplies the real one.
        ov = overrides.get(r.parsed.filename) or {}
        if ov.get("youtube_url"):
            site["youtube_url"] = ov["youtube_url"]
        rec = SL.build_record(SL.MD_DIR / r.parsed.filename, shape, manifest, site=site)

        # The RESOLVED number is authoritative, not the filename's. build_record
        # falls back to the filename for a .txt (there is no meta block to read),
        # but that number is exactly what cannot be trusted here — eleven
        # filenames point at the wrong episode. Leaving it would put two records
        # at "episode 46" (Ophuls is really 47) and silently corrupt any
        # number-keyed join downstream.
        if r.catalog_number is not None and rec.get("episode_number") != r.catalog_number:
            rec["_filename_episode_number"] = rec.get("episode_number")
            rec["episode_number"] = r.catalog_number
            rec.setdefault("_provenance", {})["episode_number"] = \
                f"resolved:{r.method} (filename said {rec['_filename_episode_number']})"

        # Hand-supplied values applied last so nothing derived can overwrite
        # them. These live in the git-tracked override file precisely because
        # this output directory is gitignored and wiped on every rebuild.
        if ov.get("podcast_mp3_url"):
            rec["podcast_mp3_url"] = ov["podcast_mp3_url"]
            rec.setdefault("_provenance", {})["podcast_mp3_url"] = "manual_override"
        if ov.get("series"):
            rec["series"] = ov["series"]
            rec.setdefault("_provenance", {})["series"] = "manual_override"

        rec["_resolution"] = {"slug": r.slug, "method": r.method,
                              "confidence": r.confidence, "url": r.url,
                              "notes": r.notes}
        records.append(rec)
    if out:
        # Wipe first: record_id changed once (".docx" is now stripped), and
        # stale files from a previous naming scheme would otherwise linger and
        # look like extra records.
        if out.exists():
            shutil.rmtree(out)
        out.mkdir(parents=True, exist_ok=True)
        ext = "yaml" if fmt == "yaml" else "json"
        for rec in records:
            (out / f"{rec['record_id']}.{ext}").write_text(
                SL.emit(rec, fmt, with_transcript), encoding="utf-8")
        print(f"wrote {len(records)} records to {out} as .{ext}")
    return records


def _same_person(a: str, b: str) -> bool:
    """Do two name strings plausibly denote the same person?

    Must be fuzzy, not substring. The page and the transcript routinely disagree
    on the form of a name — "Arthur Berman" vs "Art Berman", "William E. Rees"
    vs "William Rees" — and neither is a substring of the other, so a substring
    test reports a mismatch for what is obviously one person. A shared surname
    plus a compatible first name is the reliable signal.
    """
    # Honorifics are not part of the name. The transcript says "Professor Steve
    # Keen" where the page says "Steve Keen"; without stripping these, the
    # first-name comparison sees "professor" vs "steve" and reports a mismatch.
    HONORIFICS = {"dr", "drs", "prof", "professor", "mr", "mrs", "ms", "miss",
                  "sir", "dame", "rev", "reverend", "hon", "honorable", "phd",
                  "md", "jr", "sr", "the"}

    def toks(x):
        return [t for t in re.findall(r"[a-z]+", (x or "").lower())
                if len(t) > 1 and t not in HONORIFICS]
    ta, tb = toks(a), toks(b)
    if not ta or not tb:
        return False
    na, nb = "".join(ta), "".join(tb)
    if na == nb or RS.name_similarity(na, nb) >= 0.8:
        return True
    # Same surname, and one first name is a prefix of the other (Art/Arthur).
    if ta[-1] == tb[-1]:
        fa, fb = ta[0], tb[0]
        return fa == fb or fa.startswith(fb) or fb.startswith(fa)
    return False


def verify_guest_vs_speakers(records: list[dict]) -> list[dict]:
    """Independently check each resolution by comparing the two sources.

    The strongest available verification, and it costs nothing: the episode PAGE
    names the guest, and the TRANSCRIPT names its own speakers. Those are
    completely independent of the filename that drove the resolution, so if they
    agree, the page really does belong to this transcript.

    This is what makes an off-by-one safe to accept automatically:
    TGS-060-JonathanHaidt resolves to episode 59, and the transcript's speaker
    really is Jonathan Haidt — so 59 is right and the filename's 060 is wrong.
    A disagreement means the wrong page was fetched; treat it as a resolution
    bug, not a data quirk.
    """
    def norm(s):
        return re.sub(r"[^a-z]", "", (s or "").lower())

    out = []
    for r in records:
        guests = r.get("guests") or []
        speakers = [s for s in (r.get("transcript_speakers") or []) if s]
        host = norm(r.get("host") or "")
        non_host = [s for s in speakers if norm(s) != host]
        detail = ""
        if guests and non_host:
            hit = any(_same_person(g, s) for g in guests for s in non_host)
            verdict = "agree" if hit else "DISAGREE"
        else:
            # No guest to match on — true of every solo Frankly, which is about
            # a third of this batch. Fall back to comparing the page's TITLE
            # against the transcript text: still two independent sources, since
            # neither derives from the filename that drove the resolution.
            verdict, detail = _verify_by_title(r)
        out.append({"record_id": r["record_id"], "verdict": verdict,
                    "guests": guests, "speakers": non_host, "detail": detail,
                    "slug": r["_resolution"]["slug"]})
    return out


STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "in", "on", "for", "to", "with", "is",
    "are", "was", "were", "it", "its", "as", "at", "by", "from", "that", "this",
    "what", "why", "how", "we", "our", "you", "your", "not", "but", "about",
    "part", "frankly", "great", "simplification", "nate", "hagens", "news",
}


def _verify_by_title(rec: dict) -> tuple[str, str]:
    """Check a guest-less episode by looking for the page title's distinctive
    words in the transcript body.

    Weaker than the guest check and deliberately reported as its own verdict:
    a title can legitimately use words the speaker never says. A LOW score is a
    prompt to look, not proof of a mis-resolution.
    """
    title = rec.get("title") or ""
    body = (rec.get("transcript") or "")[:60000].lower()
    if not title or not body:
        return "unverifiable", "no title or no transcript"
    words = {w for w in re.findall(r"[a-z]{4,}", title.lower()) if w not in STOPWORDS}
    if not words:
        return "unverifiable", "title has no distinctive words"
    hits = {w for w in words if w in body}
    frac = len(hits) / len(words)
    label = ("title-agree" if frac >= 0.5
             else "title-weak" if frac >= 0.25
             else "TITLE-MISMATCH")
    return label, (f"{len(hits)}/{len(words)} title words in transcript "
                   f"({', '.join(sorted(hits)) or 'none'})")


def record_report(records: list[dict]) -> None:
    n = len(records)
    print(f"\n{'='*78}\nSHAPED {n} .txt RECORDS\n{'='*78}")
    fields = ["title", "webpage_url", "youtube_url", "published_date", "recorded_date",
              "description", "keywords", "guests", "guest_bios", "show_notes",
              "duration_seconds", "spotify_url", "transcript", "transcript_turns"]
    print("\nField coverage:")
    for f in fields:
        have = sum(1 for r in records if r.get(f))
        bar = "#" * round(28 * have / n) if n else ""
        print(f"  {f:18} {have:3}/{n}  {bar}")

    links = sum(len(row.get("links") or [])
                for r in records for row in (r.get("show_notes") or []))
    rows = sum(len(r.get("show_notes") or []) for r in records)
    turns = sum(len(r.get("transcript_turns") or []) for r in records)
    print(f"\nshow-notes rows: {rows}   external links: {links}   "
          f"transcript turns: {turns}")

    checks = verify_guest_vs_speakers(records)
    from collections import Counter
    print("\nRESOLUTION VERIFICATION — page's guest vs transcript's own speakers")
    print("  (independent of the filename, so agreement confirms the right page)")
    for v, c in Counter(x["verdict"] for x in checks).most_common():
        print(f"    {v:20} {c}")
    bad = [x for x in checks if x["verdict"] in ("DISAGREE", "TITLE-MISMATCH")]
    if bad:
        print("  MISMATCHES — likely wrong page; fix via manual_overrides.yaml:")
        for x in bad:
            print(f"    [{x['verdict']}] {x['record_id'][:44]:44} slug={x['slug']}")
            if x["guests"]:
                print(f"       page guest(s):  {x['guests']}")
                print(f"       transcript say: {x['speakers']}")
            if x["detail"]:
                print(f"       {x['detail']}")

    print("\nPer-record detail (confirm the resolution is the right episode):")
    for r in records:
        print(f"\n  {r['record_id'][:60]}")
        print(f"    resolved  {r['_resolution']['slug']} "
              f"[{r['_resolution']['method']}/{r['_resolution']['confidence']}]")
        print(f"    title     {(r.get('title') or '(none)')[:66]}")
        print(f"    dates     pub={r.get('published_date')} rec={r.get('recorded_date')} "
              f"dur={r.get('duration_seconds')}s")
        print(f"    guests    {r.get('guests')}")
        print(f"    keywords  {r.get('keywords')}")
        print(f"    notes     {len(r.get('show_notes') or [])} rows, "
              f"{sum(len(x.get('links') or []) for x in (r.get('show_notes') or []))} links")
        print(f"    turns     {len(r.get('transcript_turns') or [])} "
              f"speakers={r.get('transcript_speakers')}")
        if r.get("_gaps"):
            print(f"    GAPS      {r['_gaps']}")
        for note in r["_resolution"]["notes"]:
            print(f"    ! {note}")


# --------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pilot", type=int, help="sample N files at random")
    ap.add_argument("--seed", type=int, default=20260821,
                    help="RNG seed, so the same sample is reproducible")
    ap.add_argument("--all", action="store_true", help="use every .txt file")
    ap.add_argument("--only", help="substring filter on filename")
    ap.add_argument("--resolve-report", action="store_true")
    ap.add_argument("--resolve-csv", type=Path)
    ap.add_argument("--run", action="store_true",
                    help="fetch pages + YouTube, then build records")
    ap.add_argument("--rebuild", action="store_true",
                    help="re-emit records from the existing cache — no network, and "
                         "no rewrite of the shared site_values file. Use after a "
                         "shape_lib change so already-written output stops being stale.")
    ap.add_argument("--no-youtube", action="store_true")
    ap.add_argument("--out", type=Path)
    ap.add_argument("--format", choices=["yaml", "json"], default="yaml")
    ap.add_argument("--with-transcript", action="store_true")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    files = txt_files()
    if args.only:
        files = [f for f in files if args.only.lower() in f.name.lower()]
    if args.pilot:
        # Seeded so the pilot is reproducible and reviewable.
        files = sorted(random.Random(args.seed).sample(files, min(args.pilot, len(files))))
        print(f"pilot sample of {len(files)} (seed {args.seed}):")
        for f in files:
            print(f"  {f.name}")

    res = resolve_all(files)

    if args.resolve_csv:
        resolution_csv(res, args.resolve_csv)
    if args.resolve_report:
        resolution_report(res)

    if args.rebuild:
        # Read the cached extraction rather than regenerating it, so a rebuild
        # cannot race a concurrently-running --all fetch over the same file.
        values = (json.loads(TXT_VALUES.read_text(encoding="utf-8"))
                  if TXT_VALUES.exists() else {})
        missing = [r.parsed.filename for r in res if r.parsed.filename not in values]
        if missing:
            print(f"note: {len(missing)} of {len(res)} records have no cached site "
                  f"values and will be thin: {missing[:3]}")
        records = build(res, values, args.out, args.format, args.with_transcript)
        record_report(records)
        return 0

    if args.run:
        fetch_for(res, force=args.force)
        values = extract_for(res)
        if not args.no_youtube:
            fetch_youtube_for(res, values, force=args.force)
            _merge_searched_yt(res)
            values = extract_for(res)
        records = build(res, values, args.out, args.format, args.with_transcript)
        record_report(records)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
