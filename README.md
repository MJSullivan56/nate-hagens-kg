# The Great Simplification — Knowledge Graph

An RDF knowledge graph connecting Nate Hagens' "Great Simplification"
framework (energy, ecology, economics, human behavior) to the philosophers,
scientists, and activists whose ideas it echoes, draws on, or usefully
contrasts with. Goal: make the framework navigable and legible to students,
activists, data folks, and general audiences — not just podcast listeners.

## Status
Early scaffold. ~14 core concepts, ~16 people/schools, 8 example curated
cross-links, 1 example unreviewed candidate link (to show the review
pattern). Enough to prove the shape of the thing and start querying — not
yet comprehensive.

## Structure

**One class, one file — governance principle adopted 2026-07-11.** Every
class that has instances gets its own complete, self-contained TTL file
(class declaration + all its individuals). Small supporting classes
(controlled vocabularies with no independent meaning of their own) and
every property declaration live together in `tgs-core.ttl`. External
resource mappings (DBpedia, Wikidata) get their own dedicated files too.
Every file `owl:imports` `tgs-core.ttl`, so opening any single file in
Protege resolves the shared vocabulary via `catalog-v001.xml` — you don't
need the whole project loaded for one file to make sense on its own.

```
data/seed/tgs-core.ttl        — ALL properties + supporting classes with
                                 their instances (ConfidenceType,
                                 ReliabilityType, PolarityType) +
                                 currently-idle classes with zero instances
                                 yet (Work, Episode, Source — each gets
                                 promoted to its own file on first instance)
data/seed/concepts.ttl        — thinkr:Concept: class + all 19 instances
data/seed/persons.ttl         — thinkr:Person: class + all 25 instances
data/seed/schoolsofthought.ttl — thinkr:SchoolOfThought: class + 7
                                 instances (split from the old, overloaded
                                 thinkr:School 2026-07-11 — see
                                 docs/sidecar-cleanup-handoff.md)
data/seed/organizations.ttl   — thinkr:Organization: class + 5 instances
                                 (same split)
data/seed/academicinstitutions.ttl — thinkr:AcademicInstitution: class +
                                 3 instances (same split, first real use)
data/seed/linknotes.ttl       — thinkr:LinkNote: class + all 14 instances,
                                 plus the cross-individual relation triples
                                 each LinkNote explains (a relation without
                                 its LinkNote is meaningless anyway)
data/seed/evidences.ttl       — thinkr:Evidence: class + all 15 instances
data/seed/subjects.ttl        — thinkr:Subject class + Subject/sub-topic
                                 instances + the 2 skos:ConceptScheme
                                 individuals that organize them
data/seed/works.ttl           — thinkr:Work: class + 1 instance (promoted
                                 out of tgs-core.ttl 2026-07-11, its first
                                 real use — was empty since the original
                                 schema)
data/seed/sources.ttl         — thinkr:Source: class + 1 instance (same
                                 promotion, same date)
data/seed/crosswalknotes.ttl  — thinkr:CrosswalkNote: class + one instance
                                 per owl:sameAs assertion (DBpedia and
                                 Wikidata alike), each carrying real
                                 provenance (source database, verification
                                 date, scopeNote). Replaced separate
                                 dbpedia_links.ttl/wikidata_links.ttl files
                                 2026-07-11 — bare owl:sameAs triples had
                                 nowhere to record caveats or verification
                                 history, e.g. "this Wikidata entry is
                                 actually a different person."
data/seed/catalog-v001.xml    — Protege import resolution (maps the
                                 thinkr# ontology IRI to tgs-core.ttl
                                 locally, since that IRI isn't a real
                                 resolvable URL)
data/generated/           — output of the promote_to_rdf.py workflow (gitignored
                             or committed, your call — not present until you run it)
docs/                     — cross-cutting design/handoff docs, distinct
                             from folder-local READMEs — see docs/README.md
scripts/load_oxigraph.sh  — load everything into a local Oxigraph store
scripts/query_examples.sparql — example queries against the store
scripts/compute_confidence.py — derives LinkNote calculatedConfidence from
                             its Evidence set — never hand-set this value
extraction/README.md      — the built, working transcript/entity-triage
                             pipeline PLUS the still-aspirational LLM
                             concept/link-extraction plan, clearly
                             separated within the file
extraction/download_transcripts.py — downloads transcripts into a local
                             reference library (sitemap + listing page)
extraction/match_substack_summaries.py — matches locally-saved Substack
                             PDFs against the transcript index
extraction/init_staging_db.py — sets up the DuckDB review-queue tables
extraction/promote_to_rdf.py  — promotes approved DuckDB rows into RDF triples
requirements.txt          — Python deps for the venv
Makefile                  — venv / validate / load / review workflow shortcuts
.github/workflows/validate.yml — CI: parses every .ttl on push, checks every
                             LinkNote has valid Evidence and calculatedConfidence
```

## Design choices worth knowing about
- **Reuses existing vocabularies** (SKOS for concepts, FOAF for people,
  DCTERMS for provenance) rather than inventing everything from scratch —
  keeps you interoperable with Wikidata/DBpedia tooling.
- **owl:sameAs to DBpedia** on every person/school gives free access to a
  huge amount of already-structured biographical and thematic data without
  hand-curating it — DBpedia entities also carry `owl:sameAs` links to
  Wikidata if you want to go further.
- **Curated vs. candidate links are tracked explicitly** (`tgs:confidence`
  on a `tgs:LinkNote` attached to each cross-link). This is the most
  important design decision in the whole project: an LLM can propose
  hundreds of plausible-sounding parallels, but most surface pattern
  matches ("both talk about balance!") aren't intellectually honest links.
  Nothing should show as a real connection to an end user until a human
  reviewed it.

## Setup (macOS, using the tools already on hand)
```bash
# Oxigraph CLI, via the maintainers' own tap (confirmed current as of this writing)
brew tap oxigraph/oxigraph
brew install oxigraph

# Python environment
make venv
source .venv/bin/activate
```

## VS Code
- **Stardog RDF Grammars** (if that's what's installed) gives you Turtle/SPARQL
  syntax highlighting — useful, but it's not a query runner.
- For actually *running* SPARQL against these files inside the editor, install
  **SPARQL Notebook** (`Zazuko.sparql-notebook`) — right-click any `.ttl` file
  → "SPARQL Notebook: Use File as Store" and you get a live query cell against
  it, no server needed. Good for quick checks; use the Oxigraph store (below)
  once the graph is querying multiple files together regularly.
- **Protégé** works on any `data/seed/*.ttl` file directly now — see below,
  this changed as of the 2026-07-11 file reorganization.

## The DuckDB review workflow (for scaling up via extraction/)
Once you're running the LLM-assisted extraction pipeline in `extraction/`
across transcripts, candidate concepts/links land in a DuckDB staging table
rather than directly in Turtle — reviewing "accept/reject/edit this proposed
link" is a SQL/spreadsheet-shaped task, not a text-editing one.

```bash
make init-db                 # creates extraction/staging.duckdb with two tables
# ... extraction pass populates candidate_concepts / candidate_links,
#     you review by querying the DB directly (DuckDB CLI, a notebook, or
#     even DBeaver) and UPDATE status = 'approved' on the rows you trust ...
make promote-dry              # preview what would be written, no files touched
make promote                  # writes data/generated/{concepts,linknotes}.ttl
                               # from approved rows, marks them 'promoted'
```
`promote_to_rdf.py` validates that a candidate link's subject/object labels
actually match existing seed entities before writing (catches typos), and
writes the exact same triple + `thinkr:LinkNote` pattern used in
`data/seed/linknotes.ttl` — nothing bypasses the curated/candidate tracking.

## Working with Protégé and GitHub
- **Every `data/seed/*.ttl` file is self-contained and Protégé-openable on
  its own** (governance principle adopted 2026-07-11 — see Structure above).
  Each file `owl:imports` `tgs-core.ttl`; `catalog-v001.xml` sitting
  alongside them tells Protégé to resolve that import locally instead of
  trying to fetch `http://example.org/thinkr#` over the network (it isn't a
  real resolvable URL). Open any single file — `concepts.ttl`,
  `persons.ttl`, whichever you're working on — and Protégé will pull in the
  shared classes/properties automatically, no need to load the whole
  project just to make one file's individuals make sense.
  Bulk-editing many individuals at once is still more practical as
  text/scripts than through Protégé's individuals UI, even though each file
  now opens cleanly on its own — keep editing large batches as text or via
  scripts.
- **GitHub**: `.github/workflows/validate.yml` runs on every push/PR that
  touches a `.ttl` file — it parses every Turtle file individually and
  combined (catches the kind of syntax error a trailing `.` in a DBpedia URI
  can cause), and checks that every `tgs:LinkNote` has a `tgs:confidence`
  value pointing to one of the two valid `tgs:ConfidenceType` individuals
  (not just present, but actually valid), so an unreviewed candidate link
  can't silently get treated as curated. Push to a repo and it runs
  automatically, no setup needed beyond that file being present.

## Quick start
```bash
cd scripts
chmod +x load_oxigraph.sh
./load_oxigraph.sh
oxigraph query --location ./tgs_store --query-file query_examples.sparql
```

## Namespace note
`http://example.org/tgs#` is a placeholder throughout. Before publishing,
swap it for a URI you actually control (a GitHub Pages URL works fine and
is free) so the identifiers resolve to something real.

## Next steps (roughly in order)
1. Expand `concepts.ttl` — verify each definition against the actual source
   (transcript/book), not just the paraphrase here, and add real
   `dct:source` references (page numbers / episode timestamps).
2. Expand `persons.ttl` (and `schoolsofthought.ttl` for traditions/movements) with
   more philosophers, scientists, and activists as
   concepts demand them — don't pad it preemptively.
3. Add more curated links in `linknotes.ttl`, by hand, focusing on the concepts
   with zero links first (query #5 in `query_examples.sparql`).
4. Once the seed graph feels solid (~50-100 concepts, ~50 people, links
   covering most concepts), run the extraction pipeline in `extraction/`
   against a handful of transcripts to test candidate-link generation at
   scale, then review before promoting anything to curated.
5. Only then think about a public front-end (force-directed graph view,
   SPARQL-backed search) — the data quality is the actual hard/valuable
   part of this project, the visualization is comparatively easy once the
   graph is good.

## License / attribution
Concept definitions here are paraphrased summaries for educational/research
navigation purposes, not reproductions of Hagens' original text — link back
to https://www.thegreatsimplification.com and the original episode/book for
anything you publish.
