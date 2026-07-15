"""
Stage 1 of the bio-intro extraction pipeline (piloted 2026-07-14 by hand
on Matthew Monahan's TGS_226 transcript — see
docs/sidecar-cleanup-handoff.md for the full discussion and what it
surfaced: a new Organization, a new Organization-to-Organization
Relationship, and a corrected RelationshipType on an existing one, none
of which generic NER or web search alone would have found).

WHAT THIS DOES: isolates the likely guest-introduction portion of an
Interview or Roundtable transcript — deliberately GENEROUS (over-capture
rather than under-capture), since Stage 2 (an actual LLM pass, not yet
built — see extraction_README.md's Step 3) does the real precision work
of picking bio-relevant sentences out of the window. This script does
NOT call an LLM and does NOT itself extract structured facts — it only
narrows a ~5,000-15,000 word transcript down to the ~1,000-word region
worth spending an LLM call on.

WHY NOT A SIMPLE "FIRST SUBSTANTIAL GUEST TURN" HEURISTIC: tried that
first, on the real Monahan transcript. It failed immediately — that
transcript opens with a cold-open hook FROM THE GUEST (a compelling
quote pulled from later in the episode, played before the host's own
introduction even starts), a common podcast editing convention. A
"first real guest turn" heuristic finds the cold-open, not the intro,
and cuts off before the actual bio content. Fixed by switching to a
fixed generous window (first K speaker turns) instead of trying to find
a precise semantic boundary — more robust precisely because it doesn't
try to be clever about where the intro "really" ends.

FRANKLYS (monologues) ARE EXPLICITLY OUT OF SCOPE — MJSullivan's own
catch, 2026-07-14: no guest, no guest introduction, this whole approach
doesn't apply. Only run this against Interview/Roundtable transcripts.
Roundtables have MULTIPLE guests to introduce — this script's window
may need to be wider for those; not yet tested against a real
Roundtable transcript, worth checking before assuming the same K works.

Usage:
    python extraction/segment_intros.py --transcripts-dir extraction/transcripts_text_cache \\
        --manifest extraction/download_manifest.csv --out extraction/intro_segments/

(NOTE: --transcripts-dir must point at the .txt cache, not transcripts_raw/'s
.pdf files — this script globs *.txt and does no PDF extraction itself. The
cache is produced by extraction/index_named_entities.py's get_transcript_text();
run that first for any transcript not yet cached.)
"""

import argparse
import csv
import re
from pathlib import Path

K_TURNS_DEFAULT = 10

# TWO transcript formats confirmed in the real corpus (found 2026-07-15
# while running this against Berman/Farley's actual episodes — 5 of the 7
# target transcripts turned out to use the older format below, so this
# isn't an edge case, it's roughly half the library as of this writing):
#
# Format A — "[HH:MM:SS] Name: text" (newer transcripts, e.g. TGS-220,
# TGS-185). Timestamp precedes the name, in brackets.
#
# Format B — "Name (HH:MM:SS):\ntext" or "Name (MM:SS):\ntext" (older
# transcripts, e.g. TGS03/TGS92/TGS101/TGS07/TGS29). Timestamp follows the
# name, in parens, and is sometimes MM:SS rather than HH:MM:SS (confirmed
# on TGS03: "Nate Hagens (00:12):"). Continuation lines mid-turn repeat
# just "(HH:MM:SS):" or "(MM:SS):" alone with no name — same "new turn
# needs a name, continuation doesn't" shape as Format A, just mirrored.
TURN_PATTERN_A = re.compile(r'\[(\d{2}:\d{2}:\d{2})\]\s+([^:\n]+):\s*', re.MULTILINE)
TURN_PATTERN_B = re.compile(
    r'^([A-Z][A-Za-z.\'-]*(?: [A-Z][A-Za-z.\'-]*)*)\s*\((?:\d{1,2}:)?\d{2}:\d{2}\):\s*',
    re.MULTILINE,
)

# Repeated PDF page header/footer boilerplate ("Page X of Y", a bare
# page-number line, "The Great Simplification" running header) — confirmed
# present in this transcript library 2026-07-15 via direct inspection.
# Added here (Stage 1's own output) rather than as a separate cleanup
# script/pass: this is Stage 1's job (produce a genuinely clean window),
# and it's a precisely-matched, whole-line-only pattern — deliberately NOT
# a broad "remove repeated words" or "stitch line-wraps" transformation.
# Real guest dialogue legitimately repeats words for emphasis ("Money,
# Money, Money"); a fuzzy dedup pass would silently eat that, which is
# exactly the corruption pattern caught and reverted the same day this
# was added (see docs/sidecar-cleanup-handoff.md). Line-wraps are left
# alone too — Stage 2 reading works fine with wrapped lines, and
# collapsing them adds transformation risk for no real benefit.
BOILERPLATE_LINE_PATTERN = re.compile(
    r'^[ \t]*(Page \d+ of \d+|\d+|The Great Simplification)[ \t]*\n', re.MULTILINE
)


def strip_boilerplate(text):
    """Removes only whole-line matches of known page header/footer
    boilerplate. Does not touch anything else — no word-level edits, no
    line-wrap joining."""
    return BOILERPLATE_LINE_PATTERN.sub('', text)


def segment_intro(text, k_turns=K_TURNS_DEFAULT):
    """Returns the first k_turns speaker turns of a transcript's timestamped
    body (skipping any pre-timestamp header/boilerplate). Deliberately
    generous — see module docstring for why. Tries Format A first, then
    Format B — see the format comments above TURN_PATTERN_A/B. Returns
    None (caller should flag and skip) if neither format's pattern finds
    any matches at all."""
    for pattern in (TURN_PATTERN_A, TURN_PATTERN_B):
        matches = list(pattern.finditer(text))
        if not matches:
            continue
        body_start = matches[0].start()
        cutoff = matches[k_turns].start() if len(matches) > k_turns else len(text)
        return text[body_start:cutoff]
    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--transcripts-dir", required=True,
                         help="Directory of raw transcript .txt/.pdf-extracted-text files")
    parser.add_argument("--manifest", required=True,
                         help="download_manifest.csv — used to filter to interview/roundtable only, skip frankly")
    parser.add_argument("--out", required=True,
                         help="Output directory for the segmented intro snippets")
    parser.add_argument("--k-turns", type=int, default=K_TURNS_DEFAULT,
                         help=f"Number of speaker turns to capture (default {K_TURNS_DEFAULT})")
    args = parser.parse_args()

    transcripts_dir = Path(args.transcripts_dir)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Manifest-based type filter (fixed 2026-07-15 — previously declared
    # but never actually applied, see git history). Keyed by the PDF
    # filename's stem (local_filename minus ".pdf"), which matches the
    # .txt cache filename's stem one-for-one — confirmed against a real
    # manifest row (e.g. local_filename "TGS03ArthurBermanTranscript.docx.pdf"
    # -> cache file "TGS03ArthurBermanTranscript.docx.txt").
    # KNOWN DATA-QUALITY GAP, not fixed here: at least 2 real Roundtable
    # transcripts (RR01BermanMichauxPrieto, RR03EricksonFarleyRaworthKeen)
    # are mislabeled type=interview in the manifest rather than
    # type=roundtable — confirmed by direct inspection 2026-07-15. Both
    # still pass this filter (interview is eligible too), so it doesn't
    # cause a false skip, but a caller relying on the manifest type to
    # distinguish single- vs multi-guest windowing would be misled.
    eligible_types = {"interview", "roundtable"}
    type_by_stem = {}
    with open(args.manifest, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            local_filename = row.get("local_filename", "")
            if local_filename.endswith(".pdf"):
                type_by_stem[local_filename[:-4]] = row.get("type", "")

    skipped_frankly = 0
    skipped_unknown_type = 0
    processed = 0
    no_timestamp_found = 0

    for txt_file in sorted(transcripts_dir.glob("*.txt")):
        episode_type = type_by_stem.get(txt_file.stem)
        if episode_type == "frankly":
            skipped_frankly += 1
            continue
        if episode_type not in eligible_types:
            # Not found in manifest, or an unrecognized type value — flag
            # rather than silently process, since we can't confirm this
            # transcript actually has a guest to introduce.
            skipped_unknown_type += 1
            print(f"SKIP (type='{episode_type}', not in {eligible_types}): {txt_file.name}")
            continue
        text = txt_file.read_text(errors="replace")
        segment = segment_intro(text, k_turns=args.k_turns)
        if segment is None:
            no_timestamp_found += 1
            print(f"SKIP (no [00:00:00]-style timestamp found): {txt_file.name}")
            continue
        out_path = out_dir / f"{txt_file.stem}.intro.txt"
        out_path.write_text(strip_boilerplate(segment))
        processed += 1

    print(f"\n{processed} intro segments written to {out_dir}/")
    print(f"{skipped_frankly} Frankly (monologue) file(s) skipped via manifest type filter")
    print(f"{skipped_unknown_type} file(s) skipped — type not in {eligible_types} or not found in manifest")
    print(f"{no_timestamp_found} file(s) skipped — no recognized timestamp format")
    print("\nNOTE: the multi-guest Roundtable window-width gap (see module "
          "docstring) is still NOT fixed — this pass only closes the "
          "manifest-type-filter gap.")


if __name__ == "__main__":
    main()
