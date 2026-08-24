# Prompt for Claude Code: RDF ↔ DuckDB Migration Pipeline for nate-hagens-kg

## Context (read first, don't re-derive)

This is a personal knowledge graph project (RDF/OWL, `tgs:`/`thinkr:` namespaces)
covering Nate Hagens' "The Great Simplification" podcast — episodes, guests,
relationships, concepts, and a 4-dimension/16-facet scenario framework. It's
been built by hand via Claude chat sessions: read a transcript, verify facts,
write Turtle, validate. That process produced a genuinely solid ~7,300-triple
graph (87 episodes, 104 personas, 89 relationships, and more), but it's too
slow to scale to the ~300 remaining episodes and thousands of external links.

**The goal of this work is NOT to redesign the ontology.** The RDF model is
considered correct and stable. The goal is a faster *pipeline* around it:
scrape → stage in DuckDB → curate via SQL → export back to Turtle/N-Triples/
JSON-LD. Bidirectional live sync (edit either side, auto-propagate) is an
explicit **future nice-to-have**, not this project's scope — building for it
now would be over-engineering. This is a **batch** pipeline: import once,
curate with SQL, export when ready.

**The live system of record is an Oxigraph SPARQL endpoint at
`http://127.0.0.1:7878`, running locally.** A directory of `.ttl` files also
exists as a fallback/snapshot source — prefer the SPARQL endpoint when it's
reachable. (Note: a prior Claude session assumed the file directory *was* the
full picture and was briefly, wrongly suspicious that some files —
`doughnuthalves.ttl`, `indicators.ttl`, `crosswalknotes.ttl` — belonged to a
different project, purely from not having surveyed the file list recently.
They didn't; they're real, dated TGS content. Lesson: don't assume you know
what's in the store without querying it — this is exactly the kind of gap
querying the live endpoint directly avoids.)

## What already exists — start from this, don't rewrite it

**Read the real repo structure before writing anything.** It's more built-out
than the chat session that produced this prompt had visibility into (that
session only ever saw files the user explicitly uploaded, never the repo
itself). Confirmed structure:

```
nate-hagens-kg/
├── docs/                          (includes sidecar-cleanup-handoff.md —
│                                    real incident history, e.g. the
│                                    tgs_store relocation below)
├── data/seed/*.ttl                (the real source-of-truth Turtle files)
├── tgs_store/                     (materialized Oxigraph store — derived,
│                                    gitignored, regenerable from data/seed/)
├── extraction/
├── scripts/
│   ├── compute_relationships.py   (derives Persona has*Relationship props
│   │                                from Relationship.hasRelationshipType —
│   │                                see the detailed section below, read
│   │                                before writing any relationship logic)
│   ├── compute_confidence.py      (Evidence -> LinkNote confidence scoring —
│   │                                see below, a real sub-system with no
│   │                                DuckDB table yet)
│   ├── validate_class_purity.py   (the real "one class per file" check —
│   │                                see below for the scratch.ttl convention
│   │                                it enforces alongside)
│   ├── load_oxigraph.sh           (see Phase 1 — must be run FROM scripts/,
│   │                                takes STORE_PATH as $1, defaults to
│   │                                ../tgs_store)
│   └── query_examples.sparql
├── requirements.txt
├── .env
└── README.md
```

**Update: all 3 scripts (`compute_relationships.py`, `compute_confidence.py`,
`validate_class_purity.py`) have now been read in full.** What follows
replaces the earlier speculative version of this section — treat the
specifics below as confirmed, not "likely."

**`compute_relationships.py` — do not reimplement this in SQL, and do not
port its logic into the DuckDB pipeline. Call it, unmodified, as a
post-export step (see Phase 5).** It derives every Persona's
`has{Personal,Professional,Academic,Intellectual,Legal}Relationship` purely
from each `Relationship`'s own `hasRelationshipType`, both directions
(subject and object), then writes the result back via **targeted text
surgery on `data/seed/personas.ttl`** — never `rdflib`'s `Graph.serialize()`.
This matters for Phase 5, not just as a curiosity: `Graph.serialize()` is
confirmed (2026-07-15 incident, see the script's own docstring) to silently
strip every hand-authored `scopeNote` and comment out of a file on
round-trip. **The DuckDB → RDF export in Phase 5 must not naively serialize
a parsed graph back out — it needs the same literal-protected,
regex-targeted text-surgery approach this script already uses**
(`protect_literals`/`restore_literals` in the source), or it will
regress every scopeNote in the graph, including the ones documenting
exactly this kind of hazard. Also note the self-verification pattern
(`apply_changes()` writes, then re-parses from disk and diffs against
`desired` before declaring success) — the export script should do the
same, not trust a successful run as proof of correctness.

**`validate_class_purity.py` — this already does the "class purity" check.**
Confirmed real incident behind it: Concept-lineage facts landed in
`linknotes.ttl` instead of `concepts.ttl`, twice, mid-task. It also reveals
a real staging convention this pipeline should respect: `scratch.ttl` is
where uncertain/in-progress content is meant to be parked before being
swept to its real destination file, and `--check-scratch-empty` enforces
it's clean before a task counts as done. **The DuckDB staging tables from
Phase 3 are the natural home for this same convention** — scraped-but-not-
yet-curated data belongs in staging, not in the core tables, mirroring
`scratch.ttl`'s role exactly. Consider giving staged rows an explicit
status column (`pending` / `swept`) rather than just "present in a staging
table," so the DuckDB equivalent of `--check-scratch-empty` is a one-line
query.

**`compute_confidence.py` — a real sub-system this prompt's author never
touched.** `Evidence` individuals (with `aboutSource`, `evidencePolarity`
[Supports/Contests/Mentions], and their own `confidence` state) roll up
into a `LinkNote`'s derived `calculatedConfidence`
(Candidate/Curated/Corroborated/Disputed), via real, specific rules —
Contests-from-a-reputable-source overrides even multiple Supports;
Unverified-tier support alone can never reach Corroborated; superseded
Evidence (via `prov:wasRevisionOf`) is excluded entirely. **This means the
DuckDB schema is missing tables** — add `evidence` (with tier, polarity,
confidence, `about_source`, `superseded_by`) and `link_notes` (with
`calculated_confidence`) as real core tables, not generic `facts` rows,
given how much real query value sits in "which LinkNotes are Disputed" or
"which Evidence is Unverified-tier." Note the real bug this script's own
docstring documents fixing (stale namespace constants after a vocabulary
rename silently made every comparison match nothing, so every LinkNote
fell through to the floor state) — a concrete argument for the Phase 5
export script self-verifying against the source data the same way, not
trusting a clean run.

A working, tested Python script (`rdf_to_duckdb.py`, attached) already does
the RDF → DuckDB backfill for episodes/personas/relationships/works — built
without knowledge of `Evidence`/`LinkNote`/`ConfidenceType`, so it's missing
those tables entirely; add them before Phase 1 rather than discovering the
gap mid-migration. It implements:

- A **hybrid schema**: core tables (`episodes`, `personas`, `humans`,
  `relationships`, `interactions`, `works`, plus join tables for
  multi-valued fields like guests/subjects/roles) for the entity types
  that get queried by date, name, or URL — and one generic `facts` table
  (`subject_iri, subject_type, predicate, object_value, object_is_iri`) for
  everything else. This matters: new RDF classes have been added mid-session
  repeatedly throughout this project's history (`Archetype`,
  `InterventionFront`, `ProfessionalRole`, `ResponsePhase`, all added as real
  gaps surfaced during normal curation work) — a schema that requires a
  migration every time a new class appears will fight the project's actual
  growth pattern. Don't normalize everything into dedicated tables up front.
- **Deterministic synthetic IDs for blank nodes** (`hasInteraction`,
  `hasAlternateTerm` — this graph uses blank nodes for n-ary relationships
  like "Nate hosted Guest X on Episode Y on Date Z"). Generated via SHA1 of
  the blank node's own triples. **Real gotcha already hit and fixed**: the
  hash must be scoped by the *owning* individual (e.g. the Relationship
  IRI), not just the blank node's own literal properties — two different
  guests on the same panel episode can have interaction blank nodes with
  *identical* literal properties (same episode, same date, same Host/Guest
  roles), which collided under the first, unscoped version of this hash and
  silently dropped ~46 real interactions. Verify row counts against source
  counts after any change to this logic, the way the reference
  implementation does.
- A `load_graph()` function that tries the SPARQL endpoint first
  (`CONSTRUCT {?s ?p ?o} WHERE {?s ?p ?o}`, `Accept: text/turtle`) and falls
  back to parsing local `.ttl` files if unreachable.

Run it once as-is to confirm your environment reproduces the same table
counts before changing anything (episodes: 87, personas: 104, humans: 104,
relationships: 89, interactions: 103, works: 20 — these are known-correct
against the source graph as of this writing).

## Work to actually do, in phases — checkpoint between each one

Budget is tight on this account. **Do not run this as one long autonomous
session.** Stop at each checkpoint below, report what you found/built, and
wait for a go-ahead before continuing to the next phase. A phase that turns
up something unexpected (schema mismatch, a SPARQL endpoint that isn't
actually reachable, malformed scraped data) should stop and ask, not
improvise a large change and keep going.

### Phase 1 — Confirm the baseline (cheap, fast, do this first)
Oxigraph is not assumed to be already running — start it explicitly:

```bash
cd scripts/
./load_oxigraph.sh                                    # loads data/seed/*.ttl into ../tgs_store
oxigraph serve --location ../tgs_store --bind 127.0.0.1:7878 &
```

Confirm it's actually up before querying it (e.g. `curl -s localhost:7878/query
--data-urlencode "query=SELECT (COUNT(*) AS ?n) WHERE {?s ?p ?o}"`). If
`../tgs_store` already exists and is stale/incomplete, re-run
`load_oxigraph.sh` to reload from `data/seed/*.ttl` — that directory is the
real source of truth, the store is a derived, disposable artifact of it
(see the script's own comments for why, including a real prior incident
with a stray duplicate store from a wrong-directory run).

Then run the existing `rdf_to_duckdb.py` script against the live endpoint
(not the file fallback) and confirm the row counts match what file-parsing
produces. If they don't match, STOP and report the discrepancy — don't
guess which source is right.

**Checkpoint:** Oxigraph confirmed running and loaded, table counts
reconciled against the file-based load, or a clear discrepancy report.

### Phase 1.5 — Formalize real OWL axioms, then materialize inverse/symmetric closure with provenance

Two related but distinct pieces of work, decided together so the schema for
one accounts for the other. Neither is scoped for this prompt to fully
specify — the concrete axiom list (which properties get `owl:inverseOf`,
which classes get real `owl:disjointWith`, which cardinality restrictions
get added) is a separate, detailed task to work through directly with the
project owner before or during this phase, not something to invent here.
What follows is the architecture those decisions need to land into.

**Formalize load-bearing constraints as real OWL axioms first.** Most of
this graph's real structural rules currently exist only as prose in
`rdfs:comment`/`skos:scopeNote` — e.g. "every Episode has exactly one
hasHost," "hasXPosition must be one of -3..3" — invisible to any reasoner.
Candidates worth real cardinality/domain-range restrictions: `hasHost`,
`hasXPosition`/`hasYPosition`, `hasScenarioDimension`. Candidates for real
`owl:disjointWith` between classes: the enumeration-style classes
(`EpisodeType`, `RelationshipType`, `ProfessionalRole`) as
`owl:AllDisjointClasses`, so a reasoner could catch an individual
mistakenly typed as two of them — something no check in this project has
ever actually tested for. Load into Protégé, run HermiT (or Pellet) for a
real consistency check. **A "consistent" result only means something once
these axioms exist** — running a reasoner against the graph as it stood
before this phase would trivially pass, since there was nothing yet for it
to actually check.

**Add `owl:inverseOf` for real query-value pairs, and `owl:SymmetricProperty`
is already declared on several existing properties** (`xAxisDivergentFrom`,
`yAxisDivergentFrom`, `diagonallyDisjointWith`, `convergesWith`,
`logicallyDisjointWith` — all already symmetric by declaration, just never
reasoner-completed since Oxigraph has no reasoner). Real inverse candidates
worth adding: `hasGuest` (Episode→Persona) ↔ new `appearedInEpisode`
(Persona→Episode); `hasScenarioDimension` (Facet→Dimension) ↔ a Dimension-
side pointer to its Facets; `hasFront`/`hasSubdomain` ↔ pointers back to
the owning Framework/Front; `actsThrough` (Persona→Human) ↔ a Human-side
pointer back to their Persona.

**Do NOT add transitivity to the disjointness/divergence properties —
this is a hard rule, not a case-by-case judgment call.** Real logical
disjointness isn't transitive in general (A disjoint from B and B disjoint
from C does not mean A disjoint from C), and marking
`thinkr:diagonallyDisjointWith` transitive would let a reasoner silently
chain incompatibilities that were never actually asserted or true — a
failure mode that would look like a working feature right up until it
produced a wrong conclusion somewhere in a larger future grid. The one
real transitive candidate is a genuine part-whole hierarchy
(`Framework → Front → Subdomain`), and even that should be answered via
SPARQL 1.1 property paths at query time (`?x thinkr:partOf+ ?framework`,
which Oxigraph already supports natively, no reasoner needed) rather than
materialized — materializing a transitive closure adds real storage bloat
and staleness risk for something a property-path query already answers
cheaply.

**Materialize the inverse/symmetric closure — but this isn't DL reasoning,
it's cheap mechanical closure, and it should be built the same way
`compute_relationships.py` already builds `has*Relationship`:** a new
sibling script, `compute_inverses.py`, following the identical established
pattern (compute desired state from every property with a declared
`owl:inverseOf`/`owl:SymmetricProperty`, diff against current, write back
via the same literal-protected text surgery, self-verify by re-parsing).

**Provenance requirement, decided explicitly — materialize into DuckDB,
not just RDF, since this data exists specifically to power Phase 4's
curation queries.** Every row in the generic `facts` table gets an
`is_inferred BOOLEAN` column. Asserted, curated facts (everything already
in the core tables, and anything hand-verified in `facts`) get `false`.
Anything `compute_inverses.py` (or any future derivation script) produces
gets `true`. **All inferred/derived triples land in `facts` with
`is_inferred=true`, regardless of whether the "forward" direction of that
property already has its own dedicated core table** — e.g. a newly
materialized `appearedInEpisode` row does NOT get added to
`episode_guests` (which represents only the asserted `hasGuest` direction);
it goes into `facts`. One column, one table to check, rather than needing
every core/join table to separately carry the same flag. This gives Phase
5's export a direct, literal lever matching what was actually decided:
`WHERE is_inferred = false` for a conservative export of only what was
actually asserted, or including reviewed inferred rows once a human's
looked at them — the project owner explicitly does not want inferred and
asserted facts silently blurred together with no way to tell them apart
later.

**Checkpoint:** axiom list drafted and reviewed with the project owner
(who is not a developer — walk through what each axiom means in plain
terms, don't just present a finished OWL file), HermiT run clean or
violations reported, `compute_inverses.py` run with `is_inferred` correctly
set, a sample "missing inverse" curation query demonstrated working.

### Phase 2 — Design and validate the Apify scrape shape
Design a flat JSON shape (explicitly **not** JSON-LD — no inferred RDF
semantics at scrape time; that's a curation-time decision, not a scraping
one) that captures, per episode, without interpretation:

```json
{
  "episode_url": "...",
  "episode_number": 213,
  "title": "...",
  "show_summary": "...",
  "guest_names": ["..."],
  "recorded_date": "2026-02-17",
  "issued_date": "2026-03-11",
  "subjects": ["Human Behavior"],
  "transcript_url": "...",
  "replay_url": "...",
  "show_notes": [
    {"timestamp": "16:47", "topic": "...", "links": ["..."]}
  ],
  "backlinks": [{"title": "...", "url": "..."}]
}
```

Same shape for every episode type (Interview, Frankly, Reality Roundtable) —
don't special-case the shape by type; type-specific handling is a curation
decision downstream, not a scraping one. Test it against 2-3 already-known
real episode pages (e.g. `episode/213-christine-webb`,
`frankly-original/132-what-to-do-as-the-world-falls-apart`) and confirm the
shape captures everything a human would need, including the show-notes
table links, which are often the majority of an episode's real value.

**Checkpoint:** shape validated against 2-3 real pages, sample output shown
before building the full Apify actor.

### Phase 3 — Staging tables + loader for scraped data
Add staging tables for the Apify JSON output (raw, unprocessed — a
`raw_episode_scrapes` table or similar, JSON columns are fine in DuckDB) and
a loader that ingests the Apify output into them. Keep this **separate**
from the core tables built in Phase 1 — scraped data is unverified and
shouldn't be mixed with the already-curated graph data until it's reviewed.

**Checkpoint:** N real scraped episodes loaded into staging tables, a few
spot-checked by hand against the actual episode pages.

### Phase 4 — Curation queries / views
Build the actual "missing links or illogical relationships" queries this
backfill exists to enable — a few examples already proven useful this
session, extend from these:

```sql
-- Episodes with a guest but no corresponding interaction record
SELECT e.local_name, e.pref_label FROM episodes e, episode_guests eg
WHERE e.iri = eg.episode_iri
AND NOT EXISTS (SELECT 1 FROM interactions i WHERE i.episode_iri = e.iri);

-- Duplicate-persona risk: same pref_label, different IRIs
SELECT pref_label, COUNT(*) FROM personas GROUP BY pref_label HAVING COUNT(*) > 1;

-- Staged scrape data that references a person not yet in `humans`
```

Also build the diff view between staged/scraped episodes and what's already
in the core `episodes` table (by URL or episode number) — this is what
actually saves the months: a query that says "here are the 300 episodes we
don't have yet, here's what was scraped for each, ready for review."

**Checkpoint:** a working "what's missing / what's inconsistent" report
against the real current data — this is the actual deliverable being paid
for, more than the pipeline plumbing itself.

### Phase 5 — Export back to RDF (only after 1-4 are solid)

**Decided: call the 3 existing scripts unmodified as post-export pipeline
stages — do not port their logic into the DuckDB export path.** Reasoning,
worth keeping in the repo's history somewhere (a commit message, a
docs/ note) since a future session might otherwise "helpfully" try to
inline this logic: porting would mean two places implement the same
derivation rules, with real drift risk (see `compute_confidence.py`'s own
docstring for a real prior incident where exactly this kind of logic went
stale after a rename and silently produced wrong output for weeks). Calling
the existing scripts means less new code to write and verify, and
automatic benefit from any future fix to the originals.

Export sequence:

1. **DuckDB → base RDF facts.** Write a `rdflib.Graph()` from the curated
   DuckDB tables, but **do not compute or write any `has*Relationship`
   property, and do not compute or write `calculatedConfidence`** — those
   are derived, not source data; writing them here would just get
   overwritten (or drift out of sync) the moment step 2/3 runs. Serialize
   to `data/seed/*.ttl` using the **same literal-protected text-surgery
   approach `compute_relationships.py` already uses** (see its
   `protect_literals`/`restore_literals` functions) — not
   `Graph.serialize()`, which is confirmed to strip hand-authored
   `scopeNote`s and comments on round-trip.
2. **Run `python scripts/compute_relationships.py`** (unmodified, no
   `--dry-run`) to derive and write every Persona's `has*Relationship`
   properties from the `Relationship` individuals just exported.
3. **Run `python scripts/compute_confidence.py`** (unmodified, no
   `--dry-run`) to derive and write `calculatedConfidence` on every
   `LinkNote` from its `Evidence`.
4. **Run `python scripts/validate_class_purity.py`** as a final gate —
   exit code 0 required before considering the export done. If it fails,
   STOP and report which file(s) violated it; don't try to auto-fix a
   class-purity violation without review, since the real 2 incidents that
   led to this script's existence were both content landing in the wrong
   file, which needs a human judgment call about where it actually
   belongs, not a script guessing.
5. **Load into Oxigraph**: re-run `scripts/load_oxigraph.sh` against the
   freshly-written `data/seed/*.ttl`. Once this pipeline is live, `.ttl`
   files should be treated as pipeline-managed artifacts — hand-editing
   them directly should stop, since it's exactly the kind of
   sometimes-DuckDB, sometimes-hand-edited drift this migration exists to
   eliminate.

**Checkpoint:** round-trip test — export a small, already-known-correct
slice (e.g. the 16 ScenarioFacets and their disjointness relationships),
diff against the original Turtle, confirm no semantic loss, confirm
`validate_class_purity.py` still passes clean.

## Explicit non-goals — don't do these even if it seems efficient

- **Don't attempt to automate the verification/curation judgment calls.**
  Namesake disambiguation ("is this Chuck Watson the same Chuck Watson"),
  deciding whether a citation clears the bar for a full build vs. staying
  deferred, catching a copy-paste error in a source PDF, writing a
  `scopeNote` explaining *why* a relationship is asserted — none of this is
  what the pipeline should try to replace. It exists to remove the
  *mechanical* bottleneck (typing Turtle by hand, re-fetching pages,
  grep-ing for line numbers to edit) so a human curator can spend their
  time on judgment calls, not to remove the judgment calls themselves.
- **Don't invent new RDF classes or properties during this work.** If the
  scraped data doesn't fit the existing schema, flag it and stop — that's
  a modeling decision for the project owner, not something to improvise
  mid-migration.
- **Don't run large, expensive, unsupervised loops.** Scraping 300 episodes
  in one go without a checkpoint after the first handful is exactly the
  kind of thing that burns budget on a mistake repeated 300 times instead
  of caught once.
