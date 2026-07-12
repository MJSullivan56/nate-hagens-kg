"""
Matches Substack summary PDFs (manually saved by MJSullivan into
extraction/substack_summaries_raw/) against the episode transcript index,
extracts their text to a local cache for fast reuse, and writes a
METADATA-ONLY index to git.

COPYRIGHT NOTE, consistent with this project's discipline everywhere else:
the actual extracted Substack text is cached locally (gitignored) for your
own reference use, same treatment as the transcript PDFs themselves. The
committed index file (substack_summaries_index.csv) contains ONLY metadata
— filename, matched episode, match confidence, word count — never the
reproduced text itself. If you want to use a summary's content to inform a
Concept definition in the graph, paraphrase it the same way the rest of the
seed data was built; don't copy text directly from the cache into a TTL file.

MATCHING APPROACH (rebuilt 2026-07-11 after real bugs found in the fuzzy-
only version — see git history / CLAUDE.md Gotchas for the full story):

  1. PRIMARY: exact Frankly-number matching. Confirmed real format: every
     Substack post for a Frankly episode has "Frankly #N" as its own line
     near the top (light grey text in the PDF, but pdfplumber extracts
     based on the text layer, not color/style, so it's captured fine).
     Cross-referenced against the episode number embedded in each
     candidate's episode_url (both known real URL conventions handled —
     the site changed slug format at some point: newer episodes use
     "/frankly-original/147-slug", older ones use
     "/frankly-original/frankly-1-slug" or zero-padded "frankly-02-slug").
     When a number is found on BOTH sides, this is authoritative — no
     fuzzy scoring, no chance of a wrong-but-plausible match.
  2. FALLBACK: normalized-title fuzzy matching, only used when no Frankly
     number is extractable from the Substack text at all (e.g. series-hub
     posts that aren't tied to one specific episode, or non-Frankly
     content). Includes a hard veto for mismatched "Part N" markers
     (Part 3 vs Part 1 previously matched at 0.65 — wrong episode, caught
     on a real run before this fix).
  3. If a Frankly number IS found in the Substack text but does NOT match
     any candidate, this is reported as UNMATCHED with the number shown —
     it means that episode's transcript likely hasn't been downloaded yet,
     NOT that fuzzy matching should be tried instead. Falling back to fuzzy
     in this case is exactly the mechanism that produced wrong matches
     before (the real match doesn't exist among candidates, so fuzzy just
     picks the closest wrong one).

Every row in the output index records which method produced the match
(exact_frankly_number / fuzzy_title / none) so low-confidence and
high-confidence matches are never visually indistinguishable later.

Usage:
    python extraction/match_substack_summaries.py
    python extraction/match_substack_summaries.py --threshold 0.6   # stricter fuzzy fallback
    python extraction/match_substack_summaries.py --force            # re-process everything
"""

import argparse
import csv
import difflib
import re
from pathlib import Path

import pdfplumber

RAW_DIR = Path("extraction/substack_summaries_raw")
TEXT_CACHE_DIR = Path("extraction/substack_text_cache")  # gitignored
INDEX_FILE = Path("extraction/substack_summaries_index.csv")  # committed, metadata only
TRANSCRIPT_INDEX = Path("extraction/download_manifest.csv")
NO_TRANSCRIPT_FILE = Path("extraction/no_transcript_available.csv")

DEFAULT_THRESHOLD = 0.5  # fuzzy fallback only — below this, flagged as unmatched


def normalize_title(title):
    title = re.sub(r'\.pdf$', '', title, flags=re.IGNORECASE)
    title = re.sub(r'^\[Update\]\s*', '', title)
    title = re.sub(r'\s*-\s*by Nate Hagens\s*$', '', title, flags=re.IGNORECASE)
    title = re.sub(r'[^\w\s]', '', title)
    title = re.sub(r'\s+', ' ', title).strip().lower()
    return title


def extract_part_number(title):
    """See module docstring — hard veto for mismatched series installments."""
    m = re.search(r'\bpart\s+(\d+)\b', title.lower())
    return int(m.group(1)) if m else None


def extract_frankly_number_from_text(text):
    """Confirmed real format: 'Frankly #147' as its own line near the top."""
    m = re.search(r'Frankly\s*#(\d+)', text)
    return int(m.group(1)) if m else None


def extract_frankly_number_from_url(url):
    """Handles both known real URL conventions — confirmed via live fetch
    2026-07-10: newer '/frankly-original/147-slug', older
    '/frankly-original/frankly-1-slug' and zero-padded 'frankly-02-slug'."""
    m = re.search(r'/frankly-original/(?:frankly-)?(\d+)-', url)
    return int(m.group(1)) if m else None


def match_score(a_raw, b_raw):
    a_part = extract_part_number(a_raw)
    b_part = extract_part_number(b_raw)
    if a_part is not None and b_part is not None and a_part != b_part:
        return 0.0  # hard veto — different installments of the same series

    a, b = normalize_title(a_raw), normalize_title(b_raw)
    if not a or not b:
        return 0.0
    shorter, longer = (a, b) if len(a) <= len(b) else (b, a)
    if len(shorter) >= 5 and shorter in longer:
        return 0.95
    return difflib.SequenceMatcher(None, a, b).ratio()


def load_candidates():
    """Returns list of (title, episode_url, type) from everything we know
    about — both episodes with a downloaded transcript AND episodes
    confirmed to have no transcript."""
    candidates = []
    if TRANSCRIPT_INDEX.exists():
        with open(TRANSCRIPT_INDEX, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                candidates.append((row["title"], row["episode_url"], row["type"]))
    if NO_TRANSCRIPT_FILE.exists():
        with open(NO_TRANSCRIPT_FILE, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if row.get("title"):
                    candidates.append((row["title"], row["episode_url"], "no_transcript_available"))
    return candidates


def build_frankly_number_index(candidates):
    """Maps Frankly number -> (title, url, type) for exact-match lookup."""
    index = {}
    for title, url, etype in candidates:
        num = extract_frankly_number_from_url(url)
        if num is not None:
            index[num] = (title, url, etype)
    return index


def extract_pdf_text(pdf_path):
    text_parts = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            t = page.extract_text()
            if t:
                text_parts.append(t)
    return "\n\n".join(text_parts)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    if not RAW_DIR.exists():
        raise SystemExit(f"{RAW_DIR} doesn't exist — nothing to process.")

    candidates = load_candidates()
    frankly_index = build_frankly_number_index(candidates)
    print(f"Loaded {len(candidates)} known episode titles ({len(frankly_index)} with a Frankly number) to match against.")

    TEXT_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    rows = []
    unmatched = []
    exact_count = 0
    fuzzy_count = 0

    pdf_files = sorted(RAW_DIR.glob("*.pdf"))
    print(f"Found {len(pdf_files)} Substack summary PDFs.\n")

    for pdf_path in pdf_files:
        filename = pdf_path.name
        cache_path = TEXT_CACHE_DIR / (pdf_path.stem + ".txt")

        if cache_path.exists() and not args.force:
            text = cache_path.read_text(encoding="utf-8")
        else:
            try:
                text = extract_pdf_text(pdf_path)
            except Exception as e:
                print(f"  FAILED to extract text from {filename}: {e}")
                text = ""
            cache_path.write_text(text, encoding="utf-8")
        word_count = len(text.split())

        # Strategy 1: exact Frankly-number match
        substack_num = extract_frankly_number_from_text(text)
        if substack_num is not None:
            if substack_num in frankly_index:
                title, url, etype = frankly_index[substack_num]
                print(f"  MATCHED (exact #{substack_num}): {filename[:55]} -> {title[:55]}")
                rows.append({
                    "substack_filename": filename, "matched_episode_title": title,
                    "matched_episode_url": url, "matched_type": etype,
                    "match_score": "1.00", "match_method": "exact_frankly_number",
                    "word_count": word_count, "text_cache_file": str(cache_path),
                })
                exact_count += 1
                continue
            else:
                print(f"  UNMATCHED (Frankly #{substack_num} not in candidates — transcript probably not downloaded yet): {filename[:55]}")
                unmatched.append(filename)
                rows.append({
                    "substack_filename": filename, "matched_episode_title": "",
                    "matched_episode_url": "", "matched_type": "",
                    "match_score": f"frankly_#{substack_num}_not_found", "match_method": "none",
                    "word_count": word_count, "text_cache_file": str(cache_path),
                })
                continue

        # Strategy 2: fuzzy title fallback (no Frankly number in the text at all)
        best_title, best_url, best_type, best_score = None, None, None, 0.0
        for title, url, etype in candidates:
            score = match_score(filename, title)
            if score > best_score:
                best_title, best_url, best_type, best_score = title, url, etype, score

        if best_score >= args.threshold:
            print(f"  MATCHED (fuzzy {best_score:.2f}): {filename[:55]} -> {best_title[:55]}")
            rows.append({
                "substack_filename": filename, "matched_episode_title": best_title,
                "matched_episode_url": best_url, "matched_type": best_type,
                "match_score": f"{best_score:.2f}", "match_method": "fuzzy_title",
                "word_count": word_count, "text_cache_file": str(cache_path),
            })
            fuzzy_count += 1
        else:
            print(f"  UNMATCHED (fuzzy best was {best_score:.2f}): {filename[:55]}")
            unmatched.append(filename)
            rows.append({
                "substack_filename": filename, "matched_episode_title": "",
                "matched_episode_url": "", "matched_type": "",
                "match_score": f"{best_score:.2f}", "match_method": "none",
                "word_count": word_count, "text_cache_file": str(cache_path),
            })

    with open(INDEX_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "substack_filename", "matched_episode_title", "matched_episode_url",
            "matched_type", "match_score", "match_method", "word_count", "text_cache_file",
        ])
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nDone. {exact_count} exact (Frankly #), {fuzzy_count} fuzzy-matched, {len(unmatched)} unmatched.")
    print(f"Index (metadata only, committed to git): {INDEX_FILE}")
    print(f"Extracted text cache (gitignored, local only): {TEXT_CACHE_DIR}/")
    if fuzzy_count:
        print(f"\n{fuzzy_count} match(es) came from fuzzy title matching, not exact numbers —")
        print("worth a manual glance at these specifically (check match_method column).")
    if unmatched:
        print(f"\nUnmatched files, may need manual review or the transcript downloaded first:")
        for f in unmatched:
            print(f"  - {f}")


if __name__ == "__main__":
    main()
