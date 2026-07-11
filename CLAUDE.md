# Nate Hagens Knowledge Graph — Claude Code context

**Last comprehensive update: 2026-07-10.** This file was consolidated on
that date after several sessions of incremental edits — if you're reading
this much later, treat everything below as accurate as of that date, then
check `git log --oneline -20` for what's happened since. Don't trust this
file's currency blindly; the git history is the real source of truth.

## What this project is
An RDF knowledge graph connecting Nate Hagens' "Great Simplification"
(TGS) framework — energy, ecology, economics, human behavior — to the
philosophers, scientists, and activists whose ideas it echoes, draws on,
or usefully contrasts with. Goal: make the framework navigable and
legible to students, activists, data people, and general audiences.
Repo: https://github.com/MJSullivan56/nate-hagens-kg (branch `main`).

## Stack
- RDF/Turtle as source of truth (`ontology/`, `data/seed/`)
- Oxigraph as the query engine (installed via `brew tap oxigraph/oxigraph
  && brew install oxigraph`; confirmed working, version 0.5.0-beta.4 as of
  last check)
- DuckDB as a staging/review database for LLM-proposed candidate links
  (`extraction/staging.duckdb`, gitignored, not committed)
- Python venv (`make venv`) for all scripting — see KNOWN GOTCHA below
  before assuming a fresh `make venv` will just work
- VS Code: SPARQL Notebook extension (`Zazuko.sparql-notebook`) lets you
  query `.ttl` files directly in the editor — install status on Jim's
  machine was never confirmed as of last check, verify before assuming

## Key design decisions (the "why" behind the schema)
These are the load-bearing choices — worth understanding before making
structural changes:

1. **Curated vs. candidate confidence tracking is the most important
   design decision in the whole project.** An LLM can propose hundreds of
   plausible-sounding parallels between TGS concepts and historical
   thinkers, but most surface pattern matches ("both talk about balance!")
   aren't intellectually honest links. Nothing should present as a real
   connection to an end user until a human has reviewed it. This is
   enforced structurally: `tgs:confidence` is an `owl:ObjectProperty`
   pointing to one of exactly two enumerated individuals,
   `tgs:ConfidenceLevel.Curated` or `tgs:ConfidenceLevel.Candidate` (see
   `ontology/schema.ttl` — closed enumeration via `owl:oneOf`). CI
   actively validates every `tgs:LinkNote` has one of these two values,
   not just that some value is present.

2. **Every individual follows `<Domain>:<Class>.<Name>` IRI minting**
   (e.g. `tgs:Person.MarcusAurelius`, `tgs:Concept.Overshoot`,
   `tgs:LinkNote.DiscountMarcus`) and is explicitly typed
   `a tgs:SomeClass, owl:NamedIndividual` — this is Jim's established
   convention from his other ontology work, adopted here for consistency.
   Classes and properties themselves (in `ontology/schema.ttl`) are NOT
   renamed under this scheme — only individuals/instances are.

3. **`skos:prefLabel` instead of `rdfs:label`** everywhere, in
   anticipation of using `skos:altLabel` for alternate names down the
   line. Applies to both schema-level (class/property names) and
   individual-level data, for consistency.

4. **All natural-language literals get an `@en` tag**, in anticipation of
   future multi-language support. EXCEPTION: controlled-vocabulary /
   enum-style values (like the old `tgs:confidence` strings, now replaced
   by actual individuals per point 1) should NOT get language tags —
   they're codes, not prose to translate.

5. **`owl:sameAs` links to BOTH DBpedia and Wikidata** on people/schools
   where possible — DBpedia for broad, low-effort Wikipedia-mirrored
   coverage; Wikidata added deliberately per-entity because it's more
   actively maintained and has its own SPARQL endpoint. Only 2 of ~23
   people/schools have verified Wikidata links so far (EOWilson, Marcus
   Aurelius) — see `data/seed/wikidata_links.ttl`. CRITICAL: Wikidata
   Q-numbers have no mnemonic structure and are genuinely easy to get
   wrong (a plausible-looking search hit for "Marcus Aurelius Antoninus"
   is actually a disambiguation page, Q1632736 — the real entity is
   Q1430). Never copy a Q-number from memory; always verify the
   description on the search hit actually matches the intended person
   before adding.

6. **Concept/School definitions are paraphrases, not verbatim Hagens
   quotes** — copyright and accuracy reasons. They're first-draft glosses
   based on public descriptions of his framework, not checked against
   actual transcripts/book text. Worth tightening against primary sources
   over time, not urgent.

## Current data state (as of 2026-07-10)
- 407 triples total (`make validate` should confirm this exactly)
- ~19 Concepts, ~25 People, 6 Schools (including the Peak Oil movement,
  deliberately kept distinct from the `PeakOil` Concept — see
  `data/seed/people.ttl` for the reasoning), 14 LinkNotes (13 curated, 1
  deliberately-marked candidate as a review-queue example)
- Files: `data/seed/concepts.ttl`, `people.ttl`, `links.ttl` (original
  seed), plus `expansion_2026-07-10.ttl` (Jevons Paradox, Limits to
  Growth, Peak Oil, Complexity/Collapse, Money-as-energy-claim batch) and
  `wikidata_links.ttl` (the 2 verified Wikidata links)

- Extension identified but not yet built: cross-tradition "convergent
  parallel" links (e.g. Stoicism ↔ the Bhagavad Gita — independently
  developed traditions converging on similar ideas, with no causal
  lineage). The current schema CANNOT express this: every relation
  property has `rdfs:domain tgs:Concept`, so Schools can only ever be the
  *object* of a relation, never the subject — there's no School-to-School
  or School-to-Work property at all. Recommended fix when this comes up:
  (1) a new symmetric property, e.g. `tgs:convergesWith`
  (`a owl:SymmetricProperty`), distinct from `influencedBy`/`echoesIdeaOf`
  specifically because those imply direction/lineage and this doesn't;
  (2) model specific texts (like the Bhagavad Gita) as `tgs:Work`
  instances — that class has existed since the original schema but has
  zero instances so far — rather than stretching `tgs:School` to cover
  individual texts. Link at the text level first (more precise/citable);
  only add a broader tradition-level School (Vedanta, etc.) if multiple
  texts from one tradition need linking at once. CORRECTION LOGGED
  2026-07-10: blank nodes were briefly proposed for provenance on these
  claims — this would be a mistake. Blank nodes have no stable identity
  across file re-saves/merges/different-tool-loads, which is exactly why
  `tgs:LinkNote` was deliberately built as a NAMED individual in the first
  place (the curated/candidate review workflow depends on being able to
  reference one specific claim reliably over time — approve it in DuckDB,
  promote it, audit it later, diff it cleanly in git). If richer
  provenance than the current LinkNote gives (source citation, reviewer
  identity, review date, methodology) is wanted later, reach for PROV-O
  (`prov:wasAttributedTo`, `prov:wasGeneratedBy`, `prov:generatedAtTime`,
  `prov:wasDerivedFrom`) hung off named individuals, not blank nodes.
  Blank nodes remain fine for genuinely anonymous structural scaffolding
  only — e.g. the existing `owl:oneOf` list inside `ConfidenceLevel`'s
  enumeration, which nothing will ever need to reference by identity.

## Backlog (priority-ranked, as of 2026-07-10)

**HIGH — Evidence/claim provenance model.** Currently `tgs:LinkNote` conflates
the assertion ("Stoicism relates to X") with its evidence (one description,
one hand-set confidence). Proposed refactor: `LinkNote` becomes the stable
anchor for the claim itself; a new `tgs:Evidence` class holds individual
supporting/contesting pieces, each with its own `dct:description`,
`tgs:confidence`, and PROV-O attribution (`prov:wasAttributedTo`,
`prov:wasGeneratedBy`, `prov:generatedAtTime`, `prov:wasDerivedFrom` — see
the provenance note below). One `LinkNote` can have many `Evidence` children.
`LinkNote` gets a new `tgs:calculatedConfidence` — explicitly DERIVED, never
hand-asserted, computed from its Evidence set by a script or live SPARQL
aggregate (same pattern as `promote_to_rdf.py`) — never hand-written into a
TTL file, or it'll drift out of sync with its own evidence. OPEN DECISION,
Jim's call when this gets built: aggregation rule. Leaning recommendation:
ordinal not numeric, consistent with how `ConfidenceLevel` already works and
this project's general allergy to manufactured precision — e.g. `Curated` if
≥1 curated Evidence, a possible third tier like `Corroborated` for 2+
independent curated sources, rather than a weighted numeric score that would
look more rigorous than it actually is. This is a bigger change than it
sounds: touches the schema, the review workflow, and probably the DuckDB
staging tables (Evidence rows would need their own review queue).

**HIGH — Cross-tradition "convergent parallel" property.** Concrete trigger
case: Stoicism ↔ the Bhagavad Gita — independently-developed traditions
converging on similar ideas (equanimity toward outcomes, duty without
attachment to results), with no causal lineage between them. Schema
currently CANNOT express this at all: every relation property has
`rdfs:domain tgs:Concept`, so a `tgs:School` can only ever be the *object* of
a relation, never the subject — no School-to-School or School-to-Work
property exists yet. Recommended fix: (1) a new symmetric property, e.g.
`tgs:convergesWith` (`a owl:SymmetricProperty`) — deliberately distinct from
`influencedBy`/`echoesIdeaOf`, which both imply direction/lineage this
relationship doesn't have; (2) model specific texts (the Bhagavad Gita) as
`tgs:Work` instances — that class has existed since the original schema but
has zero instances so far — rather than stretching `tgs:School` to cover
individual texts. Link at the text level first (more precise/citable); only
add a broader tradition-level School (Vedanta, etc.) if multiple texts from
one tradition need linking at once. Note: this property will need the SAME
Evidence-backed provenance treatment as the item above, probably more so —
"these two ancient traditions converge" is a much bigger, more contestable
claim than a single concept-to-person link, and correspondingly easier for
an LLM to generate plausible-sounding versions of if extraction ever points
at it.

**CORRECTION LOGGED 2026-07-10 — blank nodes are NOT the right tool for
either item above.** Blank nodes were briefly proposed for provenance —
this would be a mistake. They have no stable identity across file
re-saves/merges/different-tool-loads, which is exactly why `tgs:LinkNote`
was deliberately built as a NAMED individual in the first place (the
curated/candidate review workflow depends on referencing one specific claim
reliably over time — approve it in DuckDB, promote it, audit it later, diff
it cleanly in git). Blank nodes remain fine for genuinely anonymous
structural scaffolding only — e.g. the existing `owl:oneOf` list inside
`ConfidenceLevel`'s enumeration, which nothing will ever need to reference
by identity.

**MEDIUM — Wikidata verification.** ~21 of ~23 people/schools still need
verified Wikidata `owl:sameAs` links (pattern established in
`data/seed/wikidata_links.ttl`, just needs the per-entity verification
legwork — see design decision #5 above; Q-numbers are NOT mnemonic and
guessing from memory is genuinely risky).

**MEDIUM — Primary-source verification.** Concept/School definitions are
first-draft paraphrases (design decision #6), never checked against actual
Hagens transcripts/book text. Not urgent, but a real accuracy gap.

**LOW — `tgs:Episode` still fully unused.** `tgs:Work` is on a path to its
first real use via the convergence-property backlog item above; `tgs:Episode`
has no such plan yet — no instances, no concrete trigger case identified.

**LOW — `tgs:memberOf` consistency question.** Doesn't chain up to
`tgs:relatesTo` the way the concept-to-person properties do
(`echoesIdeaOf`, `influencedBy`, etc. all do). Flagged once, never
resolved either way — low stakes, revisit whenever convenient.

**LOW — Extraction pipeline never run for real.** `extraction/README.md`'s
plan has only been tested end-to-end with fake staging data to confirm the
DuckDB→promote_to_rdf.py→graph pipeline mechanically works — never run
against actual transcripts yet.

**FUTURE, not yet actionable — dedicated Claude Skill.** Jim intends to
eventually build one (mirroring the `uwom-ontology` skill in his other
`knowledge-graph` repo) once this project's patterns feel more settled.
Natural candidate content based on what's already stable: the IRI minting
convention (design decision #2), the curated/candidate review discipline
(design decision #1, soon to be superseded by the Evidence model above),
the DBpedia+Wikidata verification workflow (design decision #5). Explicitly
NOT worth building prematurely — revisit once there's been another round or
two of real content expansion and the patterns (especially the Evidence
model, if built) have proven durable rather than still shifting.

## Ground rules for changes in this repo
- **Never point a `tgs:LinkNote`'s `tgs:confidence` at
  `tgs:ConfidenceLevel.Curated` without a human having actually reviewed
  the specific claim.** See design decision #1 — this is the most
  important rule in the repo.
- Concept/School definitions are paraphrases, not verbatim quotes — keep
  it that way (see design decision #6).
- Every `.ttl` file must parse individually and combined — run
  `make validate` before considering an edit done. CI enforces this on
  push too, and additionally validates that every confidence value is one
  of the two real enumerated individuals, not just present.
- Avoid bare DBpedia `dbr:` prefixed names for people whose surface form
  ends in a period-adjacent token (e.g. "Jr.") — Turtle parses a trailing
  `.` as end-of-statement. Use the full
  `<http://dbpedia.org/resource/...>` IRI in those cases (see
  `data/seed/people.ttl` for examples).
- `data/generated/` is the output of `extraction/promote_to_rdf.py` —
  don't hand-edit it; edit the DuckDB staging rows and re-run the promote
  script.
- Before any `git commit`/`git push`, double check the terminal prompt
  actually says `nate-hagens-kg`, not `knowledge-graph` — Jim has two
  projects open in separate terminal windows and has mixed them up before
  (harmless once, since `main` vs `master` makes it obvious after the
  fact, but worth avoiding).

## Known environment gotcha
`python3 -m venv .venv` on Jim's machine defaults to Python 3.14, which is
incompatible with rdflib 7.1.1 (AttributeError at import time — an actual
rdflib/Python 3.14 compatibility bug, confirmed reproducible, not a local
misconfiguration). Already fixed by bumping `requirements.txt` to
`rdflib>=7.6.0`. If a future `make venv` fails the same way again (e.g.
after a `.venv` wipe and rebuild on a machine where pip resolves an old
rdflib for some reason), `pip install --upgrade rdflib` inside the venv is
the fix — don't waste time re-diagnosing this one from scratch.

## Common commands
```bash
make venv            # create .venv and install requirements.txt
make validate         # parse-check every .ttl file (expect 407 triples)
make load-oxigraph    # load everything into a local Oxigraph store
make init-db           # set up the DuckDB review-queue tables
make promote-dry       # preview what promote_to_rdf.py would write
make promote            # write approved staging rows into data/generated/
```

## Working agreement
Jim edits the TTL files directly rather than routing every addition
through a Claude session first, and reports changes back. A future
session should NOT assume full knowledge of current graph state from this
file alone — always check `git log` and re-run `make validate` before
making assumptions about what exists.

## This is a separate project from other Claude Code work
This repo is its own git repository and should stay that way — don't nest
it inside another project's directory or reference files outside this
repo's tree unless explicitly asked to. Jim's other active project,
`~/projects/knowledge-graph`, is unrelated (different domain: units of
measure / UWOM ontology) and uses branch `master`, not `main` — a useful
tell if you're ever unsure which repo a terminal session is in.
