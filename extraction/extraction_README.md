# extraction/ — transcript library, entity triage, and the LLM extraction plan

This folder has grown into two genuinely different things: (1) real,
working, tested infrastructure for building a local reference library and
triaging it for named entities, and (2) a still-largely-aspirational plan
for LLM-assisted concept/link extraction at scale. Both live here; this
README covers both, clearly separated.

## What's actually built and working

**Download the reference library:**
```bash
python extraction/download_transcripts.py --type frankly
python extraction/download_transcripts.py --type interview
python extraction/download_transcripts.py --type roundtable
```
Sitemap-based discovery (primary, comprehensive) supplemented by the
listing page (catches the newest few items not yet in the sitemap).
Resumable — tracks what's downloaded in `download_manifest.csv` and what's
confirmed to have no transcript in `no_transcript_available.csv`, skips
both on rerun. Respects the site's `Crawl-delay: 10` directive.

**Match locally-saved Substack summary PDFs against the manifest:**
```bash
python extraction/match_substack_summaries.py
```
Exact Frankly-number matching as the primary strategy (a number printed
directly in each Substack PDF, cross-referenced against the episode URL),
falling back to fuzzy title matching only when no number is extractable.
Writes `substack_summaries_index.csv` (metadata only — the extracted text
itself stays in a local, gitignored cache, never committed, consistent
with this project's copyright discipline throughout).

**Index named entities across the whole downloaded corpus:**
```bash
python extraction/index_named_entities.py              # index new documents only
python extraction/index_named_entities.py --refilter     # re-apply current filters, no NER re-run
python extraction/top_persons.py                          # ranked worklist of PERSON entities
```
Two-layer design: NER itself (expensive, via spaCy) runs once per
document and caches raw results; filtering (which entity types to keep,
known-noise reclassification) is cheap and rerunnable via `--refilter`
without touching spaCy again. This is a TRIAGE tool, not a source of
truth — see its own module docstring for the full reasoning, and
`CLAUDE.md`'s bootstrap-a-person procedure for what actually happens with
a name once it surfaces here (search, verify, check for wrong-person
traps, THEN add to the graph — never mechanically promoted).

## The LLM extraction plan (aspirational — not yet run at scale)

Goal: mine the transcript library for (a) new concepts missed during
seeding, (b) evidence for/against candidate cross-links, (c) which
episodes discuss which concept. This is the "expansion" stage — run
*after* the seed graph exists, which it now does.

### Step 1 — Transcripts
Already solved by `download_transcripts.py` above — this step used to be
its own manual research effort; it isn't anymore.

### Step 2 — Extract text
Standard PDF-to-text (`pdfplumber`, already a dependency). These are
transcripts, not scanned images — no OCR needed.

### Step 3 — Per-episode LLM pass
For each transcript, prompt an LLM (chunked if long) with:
- The list of existing seed concepts + one-line definitions (from `concepts.ttl`)
- Ask it to return, as structured JSON:
  1. Which existing concepts are substantively discussed (not just name-dropped)
  2. Any new candidate concept it thinks is missing, with a proposed
     definition and the strongest supporting quote span (short, for
     internal reference only — don't republish long quotes, same
     copyright discipline as everywhere else in this project)
  3. Any guest-introduced idea that seems to deserve its own node

Keep it structured JSON out, not free text, so it's mechanical to turn
into candidate rows.

### Step 4 — Candidate link generation
Separately, take the seed concept list and seed people list and ask an
LLM to propose plausible `thinkr:echoesIdeaOf`/`thinkr:influencedBy`/
`thinkr:contrastsWith` links with a one-paragraph rationale each.

**On ingest, every candidate becomes a real `thinkr:Evidence` individual**
(`data/seed/evidences.ttl`'s pattern) with:
- `thinkr:confidence thinkr:ConfidenceType.Candidate` (never
  `ConfidenceType.Curated` on ingest — that's a human-review-only value,
  enforced by CI)
- `thinkr:evidencePolarity` (Supports/Contests/Mentions)
- `thinkr:aboutSource` pointing to a real `thinkr:Source` individual
  (which itself needs a `thinkr:reliabilityTier` — see `CLAUDE.md`'s
  design decision on why domain-scoped reliability is still an open
  backlog item, not yet needed at this scale)
- `dcterms:description` with the rationale

The `thinkr:LinkNote` itself (`data/seed/linknotes.ttl`'s pattern) gets
`thinkr:hasEvidence` pointing at that Evidence — its own
`thinkr:calculatedConfidence` is NEVER hand-set, only ever derived by
`scripts/compute_confidence.py`. Never auto-promote a candidate to
Curated — that review step is where the actual intellectual value of
this project lives; skipping it turns the graph into forced
trivia-style parallels instead of a curated argument.

### Step 5 — Review queue
Use `scripts/query_examples.sparql` to pull every Candidate-confidence
Evidence and go through it manually (or with a second LLM pass
specifically prompted to be skeptical/adversarial toward the first
pass's proposals — "is this a real connection or just surface
pattern-matching?"). Change `thinkr:confidence` to `Curated` only after
actual human review, then re-run `scripts/compute_confidence.py` to
propagate the change into `calculatedConfidence`.

### Step 6 — Re-ingest
Append reviewed triples to `data/seed/` (or `data/generated/`, matching
`promote_to_rdf.py`'s existing pattern, to keep provenance clear) and
re-run `scripts/load_oxigraph.sh`.

### A note on scale
Don't process the whole library before validating the pipeline. Run
Steps 3-4 on a handful of episodes first (the entity-index worklist from
`top_persons.py` is a reasonable place to start — highest-signal names
first), hand-review the output quality, and adjust the extraction prompt
before scaling up. LLM concept-extraction quality varies a lot based on
prompt specificity — better to catch that early than after processing
the whole backlog.
