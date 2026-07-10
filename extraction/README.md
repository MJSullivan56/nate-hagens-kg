# Extraction pipeline (transcripts → candidate concepts/links)

This is the "expansion" stage — run *after* the seed graph exists, not before.
Goal: mine the ~225 episode transcripts for (a) new concepts you missed, (b)
evidence for/against candidate cross-links, (c) which episodes discuss which
concept (for the `tgs:discussedIn` property).

## Step 1 — Get the transcripts
Most episodes have a PDF transcript at a predictable URL pattern:
`https://www.thegreatsimplification.com/wp-content/uploads/<year>/<month>/TGS-<episode#>-<Guest-Name>-Transcript.pdf`
Scrape the episode list page for the actual links rather than guessing the
pattern — it isn't fully consistent across years. Respect the site's
robots.txt / terms; this is for personal research use.

## Step 2 — Extract text
Standard PDF-to-text (pdfplumber / pypdf). These are already transcripts, not
scanned images, so no OCR needed.

## Step 3 — Per-episode LLM pass
For each transcript, prompt an LLM (chunked if long) with:
- The list of existing seed concepts + one-line definitions (from `concepts.ttl`)
- Ask it to return, as structured JSON:
  1. Which existing concepts are substantively discussed (not just name-dropped)
  2. Any new candidate concept it thinks is missing from the seed list, with
     a proposed definition and the strongest supporting quote span (short,
     for internal reference only — don't republish long quotes)
  3. Any guest-introduced idea that seems to deserve its own node

This is the step where you're already set up well: Claude (via the API, or
this very interface) can do the extraction pass. Keep it structured JSON out,
not free text, so it's mechanical to turn into triples.

## Step 4 — Candidate link generation
Separately from per-episode extraction, take the *seed concept list* and the
*seed people list* and ask an LLM to propose plausible `echoesIdeaOf` /
`influencedBy` / `contrastsWith` links with a one-paragraph rationale each —
same pattern as `data/seed/links.ttl`'s "candidate" example. Mark everything
`tgs:confidence "candidate"` on ingest. Never auto-promote to "curated" —
that review step is where the actual intellectual value of this project
lives; skipping it turns the graph into forced trivia-style parallels.

## Step 5 — Review queue
Use SPARQL query #4 in `scripts/query_examples.sparql` to pull every
candidate link and go through them manually (or with a second LLM pass
specifically prompted to be skeptical/adversarial toward the first pass's
proposals — "is this a real connection or just surface pattern-matching?").
Promote to `"curated"` only after that.

## Step 6 — Re-ingest
Append reviewed triples to `data/seed/` files (or split into
`data/generated/` to keep provenance clear) and re-run `load_oxigraph.sh`.

## A note on scale
Don't process all 225 episodes before validating the pipeline. Run steps
1-4 on ~5 episodes first, hand-review the output quality, and adjust the
extraction prompt before scaling up. LLM concept-extraction quality varies
a lot based on prompt specificity — better to catch that early than after
processing the whole backlog.
