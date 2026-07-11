"""
Matches Substack summary PDFs (manually saved by MJSullivan into
extraction/substack_summaries_raw/) against the episode transcript index by
title, extracts their text to a local cache for fast reuse, and writes a
METADATA-ONLY index to git.

COPYRIGHT NOTE, consistent with this project's discipline everywhere else:
the actual extracted Substack text is cached locally (gitignored) for your
own reference use, same treatment as the transcript PDFs themselves. The
committed index file (substack_summaries_index.csv) contains ONLY metadata
— filename, matched episode, match confidence, word count — never the
reproduced text itself. If you want to use a summary's content to inform a
Concept definition in the graph, paraphrase it the same way the rest of the
seed data was built; don't copy text directly from the cache into a TTL file.

Matching approach: normalized-title fuzzy matching, tested to correctly
handle the common case where the site's own episode title is a shortened
prefix of the fuller Substack title (e.g. "Oil 201" vs "Oil 201: What
Happens When the Oil Stops Flowing") — plain character-similarity scoring
alone badly penalizes that case, so prefix/substring containment is treated
as a strong match signal, falling back to sequence similarity otherwise.

Usage:
    python extraction/match_substack_summaries.py
    python extraction/match_substack_summaries.py --threshold 0.6   # stricter
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
TRANSCRIPT_INDEX = Path("extraction/transcripts_index.csv")
NO_TRANSCRIPT_FILE = Path("extraction/no_transcript_available.csv")

DEFAULT_THRESHOLD = 0.5  # below this, flagged as unmatched rather than guessed


def normalize_title(title):
    title = re.sub(r'\.pdf$', '', title, flags=re.IGNORECASE)
    title = re.sub(r'^\[Update\]\s*', '', title)
    title = re.sub(r'\s*-\s*by Nate Hagens\s*$', '', title, flags=re.IGNORECASE)
    title = re.sub(r'[^\w\s]', '', title)
    title = re.sub(r'\s+', ' ', title).strip().lower()
    return title


def match_score(a_raw, b_raw):
    a, b = normalize_title(a_raw), normalize_title(b_raw)
    if not a or not b:
        return 0.0
    shorter, longer = (a, b) if len(a) <= len(b) else (b, a)
    if len(shorter) >= 5 and shorter in longer:
        return 0.95
    return difflib.SequenceMatcher(None, a, b).ratio()


def load_candidate_titles():
    """Returns list of (title, episode_url, type) from everything we know about —
    both episodes with a downloaded transcript AND episodes confirmed to have
    no transcript (no_transcript_available.csv, which stores titles as of the
    2026-07-10 fix — a Substack summary matching one of these just means you
    have a summary but no full transcript for that episode, which is itself
    useful information, not an error)."""
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
    args = parser.parse_args()

    if not RAW_DIR.exists():
        raise SystemExit(f"{RAW_DIR} doesn't exist — nothing to process.")

    candidates = load_candidate_titles()
    print(f"Loaded {len(candidates)} known episode titles to match against.")

    TEXT_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    rows = []
    unmatched = []

    pdf_files = sorted(RAW_DIR.glob("*.pdf"))
    print(f"Found {len(pdf_files)} Substack summary PDFs.\n")

    for pdf_path in pdf_files:
        filename = pdf_path.name
        best_title, best_url, best_type, best_score = None, None, None, 0.0
        for title, url, etype in candidates:
            score = match_score(filename, title)
            if score > best_score:
                best_title, best_url, best_type, best_score = title, url, etype, score

        # Extract and cache text locally (never committed — see module docstring)
        try:
            text = extract_pdf_text(pdf_path)
        except Exception as e:
            print(f"  FAILED to extract text from {filename}: {e}")
            text = ""
        cache_path = TEXT_CACHE_DIR / (pdf_path.stem + ".txt")
        cache_path.write_text(text, encoding="utf-8")
        word_count = len(text.split())

        if best_score >= args.threshold:
            print(f"  MATCHED ({best_score:.2f}): {filename[:60]} -> {best_title[:60]}")
            rows.append({
                "substack_filename": filename,
                "matched_episode_title": best_title,
                "matched_episode_url": best_url,
                "matched_type": best_type,
                "match_score": f"{best_score:.2f}",
                "word_count": word_count,
                "text_cache_file": str(cache_path),
            })
        else:
            print(f"  UNMATCHED (best was {best_score:.2f}): {filename[:60]}")
            unmatched.append(filename)
            rows.append({
                "substack_filename": filename,
                "matched_episode_title": "",
                "matched_episode_url": "",
                "matched_type": "",
                "match_score": f"{best_score:.2f}",
                "word_count": word_count,
                "text_cache_file": str(cache_path),
            })

    with open(INDEX_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "substack_filename", "matched_episode_title", "matched_episode_url",
            "matched_type", "match_score", "word_count", "text_cache_file",
        ])
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nDone. {len(rows) - len(unmatched)} matched, {len(unmatched)} unmatched.")
    print(f"Index (metadata only, committed to git): {INDEX_FILE}")
    print(f"Extracted text cache (gitignored, local only): {TEXT_CACHE_DIR}/")
    if unmatched:
        print(f"\nUnmatched files (below --threshold {args.threshold}), may need manual review:")
        for f in unmatched:
            print(f"  - {f}")


if __name__ == "__main__":
    main()
