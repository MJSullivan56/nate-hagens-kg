"""
Stage 1b of the bio-intro extraction pipeline — cheap, deterministic
pre-tagging of an already-segmented intro (from extraction/
segment_intros.py's Stage 1 output), NOT a replacement for the actual
Stage 2 extraction (still needs real reading/reasoning — this only
narrows down WHERE to spend that reasoning effort within an already-
small ~1,000-word segment).

WHY THIS EXISTS: the 2nd bio-intro pilot (Berman/Farley,
2026-07-15) was slow. Web verification searches are the real,
inherent bottleneck (network round-trips, can't be sped up without
weakening the verification discipline this whole project insists on)
— but reading each intro segment cold, every time, is real overhead
this CAN reduce. This script flags candidate entity mentions and
relationship-signal sentences via regex only — no NER model, no LLM
call, near-instant — so the actual reasoning step can start from a
short highlight list instead of the full segment text.

TESTED against the real Monahan (TGS_226) intro segment before being
trusted: caught all 3 real relationship-signal sentences (the
co-founder fact, "please welcome my friend," "despite the fact that we
are friends") and all 7 real entity mentions (Ma Earth, Mangaroa Farms,
Matthew Monahan, Nate Hagens, New Zealand, The Great Simplification,
The Regeneration Will Be Funded) with zero false negatives on that one
example. A first version had a real whitespace-normalization bug
(produced a malformed "Matthew\\nMonahan" duplicate) — fixed by
normalizing whitespace BEFORE regex matching, not after. Only tested
against ONE real transcript so far — treat the signal-word list and
entity regex as a first draft, not a finished, broadly-validated tool;
expect to need adjustment once run against a real, varied batch.

FIXED 2026-07-15, after real-world testing against the 7 Berman/Farley
segments (Monahan alone didn't happen to surface these — his segment was
short enough to stay on one PDF page):
1. REAL BUG, not tuning: every PDF page in this transcript library has a
   repeated header/footer baked into the extracted text ("Page X of Y",
   a bare page-number line, "The Great Simplification" as a running
   header) — confirmed via direct inspection, not assumed. Whitespace
   normalization let this boilerplate bleed into whatever word followed
   it across the page break (`"The Great Simplification\nWow."` becomes
   `"The Great Simplification Wow"` once newlines collapse to spaces,
   with no sentence-ending punctuation between them to stop the entity
   regex). Fixed by stripping the boilerplate lines BEFORE
   normalization, at the source, not by patching the regex around it.
2. Tuning: `Nate Hagens` and `The Great Simplification` excluded from
   candidate entities outright — both appear in literally every single
   episode intro by construction (Nate hosts every episode; the show
   is always named), so surfacing them adds zero triage value, only
   noise, on every single run.
3. Tuning: the stoplist generalized from exact 2-word phrases to also
   exclude any candidate entity whose first word is a common sentence-
   continuer (But/So/As/And/With/Well/Yeah/Right — regardless of what
   follows), after seeing concrete new false positives ("But Art", "So
   Art", "As Art", "So Josh") the original narrow stoplist didn't cover.

THIS DOES NOT REPLACE VERIFICATION. Every candidate this surfaces is
exactly that — a candidate, a place to look, not a fact to assert.
Same discipline as every bootstrap this project has done: a name
showing up here is a lead, an org needs independent confirmation before
being written to organizations.ttl, same as Mangaroa Farms was.

Usage:
    python scripts/tag_intro_candidates.py --intro-file extraction/intro_segments/TGS-226-Matthew-Monahan-Transcript.docx.intro.txt
    python scripts/tag_intro_candidates.py --intro-dir extraction/intro_segments/ --out extraction/intro_candidates.csv
"""

import argparse
import csv
import re
from pathlib import Path

ENTITY_PATTERN = re.compile(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,4})\b')

# Repeated PDF page header/footer boilerplate, confirmed present in this
# transcript library (see FIXED note above) — stripped BEFORE whitespace
# normalization so it can't bleed into an adjacent real word across a
# page break.
BOILERPLATE_LINE_PATTERN = re.compile(
    r'^(Page \d+ of \d+|\d+|The Great Simplification)\s*$', re.MULTILINE
)

# First-draft stoplist — sentence-starter false positives seen on the one
# real example tested. Expect to grow this once run against more files.
ENTITY_STOPLIST = {
    "Today I", "With That", "As Of", "This Farm", "This Conversation",
    "As The", "So Maybe", "And So", "But The",
}

# Sentence-continuer prefixes that produce a false-positive "entity" no
# matter what proper noun follows (e.g. "But Art", "So Josh") — a leading
# word filter generalizes past ENTITY_STOPLIST's exact-phrase entries.
ENTITY_PREFIX_STOPWORDS = {
    "But", "So", "As", "And", "With", "Well", "Yeah", "Right",
}

# Present in literally every episode intro by construction (Nate hosts
# every episode; the show is always named) — zero triage value, pure
# noise on every single run, not a real "candidate."
ALWAYS_PRESENT_ENTITIES = {"Nate Hagens", "The Great Simplification"}

# First-draft signal-word list — same caveat, only validated against one
# transcript. "years" deliberately excluded after testing: too broad,
# matched scheduling-logistics sentences with no real relationship content.
SIGNAL_WORDS = [
    "friend", "chair", "co-founder", "cofounder", "colleague",
    "advisor", "mentor", "committee", "known each other",
    "student", "professor", "board",
]


def tag_segment(text):
    stripped = BOILERPLATE_LINE_PATTERN.sub(' ', text)
    normalized = re.sub(r'\s+', ' ', stripped)
    candidates = set(ENTITY_PATTERN.findall(normalized))
    entities = {
        e for e in candidates
        if e not in ENTITY_STOPLIST
        and e not in ALWAYS_PRESENT_ENTITIES
        and e.split(" ", 1)[0] not in ENTITY_PREFIX_STOPWORDS
    }
    sentences = re.split(r'(?<=[.!?])\s+', normalized)
    signal_sentences = [s.strip() for s in sentences
                         if any(w in s.lower() for w in SIGNAL_WORDS)]
    return sorted(entities), signal_sentences


def main():
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--intro-file", help="Tag a single intro segment file")
    group.add_argument("--intro-dir", help="Tag every .intro.txt file in a directory")
    parser.add_argument("--out", help="Write results to this CSV instead of stdout (only used with --intro-dir)")
    args = parser.parse_args()

    if args.intro_file:
        text = Path(args.intro_file).read_text(errors="replace")
        entities, signals = tag_segment(text)
        print(f"=== {args.intro_file} ===")
        print(f"Candidate entities ({len(entities)}):")
        for e in entities:
            print(f"  {e}")
        print(f"\nRelationship-signal sentences ({len(signals)}):")
        for s in signals:
            print(f"  - {s[:200]}")
        return

    intro_dir = Path(args.intro_dir)
    rows = []
    for f in sorted(intro_dir.glob("*.intro.txt")):
        text = f.read_text(errors="replace")
        entities, signals = tag_segment(text)
        rows.append({
            "file": f.name,
            "entity_count": len(entities),
            "entities": "; ".join(entities),
            "signal_count": len(signals),
            "signal_sentences": " | ".join(s[:200] for s in signals),
        })

    if args.out:
        with open(args.out, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else [])
            writer.writeheader()
            writer.writerows(rows)
        print(f"{len(rows)} file(s) tagged, written to {args.out}")
    else:
        for r in rows:
            print(f"{r['file']}: {r['entity_count']} entities, {r['signal_count']} signal sentences")


if __name__ == "__main__":
    main()
