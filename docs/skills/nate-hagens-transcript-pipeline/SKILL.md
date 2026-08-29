---
name: nate-hagens-transcript-pipeline
description: Working knowledge for the transcript chunking + NER-candidate extraction tool (nate-hagens-kg corpus). Use this skill at the start of every Claude Code session working on this pipeline, and whenever authoring/modifying the chunking script, the show-notes-alignment logic, or the NER extraction step. Captures real gotchas found during design and pilot work — this is a living document; add to it as new real issues are found, don't just read it.
---

# nate-hagens-transcript-pipeline — working knowledge

## What this tool is

A chunking + NER-candidate-extraction pipeline that converts a raw
transcript + its scraped show-notes metadata (one pair per episode) into
a single, rich, self-contained pre-staging JSON file per episode.
Explicitly **not relational form yet** — this feeds a later DuckDB
population step, not a direct SQL schema. NER candidates are
**reference-only**: nothing from this pipeline gets minted into the
`nate-hagens-kg` ontology directly — a human reviews candidates in a
separate, later pass. See `pilot-spec-transcript-chunking.md` for the
full design spec and worked example (`TGS127_chunked_example.json`).

## Real gotchas — found during design, before Code has run once

**1. The cold-open teaser is genre-conditional, not universal — detect
it per-transcript, never branch on episode type.** Confirmed real
example: `TGS_127`'s opening line is a soundbite spliced in from later in
the conversation, not real position-0 content — the real interview
begins at the *host's* (Nate's) first turn, regardless of what timestamp
the teaser itself carries. Confirmed this does NOT apply to
`Frankly-145` (a monologue) — real content starts immediately at
`00:00:00`, no teaser at all. Don't assume "Interview/Panel = has
teaser, Frankly = doesn't" either — a guest-Frankly episode is known to
exist in this corpus and could break that assumed correlation. Detect it
from the transcript's own content every time.

**2. Trailing outro/credits stripping is the same story — detect, don't
assume from genre.** `RR-24` ends with real, non-interview boilerplate
(sign-off, hosting/editing/production credits) after the last real
speaker turn. `Frankly-145` has no such block at all. Same principle as
gotcha #1: check each transcript's own ending, don't infer from segment
type.

**3. A bracketed timestamp does not always start a new speaker turn.**
Real finding from `RR-24`: a bare `[timestamp]` with no `Speaker Name:`
prefix following it is a paragraph break *within* the current speaker's
ongoing turn, not a new turn. Confirmed as the *dominant* pattern for
monologues via `Frankly-145` — a whole 24-minute piece is one continuous
turn, broken only by bare-timestamp continuation markers, never a
re-stated speaker label. Get this rule wrong and monologues in particular
will fragment into dozens of spurious "turns" that are really one
person's continuous speech.

**4. Show-notes timestamps mark moments of interest *within* an ongoing
turn — they are not turn boundaries.** A "topic-anchored chunk" is an
anchor point, not a hard content boundary. Real example: `TGS_127`'s
second show-notes entry ("Olivia Lazard + Michael Michaux," timestamped
01:23) falls inside Nate's single long intro turn, which starts at
00:00:20 and runs well past 01:23 without a break. Resolution rule: a
turn is assigned to the chunk containing its own *start* time — a long
turn can and will run past its chunk's nominal `end_seconds`. This is
expected, not a bug to "fix" by truncating turns at chunk boundaries.

**5. `transcript_source_type` and timestamp presence are independent
facts — never infer one from the other.** An *official* transcript can
still lack usable inline timestamps if they were stripped during editing
(a real, human editing choice, confirmed to occur in this corpus). Detect
timestamp presence directly per file; don't assume "official = has
timestamps."

**6. Non-official transcripts are not one uniform quality tier — there
are (at least) three real, distinct variants, each needing different
handling.** (a) Clean YouTube captions — different format, still usable
alignment logic. (b) Dense/no-diarization captions — a timestamp roughly
every dozen words (YouTube's own auto-captioning), almost certainly no
real speaker labels at all, a harder problem than alignment alone.
(c) Corrupted-inline-metadata captions — real caption timestamp/duration
data fused directly into the running prose with no separator, breaking
real words apart mid-sentence (confirmed real example: caption artifacts
merged into "you know" and "which" mid-word). This third variant needs
real cleanup before any chunking or NER pass could run against it usably
— don't treat it the same as the other two.

**7. YouTube "Chapters" (`## Chapter N:` headers) are a real, distinct
THIRD chunking-anchor mechanism — not a quality tier, and not the same
finding as gotcha #6.** Some YouTube-derived transcripts carry
algorithmically-inserted chapter groupings, independent of whether that
same transcript also has the timestamp-corruption problem from gotcha #6
— these are two separate, orthogonal axes (`chunking_anchor_available`
vs. `has_embedded_metadata_corruption`), don't conflate them into one
combined tier. Real, constructive use: for episodes with no official
transcript, Chapters are a legitimate fallback anchor (worse than real
show-notes, better than blind proportional splitting) — when used, a
Chapter's title becomes the chunk's `topic_label` directly, same
`topic_anchored` chunk shape as a show-notes chunk, `curated_links`
simply stays `[]` since Chapters carry no link data.

**8. Auto-generated transcripts contain real, recurring name-variant/ASR
corruption — expect it, don't treat single instances as one-offs.**
Confirmed independently twice in this corpus: "Simon Michaux" (real
name) rendered as "Simon Michaud" in one transcript and "Michael
Michaux" in that same episode's own show-notes; "Jared Diamond" (real,
well-known author) rendered as "Joan diamond" in a separate episode's
auto-generated transcript. Flag candidates like this explicitly in NER
output (a `_NAME_VARIANT_CONFLICT` or `_LIKELY_ASR_ERROR` style tag),
don't silently normalize or discard them — they're exactly the kind of
finding this pipeline's reference-only NER pass exists to surface.

**9. A third show-notes source format exists (website-page markdown), and
it's not just a parsing variant — it serves a genuinely different
purpose than the other two.** Confirmed via `TGS_231`: the site's own
markdown export has no structured `{timestamp, seconds, topic, links}`
data — its "Citations by Timestamp" section is prose, with only
human-readable `HH:MM:SS` (needs real parsing, including an hour-
inclusive vs. not edge case: `1:38:32` vs. `02:04`, no precomputed
seconds). More importantly, it's much denser than the YAML/JSON
`show_notes` arrays (100+ entries across ~98 minutes vs. ~60-70 in other
episodes) and reads as an exhaustive citation list, not discrete
topic-segment markers. Don't force every citation entry into its own
chunk boundary — that fragments the episode absurdly. Real, valuable
reframe instead: use this dense list as a genuine human-curated ground
truth to validate NER extraction quality directly (precision/recall
against a real reference) — something the other, sparser formats can't
offer — and fall back to coarser chunking (proportional splitting, or
clustering closely-spaced entries) for this format's actual chunk
boundaries.

## Gotchas found by actually running Phase 0 (added 2026-08-26, TGS_127)

**10. Filler chunks must not nest inside their enclosing topic chunk — the
reference's own shape is ambiguous here, and it says so.** The hand-built
`TGS-127_chunked_example.json` has `chunk_07` spanning 422-608s and
`chunk_07b_filler` spanning 528-569s — the filler sits *inside* the topic
chunk's span, so a turn starting at 550s belongs to two chunks at once and
"which chunk owns this turn" has no answer. The reference flags the resulting
contradiction itself (its `chunk_08` `_note`: a turn starting at 569s is shown
under a chunk beginning at 608s, "a real inconsistency worth Code resolving
with an explicit, code-level rule"). **Resolution now implemented: chunks are a
non-overlapping partition.** Where a gap exceeds the threshold and a turn
actually starts in its late portion, the topic chunk is CUT at that turn and the
remainder becomes the filler. Consequence to expect when diffing against the
reference: `chunk_07.end_seconds` becomes 528 (not 608), the filler runs
528-608 (not 528-569), and the 569s turn lands in the filler rather than
`chunk_08`.

**11. A gap exceeding the threshold does NOT always warrant a filler chunk.**
TGS_127 has 20 inter-anchor gaps over 90s but only 15 filler chunks. A filler is
only meaningful where a turn actually *starts* in the late part of the gap —
unflagged content that someone said. The other 5 gaps are long simply because
one enormous turn spans them, which is the anchor-point model working as
designed, not missing content. Emitting an empty filler for those would add
chunks with nothing in them.

**12. Most chunks legitimately have no turns at all, and the ratio is
structural.** 34 of TGS_127's 82 chunks are empty. Show-notes anchors are far
denser than speaker turns (67 anchors vs 93 turns across 105 minutes, and the
turns are wildly uneven — one is 4,998 characters), so a single long answer
routinely swallows five or six consecutive anchors. Do not "fix" this by
splitting turns at chunk boundaries; the turn is the real unit of speech.

**13. Never trust a document's stated count of source records — count them.**
The spec and the reference both say TGS_127 has "60 real show_notes entries";
the YAML actually has **67**. Whether the scrape grew or the count was wrong,
the source file is authoritative and hardcoding the doc's number would have
silently dropped seven chunks.

**14. Compare quote-folded when diffing prose against a hand-built reference.**
The scraped YAML carries typographic quotes (`'`, `'`) where the hand-built
reference has ASCII (`'`). Five such positions in TGS_127's description read as
a content difference but are purely a normalization artifact. Same field also
turned out to be hand-*truncated* in the reference — 543 chars (first paragraph)
against the YAML's real 1,228 (three paragraphs). Fold quotes AND check the
prefix relationship before calling a prose field divergent.

**15. Gotcha #3 (bare continuation timestamps) is NOT exercised by TGS_127.**
All 94 of its bracketed timestamps carry an explicit speaker label; the bare-
continuation count is zero. So a run that only validates against TGS_127 proves
nothing about the rule that matters most for monologues — `Frankly-145` and
`RR-24` are where it actually gets tested. Don't read a clean TGS_127 diff as
validating the turn parser generally.

**16. The outro fuses into the last turn's text, not a separate trailing
block.** In TGS_127 the sign-off boilerplate follows a `-----` separator after
Nate's final line, but any non-timestamped line appends to the current turn by
the continuation rule — so a naive parser silently ends the episode with
"...To be continued. If you enjoyed or learned from this episode..." Strip the
outro by searching the LAST TURN's own text for the boilerplate markers, not
only the text after the last turn.

**17. Transcripts carry stray NUL bytes too.** TGS_127's has 17. Same artifact
as the `.md` scrape corpus (see `extraction/shape/README.md`) — harmless to
Python but it makes `grep` treat the file as binary and skip it silently. Strip
on read; record that it happened.

**18. Use structured outputs for the NER call, not "return JSON" in the
prompt.** `output_config={"format": {"type": "json_schema", ...}}` makes a
malformed reply impossible, which matters at one call per chunk — a single
unparseable response would otherwise silently zero out a chunk's candidates
across a 48-call run. Keep `type_guess` a free-form string in the schema: the
spec requires SCHEMA-FREE extraction, so the schema must constrain the envelope
only, never the type vocabulary. (Confirmed working on `claude-opus-5`; the
model still chose 20+ distinct types unprompted, including ones no bundled
sift-kg domain has — `Material`, `Technology`, `Industry`, `TimePeriod`,
`Award_Recognition`.)

**19. The SDK version in this venv was two years stale and silently limiting.**
`anthropic` was pinned at `0.40.0`, which has no `thinking`, no
`output_config`, and no `messages.count_tokens` — so structured outputs, effort
control, and exact pre-flight token counting were all unavailable without
anyone noticing. Now `>=1.1.0` in `requirements.txt`. Note 1.x moves to
`httpx2`; if you import the HTTP layer directly, it is `import httpx2 as httpx`.

**20. Output-token volume per chunk is the cost driver, and it is easy to
underestimate by ~2x.** A pre-flight estimate assuming ~700 output tokens/chunk
projected $1.07/episode; the real run averaged ~806 output tokens across 48
chunks but with a long tail (a dense chunk emitted 40 candidates), landing at
$1.34. Estimate from a real 3-chunk probe, not from an assumed candidate count
— the probe took ~30 seconds and was within 40% where the a-priori guess was
not.

**21. Detect the outro STRUCTURALLY, not by keyword — RR-24 proves keywords are
not enough.** Its credits are four BARE-TIMESTAMP lines after a `-----`
separator, so the continuation rule appends all four to Nate's final turn and
the episode ends "...this blue-green ball. If you'd like to learn more about
this episode...". Keyword matching then makes it worse rather than better: the
only marker that fires is `hosted by`, which sits in the *third* credit
sentence, so the cut leaves two sentences of boilerplate glued to real speech.
The rule that works on all three bootstrap episodes: **the outro is everything
after the first separator that follows the LAST speaker-labelled turn.** That
needs a two-pass parse — you cannot know which turn is last on a single forward
pass. Keyword matching survives only as a fallback for transcripts with no
trailing separator, and it now records a note asking for the cut point to be
verified.

**22. Chunk-level NER DEGENERATES TO transcript-level for monologues — this
makes the spec's §2 comparison vacuous for that episode type.** `Frankly-145`
parses to exactly **one** turn for the whole 24 minutes (correct — that is what
gotcha #3 predicts). But turns are assigned to the chunk containing their start
time, so all content lands in chunk 1: **1 of 23 chunks holds anything**, 22 are
empty, and "one API call per chunk" becomes one call over the entire transcript.
Chunk-level and transcript-level NER are therefore *the same operation* here, at
the same cost, and comparing them can only ever show them identical.
**The unused signal that could fix this**: the 44 bare continuation timestamps
each carry a real time offset, currently merged into the turn's text and
discarded. They are the only sub-turn temporal structure a monologue has, and
they would align cleanly to show-notes anchors. Segmenting a single long turn at
bare-timestamp boundaries when it spans multiple anchors is the obvious
candidate fix — but it changes the `turns[]` semantics the spec deliberately
settled, so it needs a decision, not a quiet patch.

**23. `TGS_<number>` is not a unique key across series — the three series number
independently.** Reality Roundtable 24 and interview episode 24 both mint
`TGS_24`; Frankly 145 and interview 145 both mint `TGS_145`. The full IRIs stay
distinct because the EpisodeType prefix differs
(`tgs:PanelDiscussion.TGS_24_...` vs `tgs:Interview.TGS_24_...`), so nothing
literally breaks today. But CLAUDE.md decision 0d states that uniqueness comes
from `SourceAcronym + Number` **alone** and that the title fragment is "PURE
human readability [that] can be shortened or dropped without breaking
anything" — and that is false here. Needs a convention decision (distinct
acronyms such as `RR_`/`FR_`?). Flagged in each affected record's `_gaps`;
deliberately not re-designed, since CLAUDE.md requires an explicit go-ahead for
naming-convention changes.

## Real architectural decisions worth knowing before changing anything

**Chunking is show-notes-anchored, not algorithmic.** An earlier design
considered keyword-neighborhood chunking (auto-generated from ontology
labels) — rejected once it became clear every episode's own scrape
metadata already carries real, human-curated segmentation
(`show_notes: [{timestamp, seconds, topic, links}]`). Use it directly;
don't recompute what's already been curated.

**Output is self-contained, not reference-only.** Scraped episode
metadata (title, guests, description, etc.) is copied directly into each
episode's output JSON, not just pointed to by filename — avoids a later
DuckDB load needing to re-open the source scrape file.

**Chunks carry a nested `turns[]` array, not a flat `chunk_text`
string.** A single chunk can span multiple speakers (host asks, guest
answers, host follows up) — flattening that into one string loses real
speaker/timestamp structure. Each turn has its own `speaker`,
`start_seconds`, and `text`.

**NER extraction method — dual-tested, not assumed.** Both chunk-level
and transcript-level granularity get tested against each other on a
sub-sample (does fragmenting into chunks lose real entities a
whole-document pass would catch?), and schema-free extraction gets
tested against a custom structured domain (informed by sift-kg's
`academic` domain — AUTHOR/PUBLICATION/INSTITUTION/CONCEPT — plus two
real corpus-specific additions, `MATERIAL` and `SCHOOL_OF_THOUGHT`, that
no bundled domain covers). Real source available at
[github.com/juanceresa/sift-kg](https://github.com/juanceresa/sift-kg),
not just [docs](https://mintlify.wiki/juanceresa/sift-kg) — worth cloning
directly if any borrowed pattern (pre-dedup, resolution batching) needs
closer inspection than the docs describe. See the pilot spec's own
evaluation methodology (§2, §6) for the full reasoning — don't pick one
blind.
