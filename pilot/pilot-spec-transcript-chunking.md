# 30-Transcript Pilot Spec — Chunking + NER Candidate Extraction

**Status:** Ready to hand to Code, fourth pass — two open questions
resolved this session: output is self-contained (scraped metadata copied
in directly, not just referenced) and chunks carry a nested `turns[]`
array (speaker + own timestamp + own text per turn) rather than one flat
`chunk_text`, since a single chunk can span multiple speakers.

**Companion file: `TGS127_chunked_example.json`.** A real worked example
built by hand against actual TGS_127 (Ed Conway) source data — hand this
to Code alongside this spec, not as an optional extra. It proves the
schema below actually works against messy real data and resolves edge
cases prose alone leaves ambiguous: the teaser-stripping rule (§ below),
how a turn gets assigned when it runs past its own chunk's nominal
boundary, the real shape of an NER candidate entry including how to flag
a corpus inconsistency rather than just list a clean hit. **Treat it as
proof of shape, not a literal template** — a few things in it are
scaffolding from building it by hand in conversation, not part of the
real per-episode output: the `DUMMY_PLACEHOLDER_*` tags in early
iterations (later replaced with a real extraction pass on chunk 1
specifically, everything else in that file is still pending), the
`_note` fields explaining reasoning as it was being built, and
`cost_tracking: null` throughout (no real LLM call was ever made to
produce this file).

**Second companion file: `SKILL.md` (as `SKILL_transcript_pipeline.md`
in this handoff — rename to `SKILL.md` wherever your Claude Code skills
convention expects it).** Seeded with the real gotchas already found
during this session's design work, before Code has run once. **A living
document, not a one-time deliverable** — Code should keep adding to it
as the pilot actually runs and finds more, same discipline as this
repo's own `nate-hagens-ontology` skill file.

Inspired by [sift-kg](https://mintlify.wiki/juanceresa/sift-kg)'s
`sift extract` — borrowing its schema-free entity-candidate pattern and
its per-document cost-tracking discipline, not its chunking approach
(which is generic char-count chunking — wrong for this corpus, see below).
**Real source available, not just documentation**:
[github.com/juanceresa/sift-kg](https://github.com/juanceresa/sift-kg) —
Code can clone and read the actual implementation directly (pre-dedup
logic, resolution batching, postprocessing rules) rather than working
from documentation prose alone, useful if any of the borrowed patterns
above need closer inspection than the docs site describes.

**Folder layout — this is the real, expected handoff structure, not a
suggestion left implicit:**
```
pilot/
├── pilot-spec-transcript-chunking.md   (this file)
├── TGS127_chunked_example.json         (required companion, see above)
├── scraped-shownotes/
│   ├── <episode-slug>.md.json  (or .yaml, or website-export .md —
│   │                            markdown source needs prose parsing,
│   │                            not a structured schema, see §2.5)
│   └── ...
├── transcripts/
│   ├── <episode-slug>-TRANSCRIPT.md
│   └── ...
└── output/                             (empty; Code writes results here)
```
**File-pairing convention, stated explicitly so Code never has to guess
it**: a scraped-metadata file and its transcript pair share the same
`<episode-slug>` — strip the transcript's `-TRANSCRIPT` suffix and match
the remaining stem, extension-agnostic on the metadata side (`.md.json`
or `.yaml` both valid). **Filename convention**: hyphens only, no spaces
or parentheses — needed for reliable shell globbing and to avoid
quoting/escaping bugs that have nothing to do with the actual pilot logic.

---

## 1. Chunking — show-notes-anchored, not algorithmic

**Real correction from the original plan**: chunk boundaries are not
computed (no keyword-neighborhood heuristic, no fixed char/token window).
Every episode's own scrape output (`.yaml` or `.json` — same schema
either way, confirmed via a real sample from Code's own existing pipeline,
`RR-24-The-Fantasy-of-Space-Colonization`) already carries a real,
human-curated `show_notes` array (timestamp, topic, links) — Nate's
team's own segmentation. Use it directly:

1. Parse `show_notes` from the episode's scrape record: `[{timestamp, seconds, topic, links}]`.
2. For each consecutive pair of entries, a **topic-anchored chunk** spans
   `seconds[i]` to `seconds[i+1]` in the transcript, carrying that entry's
   real `topic` label and `links` as metadata — no LLM needed to produce
   this, it already exists.
3. Where a gap between consecutive entries exceeds a threshold (proposed:
   90 seconds — tune after seeing real gap-size distribution across the
   pilot's 30), split that stretch out as one or more **filler chunks** —
   real transcript content Nate's team didn't specifically flag. This is
   the only chunk type where the NER pass is actually adding structure
   that doesn't already exist.
4. **Alignment mechanism**: transcripts carry inline bracketed timestamps
   (`[00:19:29]` style) — use these to find the real character offset in
   the transcript text matching each show-notes timestamp, where present.
   **A bracketed timestamp does not always mark a new speaker turn** —
   real finding from RR-24: a bare `[timestamp]` with no `Speaker Name:`
   prefix following it is a paragraph break *within* the same ongoing
   turn, not a new one. Only a timestamp immediately followed by an
   explicit speaker name starts a new `turns[]` entry; a bare one
   continues appending to the current turn's text. Confirmed as the
   dominant pattern, not a rare edge case, via `Frankly-145`'s single
   24-minute monologue turn. **Timestamp presence and `transcript_source_type`
   are independent facts, not one implying the other** — corrected this
   session after an over-generalization: an *official* transcript can
   still lack inline timestamps entirely if they were stripped during
   editing (a real, human editing choice, confirmed to occur in this
   corpus), and a YouTube-caption-sourced transcript's own timestamp
   density varies too (confirmed: some carry a timestamp roughly every
   dozen words, an artifact of YouTube's own auto-captioning, almost
   certainly meaning no real speaker diarization at all, not just a
   different timestamp format). **Detect timestamp presence per
   transcript, don't infer it from source type** — the proportional
   character-count fallback (step 5 below, generalized) applies to any
   transcript lacking usable inline timestamps, regardless of why.
   YouTube-caption-sourced files remain excluded from this pilot's 30
   (§3) — not just for timestamp-density reasons, but because they likely
   lack speaker labels entirely, a harder problem than alignment alone.
   **Two genuinely independent findings, corrected this session after
   initially conflating them into one tier:**
   - **YouTube "Chapters" — a real, distinct third chunking-anchor
     mechanism, not a quality tier.** Some YouTube-derived transcripts
     carry algorithmically-inserted `## Chapter N:` groupings — YouTube's
     own judgment about where content breaks belong, arbitrary and coarse
     relative to Nate's team's real show-notes curation, but a genuine,
     structured signal in its own right. Worth its own field
     (`chunking_anchor_available: show_notes | youtube_chapters | none`)
     rather than being folded into a source-quality enum. **Real,
     constructive use for later**: for episodes with no official
     transcript at all, Chapters could serve as a legitimate third-tier
     fallback anchor — worse than real show-notes, better than blind
     proportional character-count splitting, since it reflects at least
     some content-aware segmentation (YouTube's, not Nate's team's). Out
     of scope for this pilot's own 30 either way, but worth designing for
     explicitly in the future custom pass rather than treated as noise.
     **Real fix for the "Chapters carry no clock-time" problem — reuse
     the existing proportional-estimation fallback, don't leave it
     unsolved.** A Chapter heading's real position sits at some fraction
     of the way through the transcript's own text; multiplied against the
     episode's real total `duration_seconds` (already in every scrape
     record), that gives a genuine, if approximate, estimated timestamp —
     the same technique already used for transcripts lacking real inline
     timestamps at all, just applied to a Chapter boundary instead of a
     show-notes one. Real assumption this leans on: roughly steady
     speaking pace across the episode — reasonable for a single
     continuous monologue voice, shakier anywhere pacing genuinely
     varies. Must carry the same `alignment_confidence: low` tag as the
     existing proportional fallback — never presented with the same
     confidence as a real inline timestamp.
     **Real decision, worth recording now**: when this fallback is
     eventually used, a Chapter's real title becomes the chunk's
     `topic_label` directly, using the exact same `topic_anchored` chunk
     shape as a show-notes-anchored chunk — not a separate chunk type.
     `curated_links` simply stays `[]` for these, since Chapters carry no
     equivalent link data; nothing else about the schema needs to change.
     Which anchor mechanism produced a given episode's chunks is already
     tracked once, at the episode level (`chunking_anchor_available`) —
     no need to duplicate that on every individual chunk.
   - **Embedded caption-metadata corruption — a separate, independent
     text-quality defect.** Confirmed real example: a timestamp and
     duration fused directly into running prose with no separator,
     breaking real words apart mid-sentence. This can occur on any
     transcript regardless of whether it has Chapters, dense captions, or
     neither — it's a text-quality problem, not tied to which
     chunking-anchor mechanism is available. Worth its own independent
     flag (`has_embedded_metadata_corruption: true | false`) rather than
     a single combined enum value implying the two always co-occur.
   All YouTube-derived variants stay excluded from this pilot's 30
   regardless of these two flags' values — the distinction matters for
   scoping the future custom pass, not this pilot's own selection filter.
5. **Fallback for missing/unusable timestamps**: proportional
   character-count splitting between named show-notes topics, applied to
   *any* transcript where real inline timestamps aren't usable — flag
   these explicitly (`alignment_confidence: low`) rather than silently
   treating them the same as a real-timestamp-aligned file. An episode
   whose YAML has an empty/missing `show_notes` array entirely falls back
   further, to filler-only chunking (one filler chunk per ~N minutes, N
   TBD from real average chunk-length once the pilot's topic-anchored
   chunks are measured).
6. **Trailing outro/credits, teaser stripping, and speaker count — detect
   directly from each transcript, never branch on genre.** Real
   correction this session: earlier passes treated these as
   genre-determined ("Frankly never has X, Interview/Panel always does")
   from a single example per genre — an overgeneralization, not a
   finding. The honest version: TGS_127 had a teaser and an outro;
   RR-24 had both too, plus 3+ speakers; `Frankly-145` had neither and
   one speaker throughout — but a real guest-Frankly episode is known to
   exist in this corpus, meaning genre predicts none of these reliably.
   Correct design: **check each transcript's own actual content for a
   teaser (real content vs. a soundbite from later in the conversation
   preceding the host's first real turn), an outro (boilerplate
   sign-off/credits after the last real turn), and however many distinct
   speaker labels actually appear** — never assume any of these from the
   episode's segment type. The multi-speaker `turns[]` handling validated
   via RR-24 is a general capability the pipeline needs for any episode,
   not an RR-specific code path.
   settled, but the need to strip it for that format is now confirmed,
   not hypothetical.

---

## 2. NER candidate extraction — dual granularity, tested not assumed

Per this session's discussion: test **both** chunk-level and
transcript-level extraction rather than picking one blind — this is
exactly the kind of empirical question this pilot exists to answer.

- **All 30 transcripts**: chunk-level NER (one LLM call per chunk — both
  topic-anchored and filler chunks get a pass, though filler chunks are
  where it matters most since they have no other structure).
- **A 5-transcript sub-sample, Interview/Panel types only**: also run
  transcript-level NER (one LLM call per whole transcript) for direct
  comparison — does fragmenting into chunks lose real entities a
  whole-document pass would catch, and at what cost difference?
  **Excludes monologues, per a real finding from Phase 0**: a Frankly
  episode produces exactly one turn with content (everything attaches to
  the chunk containing that turn's start), so "chunk-level" and
  "transcript-level" collapse into the literal same API call for that
  type — the comparison isn't just uninformative there, it's
  mathematically undefined, and would silently report "identical" every
  time regardless of whether there's a real question to answer. Confirmed
  directly: Frankly-145's own chunk-level and transcript-level NER were
  one identical operation at one identical cost ($0.09, not a genuine
  saving). A real fix exists (segmenting a long monologue turn at its own
  bare-timestamp boundaries) but requires overriding the turn-continuation
  rule (`SKILL.md` gotcha #3) deliberately settled on — flagged as an open
  decision, not implemented here.
- **Schema-free**, matching sift-kg's own pattern — do not constrain
  extraction to this ontology's existing Concept/Persona/SchoolOfThought
  types. The whole point is discovering what's NOT yet captured; forcing
  candidates into existing categories would defeat that.
- **Explicitly reference-only**: nothing from this pass gets minted. Real,
  human-curated `topic`/`links` metadata from step 1 is a *separate*,
  higher-confidence signal already in the data — don't conflate the two
  qualities in the output shape (see schema below).

**Sub-sample selection**: pick the 5 for real range, not convenience —
at least one very show-notes-dense episode, one sparse one, one with a
large filler-gap, and a mix of Interview/Monologue/Panel types if the 30
includes more than one segment type.

**Third real comparison, added this session: schema-free vs. a custom
structured domain.** Reviewed all three of sift-kg's bundled domains
(general, osint, academic) against real content from this corpus.
Neither bundled domain is a clean fit: `academic` (AUTHOR, PUBLICATION,
INSTITUTION, CONCEPT, DATASET, METHOD) is genuinely strong on four of six
types — AUTHOR/PUBLICATION/INSTITUTION/CONCEPT map closely onto this KG's
own existing classes and onto real content already handled by hand this
session (Ed Conway as AUTHOR of the PUBLICATION Material World; LSE as an
INSTITUTION) — but DATASET/METHOD feel imported from formal-paper
conventions this conversational corpus doesn't really have. `osint`
(PERSON, ORGANIZATION, LOCATION, IP_ADDRESS, URL, PHONE_NUMBER, EMAIL) is
weaker than it first appears — IP_ADDRESS/PHONE_NUMBER/EMAIL would almost
certainly return zero real hits across this whole corpus.

**Recommended instead: a custom structured domain**, using academic's
four strong types as a backbone plus two real, corpus-specific additions
neither bundled domain has any equivalent for:
- **MATERIAL** — the six critical materials aren't cleanly a CONCEPT
  (physical substances, not ideas); no bundled domain has anything for
  this.
- **SCHOOL_OF_THOUGHT** — this KG already has a real, established class
  for this (TechnoOptimism, Degrowth, etc.); no bundled domain covers it.

Plus real, evidenced relation types — not hypothetical, found by hand
this session: `AUTHOR_OF` (Ed Conway → Material World), `MATERIAL_REQUIRES`
(salt → lithium, salt → glass — real cross-material dependencies from
TGS_127's own transcript), `DISCUSSED_IN` (Concept → Episode).

**Run this as a third empirical comparison on the same 5-transcript
sub-sample**, not a blind swap-in: schema-free is better suited to
*discovery* (finding categories not yet known to look for, matching this
pilot's own "what's currently hidden" goal), a good custom domain is
better suited to *consistency* across all 30 episodes (same types
extracted uniformly, directly aggregable). Worth knowing which actually
earns its cost before committing either way for the real 30-episode run.

---

## 2.5 Phase 0 — four-episode bootstrap (one per segment type + one
format outlier), before the 30

**Expanded from a single episode, per this session's discussion**: one
Frankly monologue, one Reality Roundtable panel, one Interview
(`TGS_127`), plus a fourth — `TGS_231` (Greg Elliott), run through Code
before the 30-episode pilot — both to compare output against a known-good
reference and to isolate one-time
setup cost from real per-episode marginal cost.

**Why three, not one — resolves two real open questions, not just adds
robustness for its own sake:**
- **Frankly (monologue) — RESOLVED, via `Frankly-145`.** Neither the
  cold-open teaser nor the trailing outro/credits block appear at all —
  Nate's monologue starts real content immediately at `[00:00:00]` and
  ends right after his own closing line, no sign-off boilerplate. Both
  the teaser-strip rule (from TGS_127) and the outro-strip rule (from
  RR-24) are **genre-conditional, not corpus-universal** — real, now
  confirmed rather than assumed. Solo-speaker structure also validated
  cleanly: the whole 24-minute piece is one continuous `turns[]` entry,
  every bracketed timestamp after the first a bare continuation marker —
  the dominant real case for the bare-timestamp fix below, not a rare
  edge case.
- **RR (panel)**: tests the `turns[]` schema against 3+ speakers for the
  first time — TGS_127 only ever exercised host+one-guest. A real
  structural case single-episode testing couldn't have caught, since
  nothing in a two-person conversation would surface a bug specific to
  handling three or more.
- **Interview (`TGS_127`)**: already run, already has a real hand-
  verified reference (`TGS127_chunked_example.json`) to check Code's
  automated output against directly.
- **Format outlier (`TGS_231`, Greg Elliott) — a real, useful complication,
  not just a fourth data point.** Show notes for this episode come from
  the website's own page markdown, not structured YAML/JSON — a genuine
  third source format. Its "Citations by Timestamp" section is much
  denser than the other episodes' `show_notes` arrays (100+ entries
  across ~98 minutes, versus TGS_127's 60) and has no precomputed
  `seconds` field (`HH:MM:SS` needs real parsing, including an hour-
  inclusive vs. not edge case: `1:38:32` vs. `02:04`). More importantly,
  it's structurally a different *kind* of thing — an exhaustive citation
  list, not discrete topic-segment markers — forcing every entry into its
  own chunk boundary would fragment this episode absurdly. **Real,
  valuable reframe**: treat this dense list as a genuine human-curated
  ground truth for validating NER extraction quality directly (precision/
  recall against a real reference), something none of the other three
  bootstrap episodes could offer — and use coarser fallback chunking
  (proportional splitting, or clustering closely-spaced citation entries
  into single chunks) for this episode's actual chunk boundaries, rather
  than the dense list itself.

**Partial, not full, mitigation of the materials-episode bias flagged
last pass**: testing across three content types makes it harder for the
custom domain's apparent value to be an artifact of one favorable
episode — but only if the Frankly and RR picks are chosen deliberately
for topical diversity too, not just structural-type diversity. Recommend
picking ones that are *not* primarily about physical materials/supply
chains — otherwise the same bias just recurs across three episodes
instead of one. **Real, honest limitation**: only `TGS_127` has a
hand-verified ground truth to compare against; the Frankly and RR picks
won't have that same comparison-quality check unless separate worked
examples get built for them too (real additional effort, not assumed
here — the main value of the other two is structural coverage, not a
second and third hand-verification pass).

**Cost reporting — two numbers, not one, per episode**: real one-time
setup cost (writing/debugging the actual chunking script, sorting out
source-type detection, any tooling friction — largely a Phase 0 cost,
shouldn't repeat three times) reported separately from each episode's own
real marginal processing cost. Carry this same separation into the
30-episode pilot's own cost tracking too — worth knowing the true
marginal-cost curve independent of whatever one-time overhead the first
run(s) absorb, and worth seeing whether marginal cost itself differs
meaningfully by segment type across these three.

**What three episodes can and can't settle — still worth being precise
about, not overclaiming.** Sufficient: shape verification across all
three real structural patterns this corpus contains. Three real cost data
points, one per type — a real improvement over one, still not a full
projection (real duration variance exists *within* each type too). NOT
sufficient on its own: the chunk-vs-transcript NER comparison and the
schema-free-vs-custom-domain comparison (§2) still need the formal
5-transcript sub-sample or the full 30 before being treated as settled —
three episodes can show these comparisons *behave differently by type*
(a genuinely useful, testable hypothesis), but three data points still
isn't enough to establish how often either failure mode occurs across the
whole corpus.

---

## 3. Pilot transcript selection (the 30)

**First filter, non-negotiable for this pilot**: select only from the
clean/official-transcript population (Nate's team's own transcripts, real
inline timestamps) — explicitly exclude YouTube-caption-sourced episodes
from this pilot, since those need a separate custom alignment pass this
pilot isn't testing. Mixing the two populations would make the pilot's
cost/shape results look like they generalize to the whole remaining
corpus when they'd only actually be valid for part of it.

**Within that clean population**, a random or convenience sample still
risks a biased token-cost extrapolation (e.g., all short Frankly
monologues would understate the real cost of 90-minute Interviews).
Recommend selecting across real, known variation:
- Episode type: Interview, Monologue, Panel Discussion — proportional to
  their real share of the ~348-episode corpus if known, or at minimum a
  meaningful count of each, not zero of any.
- Duration: include some of the shortest and longest known episodes, not
  just typical-length ones.
- Show-notes density: at least a few with sparse show notes (more filler
  chunks, different cost profile than dense ones).

---

## 4. Output schema (pre-staging — explicitly NOT relational form yet)

One JSON file per transcript, matching sift-kg's own per-document output
pattern (safe to resume/re-run incrementally, matches this repo's own
established one-file-per-unit convention elsewhere).

**Two resolutions from this session's discussion, both now reflected
below**: (1) **self-contained** — the episode's own scraped metadata
(title, guests, description, etc.) is copied in directly, not just
referenced by pointer, so a later DuckDB load never has to re-open the
source scrape file; (2) **turn-level speaker structure** — a chunk can
span multiple speakers (Nate asks, a guest answers, Nate follows up), so
`chunk_text` as one flat string was wrong. Each chunk now holds a
`turns[]` array — speaker, its own precise timestamp, and its own text —
nested inside the chunk. Chunk-level NER (§2) runs over the concatenation
of a chunk's own turns at processing time, not a separately stored,
possibly-inconsistent duplicate field.

```json
{
  "episode_iri": "tgs:Interview.TGS_127_EdConway or null if not yet built",
  "source_transcript_file": "...",
  "source_yaml_file": "...",
  "source_sha256": "reused directly from the episode's own scrape record, not recomputed",
  "transcript_source_type": "official | youtube_caption",
  "chunking_anchor_available": "show_notes | youtube_chapters | none",
  "has_embedded_metadata_corruption": false,

  "title": "reused directly from the scrape record — self-contained, per this session's resolution",
  "webpage_url": "...",
  "youtube_url": "...",
  "duration_seconds": 5796,
  "published_date": "...",
  "recorded_date": "...",
  "keywords": ["..."],
  "host": "...",
  "guests": ["..."],
  "guest_bios": [ { "name": "...", "bio": "..." } ],
  "description": "...",
  "transcript_speakers": ["reused directly — free validation signal: a competent NER pass should at minimum rediscover these names"],

  "chunking_method": "show_notes_anchored",
  "_provenance": {
    "alignment_confidence": "high (real inline timestamps) | low (fallback proportional split)",
    "chunking_method": "site:show_notes | fallback:filler_only"
  },
  "_gaps": ["following this project's own established convention (see the scrape record's own _gaps field) — e.g. 'no inline timestamps, used proportional fallback' rather than a differently-named ad hoc field"],

  "chunks": [
    {
      "chunk_id": "...",
      "chunk_type": "topic_anchored | filler",
      "start_seconds": 0,
      "end_seconds": 255,
      "topic_label": "Bill Plotkin info + works... (null if filler)",
      "curated_links": [ { "label": "...", "url": "..." } ],
      "turns": [
        { "speaker": "Nate Hagens", "start_seconds": 0, "text": "..." },
        { "speaker": "Tom Murphy", "start_seconds": 12, "text": "..." }
      ],
      "ner_candidates": [
        { "text": "...", "type_guess": "...", "confidence": 0.0, "context": "..." }
      ]
    }
  ],
  "transcript_level_ner": null,
  "cost_tracking": {
    "chunk_level_input_tokens": 0,
    "chunk_level_output_tokens": 0,
    "transcript_level_input_tokens": null,
    "transcript_level_output_tokens": null,
    "estimated_cost_usd": 0.0,
    "model_used": "...",
    "extracted_at": "..."
  }
}
```

`transcript_level_ner` and the `transcript_level_*_tokens` fields are only
populated for the 5-transcript sub-sample; `null` elsewhere — makes the
comparison directly queryable across the 30 without a second file format.

---

## 5. What this pilot actually answers

- **Token/cost projection**: real per-transcript token counts (both
  granularities) × the real remaining-episode count → an honest full-corpus
  estimate — **valid for the official-transcript population specifically,
  not the whole remaining corpus.** YouTube-caption-sourced episodes are a
  known, separate problem (different format, needs a custom alignment
  pass) and should get their own future costing pass rather than being
  assumed to follow the same per-transcript cost curve as this pilot's
  results. Worth knowing roughly how many of the remaining episodes fall
  into each population, if that's not already tracked somewhere, since it
  directly affects how much of the full-corpus budget this pilot's numbers
  actually cover.
- **Shape verification**: does this JSON structure actually hold up against
  30 real, varied transcripts, or does something (a transcript with no
  inline timestamps, a show_notes array with a real gap, an unusually
  dense episode) break an assumption before it's discovered at full scale.
- **NER candidate reference**: a real, concrete answer to "what's currently
  in these transcripts that isn't yet in the ontology" — informs future
  minting sessions, mints nothing itself. One real example already found
  by hand (see the TGS_127 worked example): three conflicting renderings
  of the same real person across this corpus's own source artifacts
  ("Simon Michaux," "Michael Michaux," "Simon Michaud"). Resolving
  candidates like this into real, merged entities is deliberately a later,
  separate stage — sift-kg's own documented two-layer approach (fast
  deterministic/fuzzy pre-dedup, then a slower human-reviewed LLM
  resolution pass for genuinely dissimilar-looking name variants) is a
  credible reference architecture for that future work, not something to
  build now. Worth noting their own documented limitation directly
  applies to cases like ours: default alphabetical batching can leave
  genuinely different-looking variants of the same entity never compared
  at all (their own real example: "Robert Smith" and "Bob Smith" landing
  in separate batches) — exactly the shape of the Michaux/Michaud case.
