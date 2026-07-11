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
- RDF/Turtle as source of truth, all in `data/seed/` (the separate
  `ontology/` folder was dissolved 2026-07-11 — see governance note below)
- Oxigraph as the query engine (installed via `brew tap oxigraph/oxigraph
  && brew install oxigraph`; confirmed working, version 0.5.0-beta.4 as of
  last check)
- DuckDB as a staging/review database for LLM-proposed candidate links
  (`extraction/staging.duckdb`, gitignored, not committed)
- Python venv (`make venv`) for all scripting — see KNOWN GOTCHA below
  before assuming a fresh `make venv` will just work
- VS Code: SPARQL Notebook extension (`Zazuko.sparql-notebook`) lets you
  query `.ttl` files directly in the editor — install status on MJSullivan's
  machine was never confirmed as of last check, verify before assuming

## Reusable methodology: the thinkr:/tgs: namespace split (2026-07-10)
The project's scope expanded beyond Hagens alone — MJSullivan intends to
apply this same methodology to other thinkers, with Heather Cox Richardson
named as the concrete next candidate. This forced a real architectural
change, not just a naming tweak: `tgs:` literally stands for "The Great
Simplification," so it can never correctly hold another thinker's data.

**The split**: every CLASS, PROPERTY, and controlled-vocabulary INDIVIDUAL
(the `ConfidenceLevel`/`ReliabilityTier`/`EvidencePolarity` enum members —
every domain will reuse the exact same Curated/Candidate/Corroborated/
Disputed states) now lives under `thinkr:` (`http://example.org/thinker#`)
— this is the reusable ontology. Every actual DOMAIN INDIVIDUAL (every
`Person`, `Concept`, `School`, `LinkNote`, `Evidence`) stays under `tgs:` —
this is Hagens-specific data. `data/seed/tgs-core.ttl` (formerly
`ontology/schema.ttl`, see the 2026-07-11 governance reorganization note
below) is 100% `thinkr:`,
zero `tgs:` — verified by grep, not just assumed.

**A real bug worth knowing about if you extend this pattern again**: the
first rename pass used a regex matching bare class names like `Person`,
which incorrectly also matched the START of `tgs:Person.MarcusAurelius`
(since nothing excluded a following `.`), silently reclassifying every
`Class.Name`-style domain individual as vocabulary. Caught by actually
running a live query and getting zero results instead of trusting the
"successful" parse — the file still parsed as valid Turtle throughout,
parsing alone would never have caught this. Separately, the two Python
scripts (`compute_confidence.py`, `promote_to_rdf.py`) and the CI workflow
all construct vocabulary URIs via `TGS["ConfidenceLevel.Curated"]`-style
Python code, which the text-based rename never touched at all — required
a second, manual pass adding a `THINKER` namespace object to each. A third
subtle bug: `query_examples.sparql`'s query #2 appeared to work after the
first fix, but only because it was tested against a Python graph object
that still had `thinkr:` bound from an earlier `parse()` call in the same
session — the file itself was missing its own `PREFIX thinkr:` line, which
would have failed immediately in the Oxigraph CLI (no such inherited-binding
behavior there). Caught by re-testing against a deliberately fresh graph
with zero inherited bindings, not by trusting the first "passing" result.
General lesson, worth remembering for any future refactor of this
scale: parsing successfully and querying correctly are different bars —
verify against both, and be suspicious of a first success if the test
setup could be leaking state from earlier in the same session.

**Two-repo structure planned, NOT yet executed**: ontology as its own repo
(clean split while small — 575 triples now, cheapest this will ever be),
data repos per thinker (`nate-hagens-kg` continues as Hagens' data repo
once the ontology moves out), a future crosswalk repo for links whose
endpoints span two domains (also where `tgs:convergesWith` — see backlog
— eventually lives, since Stoicism↔Bhagavad Gita is arguably crosswalk
content even pre-HCR, not really "Hagens data" either). MJSullivan decided:
manual version pinning between repos (not git submodules — simpler,
upgradable later if needed), and defer actually splitting the crosswalk
repo + viewer tool into their own repos until there's real multi-domain
content to justify it (folders within `nate-hagens-kg` for now — zero cost
to defer since nothing exists in either yet). The ontology repo split
itself (physically separating `data/seed/tgs-core.ttl` into its own
repository) is the one piece still NOT done as of this writing — the
namespace rename happened first since it was more urgent (every hour of
delay meant more content minted under the wrong prefix), the physical
repo split is a mechanical follow-up.

**Also raised, not yet resolved**: reliability tiers may need to be
domain-scoped per claim-type rather than one fixed tier per Source —
e.g. Hagens as `Reputable` (generalist synthesist, not a credentialed
domain expert across everything he covers) vs. Richardson as plausibly
`Authoritative` specifically on American political/constitutional history
(she's a credentialed, peer-reviewed historian). Deliberately deferred
until real HCR content exists to test the distinction against, rather than
designed in the abstract now.

## Key design decisions (the "why" behind the schema)
These are the load-bearing choices — worth understanding before making
structural changes:

0a. **Governance principle (2026-07-11): one class, one file.** Every class
    with instances gets its own complete, self-contained TTL file (class
    declaration + all its individuals) — `concepts.ttl`, `persons.ttl`,
    `schools.ttl`, `linknotes.ttl`, `evidences.ttl`, `subjects.ttl`. Small
    supporting/controlled-vocabulary classes (`ConfidenceLevel`,
    `ReliabilityTier`, `EvidencePolarity`) and ALL property declarations
    live together in `tgs-core.ttl` — MJSullivan's framing: `tgs-core.ttl`
    is the direct successor to the old `ontology/schema.ttl`, which can be
    thought of as its rough prototype. Classes with zero instances yet
    (`Work`, `Episode`, `Source`) stay declared in `tgs-core.ttl` until
    their first real instance, at which point they should be promoted to
    their own file. External resource mappings get their own dedicated
    files too (`dbpedia_links.ttl`, `wikidata_links.ttl`) — this same
    principle extended to "declared external resources." Crosswalk files
    (once any exist — e.g. for `convergesWith`) should be named by
    subject + relationship, not yet needed since nothing's been built
    there. Every file `owl:imports` `tgs-core.ttl`, resolved locally via
    `data/seed/catalog-v001.xml` (Protege can't resolve
    `http://example.org/thinkr#` over the network — it's not a real URL —
    so the catalog maps it to the local file). This means any single file
    can be opened standalone in Protege and "behave reasonably well," per
    MJSullivan's explicit goal — was NOT true before this reorganization,
    when only `ontology/schema.ttl` was really Protege-friendly on its own.

0. **Emerging principle (2026-07-11, not yet fully tested): OWL for formal
   relationships, SKOS for informal ones.** Named explicitly by MJSullivan
   after noticing the pattern already forming — `thinkr:Person`/`Concept`/
   `Evidence`/`Source`/`ConfidenceLevel` etc. are OWL classes with strict,
   single-purpose axioms (a `LinkNote` has a valid `calculatedConfidence`
   or it doesn't — no ambiguity, no multi-parent messiness), while the
   Subject taxonomy (see `data/seed/subjects.ttl`) is SKOS specifically
   because real-world topic classification is genuinely multi-parent and
   fuzzy (a Concept can legitimately belong under more than one Subject).
   Deliberately NOT formalized as a hard rule yet — "let's see what the
   data tells us" was the explicit call, consistent with this project's
   general bottom-up-from-real-need methodology (see the earlier
   bottom-up-vs-top-down content strategy discussion). Treat this as a
   lens for judgment calls going forward (does a new relationship need
   OWL's strictness, or SKOS's looser semantics?), not as a rule to
   enforce mechanically before there's enough content to test it against.

1. **Curated vs. candidate confidence tracking is the most important
   design decision in the whole project.** An LLM can propose hundreds of
   plausible-sounding parallels between TGS concepts and historical
   thinkers, but most surface pattern matches ("both talk about balance!")
   aren't intellectually honest links. Nothing should present as a real
   connection to an end user until a human has reviewed it. This is
   enforced structurally: `tgs:confidence` is an `owl:ObjectProperty`
   pointing to one of exactly two enumerated individuals,
   `tgs:ConfidenceLevel.Curated` or `tgs:ConfidenceLevel.Candidate` (see
   `data/seed/tgs-core.ttl` — closed enumeration via `owl:oneOf`). CI
   actively validates every `tgs:LinkNote` has one of these two values,
   not just that some value is present.

2. **Every individual follows `<Domain>:<Class>.<Name>` IRI minting**
   (e.g. `tgs:Person.MarcusAurelius`, `tgs:Concept.Overshoot`,
   `tgs:LinkNote.DiscountMarcus`) and is explicitly typed
   `a tgs:SomeClass, owl:NamedIndividual` — this is MJSullivan's established
   convention from his other ontology work, adopted here for consistency.
   Classes and properties themselves (in `data/seed/tgs-core.ttl`) are NOT
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

## Current data state (as of 2026-07-11, post-file-reorganization)
- 678 triples total (`make validate` should confirm this exactly)
- 19 Concepts, 20 People, 6 Schools, 14 LinkNotes (13 curated, 1
  deliberately-marked candidate as a review-queue example), 14 Evidence
  individuals (one per LinkNote so far — 1:1 for now, but the model
  supports many-to-one), 0 Source individuals yet (every Evidence so far
  is unsourced/direct-reasoning, defaulting to Reputable tier), 12 Subject
  individuals (6 official + 6 derived sub-topics, all 19 Concepts tagged)
- **Files, one class per file (governance principle, 2026-07-11)** — see
  README.md's Structure section for the full rationale and per-file
  descriptions. `data/seed/tgs-core.ttl` is the shared vocabulary;
  every other file `owl:imports` it via `catalog-v001.xml`. The old
  `ontology/schema.ttl`, `data/seed/people.ttl`, and
  `data/seed/expansion_2026-07-10.ttl` no longer exist — fully dissolved
  into the new per-class files by a scripted, triple-count-verified
  repartition (673 → 678 after adding the new ontology/import
  declarations themselves).
- `scripts/compute_confidence.py` is the derivation engine for
  `calculatedConfidence` — re-run it after ANY Evidence edit, never
  hand-set that property

## Backlog (priority-ranked, as of 2026-07-10)

**DONE 2026-07-10 — Evidence/claim provenance model.** Built: `tgs:Evidence`
and `tgs:Source` classes, `tgs:ReliabilityTier` (Authoritative/Reputable/
Unverified/Unreliable) and `tgs:EvidencePolarity` (Supports/Contests/Mentions)
enumerations, `ConfidenceLevel` expanded to 4 values (added Corroborated,
Disputed). `tgs:confidence` moved from LinkNote to Evidence (has THIS piece
of evidence been reviewed?); new `tgs:calculatedConfidence` on LinkNote is
DERIVED via `scripts/compute_confidence.py` — never hand-set. Aggregation
rule implemented exactly as designed (see that script's docstring): only
Curated evidence counts; Unreliable-tier sources excluded regardless of
polarity (the eugenics-publication case); superseded evidence
(`prov:wasRevisionOf`) excluded (the Neanderthal-taxonomy case); any
Reputable-or-better Contests evidence forces Disputed, overriding
Corroborated; 2+ independent Reputable-or-better Supports -> Corroborated;
Unverified-tier support alone can never reach Corroborated regardless of
volume. All 5 rule branches individually stress-tested and passing before
shipping (not just happy-path tested). All 14 existing LinkNotes migrated —
6 got real `prov:generatedAtTime` years extracted directly from their
existing rationale text (Catton 1980, Tainter 1988, Meadows/Limits to Growth
1972, Hubbert 1956, Jevons 1865); the other 8 deliberately left without a
timestamp rather than fabricating one. `promote_to_rdf.py` and CI both
updated and re-tested end-to-end under the new model.
FOLLOW-UP NOT YET DONE: the DuckDB staging tables (`extraction/
init_staging_db.py`) were NOT extended for Evidence-level review — they
still operate at the old LinkNote-level granularity. Once real Evidence
accumulates (multiple pieces per LinkNote, actual Source records), the
staging/review workflow will need its own Evidence-aware tables. Also:
`data/seed/` has zero `tgs:Source` individuals yet — every migrated Evidence
is unsourced (implicit Reputable tier) — so Corroborated/Disputed have never
actually been exercised on real data, only on the isolated test script.

**HIGH — Physically split the ontology into its own repo.** PARTIAL
PROGRESS 2026-07-11: file-level reorganization done — `tgs-core.ttl` is
now a genuinely separate, self-contained file (was `ontology/schema.ttl`),
and every primary class has its own complete file with `owl:imports`
pointing at it. What's still NOT done: the actual cross-REPO split — everything
still lives in one git repo (`nate-hagens-kg`). The file-level separation
makes a future repo split easier when it happens (just move
`tgs-core.ttl` + `catalog-v001.xml` out), but isn't the same thing. Still
cheapest to do while the graph is small (678 triples).

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

**MEDIUM — Domain-scoped reliability tiers.** Current model is one fixed
`ReliabilityTier` per `Source`, but real epistemics don't quite work that
way — Hagens is plausibly `Reputable` generally but arguably closer to
`Authoritative` when reporting his own stated influences/intent; Richardson
would plausibly be `Authoritative` specifically on American political
history. Deliberately deferred until real multi-domain content exists to
test the distinction against — not worth designing in the abstract.

**MEDIUM — Concept evolution over time isn't modeled.** A `thinkr:Concept`'s
`skos:definition` is a single string — if Hagens revises his framing of
something between an earlier episode and a later one, there's currently no
way to represent that the definition CHANGED, only whatever the latest
paraphrase currently says. The `prov:wasRevisionOf` pattern already built
for superseded `Evidence` (the Neanderthal-taxonomy case) is the obvious
template to reuse here, just never applied to `Concept` itself. Only
matters if tracking how Hagens' thinking has shifted over time is a real
goal, as opposed to "what does he currently believe" — raised during the
bottom-up-vs-top-down content strategy discussion, not yet prioritized.

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

**FUTURE, not yet actionable — dedicated Claude Skill.** MJSullivan intends to
eventually build one (mirroring the `uwom-ontology` skill in his other
`uwom-kg` repo, renamed from `knowledge-graph` on 2026-07-10) once this project's patterns feel more settled.
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
  `data/seed/persons.ttl`/`schools.ttl` for examples).
- `data/generated/` is the output of `extraction/promote_to_rdf.py` —
  don't hand-edit it; edit the DuckDB staging rows and re-run the promote
  script.
- Before any `git commit`/`git push`, double check the terminal prompt
  actually says `nate-hagens-kg`, not `uwom-kg` — MJSullivan has two
  projects open in separate terminal windows and has mixed them up before
  (harmless once, since `main` vs `master` makes it obvious after the
  fact, but worth avoiding).

## Gotchas (lessons learned — read before repeating a mistake)
Backward-looking, as opposed to the forward-looking Backlog above. Each of
these actually happened and cost real debugging time; logged so a future
session (or MJSullivan on a tired evening) doesn't repeat it.

- **When splitting a graph by class, classes with ZERO instances yet are
  easy to forget entirely.** During the 2026-07-11 one-class-one-file
  reorganization, `thinkr:Source` (a real declared class, just with no
  individuals yet) fell through every categorization rule and printed as
  "uncategorized" — caught by checking the sanity-check output before
  trusting the triple-count match, not by the count itself (which would
  have been wrong too, but a raw mismatch alone doesn't tell you WHICH
  triples went missing). `Work` and `Episode` had the same zero-instance
  status and were included correctly only because they were remembered
  from a previous session's backlog note — worth explicitly listing every
  declared class before any future repartition, not just the ones with
  visible data.
- **A hardcoded file list anywhere is a latent bug waiting for the next
  reorganization.** `promote_to_rdf.py`'s `load_existing_labels()`
  hardcoded `concepts.ttl` + `people.ttl` by name — broke silently (no
  crash, just returned incomplete/wrong matches) the moment `people.ttl`
  split into `persons.ttl` + `schools.ttl`. Fixed by switching to
  `glob(f"{seed_dir}/*.ttl")`. Any future script that touches specific
  seed filenames by name should default to globbing instead, precisely
  because this project's file structure has already changed twice
  (2026-07-10 namespace split renamed files, 2026-07-11 governance
  reorganization split/renamed/dissolved several more) and will likely
  change again.

- **rdflib 7.1.1 + Python 3.14 are incompatible** (AttributeError at import
  time — a real upstream bug, not local misconfiguration). `python3 -m venv
  .venv` on this Mac defaults to 3.14. Fixed via `requirements.txt` pinning
  `rdflib>=7.6.0`. If `make venv` ever fails the same way again, `pip
  install --upgrade rdflib` inside the venv is the fix — don't re-diagnose.
- **Turtle parses a trailing `.` as end-of-statement**, even inside what
  looks like a safe prefixed name. Bit us on DBpedia URIs for names ending
  "Jr." (Martin Luther King Jr., William R. Catton Jr.). Fix: use the full
  `<http://dbpedia.org/resource/...>` IRI in angle brackets for those cases
  instead of the `dbr:` prefixed form.
- **`g.parse()` returns a truthy Graph object**, so `x.parse(f) or
  print(...)` in a list comprehension NEVER calls print — `or` short-
  circuits on the truthy left side. Caught in the original `make validate`
  one-liner; silently produced zero "OK" lines while still reporting a
  correct triple count, which almost passed as "working."
- **A schema's formal `rdfs:domain` can silently drift from how a property
  is actually used.** `tgs:confidence` was declared `rdfs:domain
  tgs:Concept` for a long stretch while every real usage was on
  `tgs:LinkNote` (later `thinkr:Evidence`) — the property's own
  `rdfs:comment` even said "use this on the link, not the concept,"
  contradicting its own domain axiom. Nothing caught this until a manual
  audit; SPARQL doesn't enforce domain/range at data-insert time, so wrong
  axioms don't error, they just quietly lie.
- **Renaming by regex on class names is dangerous when individuals use a
  `Class.Name` IRI convention.** A pattern matching bare `Person` also
  matches the START of `Person.MarcusAurelius` (nothing excluded a
  following `.`), silently reclassifying every domain individual as
  vocabulary during the thinkr:/tgs: split. Caught by running a live query
  and getting zero results, NOT by the file still parsing as valid Turtle —
  parsing successfully and querying correctly are different bars.
- **A prefix rename has (at least) FOUR distinct token forms to catch, not
  one** — learned the hard way across two separate rename passes
  (`tgs:`→split, then `thinker:`→`thinkr:`). (1) the RDF prefix token
  itself in `.ttl`/`.sparql` files (`thinker:Foo`), (2) the Python
  `Namespace` identifier (`THINKER = Namespace(...)`), (3) the namespace
  URI string (`http://example.org/thinker#`), and — the one that slipped
  through even after fixing the first three — (4) STRING-LITERAL prefix
  labels passed to `graph.bind("thinker", THINKER)`. That fourth one is a
  lowercase string, invisible to a regex targeting the uppercase Python
  identifier, and produces genuinely confusing output if missed: a
  serialized file with `@prefix thinker: <.../thinkr#>` — label and URI
  silently mismatched. Caught only by actually running `promote_to_rdf.py`
  end-to-end and reading its real output, not by any of the syntax/parse
  checks. Any future prefix rename needs to explicitly grep for all four
  forms, not assume fixing three means the job's done.
- **Text-based find/replace across `.ttl` files never touches vocabulary
  URIs embedded in Python code** (`TGS["ConfidenceLevel.Curated"]`-style
  construction in `compute_confidence.py`, `promote_to_rdf.py`, and the CI
  YAML). Any future namespace/prefix change needs a SEPARATE, deliberate
  pass through every `.py` and `.yml` file — it will not happen for free
  alongside the `.ttl` rename.
- **A SPARQL query can "pass" a test while silently depending on leftover
  state from earlier in the same script/session** — `query_examples.sparql`
  appeared correct after the first namespace fix because the test graph
  still had `thinkr:` bound from an earlier unrelated `parse()` call in
  the same Python process, masking that the file itself was missing its
  own `PREFIX thinkr:` line. Would have failed immediately in the real
  Oxigraph CLI. Caught only by deliberately re-testing against a fresh
  graph with zero inherited bindings. Be suspicious of a first "pass" if
  the test setup could be leaking state.
- **Two terminal tabs open in two different projects is a real, repeated
  risk**, not a one-off. `main` = this repo (nate-hagens-kg), `master` =
  the sibling project (folder renamed `knowledge-graph` -> `uwom-kg` on
  2026-07-10, branch name unchanged). Always glance at the prompt before
  `git commit`/`git push`. Already happened once — a commit with a
  Nate-Hagens-KG-themed message landed in the wrong repo's history
  (harmless, just confusing).
- **Shell brace-expansion mistakes create silent literal folders** — an
  early `mkdir -p {ontology,data/seed}`-style command (missing proper
  expansion) created an actual folder named `{ontology,data` sitting empty
  alongside the real ones. Always worth a `find . -maxdepth 1` sanity check
  after any bulk directory-creation command.
- **macOS Finder hides dotfiles/dotfolders by default** (`.github`,
  `.gitignore`, `.venv`), which can make a correctly-placed file look
  "missing." Cmd+Shift+. toggles visibility instantly.

## Common commands
```bash
make venv            # create .venv and install requirements.txt
make validate         # parse-check every .ttl file (expect 678 triples)
make load-oxigraph    # load everything into a local Oxigraph store
make init-db           # set up the DuckDB review-queue tables
make promote-dry       # preview what promote_to_rdf.py would write
make promote            # write approved staging rows into data/generated/
python scripts/compute_confidence.py --dry-run  # preview calculatedConfidence
python scripts/compute_confidence.py             # apply it — run after ANY Evidence edit
```

## Working agreement
MJSullivan edits the TTL files directly rather than routing every addition
through a Claude session first, and reports changes back. A future
session should NOT assume full knowledge of current graph state from this
file alone — always check `git log` and re-run `make validate` before
making assumptions about what exists.

## This is a separate project from other Claude Code work
This repo is its own git repository and should stay that way — don't nest
it inside another project's directory or reference files outside this
repo's tree unless explicitly asked to. MJSullivan's other active project,
`~/projects/uwom-kg` (renamed from `knowledge-graph` on 2026-07-10), is
unrelated (different domain: units of measure / UWOM ontology) and uses
branch `master`, not `main` — a useful tell if you're ever unsure which
repo a terminal session is in.
