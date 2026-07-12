"""
Rough first-pass named entity index across the local PDF library
(extraction/transcripts_raw/, extraction/substack_summaries_raw/) — for
scoping the social/professional graph backlog item (see CLAUDE.md), NOT
for building anything directly into the RDF graph. This is a triage tool:
"what names/orgs show up, how often" to help decide who's actually worth
manually researching, not an authoritative extraction.

TWO-LAYER DESIGN (rebuilt 2026-07-11 to fix a real inefficiency hit on the
same day): NER itself (spaCy running on document text) is the expensive,
slow step and rarely needs repeating once a document's raw entities are
captured. FILTERING (which entity types to keep, the timestamp-pattern
false-positive fix, any future filter improvements) is cheap and will keep
evolving as more junk patterns get discovered — this tool is a rough
triage pass by design, so filter tweaks are expected, ongoing work, not a
one-time thing. Fusing these together (the original design) meant every
filter improvement required --force, which re-ran spaCy on the ENTIRE
already-processed corpus just to apply a cheap rule change — confirmed
wasteful in practice the same day the timestamp-filter bug was fixed.

Fix: raw_entities table caches EVERY entity spaCy finds (unfiltered, all
label types) per document, keyed by source_file — this is the expensive
layer, computed once per document, essentially never needs recomputing
unless the model itself changes (e.g. upgrading to en_core_web_trf later).
The final `entities` table (used for the top-20 summary and CSV export) is
rebuilt from raw_entities by applying CURRENT filter logic — cheap, fast,
safe to rerun as often as you want.

THREE WAYS TO RUN, matching three real situations:
  1. New documents added (the common case — download more transcripts,
     match more Substack summaries, then index): just run normally. Only
     genuinely new documents get the expensive NER pass; everything else
     is skipped entirely, not even re-filtered (no need — their raw
     entities and the filter logic they'd be reprocessed against are both
     unchanged since last time).
  2. Filter logic improved (e.g. next timestamp-style bug found): run with
     --refilter. Rebuilds the final entities table from EVERY document's
     already-cached raw entities, applying the current filter rules —
     touches zero PDFs, runs zero spaCy passes, safe and fast even across
     hundreds of documents.
  3. Model upgraded, or you want a genuine clean-slate re-extraction: run
     with --force. Re-runs spaCy on everything, same as the old behavior.
     Rarely needed — situation 2 covers the vast majority of "I improved
     something, need to reapply it" cases far more cheaply.

HONEST LIMITATION, tested and confirmed, not just a guess: the small
spaCy model (en_core_web_sm, chosen for speed over the transformer model)
makes real mistakes — confirmed on a real run: mistook transcript
timestamps ("00:02:43") for PERSON entities (now filtered), and tagged
"Doughnut Economics" as PERSON in an earlier test sentence (not caught by
any current filter — ORG/PERSON confusion on unusual noun phrases is a
known weakness of the small model, not something a simple regex fixes).
Treat every result as "worth a human glance," not "confirmed fact."

Output: DuckDB only, gitignored, matching the same local-only treatment as
the raw PDFs and their text caches — this index isn't meant to be
committed to git. Export to CSV yourself if you want a spreadsheet view
(--export-csv flag).

Usage:
    python extraction/index_named_entities.py               # index new documents only
    python extraction/index_named_entities.py --limit 10     # test run first
    python extraction/index_named_entities.py --refilter      # re-apply current filters to everything, no NER
    python extraction/index_named_entities.py --force          # full re-extraction (rarely needed)
    python extraction/index_named_entities.py --export-csv    # also write entities.csv
"""

import argparse
import glob
import os
import re
from pathlib import Path
from collections import Counter

import duckdb
import spacy
import pdfplumber

DB_PATH = "extraction/entity_index.duckdb"
CSV_PATH = "extraction/entity_index.csv"
TRANSCRIPTS_RAW = "extraction/transcripts_raw"
TRANSCRIPTS_TEXT_CACHE = "extraction/transcripts_text_cache"
SUBSTACK_TEXT_CACHE = "extraction/substack_text_cache"

# Entity types worth keeping for this project's purposes. Excludes spaCy's
# other categories (DATE, MONEY, QUANTITY, ORDINAL, CARDINAL, etc.) as noise
# for this specific use case. This is exactly the kind of rule --refilter
# is for — change this set, run --refilter, done, no NER re-run needed.
KEEP_LABELS = {"PERSON", "ORG", "GPE", "NORP", "WORK_OF_ART", "DATE", "EVENT", "PRODUCT"}

TIMESTAMP_PATTERN = re.compile(r'^\d{1,2}:\d{2}(:\d{2})?$')

# Confirmed wrong TYPE on the real 148-document run, 2026-07-11 — not
# guesses, each one specifically verified against what actually showed up.
# RECLASSIFY, not discard: these are legitimate, useful named entities
# (geological epochs, real events, real products/assets) just mistagged as
# PERSON by the small model. Correcting the type preserves them for
# whatever they actually are — e.g. "Holocene"/"Anthropocene" are exactly
# the kind of term worth linking out to Wikipedia/Wikidata later, same
# spirit as the DBpedia/Wikidata links already used elsewhere in this
# project, just not as a PERSON.
RECLASSIFY_PERSON = {
    "Bitcoin": "PRODUCT",
    "COVID": "EVENT",
    "Holocene": "DATE",       # named geological epoch
    "Anthropocene": "DATE",    # same category, not yet seen but same pattern
    "Hormuz": "GPE",           # Strait of Hormuz — an actual place
    "Jekyll": "WORK_OF_ART",   # fictional character used as metaphor —
    "Hyde": "WORK_OF_ART",     # fragment of "Dr. Jekyll and Mr. Hyde"
    "Uncomfortable Questions": "WORK_OF_ART",  # recurring show segment title
}

# This one needs actual text cleanup, not just a type fix — a genuine
# tokenization artifact (the show's own branding term "Frankly" fused with
# a stray possessive), not a real distinct entity at all.
TEXT_CLEANUP = {
    "'s Frankly": ("Frankly", "WORK_OF_ART"),
}


def init_db():
    con = duckdb.connect(DB_PATH)
    con.execute("""
        CREATE TABLE IF NOT EXISTS raw_entities (
            id              INTEGER PRIMARY KEY,
            entity_text     VARCHAR NOT NULL,
            entity_type     VARCHAR NOT NULL,
            source_file     VARCHAR NOT NULL,
            source_type     VARCHAR NOT NULL,
            occurrence_count INTEGER NOT NULL
        )
    """)
    con.execute("""
        CREATE TABLE IF NOT EXISTS entities (
            id              INTEGER PRIMARY KEY,
            entity_text     VARCHAR NOT NULL,
            entity_type     VARCHAR NOT NULL,
            source_file     VARCHAR NOT NULL,
            source_type     VARCHAR NOT NULL,
            occurrence_count INTEGER NOT NULL
        )
    """)
    con.execute("CREATE SEQUENCE IF NOT EXISTS raw_entities_id_seq START 1")
    con.execute("CREATE SEQUENCE IF NOT EXISTS entities_id_seq START 1")
    return con


def already_ner_processed(con, source_file):
    return con.execute(
        "SELECT 1 FROM raw_entities WHERE source_file = ? LIMIT 1", [source_file]
    ).fetchone() is not None


def get_transcript_text(pdf_path, cache_dir):
    os.makedirs(cache_dir, exist_ok=True)
    cache_path = Path(cache_dir) / (Path(pdf_path).stem + ".txt")
    if cache_path.exists():
        return cache_path.read_text(encoding="utf-8")
    text_parts = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            t = page.extract_text()
            if t:
                text_parts.append(t)
    text = "\n\n".join(text_parts)
    cache_path.write_text(text, encoding="utf-8")
    return text


def run_ner(nlp, text):
    """The expensive step. Returns ALL entities, unfiltered — filtering
    happens later, separately, in apply_filters()."""
    doc = nlp(text)
    counts = Counter()
    for ent in doc.ents:
        cleaned = " ".join(ent.text.split())
        if len(cleaned) > 1:
            counts[(cleaned, ent.label_)] += 1
    return counts


def apply_filters(entity_text, entity_type):
    """The cheap step — safe to change and rerun via --refilter without
    touching spaCy. Returns (keep: bool, corrected_text, corrected_type).

    Normalizes curly apostrophes (U+2019, ’) to straight ones (U+0027, ')
    before any dict lookup — confirmed real bug 2026-07-11: spaCy extracted
    "'s Frankly" using the CURLY apostrophe (typographically correct, from
    the source PDF text), but TEXT_CLEANUP's key used a plain straight
    apostrophe, so the lookup silently never matched and the entity stayed
    unfixed through a --refilter run. Normalizing once here protects
    against the same mismatch for any future apostrophe-containing entity,
    not just this one specific case."""
    lookup_text = entity_text.replace("\u2019", "'")
    if lookup_text in TEXT_CLEANUP:
        entity_text, entity_type = TEXT_CLEANUP[lookup_text]
    elif entity_type == "PERSON" and lookup_text in RECLASSIFY_PERSON:
        entity_type = RECLASSIFY_PERSON[lookup_text]
    elif entity_type == "PERSON" and TIMESTAMP_PATTERN.match(entity_text):
        return False, entity_text, entity_type  # genuinely not an entity at all

    if entity_type not in KEEP_LABELS:
        return False, entity_text, entity_type
    return True, entity_text, entity_type


def rebuild_filtered_entities(con):
    """Rebuilds the final `entities` table from raw_entities by applying
    current filter logic. No spaCy, no PDFs — just cached raw data. This
    is what --refilter runs, and what a normal run does at the end for
    any newly-NER'd documents.

    Aggregates AFTER reclassification, not before — reclassifying e.g.
    "'s Frankly" and a separately, correctly-extracted "Frankly" in the
    same document both to (Frankly, WORK_OF_ART) would otherwise produce
    two rows for the same entity instead of one merged count."""
    con.execute("DELETE FROM entities")
    rows = con.execute("SELECT entity_text, entity_type, source_file, source_type, occurrence_count FROM raw_entities").fetchall()
    merged = Counter()  # (text, type, source_file, source_type) -> total occurrences
    total_raw = len(rows)
    for entity_text, entity_type, source_file, source_type, occ in rows:
        keep, corrected_text, corrected_type = apply_filters(entity_text, entity_type)
        if keep:
            merged[(corrected_text, corrected_type, source_file, source_type)] += occ

    for (entity_text, entity_type, source_file, source_type), occ in merged.items():
        con.execute(
            "INSERT INTO entities (id, entity_text, entity_type, source_file, source_type, occurrence_count) "
            "VALUES (nextval('entities_id_seq'), ?, ?, ?, ?, ?)",
            [entity_text, entity_type, source_file, source_type, occ],
        )
    return len(merged), total_raw


def print_summary(con):
    top_people = con.execute("""
        SELECT entity_text, SUM(occurrence_count) as total, COUNT(DISTINCT source_file) as doc_count
        FROM entities
        WHERE entity_type = 'PERSON'
        GROUP BY entity_text
        ORDER BY total DESC
        LIMIT 20
    """).fetchall()
    print("\nTop 20 PERSON entities by total mentions:")
    for name, total, doc_count in top_people:
        print(f"  {name}: {total} mentions across {doc_count} document(s)")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None, help="Max NEW documents to process (testing)")
    parser.add_argument("--export-csv", action="store_true")
    parser.add_argument("--force", action="store_true", help="Re-run NER on everything (rarely needed — see --refilter)")
    parser.add_argument("--refilter", action="store_true", help="Re-apply current filters to all cached raw entities, no NER")
    args = parser.parse_args()

    con = init_db()

    if args.refilter:
        print("Re-applying current filters to cached raw entities (no NER, no PDF access)...")
        kept, total = rebuild_filtered_entities(con)
        print(f"Kept {kept} of {total} raw entities after filtering.")
        print_summary(con)
        if args.export_csv:
            con.execute(f"COPY entities TO '{CSV_PATH}' (HEADER, DELIMITER ',')")
            print(f"\nExported to {CSV_PATH}")
        con.close()
        return

    sources = []
    for pdf in sorted(glob.glob(f"{TRANSCRIPTS_RAW}/*.pdf")):
        sources.append((pdf, "transcript"))
    for txt in sorted(glob.glob(f"{SUBSTACK_TEXT_CACHE}/*.txt")):
        sources.append((txt, "substack_summary"))

    if not sources:
        print(f"No source files found. Checked {TRANSCRIPTS_RAW}/*.pdf and {SUBSTACK_TEXT_CACHE}/*.txt")
        print("Run extraction/download_transcripts.py and/or extraction/match_substack_summaries.py first.")
        return

    to_process = []
    for path, source_type in sources:
        source_file = os.path.basename(path)
        if already_ner_processed(con, source_file) and not args.force:
            continue
        to_process.append((path, source_type, source_file))

    if args.limit:
        to_process = to_process[:args.limit]

    print(f"{len(sources)} total documents known, {len(to_process)} need NER (new, or --force).")

    if to_process:
        print("Loading spaCy model...")
        nlp = spacy.load("en_core_web_sm")

    for path, source_type, source_file in to_process:
        print(f"Running NER ({source_type}): {source_file}")
        if source_type == "transcript":
            text = get_transcript_text(path, TRANSCRIPTS_TEXT_CACHE)
        else:
            text = Path(path).read_text(encoding="utf-8")

        if not text.strip():
            print(f"  (empty text, skipping)")
            continue

        if args.force:
            con.execute("DELETE FROM raw_entities WHERE source_file = ?", [source_file])

        counts = run_ner(nlp, text)
        for (entity_text, entity_type), occ_count in counts.items():
            con.execute(
                "INSERT INTO raw_entities (id, entity_text, entity_type, source_file, source_type, occurrence_count) "
                "VALUES (nextval('raw_entities_id_seq'), ?, ?, ?, ?, ?)",
                [entity_text, entity_type, source_file, source_type, occ_count],
            )

    print(f"\nNER complete on {len(to_process)} document(s). Rebuilding filtered view...")
    kept, total = rebuild_filtered_entities(con)
    print(f"Kept {kept} of {total} total raw entities after filtering.")

    print_summary(con)

    if args.export_csv:
        con.execute(f"COPY entities TO '{CSV_PATH}' (HEADER, DELIMITER ',')")
        print(f"\nExported to {CSV_PATH}")

    con.close()


if __name__ == "__main__":
    main()
