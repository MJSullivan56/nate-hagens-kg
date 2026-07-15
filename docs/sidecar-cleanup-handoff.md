# Sidecar Cleanup — Handoff Doc

**Status: BACKLOG, NOT YET EXECUTED.** Reordered 2026-07-13 into
chronological order, LATEST FIRST, per MJSullivan's request. Section
dates are preserved in each header. Within a single date, sub-ordering
is a best-effort reconstruction from internal cross-references — flag
anything that reads out of order. **2026-07-14 update: session cut off
before this doc was refreshed live — the top section below was
reconstructed after the fact from the tail of that conversation, so
treat its internal ordering as reliable but its completeness as
possibly missing earlier moves from the same session that occurred
before the point the recovered transcript begins.**

## LOCAL ENVIRONMENT REFERENCE (living section, not dated/superseded —
## keep this current rather than appending a new dated copy each time
## something changes)

**Repo root**: `nate-hagens-kg/`

```
nate-hagens-kg/
├── CLAUDE.md
├── README.md
├── requirements.txt
├── Makefile
├── docs/
│   ├── sidecar-cleanup-handoff.md   (this file)
│   ├── docs_README.md
│   └── persona_human_prototype-8.ttl  (moved here 2026-07-14, out of data/seed/ —
│                                        historical/reference only, its non-canonical
│                                        content (tgs:Human.NathanHagens, a different
│                                        Schmachtenberger interaction subset) must never
│                                        be loaded by load_oxigraph.sh's *.ttl glob)
├── tgs_store/                        (Oxigraph RocksDB storage — gitignored, regenerated
│                                       via load_oxigraph.sh. MOVED HERE 2026-07-14, was
│                                       nested under scripts/ — that was an artifact of
│                                       load_oxigraph.sh's own original relative-path choice,
│                                       never a deliberate decision. tgs_store is a
│                                       materialized, fully-derived view of data/seed/*.ttl —
│                                       conceptually data, not tooling, so it belongs at the
│                                       repo root next to data/, not inside scripts/.)
├── scripts/
│   ├── load_oxigraph.sh             (bulk-loads every data/seed/*.ttl into ../tgs_store via `oxigraph load`)
│   ├── validate_class_purity.py     (NEW 2026-07-14 — confirms every data/seed/*.ttl file
│   │                                 holds instances of exactly one class; run with
│   │                                 --check-scratch-empty before considering any batch done)
│   ├── query_examples.sparql
│   └── compute_confidence.py        (derives LinkNote.calculatedConfidence from Evidence — never hand-asserted)
├── extraction/                      (expanded 2026-07-14 — see the "extraction/
│   │                                  investigation" entry below for full context;
│   │                                  two genuinely different maturity levels live here,
│   │                                  see extraction_README.md's own framing)
│   ├── download_transcripts.py      (WORKING — sitemap-based, resumable, respects Crawl-delay)
│   ├── download_manifest.csv        (tracks what's downloaded; resumable — skipped on rerun)
│   ├── no_transcript_available.csv  (tracks confirmed-no-transcript episodes; resumable)
│   ├── transcripts_raw/             (raw downloaded source files, pre-text-extraction)
│   ├── transcripts_text_cache/      (WORKING, real content — 115 files as of 2026-07-14;
│   │                                  gitignored, text never committed, per this project's
│   │                                  standing copyright discipline)
│   ├── match_substack_summaries.py  (WORKING — Frankly-number exact match, fuzzy-title fallback)
│   ├── substack_summaries_index.csv (metadata only — extracted text stays in local cache)
│   ├── substack_text_cache/
│   ├── substack_summaries_raw/
│   ├── index_named_entities.py      (WORKING — spaCy NER, two-layer: expensive raw pass
│   │                                  cached once per doc, cheap `--refilter` rerunnable)
│   ├── entity_index.duckdb          (raw NER cache)
│   ├── entity_index.csv
│   ├── top_persons.py               (WORKING — ranked PERSON-entity worklist for bootstrapping)
│   ├── promote_to_rdf.py            (writes reviewed staging rows into data/generated/ —
│   │                                  never hand-edit that output, edit staging + rerun)
│   ├── init_staging_db.py           (sets up the DuckDB review-queue tables)
│   ├── cited_sources_raw/
│   │   └── California Doughnut...Report 2025.pdf
│   └── extraction_README.md         (CAVEAT: on 2026-07-14 MJSullivan initially said this
│                                      file doesn't exist and shared the repo-ROOT README.md
│                                      instead — but a screenshot the same session showed a
│                                      file literally named extraction_README.md inside this
│                                      folder, dated 2026-07-12. Never resolved which is
│                                      authoritative. The content actually used this session —
│                                      confirming Steps 1-2 + entity-triage are WORKING, Steps
│                                      3-6 (LLM concept/link mining) are aspirational, never
│                                      run at scale — came from whatever MJSullivan pasted,
│                                      not independently confirmed against the file on disk.
│                                      Worth a `diff` next session before trusting either copy.)
└── data/
    └── seed/                        (one-class-one-file governance — every .ttl here is loaded as a unit)
        ├── scratch.ttl               (NEW 2026-07-14 — dedicated staging file for mid-task
        │                              partial enrichments; must be empty before any batch is
        │                              considered done, see its own header for the convention)
        ├── tgs-core.ttl             (schema: classes, properties — zero individuals as of 2026-07-14)
        ├── enumerations.ttl         (all thinkr:Category-marked classes + their enumerated
        │                             individuals — split out of tgs-core.ttl 2026-07-14)
        ├── humans.ttl
        ├── personas.ttl
        ├── relationships.ttl
        ├── episodes.ttl
        ├── organizations.ttl
        ├── academicinstitutions.ttl
        ├── schoolsofthought.ttl
        ├── concepts.ttl
        ├── subjects.ttl
        ├── works.ttl
        ├── sources.ttl
        ├── evidences.ttl
        ├── linknotes.ttl
        ├── crosswalknotes.ttl
        └── catalog-v001.xml         (Protégé catalog file — resolves thinkr:/tgs: imports across split files)
```

**Triplestore**: Oxigraph, served locally at `http://127.0.0.1:7878`.
NOT a background daemon — `oxigraph serve --location ../tgs_store --bind
127.0.0.1:7878` runs in the foreground in its own terminal tab and must
stay open, still run FROM `scripts/` (`load_oxigraph.sh`'s relative
paths — `../tgs_store` for the store, `../data/seed/*.ttl` for the
source files — both assume that working directory; the store's location
changed 2026-07-14, the working directory requirement did not).
`oxigraph load` (used internally by `load_oxigraph.sh`) is an offline
bulk-load command and needs exclusive access to `tgs_store` — `serve`
must be stopped (Ctrl-C) before reloading, never run concurrently with
it.

**Standard reload sequence after any seed data change**, confirmed
working 2026-07-14 (updated same day for the relocated store):
```bash
# Ctrl-C the running serve process first
cd nate-hagens-kg
rm -rf ./tgs_store
cd scripts
./load_oxigraph.sh
oxigraph serve --location ../tgs_store --bind 127.0.0.1:7878
```
`load_oxigraph.sh` does NOT clear the store itself — it only adds
triples via `oxigraph load` per file. Skipping the `rm -rf` step before
a reload leaves stale triples (e.g. old Human-pointing values alongside
new Persona-pointing ones) coexisting rather than being replaced —
confirmed the hard way earlier this session.

**Querying**: the Oxigraph browser UI (YASGUI-based) at
`http://127.0.0.1:7878` is MJSullivan's preferred way to run SPARQL —
same standing preference as UWOM's Oxigraph workflow, not curl.
Programmatic queries when needed: `curl http://127.0.0.1:7878/query -H
'Content-Type: application/sparql-query' --data '<query>'`.

**Protégé**: used for validation/visual inspection only, not editing —
every `data/seed/*.ttl` file's own header comment ("Imports tgs-core
for Protege compatibility — editing this file alone will resolve
thinkr: classes/properties via the catalog file") confirms
`catalog-v001.xml` exists specifically to let Protégé resolve the
cross-file `thinkr:`/`tgs:` imports when opening the split ontology.
Real editing happens directly in the `.ttl` files via VS Code / Claude
Code, not inside Protégé itself.

**Editing tools**: VS Code with the Claude Code extension for real
implementation work (multi-file edits, scripted migrations). Claude
Chat (this doc's origin) for architecture/planning/prototyping — the
division of labor matches the parallel `uwom-kg` project's own
established pattern. `nate-hagens-kg` and `uwom-kg` are separate repos,
opened in separate VS Code windows when working on both — multi-root
workspace switching was confirmed unreliable in the current Claude Code
VS Code extension (open GitHub issues on context not following the
active file), so each project stays in its own window rather than a
shared workspace.

**Validation**: `scripts/compute_confidence.py` derives
`LinkNote.calculatedConfidence` from `Evidence` sets — never
hand-asserted, matches UWOM's `validate_repo.py` discipline of a
scripted, re-runnable check rather than manual verification.
`scripts/validate_class_purity.py` (NEW 2026-07-14) confirms every
`data/seed/*.ttl` file holds instances of exactly one class and that
`scratch.ttl` is empty — a real, narrow, permanent check, but NOT a
SHACL validator and not a substitute for one: it catches file-placement
violations specifically, nothing about dangling references, cardinality,
or enumeration-value validity. No project-specific SHACL shapes
confirmed either way for this repo as of 2026-07-14 (unlike UWOM, which
has a mature SHACL validator) — still genuinely open, not resolved by
today's narrower script.

**Personal laptop, package manager available**: this is MJSullivan's
own machine, not a shared/managed environment — Homebrew is available
and anything reasonably needed (a SHACL engine, a different Oxigraph
version, etc.) can be installed freely. Don't hold back on suggesting a
tool because of an assumed environment-approval or install-permission
barrier that doesn't actually apply here.

**MJSullivan is NOT a professional developer** — explicitly confirmed
2026-07-14, worth calibrating future sessions accordingly, not just
this one. He's clearly capable (running Oxigraph, VS Code, git, Claude
Code day to day) but doesn't have deep devops/terminal fluency to fall
back on — commands should be given as complete, copy-pasteable
sequences with the working directory made explicit, not assumed
implicit or left as "adjust as needed." Error messages should be
walked through rather than assumed self-explanatory (e.g. distinguishing
"the process isn't running" from "wrong path" from "port conflict" when
a connection fails, rather than a single generic fix). This isn't a
one-off caveat for this thread — it should shape how technical
instructions are given in general on this project going forward.

## GOVERNANCE + FILESYSTEM CLEANUP (2026-07-14, later the same day):
## the same class-purity mistake happened twice, so a real fix got
## built instead of a third manual correction; a parallel filesystem
## version of the identical mistake got caught and fixed too

**The RDF-level problem**: `linknotes.ttl` had accumulated 14 direct
property statements on `Concept`/`Persona`/`SchoolOfThought` subjects
(`influencedBy`/`echoesIdeaOf`/`contrastsWith`/`appliesTo`/
`convergesWith`) — facts that belonged in `concepts.ttl`/`personas.ttl`/
`schoolsofthought.ttl`, landed in `linknotes.ttl` instead because that's
where the surrounding work (the Batch 5 Persona migration) happened to
be centered. MJSullivan named this explicitly as a repeat offense, not
a one-off. Fixed: every statement moved to its OWN subject's actual
home file, merged into that subject's existing individual block (not
left as an orphaned triple) — 12 to `concepts.ttl`, 1 to `personas.ttl`
(`Persona.MartinLutherKingJr`'s `appliesTo`), 1 to `schoolsofthought.ttl`
(`SchoolOfThought.DoughnutEconomics`'s `convergesWith`). Verified via
exact triple-count match before/after (1970 -> 1970) and all 17
individual facts confirmed still resolving correctly post-move.
`linknotes.ttl` now holds ONLY `thinkr:LinkNote` individuals (plus the
`LinkNote` class declaration itself — consistent with the
`Relationship`/`Persona` precedent of a class living in its own
instances' file).

**A parallel audit found the same violation pattern in 2 more files,
NOT yet fixed, confirmed real via a proper subject-class-prefix script
(not just eyeballing)**: `episodes.ttl` mixes `Series` individuals in
with `Episode` instances; `subjects.ttl` mixes `ConceptScheme`
individuals in with `Subject` instances. Both would need a genuinely
new file each (`series.ttl`, `conceptschemes.ttl`) — bigger than a
same-day relocation, deliberately left open pending confirmation.

**Root-cause fix, not just this one correction**: MJSullivan proposed
`data/seed/scratch.ttl` — a dedicated staging file for mid-task partial
enrichments, with every entry requiring an explicit destination comment,
swept to its real home before any task counts as done. Built, with a
full header explaining the convention. Deliberately IS loaded by
`load_oxigraph.sh` like every other seed file (queryable while content
is still in flight, not invisible until promoted) — the violation isn't
"data existing somewhere provisional," it's "provisional data with no
designated legitimate home, forcing it into whatever file's already
open."

**`scripts/validate_class_purity.py` built alongside it** — confirms
every `data/seed/*.ttl` file's named subjects belong to exactly one
class, and (via `--check-scratch-empty`) that `scratch.ttl` has no real
content beyond its own header. Tested against the actual repo state,
not just written and assumed correct: confirmed it catches the two
still-open violations, confirmed `linknotes.ttl` now reads clean,
confirmed the scratch-non-empty case genuinely fails (exit 1) — caught
one real testing mistake along the way (a shell pipe silently swallowed
the script's actual exit code on the first attempt; re-tested properly
before trusting the result). This does NOT close the SHACL-validator
gap flagged repeatedly earlier — it's one narrow, permanent check, not
a general-purpose validator.

**The identical mistake, one layer down, same day**: a second
`tgs_store` had accumulated at the repo root, duplicate of the real one
under `scripts/tgs_store` — near-certainly from a `load_oxigraph.sh` or
`oxigraph serve` invocation run from the wrong working directory at
some earlier point (`load_oxigraph.sh`'s paths are relative to
wherever it's launched from, not to its own location on disk — the
same category of mistake as the class-purity issue above, just at the
filesystem level: something landed in the wrong place because of
*where you happened to be standing*, not a deliberate choice).
Diagnosed properly before touching anything: confirmed via `ps aux`
which server process was actually running, then `lsof -a -d cwd -p
<pid>` to confirm its real working directory (`scripts/`) rather than
trusting file-modification timestamps alone. Once confirmed which
`tgs_store` was live, deleting the stale root-level one was safe
immediately, no `Ctrl-C` needed first — the running server had zero
open file handles into it.

**Then, on reflection, relocated the LIVE store too**: `scripts/` was
never a deliberate home for `tgs_store`, just an artifact of
`load_oxigraph.sh`'s own original relative-path default. `tgs_store` is
a materialized, fully-derived view of `data/seed/*.ttl` — conceptually
data, not tooling — so it now lives at the repo root, alongside `data/`,
not nested inside `scripts/`. `load_oxigraph.sh`'s `STORE_PATH` default
changed from `./tgs_store` to `../tgs_store`; the requirement to still
RUN the script from `scripts/` itself did NOT change (only the store's
own location moved, not the script's working-directory assumption).
Full migration: stop the server, `mv scripts/tgs_store ./tgs_store`
from repo root, restart with `--location ../tgs_store` from `scripts/`.

## SCALE TRANSITION (2026-07-14, same day, following the `discusses`-gap
## investigation below): first real Persona bootstrap completed, model
## confirmed ready for VERY LARGE expansion, two blockers checked and
## cleared

**Context**: `extraction/download_transcripts.py` was re-run 3x, landing
344 real transcript PDFs in `extraction/transcripts_raw/` (one real
mid-session bug: the folder briefly went missing between two runs —
never conclusively diagnosed, `download_manifest.csv` stayed accurate
throughout so no data was lost, just flagged in case it recurs).
`extraction/index_named_entities.py` and `top_persons.py` — confirmed
genuinely incremental/safe to rerun by reading the actual source, not
just the README — surfaced a real, much larger corpus than the graph's
current 25 people / 14 episodes: ~230 real Interview transcripts, 96
Frankly monologues, 18 Reality Roundtables, and a long roster of
frequently-recurring guests not yet modeled at all.

**MJSullivan's framing, worth keeping close through the expansion
phase**: "the expectation is that this will become a VERY LARGE graph...
this is why we needed to get the model right." Today's batches 0-6 were
explicitly validated against that bar, not just against today's small
seed set.

**First real bootstrap completed end-to-end**: Art Berman (519
mentions/20 documents in the entity index) — `Human.ArtBerman`/
`Persona.ArtBerman`, 4 confirmed guest episodes (2 exactly dated via
thegreatsimplification.com's own episode pages, 2 honestly flagged
date-unconfirmed), 2 `Relationship` individuals (his TGS guest history,
and a genuine cross-link to `Organization.TheOilDrum` — he was a
Managing Director/contributor there, the same org Nate has his own
`Relationship` with), and `Concept.EnergyBlindness`'s first-ever
intellectual lineage (`influencedBy`, `Candidate` confidence — he's
widely credited with coining the term). Confirmed via search: no
genuine Wikipedia page exists (checked twice, stated explicitly per the
bootstrap procedure rather than silently omitted) — Wikidata was NOT
separately checked, a real gap distinct from "confirmed absent," not yet
resolved. One real process bug caught mid-bootstrap: validated against
a stale copy of `personas.ttl` (forgot to re-sync the working copy after
editing it), got a false "25/25" Human/Persona count, caught by not
trusting the surprising number, traced to the actual cause, fixed.
Lesson: always re-copy before validating, every time, no exceptions.

**The bootstrap procedure itself needed updating before this could
happen** — `CLAUDE.md`'s existing version (2026-07-11) predates the
`Person`->`Human` rename, the `School` 3-way split, AND the whole
Persona architecture. Updated version used for Berman (not yet written
back into `CLAUDE.md` — do that before the next bootstrap session):
verify identity -> Human gets biography only -> Persona gets
`actsThrough` + everything public-facing -> verify each affiliation's
own legitimacy before creating it -> `memberOf` stays on Human ->
`Relationship` (Persona-Persona/Persona-Org) for anything structured ->
`CrosswalkNote.aboutEntity` points at Persona, never Human -> test with
a real query, not just "the file parses."

**Two structural questions raised, both checked and cleared before
scaling further** (small, cheap to verify now; would have been
expensive to discover wrong after dozens more individuals depended on a
false assumption):
1. Does `thinkr:hasGuest` actually support multiple values on one
   `Episode`, cleanly? Tested directly (isolated test triple, never
   written to real data) — confirmed yes, resolves correctly, no schema
   change needed.
2. Does a Roundtable `EpisodeType` need minting? No — `thinkr:
   EpisodeType.PanelDiscussion` already exists, already carries
   `skos:altLabel "roundtable"`/`"Reality Roundtable"` — someone
   anticipated this exact mapping when the schema was originally built.
   Just needs to actually get used.

**A real episode-numbering risk surfaced, confirming an existing design
decision was right rather than revealing a new problem**: raw "TGS+
number" is NOT a safe unique identifier across the real corpus —
`TGS118`, `TGS140`, `TGS60`, `TGS46`, `TGS80`, `TGS97` all have TWO
different guests sharing the same number (a site-side numbering quirk
over the show's history, not a local bug). `CLAUDE.md`'s existing IRI
convention already mandates a title fragment alongside the number for
exactly this reason — zero tolerance for a future shortcut that treats
number-alone as sufficient. Related, confirmed via
`download_manifest.csv`: episode TYPE should always come from that
manifest's own `type` column (sourced from which index page the URL was
discovered under on the real site) — never inferred from filename
pattern, which has visibly drifted in style over the show's history
(concatenated-no-hyphens early on, hyphenated-with-title-words later,
confirmed across Frankly/TGS/RR filenames alike).

**Real structural risks flagged for the scale-up, ranked by
priority — none blocking, all worth deciding deliberately rather than
discovering the answer implicitly a hundred bootstraps from now:**
1. **No confirmed validator for this repo** (unlike UWOM's
   `validate_repo.py`). All validation this entire session has been
   ad hoc `rdflib`/live-SPARQL checks, hand-run and hand-read after every
   batch — works because the batches were small enough to eyeball.
   Will NOT hold up at "very large." Single highest-priority
   infrastructure gap before mass expansion, ranked above all of the
   items below.
2. **`compute_confidence.py` was never actually run this session** —
   every `calculatedConfidence` value touched (the `EnergyBlindness`/
   Berman `LinkNote`) was hand-approximated to match its Evidence,
   explicitly flagged as needing the real script run before being
   trusted. Fine as a one-off caveat; a real liability if it accumulates
   across dozens of new `LinkNote`s without ever being reconciled
   against the actual script.
3. **`hasPersonalRelationship` is a known-wrong name** — used for
   professional/academic relationships too, since
   `hasOrganizationRelationship`/`hasSchoolRelationship` were never
   built out (documented, deliberate simplification from Batch 3, not a
   new problem). Cheap to fix now at ~9 `Relationship` individuals;
   genuinely disruptive to fix after hundreds more exist under the
   current name.
4. **`memberOf` + structured `Relationship` deliberately coexist**
   (confirmed intentional, University of Minnesota precedent) — fine at
   Nate's handful of affiliations, real ongoing double-maintenance cost
   at hundreds of guests each with real institutional histories. Worth
   deciding now whether this is permanent or transitional.
5. **The bootstrap procedure is intentionally human-in-the-loop** (by
   design, per `CLAUDE.md` — wrong-person traps need judgment, this is
   correct and should NOT change) **but the delivery mechanism doesn't
   scale to "very large" done one person at a time in a chat window.**
   Discipline should survive; move the actual execution to Claude Code,
   which can run the same verify-then-build-then-validate loop across
   many candidates per session while a human spot-checks rather than
   hand-types every triple.
6. **The `discusses` confidence-model recommendation from the earlier
   entry below is still not formally confirmed by MJSullivan** — lock
   this in before Step 3 (LLM concept-mining) ever runs at volume;
   retrofitting hundreds of already-asserted direct claims into the
   Evidence structure later is far more painful than deciding it once
   now.

**Concrete next-session plan, in order:**
1. Build a real, repeatable validation script (item 1 above) before
   anything else at volume.
2. Write the updated bootstrap procedure back into `CLAUDE.md` (it's
   proven now, on a real second example, per the original 2026-07-11
   note's own stated bar for generalizing it).
3. Move primary bootstrap/seeding execution to Claude Code; keep Claude
   Chat for architecture/planning per this project's established
   division of labor.
4. Lock in the `discusses` and `hasPersonalRelationship`-family
   decisions.
5. Seed the 18 real Roundtable episodes from `download_manifest.csv`
   (title/URL/type all ground-truth, no filename parsing) — first real
   test of the multi-guest `hasGuest` pattern at true scale, not just an
   isolated 3-guest test triple.
6. Continue the `top_persons.py` bootstrap queue — Josh Farley, Jeremy
   Grantham, Steve Keen, Chuck Watson, Simon Michaux next in line by
   mention count among genuinely new (not-yet-modeled, not name
   fragments) candidates.

## PAUSED (2026-07-14, third conversation of the day): insight-gap
## review led to a real extraction/ investigation — closing the
## `discusses` gap looks doable, one hand-verified pilot done, more
## needed before automating

**Starting point**: re-ran the "what insights, what gaps" question
against the now-fully-migrated Persona graph (post Batches 0-6). Real
findings, via live query, not speculation:
- Only 2 of 14 Episodes have any `thinkr:discusses` link to a `Concept`
  (`TGS_226`→`MoneyAsClaimOnEnergy`, `TGS_42`→`Metacrisis`) — the
  property built specifically to close the "zero Episode->Concept
  links" gap flagged back on 2026-07-13, still 12 episodes short.
- 7 Concepts have zero intellectual lineage of any kind asserted
  (`CarbonPulse`, `EROI`, `EnergySlaves`, `GreatSimplification`,
  `GrowthImperative`, `HumanPredicament`, `TheoryOfChange`) — though
  some of these may be genuinely Nate-original with no historical
  lineage to trace, not necessarily a modeling gap.
- `Persona.NateHagens` has NO `CrosswalkNote` — no DBpedia/Wikidata
  mapping exists for the seed subject of the entire graph.
- Persona richness is heavily skewed toward Nate (16 predicates) with
  every other Persona flat at 4-7 — expected given today's earlier
  batches were architecture, not content enrichment.
- Nate's `memberOf` list has 2 organizations (University of Vermont,
  University of Chicago) with no matching structured `Relationship` —
  same category of gap Batch 4 already closed for Oil Drum/Post
  Carbon/Peak Oil, just not extended to these two yet.

**Decision**: closing the `discusses` gap ranked as the highest
insight-value-per-effort target, since it's the piece that would let
you query "what ideas came up across the show" at all, not just "who
was on which episode." MJSullivan confirmed the transcript library +
NER extraction infrastructure exists, though was unsure of its current
state — investigated for real rather than assuming.

**What `extraction/`'s own README says exists vs. is aspirational**
(content as pasted by MJSullivan this session — see the
LOCAL ENVIRONMENT REFERENCE section above for an unresolved caveat
about whether this matches the actual `extraction_README.md` on disk):
- WORKING: transcript download (sitemap-based, resumable), Substack
  summary matching, and named-entity triage (`index_named_entities.py`
  / `top_persons.py`, spaCy-based, two-layer expensive-NER +
  cheap-refilter design).
- ASPIRATIONAL, NEVER RUN AT SCALE: the actual LLM concept/link mining
  plan (Steps 3-6) — per `CLAUDE.md`'s own prior note, only tested
  against fake staging data, never real transcripts. This is precisely
  the step that would produce `discusses` links.
- A real, previously undocumented design gap surfaced by reading this
  README closely: `discusses` is never mentioned in the Evidence/
  Candidate-Curated review section that `echoesIdeaOf`/`influencedBy`/
  `contrastsWith` explicitly get (Step 4-5) — no stated confidence
  model for it at all. Flagged as an open decision, not resolved
  unilaterally.

**Real findings from actually inspecting `transcripts_text_cache/`
(115 files, uploaded this session)**, not assumptions:
- ZERO of the 9 uncovered Interview-type episodes (`TGS_5`, `20`, `31`,
  `42`, `50`, `85`, `126`, `132`, `165`, `217`) have a downloaded
  transcript in the cache at all — a gap in the source library itself,
  not something extraction can fix by re-running anything. Worth
  checking against `no_transcript_available.csv`/`download_manifest.csv`
  next session to see if this is already known/tracked or a fresh
  discovery.
- Of the 3 uncovered Monologues, `Frankly-138` and `Frankly-139` DO
  have real transcripts; `Frankly-145` has only show notes, not a full
  transcript — another real source-library gap, not an extraction bug.
- Bonus, out-of-scope-for-now discovery: an unmodeled Reality Roundtable
  transcript (`RR10...Schmachtenerger...`, filename misspelled) very
  likely featuring Daniel Schmachtenberger on an episode format
  (`RR`/Roundtable) this graph has never seeded at all — zero
  Roundtable `Episode` individuals exist currently. Flagged as a
  separate future "new episode" discovery, deliberately not chased
  this session.

**One real hand-verified pilot completed**: read `Frankly-138`
("How to Think About the Future, Part 1") in full and manually ran what
Step 3 would automate — checked all 19 existing Concepts against the
transcript for substantive discussion vs. mere name-drop. Results:
- Confident matches: `ComplexityCollapse`, `Wetware` — both sustained,
  multi-paragraph discussion, not incidental.
- Weaker/genuine-judgment-call matches: `HumanPredicament` (the exact
  phrase used once, briefly), `Metacrisis` (the idea is clearly present
  — coupled, mutually-amplifying crises — but the term itself never
  appears), `GreatSimplification` (invoked as one of several scenario
  branches, but also literally the show's own name, genuinely
  ambiguous), `TheoryOfChange` (loosely echoed, not the specific
  framing from the concept's own definition).
- Correctly excluded despite the word appearing — this is the important
  part, the exact failure mode Step 3 exists to catch: `PeakOil`
  (appears only inside a list of professional-identity camps, a
  name-drop) and `CircleOfTrustLocalism` (one passing phrase at the very
  end, undeveloped).
- Two strong NEW concept candidates surfaced, exactly matching Step 3's
  item 2: "Scenario Thinking" (explicitly named, defined, the organizing
  device for this whole 4-part series) and "Shortfall Risk" (explicitly
  defined, borrowed from Hagens' own Salomon Brothers background,
  reapplied to ecological/civilizational thresholds) — neither exists
  in `concepts.ttl` currently.
- Incidental corroboration, not a new fact: Iain McGilchrist mentioned
  by name as a recent-or-upcoming guest, consistent with the existing
  `TGS_217` relationship (dated 2026-03-24).

**This pilot concretely resolved the open `discusses`-confidence-model
question, at least as a recommendation**: given how genuinely
ambiguous the `GreatSimplification`/`TheoryOfChange` cases were, even
under careful by-hand review, `discusses` should get the same
Evidence-backed Candidate->Curated review treatment as
`echoesIdeaOf`/`influencedBy`/`contrastsWith` — NOT a direct
high-confidence assertion like `hasHost`/`hasGuest`. Recommendation
only, not yet formally confirmed by MJSullivan.

**Explicitly NOT done, next-session starting point:**
1. Pilot `Frankly-139` too — README's own advice is to validate on a
   handful before scaling, one episode isn't enough.
2. Check `download_manifest.csv`/`no_transcript_available.csv` to
   understand why zero Interview-episode transcripts are downloaded —
   possibly straightforward to fix by re-running
   `download_transcripts.py --type interview`, possibly a genuine
   never-published-transcript situation. Not yet investigated.
3. Formalize the by-hand Step 3 pass into an actual script once 2-3
   pilot episodes validate the pattern.
4. Get MJSullivan's explicit confirmation on the `discusses`
   confidence-model recommendation above before building anything that
   assumes it.
5. Resolve the `extraction_README.md` file-vs-pasted-content discrepancy
   flagged in the LOCAL ENVIRONMENT REFERENCE section.
6. The RR10 Roundtable discovery, whenever it becomes a priority — would
   require first deciding whether to seed a `RoundtableEpisode`
   type/individual pattern at all, not yet scoped.

## RESOLVED (2026-07-14, same day as the entry below, different
## conversation): the Persona-centered refactor is COMPLETE and
## live-verified — Batches 0 through 6

**This closes out the "SESSION CUT OFF" entry immediately below.**
Everything that entry flagged as prototype-only, not-yet-executed, or
next-session scope is now done, loaded into the real Oxigraph store,
and validated via live SPARQL query at every step — not just parsed
successfully. Full batch-by-batch detail lives in this session's own
transcript; this entry is the closing summary a future session (or a
future you) needs without re-reading the whole thing.

**Batches 0-2** (schema, 25 minimal `Persona` shells for every existing
`Human`, `Episode.hasHost`/`hasGuest` migrated to `Persona`) — done,
live-verified.

**Batch 3** (`relationships.ttl` fully rebuilt: `hasSubject`/`hasObject`
→ `Persona` on all 4 original relationships, `thinkr:role` retired in
favor of explicit `subjectRole`/`objectRole` on every interaction,
`dcterms:date` added wherever `episodes.ttl` confirms one with an
honest `scopeNote` where it doesn't, prefLabels naming the relationship
type. Also migrated `hasPersonalRelationship`/`hasPersonEntityType`/
`hasProfessionalRole` domains `Human`→`Persona` — a scope expansion
beyond the original plan, made explicitly and flagged at the time, not
silently folded in. **Closed a real, previously-undetected gap**: Daniel
Schmachtenberger's `Relationship` only modeled 3 of his 7 confirmed
`episodes.ttl` guest appearances — expanded to all 7.) — done,
live-verified.

**Batch 4** (folded in `persona_human_prototype-8.ttl`'s Oil Drum/Post
Carbon Institute/Peak Oil movement `Relationship` individuals; fixed an
orphaned `University of Minnesota` `Relationship` that existed but was
never actually linked back via `hasPersonalRelationship`) — done,
live-verified.

**File reorganization** (all 31 `owl:NamedIndividual`s AND their 9
owning `Category` classes moved out of `tgs-core.ttl` into a new
`enumerations.ttl` — one-class-one-file restored for that family.
First attempt at this had a real bug, a fragile string-splitting script
that misaligned classes with the wrong instance groups — caught by
actually reading the output rather than trusting the script ran without
an error, then rebuilt correctly.) — done, live-verified.

**Batch 5** (the actual core mechanism: `influencedBy`/`echoesIdeaOf`/
`contrastsWith`/`relatesTo` range flipped `Human`→`Persona`; every
instance in `linknotes.ttl` repointed — both the direct `Concept`
statements AND every `LinkNote.aboutObject`/`aboutSubject`, since each
pair asserts the same fact and migrating one without the other would
have split it; all 29 Human-targeting `CrosswalkNote.aboutEntity`
triples repointed, the 11 non-Human ones correctly left alone;
`thinkr:appliesTo` migrated too on MJSullivan's explicit approval — its
one instance turned out to already be repointed as a side effect of an
earlier blanket text replacement, only the schema domain needed a
follow-up fix to match.) — done, live-verified. **This was the
migration flagged as "not yet executed, not even fully scoped" across
two separate earlier sessions — it's the reason `LinkNote`/`Evidence`/
`compute_confidence.py` exist at all, not a peripheral cleanup.**

**Batch 6** (documentation close-out): the full architectural rationale
written into `CLAUDE.md` as a new `0f.` governance entry, alongside the
existing `0a`-`0e` foundational decisions. `persona_human_prototype-8.ttl`'s
stale header comment (still describing the superseded "Persona is a
proxy" model despite the file's own body having moved on) corrected.
This entry.

**What's still genuinely open, not resolved today, worth carrying
forward:**
1. Which specific `foaf:homepage` links (Substack/personal site/
   LinkedIn) belong on `Persona` vs. stay on `Human` — flagged as an
   open question back on 2026-07-12, still not decided.
2. `thinkr:memberOf` stays flat on `Human` rather than being fully
   converted to `Relationship` individuals for every organization —
   confirmed intentional (coexists with the structured version, per the
   University of Minnesota precedent), not a gap, but worth knowing this
   was a deliberate scope boundary, not an oversight.
3. `CLAUDE.md`'s "Current data state" and "Backlog" sections (further
   down in that file) were NOT touched today and are stale relative to
   everything in this doc — genuinely out of scope for this pass, not
   forgotten.
4. No SHACL validator or equivalent confirmed to exist for this repo —
   still genuinely unknown as of this writing, per the Local Environment
   Reference section above.

## SESSION CUT OFF (2026-07-14): Persona-centered architecture fully
## rebuilt and stress-tested; core mechanism migration still the real
## next step

**Status: prototype-only (`persona_human_prototype-8.ttl`), NOT yet
folded into the real graph.** Picked up directly from the MAJOR
GENERALIZATION entry immediately below and executed against it.

**THE final, settled principle — no Human-to-Human relationships
anywhere in this graph:**
> There will be Persona-to-Human relationships (via `actsThrough`
> only — a `Persona` pointing back to its `Human`). Every OTHER
> relationship in the graph is Persona-to-something: Persona↔Persona
> (guest-to-guest), Persona↔Organization/SchoolOfThought/
> AcademicInstitution (professional ties), Concept↔Persona
> (intellectual influence — NOT YET EXECUTED, see gap 3 below),
> Episode↔Persona (hosting/guesting, already built).

This is a real revision from the "Persona is a proxy for the Human"
framing settled just two messages earlier in the same thread (where
`Relationship.hasSubject` stayed `Human`, with `Persona` merely
cross-referencing via `hasPersonalRelationship`/
`hasProfessionalRelationship` held on both individuals). Both readings
were internally coherent; this session explicitly chose the more
sweeping one: `Human` is now a **pure leaf node** — biographical facts
only (name, birthdate, earned credentials, employment history),
reachable by exactly one relationship type (`actsThrough`, incoming
from its Persona/s) — while `Persona` owns every `Relationship`
(`hasSubject`/`hasObject` both `Persona`, never `Human`).
`thinkr:memberOf` (legal/formal weight) moves back to being asserted
via the Persona-owned `Relationship` structure rather than a flat
property on either individual; the earlier `thinkr:affiliatedWith`
property is superseded/dropped as a result.

**Rebuild executed and validated**: `Relationship.hasSubject` flipped
from `Human` to `Persona` across all 7 real `Relationship` individuals
in the prototype; the guest relationships (Monahan, McGilchrist,
Schmachtenberger) flipped from Human↔Human to Persona↔Persona.
Confirmed via live query: zero `Human` leakage anywhere in
`Relationship` subjects/objects.

**Real bug caught mid-rebuild, not hypothetical**: all three guest
`Relationship` individuals (Monahan, McGilchrist, Schmachtenberger)
silently lost their actual property declarations somewhere during an
earlier rebuild pass in the same thread — only bare references to them
survived elsewhere in the file. Caught by noticing McGilchrist's
relationship query came back empty, traced, and all three fully
reconstructed with original content restored (interaction dates,
roles, episodes intact). Worth remembering generally: "it parses"
isn't the same as "it's complete" — worth a verification pass even
late in a long rebuild session.

**Schema enrichment, same session, two real gaps caught and fixed:**
1. **Single `thinkr:role` → `subjectRole`/`objectRole` pair.** The old
   design assumed every `PodcastAppearance` is a clean host/guest
   binary with the guest's role left implicit; breaks the moment a
   relationship isn't (co-host, moderator, panelist — `InteractionRole`
   as a category is already extensible, the missing piece was one role
   slot per party). Every existing interaction rebuilt with both roles
   explicit. Proven to matter concretely via the reciprocal Monahan
   case (Nate hosted him on TGS episode 226; Monahan hosted Nate on his
   own show "The Regeneration Will Be Funded") — without the fix there
   was no clean way to distinguish direction except by which property
   happened to be populated.
2. **`dcterms:date` added to every `PodcastAppearance`.** Checking
   revealed some appearances had dates sitting on the real `Episode`
   individual but never copied onto the interaction blank node; others
   (Bend Not Break Part 1, episode 50, the off-show Monahan appearance)
   have no confirmed date at all. Resolved 8 of 10 appearances with
   real dates; the other 2 get an honest `skos:scopeNote` flagging the
   date as unconfirmed rather than fabricating one or blocking the
   interaction from existing. Explicit design choice, confirmed by
   MJSullivan: date is present-when-known, not a hard requirement —
   consistent with this project's standing practice of asserting
   uncertainty rather than omitting the fact.

**prefLabels updated on all 7 `Relationship` individuals** to include
the relationship type in the label text (e.g. "Nate Hagens'
professional relationship with Post Carbon Institute"), including the
one multi-valued case (University of Minnesota, both Academic and
Professional) reading naturally as "academic and professional" rather
than needing a workaround. Flagged for later, not now: a third type or
more multi-valued cases would make hand-written "X and Y" conjunctions
unwieldy — fine for the current single two-valued case.

**Real merge test against the live graph** (same "what insights, what
gaps" question asked in an earlier session, re-run for real this time
by actually merging the prototype and running live queries):

What worked:
- Role-reversal detection (the Monahan case) resolves correctly via a
  real query — only possible because of the subjectRole/objectRole
  split above.
- A full professional-footprint query for Nate (institutional ties,
  type, provenance, honest about unconfirmed dates) works cleanly in
  one query.

What's confirmed still broken/missing, not speculation:
1. **Real IRI collision on merge, demonstrated not hypothesized.**
   `relationships.ttl` (already adopted into the real graph earlier the
   same night) already has an individual at the same IRI the prototype
   reuses — built Human-to-Human. Merged naively, one individual ends
   up with two subjects (`Human.NateHagens` and `Persona.NateHagens`),
   two objects, two labels, four interaction blank nodes, all
   simultaneously true. Folding this in requires a real migration —
   removing the old Human-based triples, not just adding Persona-based
   ones alongside — same category of work as the `Person`→`Human`
   rename described further down this doc.
2. **Only Nate has a rich Persona.** McGilchrist's real credentials
   (Royal College Fellowship, Ralston College Chancellorship) are still
   sitting in prose, not modeled — his `hasProfessionalRelationship`
   count is confirmed zero. The pattern exists but has only been
   applied to one person so far.
3. **The graph's actual core mechanism is still untouched.** Every
   `Concept`→`influencedBy`/`echoesIdeaOf` link still points at
   `Human`, confirmed zero pointing at `Persona` — meaning the
   "sweeping implication" flagged in the MAJOR GENERALIZATION entry
   immediately below (that `Concept`↔thinker links, reaching
   `linknotes.ttl`/`crosswalknotes.ttl`, are where Persona should
   matter most, not just the episode layer) has NOT been executed.
   This whole session built and stress-tested the pattern without yet
   touching the thing it was ultimately meant to fix.

**Documentation debt surfaced, not yet fixed**: the prototype file's
own header comment (marked "v4") still describes the SUPERSEDED
"Persona is a proxy, hasSubject stays Human" model — stale relative to
the actual body of the file, which is fully rebuilt to the
Persona-owns-relationships model. Needs updating before this file is
trusted as a reference next session.

**Explicitly flagged by MJSullivan as needing to travel beyond this
doc**: the "Persona takes a back seat to Human... no, Persona IS the
load-bearing entity, Human takes a back seat" framing inverts what most
general-purpose ontology engineers (FOAF, schema.org, DOLCE background)
will instinctively expect — worth a clear, standalone explanation in
`CLAUDE.md` or the skill documentation itself, not just buried in this
handoff doc. NOT yet written — `CLAUDE.md` currently has no
Persona/Human architecture section at all (confirmed by search of the
uploaded copy).

**Not yet done, explicit next-session scope, in likely priority order:**
1. Real, non-destructive migration of `relationships.ttl`'s existing
   Human-based individuals to Persona-based (resolves the IRI collision
   above).
2. The actual core-mechanism migration: `Concept`→`influencedBy`/
   `echoesIdeaOf`/`contrastsWith` and `CrosswalkNote.aboutEntity`
   repointed from `Human` to `Persona` — the biggest, most consequential
   piece, not yet even fully scoped.
3. Build out a real (non-minimal) Persona for McGilchrist.
4. Write the Persona-over-Human architectural rationale into
   `CLAUDE.md`.
5. Fix the prototype file's stale header comment.

## MAJOR GENERALIZATION (2026-07-13, same thread): historical figures
## are PURER Persona cases than modern guests, and this reaches the
## graph's core mechanism, not just the episode layer

Two further insights from MJSullivan, both tested concretely, both
expanding this well beyond the original Show/Persona motivation:

**1. "Persona conferred by appearing, not chosen"** — `Episode.hasGuest`
currently points directly at `Human` in the real graph (no `rdfs:range`
is even declared, domain=`Work` only). But being a guest is exactly the
kind of public-facing fact this whole thread concluded belongs to
`Persona`. Tested and confirmed working: `hasHost`/`hasGuest` should
point at `Persona`, with even a MINIMAL persona (identical name, zero
distinguishing content, existing solely because the appearance
happened) being sufficient — demonstrated concretely with a hypothetical
guest example. Full real-graph migration scope, not yet executed: add
`rdfs:range thinkr:Persona` to both properties; create minimal `Persona`
individuals for all 4 existing guests (Nate already has a rich one);
repoint every `hasHost`/`hasGuest` triple across all 10 real `Episode`
individuals; decide whether `Relationship.hasObject` should shift from
`Human` to `Persona` too for consistency with `hasSubject`.

**2. Marcus Aurelius (and, by extension, most historical figures in this
graph) are PURER Persona cases than any modern guest** — not just another
example of the same pattern. For a modern guest, the Persona is thin
because the *appearance* was thin (could in principle research more of
the private Human). For Marcus Aurelius, the thinness is PERMANENT and
EPISTEMIC, not a research backlog — there is no separately-attested
private individual distinct from Emperor-and-Stoic-author Marcus; that
public role IS essentially the entire historical record. Tested
concretely: `Human.MarcusAurelius` deliberately near-empty,
`Persona.MarcusAurelius` carrying essentially all known content
(`hasTGSRole.Author`, the Stoic/Emperor identity), confirmed via live
query that a `Concept` correctly resolves to the Persona rather than the
near-empty Human.

**The sweeping implication, stated plainly rather than undersold**: every
one of the 14 existing `Concept`→`Human` connections in this graph
(`echoesIdeaOf`/`influencedBy`/`contrastsWith` — Catton, Jevons, the
Meadows, Ostrom, Bateson, Aristotle, Hubbert, E.O. Wilson, Freud, MLK,
Buddha, Epictetus, Marcus Aurelius, Kahneman) is fundamentally about that
person's PUBLIC INTELLECTUAL ROLE, never a private biographical fact.
Which means `thinkr:influencedBy`/`echoesIdeaOf`/`contrastsWith` should
ALSO point at `Persona`, not `Human` — the SAME migration as
`hasHost`/`hasGuest`, but reaching the actual core mechanism this whole
graph was built around (the reason `LinkNote`/`Evidence`/`compute_confidence.py`
exist at all), not just the episode layer. This is a substantially
bigger migration than anything scoped above — touches
`linknotes.ttl`/`crosswalknotes.ttl` (every `CrosswalkNote.aboutEntity`
too, by the same logic) in addition to `episodes.ttl`/`tgs-core.ttl`.
NOT executed, NOT even fully scoped yet — flagged as the real
next-session starting point, likely bigger than the `School` split or
the `Person`→`Human` rename once actually sized up.

## RESOLVED (2026-07-13): Persona/Human/Role design, fully settled

Picked back up and actually prototyped (3 revisions) the day after the
escalation above was written. Real, tested conclusions, not just
discussion this time:

**The `Human`/`Persona` split, confirmed correct via 3 concrete
corrections** (each caught a real error in the first prototype, not
hypothetical):
1. `thinkr:memberOf` (legal/formal weight — fiduciary duty, ability to
   sign or be sued) is EXCLUSIVELY a `Human`-level claim. A `Persona`
   gets the new, weaker `thinkr:affiliatedWith` instead — a public-image
   association, not formal membership. The same organization can appear
   under both properties on different individuals simultaneously; this
   is two different claims about one relationship, not duplication.
2. `Persona` NEVER gets structured name properties
   (`foaf:givenName`/`familyName`) — proven via Cher (legal name
   Cherilyn Sarkisian) and Sting (Gordon Sumner): a persona's public
   name isn't guaranteed to even decompose into given+family. `Persona`
   gets `skos:prefLabel` only.
3. `thinkr:actsThrough` links a `Persona` back to its `Human`(s) —
   naming/directionality borrowed from DOLCE+DnS Ultralite's real
   `actsThrough`/`actsFor` pair (the one piece of DOLCE flagged as
   worth keeping, from the full ontology examined 2026-07-12).

**THE settled principle, MJSullivan's own insight — "persona = role,"
then correctly bounded by a follow-up question that could have gone
either way:**
> A role changes what someone does; a persona changes who the public
> thinks they're dealing with. Only the second one needs a new
> individual.

Concretely: a NEW `Persona` is warranted ONLY when the public NAME/BRAND
itself genuinely differs (Cher-vs-legal-name level) — NOT for different
professional capacities under one already-consistent public name, which
are just multiple `thinkr:hasTGSRole` values on a SINGLE `Persona`
(already multi-valued, no new mechanism needed). Proven concretely, not
just asserted: a second "ISEOF director" `Persona` was built and tested
— it turned out to contain nothing but one more role tag and one more
affiliation, no genuinely distinct name/brand/audience. Collapsed back
into one `Persona` carrying all 4 `hasTGSRole` values
(`Educator`/`Blogger`/`Author`/`InstituteExecutive`) — nothing real was
lost, confirmed via query. Cardinality question explicitly settled via
the actor analogy: "an actor can have a role of leading man, comic,
singer, dancer" — one persona, many simultaneous roles, matching how
`hasTGSRole` already worked from the start.

**Cardinality summary**: `Human` → `Persona` is 1..n (one human may have
multiple genuinely distinct public identities). `Persona` →
`hasTGSRole`/`affiliatedWith` is also n-valued (one persona can hold
many roles/affiliations at once) — NOT 1, confirmed by the actor test
above.

Full working prototype (not yet in `data/seed/` — still explicitly a
sandbox artifact, learned from the `relationship_prototype.ttl` mistake
of accidentally living in the real graph for hours): `Human.NathanHagens`
(biographical, legal, earned credentials) + `Persona.NateHagens` (public
identity, all 4 roles, `affiliatedWith`, `hasPersonalRelationship`, media
homepages) + `thinkr:actsThrough` linking them. Tested via live SPARQL
query confirming zero `memberOf`/`givenName` leakage onto `Persona` and
all 4 role values correctly present after the collapse.

**Still genuinely open**: whether this whole pattern gets formally
adopted into the real graph (same "prototype first, decide later"
discipline as `Relationship`'s own journey), and the still-unmodeled
`Show`/`TGS-the-show`/ISEOF entities this was originally meant to
connect to (see the ESCALATION section above, not resolved by this
update).

## Execution caution (2026-07-12): the Person→Human rename risks

**EXECUTION CAUTION (2026-07-12, same discussion)**: MJSullivan proposed
a simple VS Code global find/replace as "trivial, low-risk" for the RDF
side. Checked directly rather than taking that at face value — it's
NOT actually low-risk unscoped, three concrete problems found in under
five minutes:
1. `foaf:Person` (the real external vocabulary link, live in
   `persons.ttl` line 98) would corrupt to `foaf:Human` — not a real
   FOAF term.
2. Common English words get mangled — confirmed real example:
   "Personal" (as in "Personal blogs" in `tgs-core.ttl`) → "Humanal,"
   not a real word. Any future prose using "person" generically has the
   same risk.
3. `PersonEntityType`/`hasPersonEntityType` — 19 occurrences across
   `episodes.ttl`, `persons.ttl`, `tgs-core.ttl` — a genuine, UNDECIDED
   design question hiding inside what looked like a mechanical rename:
   should these cascade to `HumanEntityType`/`hasHumanEntityType` too?
   A blind find/replace would silently decide "yes" without it ever
   being a deliberate choice.
Safe patterns, if/when this executes: `thinkr:Person ` and `tgs:Person.`
(WITH the trailing space/period specifically to exclude
`PersonEntityType` and `Personal`) — never bare `Person`. `foaf:Person`
needs an explicit exclusion regardless of how the search is scoped.
RECOMMENDATION: execute this the same way as every other large rename
this session (`ConfidenceLevel`→`ConfidenceType`, the `School` split) —
scripted with a baseline triple count and `compute_confidence.py`
before/after comparison, plus a full `grep -rn "Person\b"` sweep after,
not a manual VS Code find/replace however mechanical it looks going in.

## Naming resolved (2026-07-12): Person→Human, keeping Persona

**SUPERSEDED (2026-07-12), same session — better solution found**:
MJSullivan pushed back on compromising away from "Persona" (which he
explicitly likes) and proposed the inverse fix instead — rename
`thinkr:Person` to `thinkr:Human`, keeping `Persona` for the public-
identity concept. This solves the collision more completely than
`Identity`/`PublicIdentity` did (`Persona`/`Human` share zero characters,
vs. `Persona`/`Person` sharing six) AND is arguably more semantically
honest — every current `Person` individual (Nate Hagens, Iain
McGilchrist, Aristotle, Marcus Aurelius) genuinely IS a human being;
"Person" always carried a faint legal/philosophical connotation (as in
"corporate legal person") that was never actually what this graph meant.
No technical obstacle: `Human` would stay `rdfs:subClassOf foaf:Person`
exactly as now — the external vocabulary term doesn't need to match our
own local class name, same precedent as `Work` sitting atop
`dct:BibliographicResource` without being called that itself.
SCALE, why this is its own pass and not folded into the Show/Persona/
Identity prototype work: `Person` is almost certainly the single most
cross-referenced class in the entire graph — every `CrosswalkNote`,
`LinkNote`, `Evidence`'s implicit chain, `hasHost`/`hasGuest` on every
`Episode`, `dct:creator` on every `Work`, `memberOf` on every
`School`-descendant all touch `Person` individuals. Closer in scale to
the `School`→3-classes split than to a simple naming tweak. NOT
executed — captured here as the naming decision to actually run with
next session, superseding `Identity`/`PublicIdentity` above.
One open sub-question from MJSullivan's own example worth flagging:
his illustrative `tgs:Human.NathanHagens` used "Nathan" rather than the
current `tgs:Person.NateHagens` — unclear if that individual-renaming
was intentional (connecting to the `foaf:givenName "Nathan"` vs.
commonly-known-as-"Nate" distinction already resolved earlier) or just
illustrative shorthand. Confirm before executing, don't assume either
way.

## Strong validation (2026-07-12): real DOLCE+DnS Ultralite ontology examined directly

**STRONG VALIDATION (2026-07-12): real DOLCE+DnS Ultralite ontology
examined directly** (MJSullivan downloaded and reformatted it into
Turtle, ~2980 lines, a genuine established foundational ontology from
LOA-CNR, not a toy example). Two findings worth treating as load-bearing:

1. **DOLCE's own creators made almost exactly the naming mistake being
   avoided here, and had to fix it.** `SocialPerson`'s own
   `owl:versionInfo`: *"Formerly: Person (changed to avoid confusion
   with commonsense intuition)."* They originally named the
   social-identity concept `Person` — same word as the general concept —
   and renamed it after real confusion resulted. This isn't abstract
   caution, it's a documented historical correction from established
   practice. Treat the `Identity`/`PublicIdentity` naming question as
   effectively settled by this — reusing `Person`-adjacent naming for
   the persona concept has a real, precedented failure mode, not just a
   hypothetical one.
2. **DOLCE's `Role` independently confirms the `InteractionRole`
   collision-avoidance was correct**: DOLCE's `Role` is
   `rdfs:subClassOf :Concept`, defined as "a Concept that classifies an
   Object" — a CLASSIFIER, not an entity type. Much closer to how
   `PersonEntityType`/`ProfessionalRole`/`InteractionRole` already work
   in this graph than to what a `Persona`-replacement class needs to be.
   Independent confirmation from an unrelated ontology that ruling out
   `Role` for the new class was the right call.

PRACTICAL WARNING, worth remembering beyond just this decision: DOLCE's
core distinctions (`Agent`, `Person`, `SocialObject`) all rely on
`owl:equivalentClass`+`owl:unionOf` — elegant on paper, but that
construct is INERT without a reasoner actually running inference, and
this project's toolchain never does (same caveat repeated for every
`subClassOf`/`subPropertyOf` relationship built tonight). Adopting
DOLCE's actual patterns wholesale would mean decorative triples doing
nothing, the same trap `owl:sameAs` turned out to be. DOLCE's `Person`/
`SocialAgent`/`Agent` architecture is confirmed too complex to adopt
directly — one loosely-useful idea worth keeping as inspiration only:
`actsThrough`/`actsFor` (a cardinality-constrained, directional pair
linking a social identity back to whichever physical person(s) are
behind it, general enough to support delegation chains) is a clean shape
for the eventual `Person`↔`Identity` link, without needing DOLCE's
surrounding `Situation`/`Description`/`Concept` apparatus it's actually
embedded in.

## Naming reconsideration (2026-07-12): "Persona" too close to "Person"

**NAMING RECONSIDERATION (2026-07-12, same discussion)**: MJSullivan
flagged "Persona" as visually too close to "Person" for his stated
flattened/editorial VS Code workflow — a real concern given how many
naming decisions tonight were driven by exactly this preference.
Gemini research (see below) surfaced real, established alternatives from
actual ontology engineering: RiC-O (International Council on Archives)
explicitly separates Person from Persona; DOLCE uses SocialAgent/
SocialRole; a dedicated "PersonasOnto" model exists. ONE claim spot-
checked and confirmed real: `foaf:Person rdfs:subClassOf foaf:Agent` in
the actual FOAF spec (`foaf:Organization` too) — the "shared superclass"
pattern is structurally genuine, though Gemini's specific claim that
`foaf:Agent` itself encodes the pseudonym/persona distinction was
overstated (`foaf:Agent` is just FOAF's broad person-or-org-or-bot
category, not specifically about public vs. private identity). RiC-O/
DOLCE/PersonasOnto specifics NOT independently verified — diminishing
returns for a capture-and-defer task, and the core insight doesn't
depend on those citations being exactly right.
CANDIDATE NAMES, none decided: `Identity` (clean, no collision, no
jargon) or `PublicIdentity` (more verbose, leaves zero ambiguity).
EXPLICITLY REJECTED: `Role`/`SocialRole` — collides with the
already-existing `thinkr:InteractionRole` (`Host`/`Guest` in the
prototype), same word for a genuinely different concept, exactly the
kind of collision this project has caught and avoided elsewhere
(`School`→`SchoolOfThought`, the `Subject` overloading discussion).

## ESCALATION (2026-07-12): `thinkr:Show` and `thinkr:Persona` — a new
## architectural direction, NOT prototyped yet, next session's starting point

Raised by MJSullivan immediately after the `foaf:homepage` addition
above — and directly exposed a real category error in that same addition,
worth understanding precisely rather than glossing over.

**The triggering mistake**: `foaf:homepage` was added directly to
`Person.NateHagens` for `natehagens.com`, `natehagens.substack.com`, and
his LinkedIn — but these aren't actually uniform. `natehagens.substack.com`
is explicitly branded **"The Great Simplification | Nate Hagens"** on the
page itself — that's a link belonging to his public, professional
identity as TGS's host, not to him as a private individual. LinkedIn reads
more genuinely personal. `natehagens.com` is genuinely ambiguous either
way. The property was correct in shape (`foaf:homepage`, multi-valued)
but wrong in WHOSE homepage it was attaching them to.

**The proposed fix — `thinkr:Persona`, distinct from `thinkr:Person`**:
motivated by a second, sharper example — Heather Cox Richardson (the
planned second thinker for this whole reusable-methodology project) uses
her newsletter, YouTube, AND Facebook together as "the face of her
brand." Her Facebook page isn't about her as a private individual, it's
about her PERSONA as a historian/public commentator. A `Person` may have
one or more `Persona`s (most people modeled here would have exactly one,
but the distinction matters even at cardinality one — a pen name or
stage name would be the clean, obvious case for more than one).
Candidate shape: `thinkr:Persona rdfs:subClassOf thinkr:NamedEntity`,
`thinkr:isPersonaOf` linking a `Persona` back to its `Person`, with
`foaf:homepage`-style properties moving OFF `Person` and ONTO `Persona`
for anything that's actually brand/public-role-level rather than
genuinely personal.

**The proposed `thinkr:Show` concept, connected but distinct**:
platform-agnostic on purpose — HCR's "show" isn't one platform, it's
newsletter+YouTube+Facebook together functioning as one brand. TGS's
show spans its own website, YouTube, and Substack the same way. A `Show`
would aggregate `Episode`s (likely via the same `dct:isPartOf`/
`dct:hasPart` pattern already proven on `Series`), and a `Persona` would
be "the face of" one or more `Show`s.

**Genuinely open, NOT decided — this is why it's next-session work, not
a quick addition**:
1. Is `Show` structurally more like `Series` (`Work` + `dcmitype:Collection`
   — a content aggregation) or more like `Organization` (has a team, a
   revenue model, ongoing business existence) — or does it need BOTH
   superclasses, same as `Series` itself needed both `Work` and
   `Collection`? Unresolved.
2. How does `Show` relate to the ALREADY-BUILT `Series`? A `Show` is
   ongoing/indefinite; a `Series` is bounded/finishable ("How to Think
   About the Future," 3 parts, done). Likely BOTH aggregate `Episode`s
   simultaneously (one `Monologue` could be `dct:isPartOf` both its
   `Series` AND the overarching `Show` at once, multi-valued, no
   conflict) — but not yet tested against real data.
3. Which SPECIFIC existing `foaf:homepage` links move from `Person` to
   `Persona`? Substack clearly moves (explicitly branded). LinkedIn
   probably stays on `Person`. `natehagens.com` is genuinely ambiguous —
   needs a real decision, not a default.
4. Does `thegreatsimplification.com` and its YouTube channel belong to
   `Show` directly, or to the `Persona` as "host of the show," or both
   via different properties? Not yet worked through.
5. ISEOF (Nate's employer, confirmed real — "Executive Director of The
   Institute for the Study of Energy & Our Future" — but still not
   modeled as any individual at all) is a DIFFERENT, separate gap that
   surfaced during this same discussion — worth deciding whether it's an
   `Organization` (most likely fit) at the same time as this work, not a
   reason to conflate it with `Show`/`Persona`.

NOT prototyped tonight per MJSullivan's own call, given the hour — this
is the concrete next-session starting point, with the real triggering
example (the `foaf:homepage` mistake) already caught and preserved above
so it doesn't need rediscovering.

## RESOLVED (2026-07-12): name/birthdate vocabulary for `thinkr:Person`

Reopens the deferred firstName/family_name backlog item from earlier —
vocabulary now decided, though the actual name-splitting judgment calls
(Marcus Aurelius's praenomen, Catton's "Jr.", Aristotle having no
surname) remain exactly as unresolved as before. This only settles WHICH
vocabulary, not WHEN to apply it to any given individual.

- **Names**: `foaf:givenName`/`foaf:familyName` — `Person` already
  `rdfs:subClassOf foaf:Person`, so this extends an already-adopted
  vocabulary rather than introducing a new one.
- **Birthdate**: `dbo:birthDate` (DBpedia Ontology), NOT `foaf:birthday`
  (that FOAF term is specifically scoped to a RECURRING birthday —
  month/day only, no year — wrong shape for an actual date of birth) and
  NOT `schema:birthDate` (schema.org has zero prior usage in this graph,
  whereas DBpedia is already a first-class citizen — every
  `CrosswalkNote` targets `dbpedia.org` URIs).
- **Precision varies by what's actually known — same pattern already
  proven on `Work.RealityBlind`'s `dct:issued "2021"^^xsd:gYear`**:
  `dbo:birthDate "1969"^^xsd:gYear` when only the year is public (the
  common case — confirmed real-world instance: Nate Hagens' own birth
  year is publicly known, but no month/day is), `"1969-03-15"^^xsd:date`
  when the full date is genuinely known. Deliberately NOT range-
  restricting `dbo:birthDate` to one datatype — either choice would make
  the other, equally valid case a documented violation.
- **Real ambiguity surfaced and deliberately left unresolved, not
  papered over**: Nate Hagens is commonly known as "Nate" (matches
  `skos:prefLabel`) but his fuller given name is "Nathan" (confirmed via
  his own X handle, @NJHagens = Nathan John Hagens). Prototype uses
  "Nathan" for `foaf:givenName` with a `scopeNote` flagging the
  distinction explicitly, rather than silently picking one form.

Prototyped in `relationship_prototype.ttl` (shared with MJSullivan,
2026-07-12) — parses correctly, `dbo:birthDate`'s `xsd:gYear` datatype
confirmed preserved via live query. **UPDATE, same day**: discovered to
have been sitting in `data/seed/` the entire time (not actually external
to the graph as intended), and formally adopted rather than removed —
schema redistributed into `tgs-core.ttl`, `Relationship`'s own instances
promoted to a new `relationships.ttl` (same one-class-one-file rule as
`Work`/`Source`/`Episode`), Nate's merged data folded into his single
real declaration in `persons.ttl` (previously duplicated across two
files). All 4 originally-tested queries re-confirmed identical after the
merge. `relationship_prototype.ttl` no longer exists as a separate file.

## `thinkr:School` overloading (2026-07-11) — real, not hypothetical

MJSullivan flagged `School` as heavily overloaded — candidates
`SchoolOfThought`/`Philosophy` for the intellectual-movement sense.
Checking the actual data confirms this isn't a hypothetical concern: all
12 current `School` individuals genuinely split into two different KINDS
of thing that happen to share one class:

**Intellectual movements/frameworks** (no legal existence, no staff,
just an idea or a loose community): `Stoicism`, `DoughnutEconomics`
(the FRAMEWORK — the actual org applying it, CalDEC, is already
correctly separate), `PeakOilMovement` (explicitly defined as
"loosely-organized," not a legal entity), `BehavioralEconomics`,
`DegrowthMovement`, `SystemsEcology`, `CivilRightsMovement`. 7 total.

**Real organizations** (legal entities, actual staff/roles, the kind of
thing someone is literally employed by or a board member of):
`TheOilDrum` (Nate was literally "Managing Editor"), `PostCarbonInstitute`
(real 501(c)(3), Nate's a board member), `MaEarth`, `BiomeTrust`,
`ConsilienceProject` (all "non-profit... founded YYYY" — organizational
by their own definitions). 5 total.

**Further split proposed, also concrete, not hypothetical**: MJSullivan's
own example — "an Organization might decide to sponsor Nate whereas an
Academic Institution would never" — a real, telling test: the two
categories support genuinely different, non-overlapping relationship
verbs (sponsorship makes sense for `PostCarbonInstitute`, would be
strange for a university; conferring a degree or granting tenure makes
sense for a university, not for `PostCarbonInstitute`). That's a strong
signal for a genuine third category, not just two:

**Academic institutions** — NOT currently modeled as individuals AT ALL,
only ever mentioned in prose inside `Person.NateHagens`'s own
`rdfs:comment` (University of Vermont — PhD; University of Chicago —
Master's; University of Minnesota — teaching, see the earlier tense-
conflict note). If this split happens, these become real individuals for
the first time, not just a rename of existing ones.

**NOT decided**: exact class names (`SchoolOfThought` vs `Philosophy`
still open), whether all three are siblings or share a superclass (same
pattern as `Person subClassOf foaf:Person, thinkr:NamedEntity` would be
the obvious template if so), and whether this executes as part of the
same rework as the sidecar cleanup above or as its own separate pass —
these touch genuinely different parts of the graph (classes/instances,
not sidecar naming) so may not need to be bundled together at all.

## Editorial sketch (2026-07-11) and what it surfaced

MJSullivan sketched a full illustrative example (VS Code-editor-friendly,
flattened, nested-blank-node style — `Person` with `hasPersonalRelationship`/
`hasOrganizationRelationship`/`hasSubjectRelationship` arrays, each pointing
at a named `Relationship` individual carrying typed blank-node metadata
underneath). Specific sub-relationship names in that sketch (professional,
parental, marriage, employment, consulting, author, publisher, educational,
legal, etc.) were explicitly fictional PLACEHOLDERS, not a proposal — the
value was in seeing the shape, not the specific vocabulary.

Two real things came out of it anyway, worth keeping even though nothing
here is decided:

1. **Blank nodes ARE fine for this layer, just not the one I'd tested.**
   My earlier blank-node rejection tested cross-FILE reference (a
   `LinkNote` in one file pointing at an `Evidence` in another) — that
   genuinely can't work. But blank nodes nested INSIDE an already-named,
   stable parent individual, never needing external reference, is a
   different and legitimate use — and it sidesteps the multi-instance
   naming problem (no name needed for `[ metadata1 ]` at all). Worth
   remembering both halves of this, not just "blank nodes don't work
   here."

2. **"Legal relationship" is a genuinely distinct axis, not just another
   item in a flat list of relationship types.** It describes WHAT FORMAL/
   BINDING STRUCTURE governs a relationship (a contract, IP terms, board
   fiduciary duty), which can sit ORTHOGONALLY underneath any of the
   other relationship types (educational + legal, employment + legal,
   etc.) rather than competing with them as a sibling category. Not
   decided how to model this yet — captured here so the insight isn't
   lost before the real design pass happens.

Naming collision caught during discussion: the sketch's
`SubjectRelationship` (with author/publisher sub-types, describing a
relationship to a PUBLICATION) would collide conceptually with the
already-existing `thinkr:Subject` (the topic taxonomy — Energy Systems,
Human Behavior, etc.) — different meanings, same word. If this pattern
gets built, `WorkRelationship` avoids the collision (`thinkr:Work` already
exists for the publication concept).

## CAVEAT (2026-07-11, MJSullivan's own words, not softened)

**"MJSullivan is not 'seeing' how real data should look while leveraging
the pattern developed. We need a concrete set of inter-related examples
for me to finally 'get it'. At the moment, I don't."**

This matters more than anything else in this document. Everything below —
the confirmed conventions, the worked examples, the open questions — was
produced through abstract discussion, one isolated example at a time
(a single renamed `Evidence`, a single renamed `LinkNote`, a single
renamed `CrosswalkNote`, discussed separately). That is NOT the same
thing as a genuinely graspable, intuitive picture of how the whole
pattern works TOGETHER, and MJSullivan has explicitly said the current
material doesn't get him there.

**What's actually needed, as a real next step, not yet built:** a single,
coherent, NARRATIVE worked example — not isolated before/afters — that
shows multiple sidecars operating together around one connected scenario.
Concretely, this likely means actually confronting the still-unresolved
multi-instance problem (see ESCALATION section below) with a real
worked case rather than discussing it in the abstract: e.g., walk through
what it ACTUALLY looks like, in full, if a second Aristotle-on-money
citation is added (does it collide with `Evidence.Aristotle_Money`? what
does the resolved individual look like start to finish, with every
property populated with real values, not placeholders?), and/or what it
ACTUALLY looks like if Nate's UMN affiliation turns out to be two
separate periods (both `AffiliationNote` individuals shown in full,
side by side, with real dates once known).

Until that exists, do NOT treat this document as ready to execute
against — it captures real decisions and real open questions, but it has
not yet achieved its actual purpose of making the pattern intuitively
clear.

## ESCALATION (2026-07-11, same day): the multi-instance problem

Raised by MJSullivan after the initial cleanup conventions above were
already confirmed — genuinely bigger than a naming detail, worth its own
section rather than burying it in Open Questions.

**The problem**: `Subject_Object` naming (confirmed convention #1/#2
above) implicitly assumes AT MOST ONE relationship-instance per entity
pair. Real examples where that's false:
- Aristotle may have written/lectured about money in MULTIPLE places
  (Politics Book I is only the one currently cited) — a second instance
  has nowhere to go under `Evidence.Aristotle_Money` without colliding.
- Nate's UMN affiliation may not be one continuous period — "on and off,
  different dates, even different roles" (guest lecturer vs. some other
  capacity at different times) — same collision problem for
  `Affiliation.NateHagens_UniversityOfMinnesota`.

**What's NOT broken**: the underlying sidecar architecture. Each
`Evidence`/`LinkNote`/`AffiliationNote` is its own uniquely-IRI'd
resource — RDF can't duplicate a bare triple, but nothing stops multiple
distinct sidecar individuals from all pointing at the same entity pair
via `aboutSubject`/`aboutPerson`/`aboutSchool` etc., each carrying its
own distinct dates/source/role. This is purely a NAMING problem, not a
structural one.

**Candidate directions, NONE decided — explicitly not resolved as of this
writing, MJSullivan's own words: "we don't yet have a comprehensive
solution at the moment":**
1. Ordinal suffix (`Aristotle_Money_1`, `_2`) — simple, loses mnemonic
   value, awkward if a chronologically-earlier instance is discovered
   after a later one was already numbered 1.
2. Meaningful disambiguator specific to the sidecar type — a citable
   `Work` for Evidence-type sidecars (`Aristotle_Money_PoliticsBookI`),
   a role+date range for Affiliation-type sidecars
   (`NateHagens_UMN_GuestLecturer_2015`) — more self-documenting, but
   "what goes in the disambiguator" isn't a single universal rule across
   sidecar types, would need its own decision per type.
3. Stop expecting the name to carry full uniqueness at all — let the
   IRI be "good enough to recognize," put the actual disambiguating
   facts entirely in the properties (dates, sources, roles), not the
   name.

**Recommended next step, not a decision**: don't resolve this in the
abstract. Wait for a REAL case that actually needs it (a second
Aristotle-on-money citation, or confirmation of Nate's actual UMN
date/role history) and design against that concrete example — same
"let's see what the data tells us" principle already used for the
OWL/SKOS split and the Subject taxonomy sub-topics.

## OPEN QUESTIONS — must be resolved before any execution

1. **Does `hasSubject`/`hasObject`/`hasRelationshipType` replace
   `LinkNote`'s existing `aboutSubject`/`aboutObject`, or does it
   describe a NEW/merged concept combining what `LinkNote` and
   `Evidence` currently do separately?** The worked example in the
   original request named the individual `Evidence.Aristotle_Money`
   but gave it `LinkNote`-shaped properties plus a `hasEvidence`
   pointing elsewhere — genuinely ambiguous which reading is intended.

2. **Does `hasRelationshipType` (with values like `WroteAboutThisTopic`)
   replace the current multiple-specific-properties design
   (`echoesIdeaOf`/`influencedBy`/`contrastsWith`/`convergesWith`) with
   one generic relation property plus an explicit type value?** This is
   a substantially bigger architectural change than a naming cleanup —
   it would touch the confidence-aggregation logic
   (`compute_confidence.py`), which currently doesn't care which
   specific property was used, but a redesign here is worth doing
   deliberately, not as a side effect of a rename.

3. **What is `thinkr:LinkNote` actually renamed to?** `thinkr:Link` is
   used as a placeholder above, not confirmed. Candidates worth
   considering: `Link`, `Relation`, `Connection`.

4. **What is `thinkr:CrosswalkNote` (and its `crosswalkSource`/
   `CrosswalkSource` properties/class) actually renamed to?**
   `IdentityLink` is a placeholder, not confirmed. Candidates worth
   considering: `IdentityLink`, `ExternalReference`, `SameAsNote`
   (keeps "Note" just for this one, if that's acceptable), or simply
   `ExternalLink`.

4b. **RESOLVED 2026-07-11, fold into the same rework: drop the direct
   `owl:sameAs` triple entirely, rely solely on `aboutExternalURI`.**
   `owl:sameAs` formally implies full bidirectional property inheritance
   under OWL reasoning (a well-documented, legitimate community concern —
   the "sameAs problem," widely misused across the Linked Open Data
   cloud for exactly this reason) — not something we actually mean when
   linking e.g. `tgs:Person.Aristotle` to a DBpedia URI. This doesn't
   currently cause a practical problem (nothing in this project's
   toolchain ever runs a reasoner — same caveat repeated for every
   subClassOf/subPropertyOf relationship built tonight), but "doesn't
   currently bite us" isn't sufficient justification to keep asserting
   something semantically wrong. `skos:exactMatch` was considered as a
   replacement but rejected — formally scoped to skos:Concept-to-
   skos:Concept alignment, imprecise for Person/School/Work the same way
   reusing EvidencePolarity for PersonEntityType would have been.
   `thinkr:aboutExternalURI` already does this job correctly — it's a
   self-defined property with self-defined (non-identity) semantics, so
   there's no OWL-identity baggage to strip out. Net effect: the direct
   `owl:sameAs` triple currently sitting alongside every `CrosswalkNote`
   goes away; `aboutExternalURI` (inside the sidecar) becomes the sole
   way to express the external mapping. Affects all 37 existing
   `CrosswalkNote` individuals — fold into the same scripted rework as
   the rest of this document, not a separate pass.

5. **What is `thinkr:AffiliationNote` (proposed same session, not yet
   built) renamed to, given the "drop Note" rule applies to it too?**
   `Affiliation` is the obvious candidate but not yet confirmed.

## Worked examples (illustrating confirmed conventions only)

**Evidence**, using a real existing individual:
```turtle
# OLD:
tgs:Evidence.MoneyAristotle a thinkr:Evidence, owl:NamedIndividual ;
    thinkr:confidence thinkr:ConfidenceType.Curated ;
    thinkr:evidencePolarity thinkr:PolarityType.Supports ;
    dcterms:description "Aristotle's distinction in Politics Book I between oikonomia..."@en .

# NEW (naming only — entity order + underscore):
tgs:Evidence.Aristotle_Money a thinkr:Evidence, owl:NamedIndividual ;
    thinkr:confidence thinkr:ConfidenceType.Curated ;
    thinkr:evidencePolarity thinkr:PolarityType.Supports ;
    dcterms:description "Aristotle's distinction in Politics Book I between oikonomia..."@en .
```

**LinkNote** (class rename pending exact name — using placeholder
`thinkr:Link` below), real existing individual:
```turtle
# OLD:
tgs:LinkNote.OvershootCatton a thinkr:LinkNote, owl:NamedIndividual ;
    thinkr:aboutSubject tgs:Concept.Overshoot ;
    thinkr:aboutObject tgs:Person.WilliamCatton ;
    thinkr:hasEvidence tgs:Evidence.OvershootCatton ;
    thinkr:calculatedConfidence thinkr:ConfidenceType.Curated .

# NEW (naming only — entity order + underscore + dropped "Note"):
tgs:Link.Catton_Overshoot a thinkr:Link, owl:NamedIndividual ;
    thinkr:aboutSubject tgs:Person.WilliamCatton ;
    thinkr:aboutObject tgs:Concept.Overshoot ;
    thinkr:hasEvidence tgs:Evidence.Catton_Overshoot ;
    thinkr:calculatedConfidence thinkr:ConfidenceType.Curated .
```

**CrosswalkNote** (class rename pending exact name — using placeholder
`thinkr:IdentityLink` below, NOT confirmed), real existing individual:
```turtle
# OLD:
tgs:CrosswalkNote.AristotleDBpedia a thinkr:CrosswalkNote, owl:NamedIndividual ;
    thinkr:aboutEntity tgs:Person.Aristotle ;
    thinkr:aboutExternalURI <http://dbpedia.org/resource/Aristotle> ;
    thinkr:crosswalkSource thinkr:CrosswalkSource.DBpedia ;
    thinkr:verifiedOn "2026-07-11"^^xsd:date ;
    skos:scopeNote "Verified via direct web search confirming subject match before linking."@en .

# NEW (naming only — person-first already true here, dropped "Note",
# dropped "Crosswalk" — property names thinkr:crosswalkSource /
# thinkr:CrosswalkSource would ALSO need renaming for consistency,
# not shown here since the replacement term isn't decided yet):
tgs:IdentityLink.Aristotle_DBpedia a thinkr:IdentityLink, owl:NamedIndividual ;
    thinkr:aboutEntity tgs:Person.Aristotle ;
    thinkr:aboutExternalURI <http://dbpedia.org/resource/Aristotle> ;
    ...
```

## CONFIRMED conventions (not open questions)

1. **Underscore between the two cross-referenced entities.**
   `Evidence.MoneyAristotle` → `Evidence.Aristotle_Money`. This is
   specifically about separating the TWO ENTITY REFERENCES, not a
   general word-separator rule within a single title (that's a
   different, already-settled convention — see Episode naming).

2. **Person/Org comes first in the entity order.**
   `Aristotle_Money`, not `Money_Aristotle`. Applies uniformly across
   all sidecar families for consistency.

3. **Drop the "Note" suffix** from class names and instance prefixes.
   `thinkr:LinkNote` → `thinkr:Link` (exact replacement name not yet
   finalized — see Open Questions). Same for the not-yet-built
   `AffiliationNote` → `Affiliation`.

4. **Stop using "Crosswalk" terminology** for the DBpedia/Wikidata
   identity-mapping sidecar. Reserve "Crosswalk" for a future, more
   formal cross-ontology alignment concept if one is ever actually
   needed. Replacement name NOT yet decided — see Open Questions.

## Why this matters

The sidecar pattern (`LinkNote`, `Evidence`, `CrosswalkNote`, and the
just-designed `AffiliationNote`) has grown organically across tonight's
session, each one modeled after the last without a unified naming pass.
Current state has real inconsistencies:
- Entity order within a name is inconsistent (`MoneyAristotle`,
  `OvershootCatton` — concept-first; no stated rule)
- No separator between the two referenced entities (`MoneyAristotle`
  reads ambiguously — is it "Money" + "Aristotle," or some single
  concept "MoneyAristotle"?)
- "Note" suffix on every sidecar class adds length without adding
  meaning once the pattern itself is well understood
- "Crosswalk" was named early, before its actual scope was clear —
  MJSullivan wants to reserve that term for if/when a genuine
  crosswalk concept (in the formal cross-*ontology* alignment sense) is
  actually needed, not use it up on what's really just identity-mapping
  provenance

## Scope (exact counts as of 2026-07-11)

- 15 `LinkNote` individuals (`data/seed/linknotes.ttl`)
- 15 `Evidence` individuals (`data/seed/evidences.ttl`)
- 37 `CrosswalkNote` individuals (`data/seed/crosswalknotes.ttl`)
- **67 total** individuals needing rename, plus their 2-3 class/property
  declarations each in `tgs-core.ttl`

## Recommended execution approach, whenever this is picked up

Same discipline as every other large rename this session (the
`ConfidenceLevel`→`ConfidenceType` rename, the `dbpedia_links.ttl`/
`wikidata_links.ttl` → `crosswalknotes.ttl` consolidation): a scripted,
verified transformation, NOT manual find-and-replace. Establish baseline
triple count and `compute_confidence.py` output before touching anything,
verify identical results after, confirm zero stray references anywhere
in scripts/docs via `grep -rl` across the whole repo before declaring it
done.
