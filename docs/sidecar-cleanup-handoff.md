# Sidecar Cleanup — Handoff Doc

**Status: BACKLOG, NOT YET EXECUTED.** Reordered 2026-07-13 into
chronological order, LATEST FIRST, per MJSullivan's request at the
time. **PREFERENCE REVERSED 2026-08-13: MJSullivan now prefers TRUE
CHRONOLOGICAL order (oldest first)** — raised directly after a real
instance of confusion this session, where an old (2026-07-11),
since-abandoned design section was mistaken for a live open question
because it sat mid-document with no immediately obvious signal of its
age. Split the difference rather than risk a full manual reorder: the
existing ~25 sections stay exactly where they are (latest-first,
unchanged); a `## CONVENTION CHANGE` marker near the end of this
document marks the exact point where the ordering flips; everything
from that marker onward is true chronological order, appended at the
BOTTOM as it happens, starting from the 2026-08-13 session entry.
Physically reordering the pre-2026-08-13 material is tracked as
`[2026-08-13-8]`, not done in this pass. Section dates are preserved in each header.
Within a single date, sub-ordering is a best-effort reconstruction
from internal cross-references — flag anything that reads out of
order. **2026-07-14 update: session cut off before this doc was
refreshed live — the top section below was reconstructed after the
fact from the tail of that conversation, so treat its internal
ordering as reliable but its completeness as possibly missing earlier
moves from the same session that occurred before the point the
recovered transcript begins.**

## LOCAL ENVIRONMENT REFERENCE (living section, not dated/superseded —
## keep this current rather than appending a new dated copy each time
## something changes)

**Standing practice, established 2026-08-13, applies to every session
from here forward**: end every session with a dated write-up in this
doc's chronological log — what got accomplished/changed, real bugs
caught and fixed, and any lessons learned — the same way a batch isn't
considered done while `scratch.ttl` has content in it. Not optional,
not just for sessions where something went wrong.

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

## BACKLOG moved out to its own git-versioned file, 2026-08-13

**See `docs/backlog.md`** — moved out of this document specifically so
backlog items (real ideas not yet being worked on) have their own
visible git history, separate from this doc's session-by-session
narrative. Same append-only convention as this file; status changes
get noted inline there, never silently deleted.

## GAYA HERRINGTON REAL BOOTSTRAP + has*Relationship PROPERTY FAMILY
## (2026-07-15, new session): first real end-to-end guest bootstrap under
## the corrected Stage 2 design (not just an eval-harness metric), which
## surfaced a genuine modeling bug in hasPersonalRelationship — fixed by
## minting a full RelationshipType-mirroring property family, auditing it
## for symmetric completeness across the whole graph, and building a
## derivation script for it. Also resolved the long-open foaf:homepage
## Persona-vs-Human question and documented a formatting convention that
## had never been written down.

**Part 1 — Gaya Herrington bootstrap.** Real triples written (not a dry
run): `Human.GayaHerrington`/`Persona.GayaHerrington`,
`Organization.SchneiderElectric`/`StopStraatintimidatie`/`ClubOfRome`,
`AcademicInstitution.HarvardUniversity`, `Interview.TGS_57_...`,
`Work.UpdateToLimitsToGrowth2021`/`FiveInsightsForAvoidingGlobalCollapse`,
5 `Relationship` individuals, `LinkNote`/`Evidence.LimitsToGrowth_GayaHerrington`,
2 `CrosswalkNote`s (Wikidata + DBpedia). Real WebSearch/WebFetch used
throughout, not memory — confirmed her Wikipedia/Wikidata/DBpedia pages,
the exact 2021 JIE paper citation (DOI 10.1111/jiec.13084), and the TGS_57
episode's real air dates via the show's own page.

MJSullivan pushed for a deeper research pass beyond the podcast intro
("I'm 100% sure that if I spent five minutes I would find a handful of
other resources") — correct. A direct WebFetch of her own bio site
(gayaherrington.com/about) surfaced: Schneider Electric is now a PAST
role, not current (she's been an independent advisor since 2026) —
corrected everywhere it had been asserted as current; a Post Carbon
Institute board seat, which is especially notable because that
Organization already exists in this graph and Nate Hagens sits on the
same board — a real, verified cross-connection between two bootstrapped
guests, confirmed live via SPARQL; a current Adjunct Professor role at
Harvard (distinct from her Harvard degree, which stays prose-only); and
Club of Rome membership — thematically the sharpest find, since the Club
of Rome is literally the organization that commissioned the 1972 Limits
to Growth study she later empirically re-tested. Lower-confidence leads
(Cascadia/Bioregional Finance, R3.0 board, York University collaboration,
guest lecturing at Berkeley/Cambridge/UCLA/Shizenkan) were deliberately
left as prose only — not independently verified against a primary source,
flagged honestly rather than modeled as structured facts.

REAL, FLAGGED SCHEMA GAP: none of the 4 existing Concept-facing relation
properties (`echoesIdeaOf`, `influencedBy`, `appliesTo`, `relatesTo`)
cleanly fit "direct empirical re-test of a named study" — `relatesTo`
(the generic escape hatch) was used with a full scopeNote explaining why,
same posture as the deliberately-unfixed
`LinkNote.MartinLutherKingJr_GrowthImperative` reversed-subject/object
case. Worth a future backlog line: a dedicated "empirically
validates/updates" property if a second case like this surfaces.

METHODOLOGICAL FINDING worth keeping: the "stub Human, defer real
verification to Pass 2" convention (see the STAGE 2 SCOPE entries below)
effectively collapsed into a single pass here — real WebSearch/WebFetch
verification was already happening in the same session as the mint, so
there was no meaningful "later" to defer to. Pass 2 may naturally
collapse into Pass 1 whenever the person doing the bootstrap is already
verifying as they go, rather than being a strictly separate later step.

A privacy judgment call, flagged not silently made: a one-year-old
daughter mentioned in the TGS_57 transcript was excluded from
`Human.GayaHerrington`'s comment as privacy-sensitive and not central to
her public Persona — consistent with this project's publications/
credentials/public-role scope, not a hard rule.

**Part 2 — the has*Relationship property family retrofit.** MJSullivan
caught, correctly, that `Relationship.GayaHerrington_SchneiderElectric`
and `_StopStraatintimidatie` had been filed under
`thinkr:hasPersonalRelationship` even though neither is personal —
`thinkr:hasRelationshipType` on the Relationship itself already said
Professional. Root cause: `hasPersonalRelationship` had always been a
catch-all (see its pre-2026-07-15 comment: "only this one built so far"),
asserted regardless of a Relationship's actual type.

Fix, after some real back-and-forth: MJSullivan first proposed a
hasObject-CLASS-based rule (Persona->Persona = Personal,
Persona->Organization = Professional) — flagged as contradicted by real
data already in the graph (`Relationship.NateHagens_IainMcGilchrist` and
`_DanielSchmachtenberger` are Persona->Persona but Professional-only, and
`Relationship.NateHagens_GayaHerrington` — the exact case that started
this — is also Persona->Persona but Professional-only; applying the
proposed rule would have reverted the very fix being made). MJSullivan
then confirmed the right rule: "whatever relationshipType you land on
should be the has*Relationship property" — i.e. `hasRelationshipType`
(already evidence-based, already hand-verified against real transcript
quotes) stays the sole discriminator, and a Relationship with multiple
types (Monahan, Farley — both Personal+Professional, evidenced with
direct quotes) legitimately appears under multiple properties. Minted
3 new sibling properties in `tgs-core.ttl`: `hasProfessionalRelationship`,
`hasAcademicRelationship`, `hasLegalRelationship` (the last with zero
instances yet, built anyway since the full family was the explicit ask).

Separately, MJSullivan caught that `Relationship.NateHagens_PeakOilMovement`
(Persona->SchoolOfThought) was itself MISTAGGED Professional, not just
filed under the wrong property — "That's not professional... more of a
'I subscribe to this' relationship." Its own pre-existing scopeNote had
already half-admitted the mismatch ("not a formal joinable organization").
Minted a 5th type, `RelationshipType.Intellectual` (and
`hasIntellectualRelationship`), specifically for "subscribes to/aligns
with a school of thought's ideas" — distinct from Professional
(employment) and Academic (institutional/teaching ties). Only one
Relationship in the graph needed retyping.

MJSullivan also flagged a genuine misunderstanding worth naming for future
sessions: seeing the same Relationship IRI listed under two different
has*Relationship properties initially read as "duplication/bloat," until
tracing it back to the Relationship's own multi-valued
`hasRelationshipType` clarified it was correct, not a bug — worth
remembering that this specific shape (one Relationship, multiple sibling
properties) will keep looking surprising to a human editor scanning the
file unless the reason is visible nearby.

**Part 3 — symmetric-indexing audit.** While verifying the retype was
complete, a live SPARQL audit (both subject-side and object-side) found a
SEPARATE, real gap: `has*Relationship` had only ever been asserted on
whichever Persona happened to get bootstrapped/enriched, never
symmetrically on both parties. Concretely: Nate is `hasSubject` on
`Relationship.NateHagens_ArtBerman`/`_JoshFarley`/`_GayaHerrington` but
none were listed on `Persona.NateHagens` itself (only on the guest's own
Persona); `Persona.MatthewMonahan` had ZERO `has*Relationship` at all
despite being a party to 2 Relationships; `Persona.IainMcGilchrist`/
`DanielSchmachtenberger` were each missing their one entry. MJSullivan
chose symmetric indexing (both parties list a shared Relationship, when
both are Personas) over a single-canonical-side rule, given the
alternative would hide real facts unless a reader opened the Relationship
itself. Backfilled all 4 Personas; a full audit query afterward confirmed
zero subject-side gaps, zero object-side gaps, zero type/property
mismatches.

**Part 4 — `scripts/compute_relationships.py`.** MJSullivan asked for
pros/cons of deriving has*Relationship via script (mirroring
`compute_confidence.py`) rather than hand-maintaining it, given how many
times this session's own manual audits had already caught drift. Real
cost flagged before building: `compute_confidence.py` reserializes via
`rdflib.Graph.serialize()`, which strips every hand-authored section
comment (confirmed happening to `linknotes.ttl` earlier this same
session). MJSullivan's resolving framing: "I see the current state as
bootstrap phase not a hand-editing phase which can and will come later"
— i.e. that cost matters less right now than it would in a mature
curation phase, but should still be minimized where cheap.

Built with literal-safe targeted text surgery instead of a full rdflib
round-trip: every string literal in `personas.ttl` is placeholdered out
first (confirmed via grep that literals genuinely contain `;`/`.`/`,`,
making naive structural regex unsafe), then only `has*Relationship`
predicate-object chunks are located and rewritten; every comment and
`skos:scopeNote` survives untouched. Self-verifies by re-parsing the
written file and diffing against the intended state, hard-failing if they
don't match — added specifically because the script's OWN development
caught two real "reports success but silently does nothing/does the
wrong thing" bugs: (1) a key-mismatch (`Persona.IainMcGilchrist` vs.
`IainMcGilchrist`) that made every apply-mode block-rewrite a silent
no-op while still printing "Updated ... rewritten"; (2) a double-prefix
bug (`tgs:Relationship.Relationship.X`) caught immediately by the
self-verification step on the very next test run. Both were only caught
by actually inspecting the written output and re-parsing it — not by
trusting "the script ran without an error," the same lesson CLAUDE.md's
Gotchas section already documents for this exact class of mistake.
Tested via a disposable sandbox copy (never against the real repo until
proven correct): addition, removal, and idempotency (a second dry-run
after applying correctly reports zero remaining changes) all confirmed.
Run against the real repo: zero changes needed, confirming the manual
retrofit work above already matched what the script independently
derives.

**Part 5 — foaf:homepage: Persona, not Human, no split.** Closed the
open question flagged twice already (Persona.NateHagens's own
2026-07-14 scopeNote, and CLAUDE.md's design-decision-0f "still open"
list): a homepage is a public-facing fact, same category as every other
property already migrated under 0f (Relationships, Episode hosting,
Concept-influence), not biography — so all 3 links
(natehagens.com/Substack/LinkedIn) moved from `Human.NateHagens` to
`Persona.NateHagens`, no split. The LinkedIn case was the one worth
stress-testing (reads more CV-like than the other two) — resolved by
noting LinkedIn had ALREADY been used as Persona-shaped public evidence
elsewhere this session (Herrington's current affiliations, a citation for
a public claim about Nate's Reality Blind), not biography, so a uniform
rule beats a per-link judgment call. Both stale scopeNotes referencing
this as unresolved were updated to say it's resolved, not left dangling.

**Part 6 — multi-value-per-line formatting, newly documented.**
MJSullivan flagged, while reviewing the has*Relationship work directly in
the IDE, a real requirement that had never been written down: a property
with 2+ values needs one value per line (so a human editor can tell
"multi-valued" at a glance, from the text's shape alone); a property with
exactly 1 value stays on one line. This was ALREADY being followed by
hand throughout this session's edits (coincidentally), but
`compute_relationships.py`'s first version always emitted single-line
comma-joined values regardless of count — meaning the derivation script
would have silently regressed the very convention it was just asked to
respect, the next time it actually had a real change to write (it hadn't
yet, since the graph already matched by hand when first tested). Fixed
the script's line-generation logic and added a new CLAUDE.md ground rule
(2nd bullet, right after the confidence rule) with the worked example.
NOT applied retroactively: `episodes.ttl`'s `hasReplay`/`dct:subject`
lines (~15 occurrences) and `relationships.ttl`'s 2
`hasRelationshipType` lines are still single-line as of this writing —
MJSullivan's explicit call was to enforce going forward only, consistent
with the bootstrap-phase framing from Part 4; tracked as a LOW-priority
CLAUDE.md backlog item, not silently dropped.

**Triple count**: 2,023 (session start) -> 2,201 (data/seed/, after all 6
parts). Validated throughout via `make validate`,
`scripts/validate_class_purity.py --check-scratch-empty` (2 pre-existing
violations, both unrelated to this session's work), and repeated live
Oxigraph queries after every reload — never trusted a script's own
"success" message without independently re-querying, per the lesson Part
4 relearned the hard way.

**Explicitly not resolved, still genuinely open:**
- The `relatesTo`-as-escape-hatch schema gap for
  Herrington/LimitsToGrowth (Part 1) — no dedicated "empirically
  validates/updates" property exists yet, deliberately not invented for
  a single instance.
- Retroactive multi-value-per-line cleanup for `episodes.ttl`/
  `relationships.ttl` (Part 6) — tracked in CLAUDE.md's backlog, not
  scheduled.
- Whether `has*Relationship` should eventually be extended to
  Organization/SchoolOfThought-to-Organization Relationships (the
  MangaroaFarms<->BiomeTrust case has no Persona party at all, so it's
  out of scope for this property family entirely — not yet discussed
  whether that gap needs its own solution or is fine as-is).
- Whether the "Pass 2 collapses into Pass 1 when the bootstrapper is
  already verifying" finding (Part 1) should change how the stub-Human
  convention is described going forward, or stays situational.

## STAGE 2 SCOPE, PART 2 (2026-07-15, continuing the same conversation
## after a stated "may pick this up in a few hours" pause that never
## actually broke): stub-Human minting settled, a 10-segment taxonomy
## exercise surfaced 5 real new extraction categories plus a 4th
## Human/Persona case, concept-mining scoped (and prototyped outside the
## repo), and a real evaluation methodology replaced a proposed point
## system

**Picks up directly from the STAGE 2 SCHEMA DESIGN entry above — read
that one first.** That entry landed on "mint only Persona, park bio-leads
in a scopeNote, defer Human entirely to Pass 2." Everything below either
refines or extends that, in the order it actually came up.

### Stub-Human minting, refining (not reversing) the Persona-only call

MJSullivan's own example, sharpened further: `Persona.NateHagens`'s
public name is "Nate Hagens"; `Human.NathanHagens`'s actual given name,
"Nathan," came from an entirely different source than the show. Question
raised: does "defer Human entirely" actually work, given `actsThrough`
is the only thing that ever reaches `Human` — doesn't every new Persona
still need *something* to act through?

**Resolution**: mint a **stub `Human`** alongside every new `Persona`,
not a deferred one. The stub's `skos:prefLabel` is simply copied from the
Persona's public name — an explicit, calibrated bet: right roughly 90%
of the time, wrong the other 10% (Nate/Nathan, Cher-style splits), and
consciously accepted rather than blocked on. **What licenses accepting
that risk, stated plainly by MJSullivan**: "we are not building a
general-purpose social graph here... everyone mentioned in this Thinkr
ontology will be a Persona one way or the other — they are after all
true 'thinkers'." Every individual that actually matters to this graph
*is* a thinker, which means the Human record's entire job is satisfying
one structural link (`actsThrough`), not carrying research weight the
way it would in a genealogy or social-network project. That changes the
risk calculus enough that "best-guess stub, honestly flagged" beats
"block on verification."

**Practical fold-in**: the `human_lead` scopeNote from the prior entry
now has an obvious home — it becomes the stub Human's own
`rdfs:comment`/scopeNote, honestly marked as name-unverified-copied-
from-Persona plus whatever bio-shaped leads the transcript surfaced. No
separate holding field needed. **Not yet done**: `extraction/
eval_stage2_yaml.py` still only emits the `persona`/`human_lead` shape
from the prior entry — it has NOT been updated to actually emit a stub
`Human` block. Flagged, not forgotten.

### 10-segment taxonomy exercise: what else is actually in these things

MJSullivan's framing of the real difficulty: "How to determine what is
'good stuff' is the issue I am having." Randomly sampled 10 fresh intro
segments (seed 20260715, explicitly excluding every segment already
picked apart this session — Berman, Farley, Pinsky, Monahan) and read
all 10 in full, cataloguing what's actually extractable rather than
speculating: Peter Brannen, Alexa Firmenich, Nora Bateson, Vanessa
Andreotti, Pedro Prieto, Giorgos Kallis, Gaya Herrington, James Fleay,
Daniel Zetah, Doomberg.

**Five real, new candidate categories surfaced, none present in the
Berman/Farley/Pinsky set at all — pure luck of an 8-9-file prior sample,
confirming the value of actually sampling wider rather than assuming the
first pilot generalizes:**
1. **Named published works** (Brannen: 2 books; Andreotti: 1 book;
   Prieto: 1 co-authored book naming a real third-party co-author,
   Charlie Hall) — already schema-supported (`thinkr:Work` +
   `dct:creator`), just never triggered by the earlier sample.
2. **Past-vs-current affiliation status** (Brannen: "was previously a
   visiting scholar"; Herrington: KPMG then Schneider Electric) — nothing
   in the current schema distinguishes "was" from "is."
3. **Founder roles** (Firmenich: co-founded Ground Effect; Fleay:
   founder of DUNE) — reads differently than plain membership, no
   current property distinguishes it.
4. **Guest-stated relationship TO the host**, reverse of every signal
   captured so far (Fleay: "I'm a longtime listener and fan... been
   quite affected by your work" — the guest describing a relationship to
   Nate, not the usual host-to-guest direction).
5. **Third-party mentions with enough specificity to be a real lead vs.
   too thin to chase** — contrast Pinsky's earlier "Daniel Pauly, a
   friend of mine" (full name + explicit relationship + institutional
   context, worth chasing) against Zetah's "a Canadian fella named
   Lance" (first name only, incidental, correctly discarded).

**Real negative/calibration examples, equally valuable**: Kallis's
segment has zero relationship-signal language at all — confirms empty
output is a valid, expected result, not an extraction failure. Zetah has
zero institutional relationships — he's a farmer, correctly yields
nothing there. Bateson's segment is almost entirely substantive
philosophical discussion with thin structured yield despite ~1,000 words
— also expected, not a failure. Prieto's `discusses`-shaped content is a
one-off news event (an April 2026 Iberian blackout), a real case for NOT
forcing every topic into the durable `Concept` scheme. Andreotti's
segment independently produced a SECOND real instance of the host-
asserted explicit-concept-connection pattern ("at the core of your story
is the superorganism... our stories rhyme") — confirms the pattern
recurs across guests, not a Farley one-off.

### Human/Persona taxonomy: a real 4th case, resolved as a Pass-2 triage
### note rather than a Stage 2 field

Doomberg's segment ("an anonymous energy finance professional, part of a
team of analysts") broke the stub-Human assumption above outright — not
a hidden-but-real Human (the Cher case), but plausibly **no singular
Human to stub at all**. Checked against the schema directly: `thinkr:
actsThrough` carries no cardinality constraint anywhere in `tgs-core.ttl`
— nothing currently forces a Persona to have a Human. So this needs a
documented decision, not a schema change: **for a Doomberg-shaped case,
leave `actsThrough` deliberately unasserted**, with a scopeNote on the
Persona explaining why ("anonymous team, no individual(s) disclosed") —
same open-world-safe move already used for the Contributor/Mention
design elsewhere in this project (absence isn't a claim nothing exists,
just an honest "not disclosed," freely upgradable later).

MJSullivan proposed a 4th case on top of this: the well-known-celebrity
case (Al Gore was the example) — real, but resolved as a **triage note
on case 1, not a new structural case**. Al Gore is identical in shape to
an ordinary guest (Persona + stub Human, `actsThrough` asserted) — what
differs is only how much effort Pass 2 needs to verify him (trivial,
given how thoroughly documented he is), not the RDF shape itself.
Recommended keeping this out of Stage 2's extraction prompt entirely:
"is this person externally well-documented" is a fact about source
availability outside the transcript, which Stage 2 structurally can't
check without doing the same web lookup that IS Pass 2's job — let Pass
2 notice it's fast as a natural byproduct of actually doing the check,
rather than asking Stage 2 to predict fame level from ~1,000 words of
transcript.

**Settled 4-case taxonomy**:
1. Ordinary guest — Persona + stub Human, name copied, Pass 2 verifies (moderate effort)
2. Deliberately-obscured public figure (Cher) — Persona + Human, but Human stays thin even after real verification
3. Anonymous/pseudonymous collective (Doomberg) — Persona, `actsThrough` deliberately unasserted, flagged not guessed
4. Well-known celebrity (Al Gore) — same shape as case 1, just trivially fast for Pass 2 to verify; not a Stage 2 concern

### Concept-mining: scoped, and prototyped OUTSIDE the repo per MJSullivan's explicit request

Trigger: reviewing the Doomberg segment by hand, MJSullivan noticed how
many topic/keyphrase mentions it contains ("economy decisions," "energy
transactions," "geopolitical stage," etc.) and proposed ranking mentions
by frequency across episodes, with high-ranking ones minted and linked
to Wikipedia/Wikidata.

**Two real corrections before any building happened:**
1. **The extraction step needs different machinery than the existing
   person-bootstrap tooling.** `top_persons.py`/`index_named_entities.py`
   already do exactly the "rank by frequency, surface a worklist"
   pattern — but they run on spaCy NER, which is scoped to PERSON/ORG/
   GPE-style proper nouns and will NOT reliably catch abstract topic
   phrases like "global supply chain" (confirmed by direct inspection of
   what spaCy's model is actually built to tag, not assumed). Real
   automation here needs LLM-based keyphrase extraction, Stage-2-shaped,
   not a new mode of the existing NER tool. The ranking/worklist logic
   is reusable; the extraction logic is not.
2. **Most high-frequency terms are `Subject`-shaped, not `Concept`-
   shaped**, and frequency alone can't tell the two apart. Every
   individual in `Concept` today (19 total: EnergyBlindness,
   Superorganism, JevonsParadox, CarbonPulse, etc.) is a specific,
   named, definable theoretical framework. "Global supply chain,"
   "energy transactions," "international labor" are generic domain
   vocabulary that would appear in any macro-energy-economics
   conversation — much closer to the existing `thinkr:Subject` SKOS
   taxonomy (already 12 individuals: EnergySystems, Geopolitics,
   MonetarySystemAndGrowth, SystemsFrameworks, etc.) than to `Concept`.
   Minting "energy shortages" as a `Concept` alongside "the
   Superorganism" would dilute a class that's stayed genuinely curated
   so far — the same one-class-purity instinct that's been protecting
   file boundaries all session, one level up at the modeling level.

**Prototype built and validated, explicitly per MJSullivan's own
request to keep it OUT of the repo**: `concept_mining_prototype.ttl`,
written to the session scratchpad (NOT `nate-hagens-kg/`, not committed,
not loaded into Oxigraph), hand-extracted from the same 10 segments
above, sorted into four buckets — (A) matches an existing `Concept`,
a `discusses`-link candidate (8 hits — CarbonPulse/Brannen,
Superorganism+Metacrisis/Andreotti, EROI/Prieto, GrowthImperative/
Kallis, LimitsToGrowth/Herrington, EnergyBlindness+MoneyAsClaimOnEnergy/
Doomberg); (B) plausible new `Concept` candidate, deliberately kept to
ONE entry (Andreotti's "Modernity as a who" framework, later downgraded
— see below); (C) matches the existing `Subject` taxonomy, tagging
candidates only, not new individuals (5 entries — this bucket absorbed
most of what looked Concept-shaped at first glance, including the whole
original Doomberg list); (D) discarded, shown explicitly rather than
silently dropped, including two flagged as genuinely borderline calls
rather than clean cuts. Parses clean (24 triples). This confirmed the
Bucket A/C split empirically, not just as a stated hypothesis — the
Doomberg-derived list MJSullivan pulled out by hand landed almost
entirely in Bucket C once checked against the real Subject taxonomy.

### Concept-candidate evaluation: a proposed point system rejected in
### favor of reusing the existing Evidence/Confidence machinery — with a
### real worked example

MJSullivan asked directly how to evaluate a Bucket-B candidate (the
Andreotti "Modernity as a who" prototype entry) and proposed a points
system: Wikipedia page = 10, own webpage = 10, 1 point per episode
mention, etc.

**Rejected, with a specific citation, not just a preference**: additive
point scoring conflicts with a constraint this project already set for
itself in `CLAUDE.md`'s backlog — "stays ORDINAL, not numeric... a
weighted numeric decay formula would be a real regression." The concrete
failure mode: `compute_confidence.py` already encodes that a strong
Reputable-or-better rebuttal must *override* a pile of supporting
evidence ("forces Disputed, overriding Corroborated even if supporting
evidence also exists") — a point sum can't represent that asymmetry,
more points always wins under addition. **Recommendation, adopted**:
don't build a new scoring axis at all — treat "should this become a
Concept" as a claim needing Evidence, using the exact `LinkNote` →
`Evidence` → `calculatedConfidence` machinery that already exists.

**Then actually tested against the real candidate, not left as
architecture-only reasoning** — MJSullivan explicitly asked "is there
any other supporting websites or organizations" for the Andreotti
candidate, so real `WebSearch` calls were run rather than reasoned about
in the abstract. Findings: Andreotti herself is genuinely well-
documented (real Wikidata entry Q57450974, confirmed her actual
UBC-then-UVic career sequence — which incidentally corrected an earlier
flag from the per-segment review, where the transcript's own phrasing
had conflated UBC and UVic into one institution); "Hospicing Modernity"
the book is independently reviewed and cited (Goodreads, a blog review,
an e-flux journal conversation, a named UBC professor's endorsement) —
Curated-tier-worthy on both counts. But the specific proposed Concept,
"Modernity as a who," is NOT independently cited by anyone as a
reusable, named idea the way "Jevons Paradox" or "EROI" are — it reads
as a rhetorical device within the book, not (yet, externally) a
standalone concept.

**Concrete resulting recommendation, a real refinement of the candidate
itself, not just a confidence downgrade**: mint the underlying
`thinkr:Work` (the book — clean bibliographic path, real external
verification available) with the guest as `dct:creator`, rather than a
freestanding abstract `Concept` the evidence doesn't actually support.
Same content, lower-risk container. MJSullivan's own reaction, worth
recording verbatim since it's a real confirmation of the whole approach
(real verification over speculation, holding the project's own stated
principles even against MJSullivan's own suggested shortcut): "wow.
excellent summary. Much better than I could do in a day's worth of
work."

### Explicitly not resolved, still genuinely open

- `extraction/eval_stage2_yaml.py` has NOT been updated to emit the
  stub-Human block (target_class Human + name-copied-from-Persona +
  scopeNote), only the `persona`/`human_lead` shape from the prior
  entry.
- Whether "is this guest already in the graph" (new mint vs. addition
  to an existing Persona) belongs inside Stage 2's own output or stays a
  separate reconciliation step against `personas.ttl` — still leaning
  the latter, still not a final decision.
- Concept-mining automation itself (the LLM keyphrase-extraction step)
  is scoped and prototyped by hand on 10 segments, but no actual script
  exists yet — `concept_mining_prototype.ttl` was explicitly a by-hand,
  outside-the-repo exercise to let MJSullivan "see" the idea before any
  build commitment, not a first version of real tooling.
- How Pass 2 itself gets triggered/scoped (per-guest, batch, manual-only)
  — unchanged from the prior entry, still open.

## STAGE 2 SCHEMA DESIGN (2026-07-15, later the same day): guest_biography
## extraction schema corrected twice in one conversation — Persona not
## Human is the mint target, and the transcript itself can only ever
## source Persona-level facts

**Trigger**: reviewing `extraction/eval_stage2_yaml.py`'s YAML schema
against a real `Relationship` individual MJSullivan had open in the IDE
(`Relationship.JoshFarley_UniversityOfVermont`, `hasSubject:
Persona.JoshFarley`) surfaced that the schema's own `guest_biography`
shape — `target_class: thinkr:Human`, `property: thinkr:memberOf` — was
never actually correct. It mirrors the legacy flat-`memberOf`-on-Human
pattern, not the structured `Relationship`-with-`Persona`-subject pattern
this project has used for every real bootstrap since the 2026-07-14
Persona-centered refactor (design decision 0f, `CLAUDE.md`).

**Correction #1 — mint target is `Persona`, relationship shape is
`hasPersonalRelationship` → `Relationship` sidecar, not flat
`memberOf`.** Per decision 0f: `Human` is a pure leaf node reachable only
via `actsThrough`; every other relationship — including institutional
ones — runs through `Persona` via a `Relationship` individual
(`hasSubject`: the Persona; `hasObject`: the institution/org;
`hasRelationshipType`: Academic/Professional/etc.). Corrected schema
shape:

```yaml
persona:
  target_class: thinkr:Persona
  public_name: <name as publicly known>
  relationships:
    - property: thinkr:hasPersonalRelationship
      hasObject_name: <org/institution name>
      hasObject_type: thinkr:AcademicInstitution | thinkr:Organization
      hasRelationshipType: thinkr:RelationshipType.Academic | .Professional
      role_or_position: <title, if stated>
      department: <dept, only if AcademicInstitution and stated>
```

Kept `hasPersonalRelationship` as the property name despite it being a
known-imprecise name for non-personal relationships too (documented
elsewhere in this doc as a real, deliberately-deferred rename) — not
something to silently fix inside a schema-correctness pass.

**A concrete real-data check confirmed the correction's premise, not
just the naming**: `extraction/eval_stage2_yaml.py`'s own two test
files turned out to already span the two real downstream cases this
schema needs to handle — `Human.JoshFarley` / `Persona.JoshFarley` both
already exist (grep-confirmed in `humans.ttl`/`personas.ttl`); Malin
Pinsky has **zero** hits anywhere in the graph. So the schema has to
work for both "add a Relationship to an existing Persona" and "mint a
new Persona from scratch" — it wasn't accounting for either.

**Correction #2, deeper — the "mint a new Persona from scratch" case
does NOT mean minting a `Human` alongside it.** MJSullivan's own example,
already true in the live graph: `Persona.NateHagens`'s public name is
"Nate Hagens"; `Human.NathanHagens`'s given name "Nathan" came from an
entirely different source (his own X handle), never from anything TGS
itself said. **A podcast intro is structurally a Persona-generating
source, not a Human-verifying one** — it reliably tells you the guest's
public role, affiliations, and how they're publicly known; it does not
reliably tell you their actual legal name, birthdate, or other private
biographical facts, because the source was never positioned to state
those accurately regardless of how confidently it reads.

**The Human/Persona split itself is genuinely blurry, not just
under-sourced, and gets harder to execute for less famous guests, not
easier.** For a maximally public figure (MJSullivan's example: Cher),
the split is clean because it's total — the entire public surface,
*including anything that looks like a personal website*, is still
Persona content; the Human is deliberately almost fully hidden except
scraps on something like a Wikipedia page. For a university-faculty-page
guest — most actual TGS guests — the same document is simultaneously
Persona content (their public professional role) and genuine Human
content (an earned PhD is a real biographical fact, not branding). There
is no mechanical rule that cleanly separates those two readings of one
source; it takes real human judgment per source, sometimes per sentence,
matching the "wrong-person-trap" discipline already required elsewhere
in the bootstrap procedure.

**Resulting design decision, confirmed by MJSullivan**: Stage 2 mints
**only** `Persona` individuals from transcript extraction. Any
bio-shaped details the intro happens to surface (credentials, career
history, degrees) get written into a `scopeNote`-style `human_lead`
field, explicitly framed as unverified candidate Human facts for a
**separate Pass 2** — not asserted as `Human` facts from the transcript
extraction itself. Pass 2 reuses the *existing* bootstrap procedure's
verification discipline (`CLAUDE.md`'s "FIRST-DRAFT BOOTSTRAP A NEW
PERSON PROCEDURE" — confirm identity, check for a genuine Wikipedia
page, explicitly distinguish "confirmed absent" from "not yet
checked") — and needs to stay alert to the Cher trap specifically: a
"personal website" found during that later verification pass may itself
just be more Persona surface, not real evidence about the Human
underneath.

```yaml
human_lead:
  scopeNote: |
    <unverified candidate Human-level facts stated in the transcript —
    credentials, career history, degrees — explicitly flagged as leads
    for a separate Pass 2 that does real web verification before
    creating/updating a Human individual. NOT asserted as fact here.>
```

**Explicitly not resolved, flagged for whenever Pass 2 actually gets
built**: how Pass 2 itself should be scoped/triggered (per-guest, batch,
manual-only), and whether "is this guest already in the graph" (the
Farley-vs-Pinsky distinction above) belongs inside Stage 2's own output
or stays a separate reconciliation step run against `personas.ttl`
afterward — current lean is the latter (keep Stage 2's job narrow:
extract facts from text, don't also decide identity), not yet a final
decision.

**`extraction/eval_stage2_yaml.py` updated to this schema and re-run the
same session, immediately after this entry was drafted** — both gold
files (Josh Farley, Malin Pinsky) came back 100% recall on relationships
(2/2 and 3/3), `target_class: thinkr:Persona` correct on both,
`human_lead` populated on both with real, non-filler content. Spot-
checked Josh Farley's raw output directly: the split worked as designed
— his Columbia degree, the Herman Daly correspondence, and his Brazil
fellowship all landed in `human_lead` as unverified leads rather than
being asserted as Persona relationships, and `hasRelationshipType`
mapped correctly (Academic for the AcademicInstitution, Professional for
the Organization) without that mapping rule needing a second pass. Real,
not hypothetical, corroboration that the split is learnable from a
single system-prompt instruction, at least on these 2 examples.

**Session paused here** — MJSullivan may pick this back up in a few
hours. Genuinely still open, not resolved by this re-run: the two
"explicitly not resolved" items above (how Pass 2 gets triggered/scoped;
whether new-vs-existing-guest detection belongs in Stage 2's own output
or stays a separate reconciliation step) — the re-run demonstrates the
schema extracts cleanly, not that either of those two design questions
has been answered.

## SIDECAR NAMING RETROFIT (2026-07-15, later the same day): LinkNote/
## Evidence/CrosswalkNote brought into compliance with Relationship's
## already-correct {Subject}_{Object} pattern — 76 individuals renamed,
## zero triples lost, found while reviewing the Berman/Farley pilot's
## own output

**Trigger**: reviewing the bio-intro pilot entry immediately below (the
one that added `LinkNote.SuperorganismFarley`) surfaced that its name
didn't match `Relationship`'s already-established
`{Subject}_{Object}`-with-real-local-names convention — MJSullivan caught
this by eye, not tooling.

**Audit, run before touching anything, per MJSullivan's explicit request
to see the full violation list first:**
- `thinkr:Relationship` (13 individuals): 0 violations — confirmed
  compliant, not assumed, by checking every `hasSubject`/`hasObject`
  pair's bare local name against the individual's own name.
- `thinkr:LinkNote` (17 individuals): 17/17 violations (e.g.
  `SuperorganismFarley` should be `Superorganism_JoshFarley`).
- `thinkr:CrosswalkNote`: reported as 39/39 in the initial write-up,
  corrected to the actual **40**/40 once the rename map was built
  programmatically — a real, if small, undercount in the manual
  audit-report pass, caught by the script's own count rather than
  trusted blindly. All 40 violated (e.g. `AristotleDBpedia` should be
  `Aristotle_DBpedia`).
- `thinkr:Evidence` (19 individuals): 19/19 violations, with the added
  wrinkle that 2 `LinkNote`s (`EnergyBlindness_ArtBerman`,
  `Superorganism_JoshFarley` — both from the pilot two entries below)
  each have 2 `Evidence`, needing a disambiguation rule beyond simple
  base-renaming.

**One real aside caught and deliberately NOT fixed under this task**:
`LinkNote.MlkGrowth`'s `aboutSubject`/`aboutObject` are reversed relative
to every other `LinkNote` in the file (`Persona.MartinLutherKingJr` is
the subject, `Concept.GrowthImperative` the object — everywhere else a
`Concept` is the subject). Flagged, not touched — a rename task that
also quietly "corrects" a semantic assignment along the way is a rename
task that's hard to trust later. Its new name
(`LinkNote.MartinLutherKingJr_GrowthImperative`) faithfully reflects
whatever `aboutSubject`/`aboutObject` actually say, reversed order and
all — MJSullivan confirmed this was exactly the right call before
execution.

**FOLLOW-UP, same day, MJSullivan's own catch**: flagging this only in
this doc and in chat wasn't enough — once the individual has a
well-formed, internally-consistent-looking name, the anomaly is
invisible to anyone just browsing or querying `linknotes.ttl` directly,
since the name and its own properties agree with each other (just not
with the rest of the file's pattern). Fixed by adding an explicit
`skos:scopeNote` directly on `tgs:LinkNote.MartinLutherKingJr_GrowthImperative`
itself stating the reversal, that it's unreviewed, and pointing back
here — live-verified via SPARQL query against the reloaded store.
General lesson worth keeping: when a rename makes a pre-existing
anomaly look ordinary, the flag needs to live IN the data, not just in
a doc about the data.

**Evidence-disambiguation rule, the one real judgment call, confirmed by
MJSullivan before execution**: base name = owning `LinkNote`'s new name;
when a `LinkNote` has 2+ `Evidence`, the general/original one keeps the
bare base name and any episode-specific one gets `_TGS_<number>`
appended. Applied: `EnergyblindnessBermanTranscript` →
`EnergyBlindness_ArtBerman_TGS_220` (renamed suffix from the ad hoc
"Transcript" to match the episode-number convention already used on the
Farley case); `SuperorganismFarleyTGS185` →
`Superorganism_JoshFarley_TGS_185`. **Explicitly flagged as an
unresolved gap, not solved here, per MJSullivan's own instruction**: the
rule only cleanly covers "exactly one general + N episode-specific" —
it does not yet say what happens if a future `LinkNote` gets two-or-more
episode-specific `Evidence` and zero general ones. Written into
`CLAUDE.md`'s new 2a as an explicit open question rather than silently
glossed over, to save re-deriving it from scratch next time.

**Pre-flight sanity check MJSullivan specifically asked for, not just
assumed**: confirmed `thinkr:CrosswalkSource.DBpedia` and
`thinkr:CrosswalkSource.Wikidata` are the actual, exact local names in
`data/seed/enumerations.ttl` (grepped directly) before trusting all 40
CrosswalkNote renames were correctly formed — both confirmed exactly as
expected.

**Execution — boundary-safe text substitution, not an rdflib
parse-and-reserialize round trip**: deliberately NOT done via rdflib
graph rewrite + `.serialize()`, unlike `compute_confidence.py`'s write
pass two entries below (which is why that pass silently dropped this
file's decorative section-comments) — a plain-text regex substitution
with `\b` word-boundaries around each full `ClassName.OldLocalName`
token preserves 100% of existing formatting/comments while still being
exact (word boundaries correctly prevent `EnergyblindnessBerman` from
matching inside `EnergyblindnessBermanTranscript`, confirmed by design
before running, not by luck). Built the full old->new mapping
programmatically from live triples (never hand-typed), checked it for
name collisions before writing anything (none found), then applied all
98 substitutions (17+40+19, plus every `hasEvidence`/cross-reference
occurrence of each renamed IRI) across the 3 owning files
(`linknotes.ttl`, `evidences.ttl`, `crosswalknotes.ttl`).

**Verification, same discipline as every batch this week:**
- Baseline triple count: 2,022 (matching the pilot entry below's final
  count). After the rename: 2,022 — exactly unchanged, as a pure rename
  should be.
- Grepped all of `data/seed/` for every one of the 76 old names after
  the substitution pass: zero residual references anywhere, including
  files never touched by the substitution itself (confirms nothing
  outside the 3 owning files was pointing at an old IRI — true by
  schema design, `LinkNote`/`Evidence`/`CrosswalkNote` are never
  themselves the object of any other class's property, but checked
  directly rather than assumed).
- `scripts/validate_class_purity.py --check-scratch-empty`: clean except
  the same 2 already-known, already-flagged violations
  (`episodes.ttl`/Series, `subjects.ttl`/ConceptScheme) — untouched,
  unworsened.
- Reloaded the live Oxigraph store (stop `serve`, `rm -rf ./tgs_store`,
  reload, restart `serve`) and live-SPARQL-queried: every sampled OLD
  name (`LinkNote.SuperorganismFarley`, `LinkNote.MlkGrowth`,
  `Evidence.EnergyblindnessBermanTranscript`,
  `CrosswalkNote.AristotleDBpedia`,
  `CrosswalkNote.MartinLutherKingJrWikidata`) returns zero triples;
  every sampled NEW name resolves with its full original property set
  intact, including that `LinkNote.Superorganism_JoshFarley`'s
  `hasEvidence` correctly points at the newly-renamed
  `Evidence.Superorganism_JoshFarley_TGS_185`, not a dangling reference
  to the old name. Class counts confirmed unchanged: 17 `LinkNote`, 19
  `Evidence`, 40 `CrosswalkNote`.
- Updated the prose cross-references this rename would otherwise leave
  stale: this doc's own bio-intro pilot entry (below) and
  `CLAUDE.md`'s IRI-minting worked example (which, unhelpfully, had
  been citing the exact non-compliant pattern this task fixes). Left
  the handoff doc's older (2026-07-11) "Worked examples"/"Open
  Questions" sections alone — those are explicitly framed as historical
  OLD/NEW illustrations of a different, already-closed design
  discussion, not live current-state claims.

**Documentation decision**: written into `CLAUDE.md` as new decision
2a, directly under the existing IRI-minting convention (decision #2) —
not a new dedicated `NamingConventions.md` file. MJSullivan's call: one
additional rule doesn't justify mirroring UWOM's separate doc; a single
CLAUDE.md bullet is the right-sized home for it.

## BIO-INTRO EXTRACTION PILOT, 2nd application (2026-07-15): Art Berman +
## Josh Farley — mostly RelationshipType corrections and Evidence-
## strengthening on already-known people, not new-entity discovery like
## Monahan; a real infrastructure bug (compute_confidence.py) found and
## fixed along the way

**Starting point / two real discrepancies caught before any work began,
worth recording so they don't recur:** the task brief for this session
described `scripts/segment_intros.py` as "already exists (built this
week)" — it did not exist anywhere in the repo (confirmed via `find` and
`git log`); MJSullivan supplied it mid-session from wherever it had
actually been saved (turned out to belong in `extraction/`, not
`scripts/` — moved/used from there instead). Separately, this doc's own
STEP 0 instructions pointed at "the most recent dated entries about...
the bio-intro extraction pilot done on Matthew Monahan" — no such dated
entry exists in this file; the Monahan pilot's real output (Mangaroa
Farms, the Mangaroa Farms->Biome Trust Relationship, the corrected
RelationshipType.Personal on Relationship.NateHagens_MatthewMonahan) only
ever landed as an **uncommitted** diff against `organizations.ttl` and
`relationships.ttl`, cross-referencing "see docs/sidecar-cleanup-
handoff.md for the fuller discussion" — a discussion that was never
actually written here. **Still not fixed as of this entry** — flagged,
not resolved, since writing that retroactive entry wasn't this session's
job. Do it before/alongside actually committing the Monahan diff.

**Scope, matching the task's own "small and deliberate" instruction:**
two already-bootstrapped Personas, both single-guest Interviews, 7
episodes total — Art Berman (TGS_3, TGS_92, TGS_101, TGS_220) and Josh
Farley (TGS_7, TGS_29, TGS_185). Explicitly did NOT touch the Roundtable
transcripts (RR01, RR03) both guests also appear in, or the 2 additional
real Berman appearances (TGS_44/"ArtBermanPt2", TGS_54/"ArtBerman3")
whose existence gets corroborated below — all deliberately deferred, not
forgotten.

**Stage 1 (`extraction/segment_intros.py`) — the manifest-type-filter gap
flagged in the task brief was real and got fixed** (the eligible-types
check existed as a variable but was never actually applied to the file
loop — now keyed off `download_manifest.csv`'s `local_filename`, skips
Frankly transcripts for real). **A second, more consequential gap was
found independently this session, not previously flagged anywhere:** the
transcript corpus actually has TWO incompatible timestamp formats, not
one — `[HH:MM:SS] Name: text` (newer transcripts, e.g. TGS-220, TGS-185)
and `Name (HH:MM:SS):` / `Name (MM:SS):` (older transcripts — confirmed
on TGS03/TGS92/TGS101/TGS07/TGS29, i.e. 5 of this pilot's own 7 targets).
Without support for the second format, Stage 1 would have silently
produced usable output for only 2 of the 7 episodes this pilot actually
needed. Fixed by trying both patterns in sequence. Real corpus-wide
effect, not just a fix for this pilot's narrow target list: re-running
Stage 1 against the full `transcripts_text_cache/` went from 118
processed intro segments (manifest-filter fix only) to 244 (both fixes)
— roughly half the interview/roundtable library was on the older format.
The Roundtable multi-guest window-width gap flagged in the task brief
remains genuinely untouched, as instructed (Berman/Farley are both
single-guest).

**Stage 2 (by-hand reading, same as the Monahan pilot — no LLM API call
made, per the task's own explicit instruction not to build that
automation yet for a pilot this small):**

*Art Berman* — no new Organization surfaced (unlike Monahan). What the
intros surfaced instead:
- `RelationshipType.Personal` added to `Relationship.NateHagens_ArtBerman`
  (previously Professional only) — Nate calls him "my friend" directly in
  3 of the 4 modeled episodes (TGS_92, TGS_101, TGS_220).
- The relationship's existing "incomplete roster" scopeNote (already
  flagging TGS_44/TGS_54 as probable additional, unmodeled appearances)
  gets real primary-source corroboration: in TGS_101 (aired 2023-11-29)
  Nate says "I think this is his fifth appearance" — consistent with
  TGS_3 + 44 + 54 + 92 + 101 = 5. Still not modeling 44/54 as individuals
  this session (out of scope), just upgrading the existing flag from
  "the transcript library suggests" to "Nate's own words confirm."
  Also captured, same scopeNote: Nate's own account of how they met —
  both wrote for The Oil Drum, corroborating the pre-existing
  `Relationship.NateHagens_TheOilDrum` / `Relationship.ArtBerman_TheOilDrum`
  pair as the actual origin of this relationship, not a coincidence.
- A new `Evidence` (`Evidence.EnergyBlindness_ArtBerman_TGS_220` — renamed
  2026-07-15, see the naming-convention entry below) added to
  the ALREADY-EXISTING Candidate-confidence
  `LinkNote.EnergyBlindness_ArtBerman` — that LinkNote's original Evidence
  explicitly flagged "not yet cross-checked against a specific TGS
  episode... establishing first use"; TGS_220 closes exactly that gap:
  Berman himself says "it's a blunder based on energy blindness" on
  Nate's own show. Still left Candidate, not upgraded to Curated — that's
  a human-review call (design decision #1), not something a pilot script
  or this session gets to decide unilaterally, however strong the new
  citation looks.

*Josh Farley* — also no new Organization. The Gund Institute for
Environment (already documented as prose on `Human.JoshFarley`, repeated
in TGS_185's intro) was considered and deliberately NOT minted as its own
individual — it's a research institute within UVM, not the kind of
legally-distinct entity Mangaroa Farms was, and nothing here is actually
NEW information versus what the original bootstrap already captured.
Same deferred status as Berman's ASPO-USA. What DID surface:
- `RelationshipType.Personal` AND `RelationshipType.Academic` added to
  `Relationship.NateHagens_JoshFarley` (previously Professional only) —
  repeated across all 3 modeled episodes: Farley was "the chair of my PhD
  committee" and "one of my best friends" (TGS_7), "my old friend" (TGS_29),
  "my friend and PhD advisor" / "my PhD chair" (TGS_185). Academic here is
  deliberately distinct from the existing institutional
  `Relationship.JoshFarley_UniversityOfVermont` — this is "personally
  chaired Nate's own PhD committee," not just "both connected to UVM."
- The clean, unambiguous instance of the "host-asserted explicit
  concept-connection" pattern this whole pilot was designed to test for
  (the Robert Lustig precedent discussed before piloting): a new
  `LinkNote.Superorganism_JoshFarley` (renamed 2026-07-15, see the
  naming-convention entry below) (`Persona.JoshFarley echoesIdeaOf
  Concept.Superorganism`, Candidate confidence), backed by TWO Evidence
  individuals — Nate's own words in TGS_7 ("We have followed parallel
  paths to agree that humanity is currently functioning as a mindless,
  energy-hungry, superorganism...") and independent corroboration in
  TGS_185, where Farley himself uses the term unprompted. `echoesIdeaOf`
  (not `influencedBy`) is the correct property here — "parallel paths"
  is explicitly independent convergence, not one-directional influence.
- `Human.JoshFarley`'s bio comment enriched with a specific current-
  research-focus list from his own TGS_185 introduction (essential
  resources, monetary/financial system democratization, cooperation,
  information economics, the commons) — minor, but a direct, accurate
  addition sourced from the primary text rather than the original
  general-web-search bootstrap.

**Real, unplanned infrastructure bug found and fixed:**
`scripts/compute_confidence.py` still referenced the PRE-RENAME
vocabulary (`ConfidenceLevel.*`, `ReliabilityTier.*`, `EvidencePolarity.*`)
from before this project's `ConfidenceType`/`ReliabilityType`/
`PolarityType` renames — exactly the "text-based rename never touches
vocabulary URIs embedded in Python code" gotcha CLAUDE.md already warns
about, just never actually caught for THIS particular rename. Practical
effect: every comparison in the script silently matched nothing against
the real graph, so every LinkNote fell through to the rule-6 floor state
regardless of its actual Evidence, and `--write` mode would have
serialized undefined `ConfidenceLevel.*` individuals into the seed files
(exactly the kind of value the CI check is supposed to catch, since it's
not one of the two real `ConfidenceType` individuals). Caught by
`--dry-run` returning a suspiciously uniform 17/17 "Candidate" — including
LinkNotes with a single Curated+Supports, no-Source Evidence that should
be a textbook rule-5 "exactly 1 -> Curated" case. Fixed (3 namespace
constants), re-verified via `--dry-run` and a live-query spot-check
(`LinkNote.JevonsJevons` now correctly resolves `Curated`), then actually
run — this was necessary to complete this session's own required
verification step (design decision #1's "never hand-set calculatedConfidence"
rule), not optional cleanup layered on top of the pilot.

**Verification, same discipline as every batch this week:** baseline
1,990 triples in `data/seed/*.ttl` before this session's edits (already
including the still-uncommitted Monahan enrichments from earlier this
week); 2,022 after this pilot's edits + a real `compute_confidence.py`
run (+32). `scripts/validate_class_purity.py --check-scratch-empty`
clean except for the 2 already-known, already-flagged, untouched
violations (`episodes.ttl`'s Series mixing, `subjects.ttl`'s ConceptScheme
mixing) — nothing from this session made either worse.
`data/seed/scratch.ttl` never used this session — everything found was
confident enough (backed by primary-source transcript quotes, no brand-
new unverified entity) to go directly to its real destination file.
Live-reloaded the Oxigraph store (stopped the running `serve` process,
`rm -rf ./tgs_store`, reloaded, restarted `serve`) and individually
SPARQL-queried every new/corrected fact above — all resolve correctly
against the live store, not just "the file parses."

**Is the pattern worth Stage 2 automation at real scale? Recommendation,
not yet decided by MJSullivan:** worth continuing to pilot, but this 2nd
run changes the picture from Monahan's alone. Stage 1's dual-format
window-capture held up robustly once both real formats were supported.
But this pilot's actual YIELD was more modest than Monahan's — mostly
RelationshipType corrections and Evidence-strengthening on people already
well-modeled, not a brand-new Organization/Relationship — which may mean
the technique's marginal value is highest on FIRST-appearance/newly-
bootstrapped guests (where basic facts are still being established) and
lower on repeat guests whose relationships are already fairly complete,
rather than a sign the pattern itself is weakening. Worth testing next on
a guest who has NOT yet been bootstrapped at all, to properly compare
against Monahan's outcome instead of against this session's. Stage 2
itself is still 100% by-hand reading across both pilots now (2 data
points) — genuinely not yet enough volume to justify real LLM-API
automation per the task's own explicit guidance, but the 4-category
extraction pattern (bio/credential facts, org mentions, explicit
host-asserted concept-connections, relationship-type signals) has now
worked cleanly and consistently twice, which is a reasonable signal for
eventually turning it into a structured prompt once volume actually
justifies building that.

**Explicitly NOT done, next-session starting point:** write the
retroactive Monahan dated entry this doc's own STEP 0 already assumed
existed; the Roundtable window-width gap; any additional Personas beyond
Berman/Farley (explicit checkpoint per the task brief — stop here, don't
auto-continue).

## BIO-INTRO EXTRACTION PILOT, 1st application (2026-07-14): Matthew
## Monahan — the original pilot the 2nd-application entry above
## references but that was never actually written up here; done
## retroactively 2026-07-15 in Claude Chat, documenting real work from
## the prior day

**Why this entry is dated 2026-07-14 despite being written 2026-07-15:**
this records when the actual enrichment work happened, not when the
write-up was produced — matching this doc's own standing convention
(dated entries reflect the work, not the authoring session). The gap
itself — real Persona/Organization/Relationship edits sitting as an
uncommitted diff for a full day, cited by their own scopeNotes as
pointing to a discussion that didn't exist yet — is exactly the kind of
mistake this doc exists to prevent, and it happened anyway. Caught by
Claude Code during the 2nd-application pilot (see entry above), not by
the original session that produced the diff.

**Origin**: MJSullivan noticed that Nate's own guest introductions
(the first few minutes of most Interview episodes) are a different,
richer kind of source than either generic NER or general web search —
concretely illustrated with a Robert Lustig snippet where Nate directly,
explicitly maps the guest's work onto an existing Concept
(`Concept.Superorganism`) in his own words. Rather than pilot on a
fresh, unbootstrapped guest, the decision was to first enrich a handful
of ALREADY-bootstrapped Personas and see what actually surfaced —
deliberately testing the technique against known context before
deciding whether to extend the standard bootstrap workflow.

**Only one existing Persona had real transcript text actually available
in this session** (Claude Chat, not Claude Code — no direct filesystem
access to `extraction/transcripts_raw/`): Matthew Monahan, `TGS_226`,
from the `transcripts_text_cache/` archive MJSullivan had uploaded
earlier the same day. Berman, Farley, and McGilchrist's real transcripts
existed on MJSullivan's machine but were never uploaded to this
conversation — genuinely why this pilot was 1 person, not more, and why
the natural continuation became "hand this to Claude Code, which
already has the full corpus on disk" (see the 2nd-application entry
above).

**What reading the actual intro segment (first ~2 minutes, read by hand,
no script) surfaced, all independently verified before being asserted,
same discipline as every bootstrap this week:**

1. **`Organization.MangaroaFarms` — a genuinely new individual**, not
   previously in the graph at all. The transcript itself only says
   Monahan is "involved... through Mangaroa Farms... a regenerative farm
   and educational hub" — thin enough that it was treated as a lead, not
   a fact, and independently verified via 7 separate sources (mangaroa.org's
   own About page, NZBusiness Magazine, Good Magazine, Quorum Sense,
   Waterford Press, Crunchbase, Commonweal) before being written into
   `organizations.ttl`. Real: founded 2018 by Matthew and his brother
   Brian Monahan (with Catlin Powers), a working farm/food hub/education
   centre in Upper Hutt, New Zealand.
2. **A real structural fact the transcript itself never quite stated,
   only surfaced by the independent verification pass**: Mangaroa Farms
   is owned by/part of `Organization.BiomeTrust`, per Mangaroa's own
   About page — already a real individual in this graph. Modeled as
   `Relationship.MangaroaFarms_BiomeTrust`, the FIRST Organization-to-
   Organization `Relationship` in the graph. Checked, not assumed: confirmed
   `thinkr:hasSubject`/`hasObject` have no `rdfs:range` restriction that
   would have made an Org-to-Org pairing schema-invalid before asserting
   this was safe.
3. **`RelationshipType.Personal` added to `Relationship.NateHagens_MatthewMonahan`**
   (previously Professional only) — direct textual evidence, not
   inference: Nate's own words in the transcript, "my friend Matthew
   Monahan" and "despite the fact that we are friends" as his stated
   reason for having him on.
4. **Noted, deliberately NOT formally modeled**: Ma Earth being "on
   their third round of funding... as of the release of this episode" —
   a real, point-in-time fact, but exactly the kind of volatile,
   dated-status detail flagged as a bad fit for permanent graph content
   in the GUI/product-roadmap backlog discussion the same day (content-ops
   burden, facts that rot). Left as transcript content, not asserted as
   a graph fact.

**Verification**: combined graph triple count 1,970 -> 1,990 (+20) after
this pilot — confirmed via `rdflib` parse of the full `data/seed/`
directory at the time, not just the individually-touched files.
`Organization.MangaroaFarms` confirmed correctly typed; both new
`Relationship` individuals confirmed resolving `hasSubject`/`hasObject`
correctly; `Relationship.NateHagens_MatthewMonahan`'s `hasRelationshipType`
confirmed returning both `Personal` and `Professional`.
`scripts/validate_class_purity.py --check-scratch-empty` run clean —
only the 2 already-known, already-flagged violations (`episodes.ttl`
Series, `subjects.ttl` ConceptScheme), `scratch.ttl` correctly empty
throughout (everything found was confident/verified enough to write
directly to its real destination file, same as the 2nd-application
pilot's own later finding that scratch wasn't needed either).
**NOT independently confirmed against a live-reloaded Oxigraph store in
this same session** — that reload/live-query step happened later, as
part of the 2nd-application pilot above, which explicitly re-verified
these Monahan facts alongside its own Berman/Farley additions before
declaring the store good. Recorded here for completeness, not because
this entry did that verification itself.

**What this pilot's outcome, compared against the 2nd-application
pilot's outcome, actually tells us**: Monahan (a relatively thin
original bootstrap) yielded a brand-new Organization and a new
cross-organization Relationship. Berman and Farley (both more thoroughly
bootstrapped via general web search originally) yielded relationship-
type corrections and Evidence-strengthening, not new entities. Two data
points is not a lot, but the direction is consistent and worth taking
seriously when deciding how to prioritize this technique going forward:
its marginal value looks highest on thin/early bootstraps, lower on
already-well-modeled people — suggesting this might belong as a
standard STEP in the bootstrap procedure itself (read the intro before
or alongside the general web search, not after), rather than a separate
enrichment pass applied retroactively to already-finished Personas.
Not yet decided by MJSullivan.

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

## ⚠️ SUPERSEDED (flagged 2026-08-13, original material 2026-07-11) —
## everything from here to the end of this document is an ABANDONED
## design path, not a live open question. Read for historical context
## only; do not execute against it.

**What this whole block actually is**: an early, exploratory planning
session from 2026-07-11 — BEFORE the Persona architecture existed at
all (it still references `tgs:Person.Aristotle`, not
`tgs:Persona.Aristotle` — a strong, unambiguous sign of its age). It
proposed a much bigger redesign than what actually got built: merging
`LinkNote`/`Evidence` into one class, collapsing `influencedBy`/
`echoesIdeaOf`/`contrastsWith`/`convergesWith` into one generic property
plus a type value, renaming `LinkNote` and `CrosswalkNote` entirely, and
dropping `owl:sameAs`. NONE of that happened.

**What actually got built instead, weeks later** (Claude Code, commits
`cea3de0`/`a36a8ce`, confirmed clean via `validate_class_purity.py` as
recently as 2026-08-13): a much NARROWER fix — just correcting the
LOCAL-NAME pattern (`{Subject}_{Object}`) on `Relationship`/`LinkNote`/
`Evidence`/`CrosswalkNote` exactly as those classes already existed,
using the properties exactly as they already existed. No class merging,
no renaming, no property collapsing. `LinkNote` is still called
`LinkNote`. `CrosswalkNote` is still called `CrosswalkNote`.
`owl:sameAs` is still live and used 42 times across the graph (28 of
them in `humans.ttl` alone) — confirmed via direct grep 2026-08-13, NOT
the zero this block's own "RESOLVED" note (4b, below) claims.

**Why this is being marked rather than deleted**: it's a real record of
reasoning that led AWAY from a design path, which has some value — but
it was sitting mid-document with no clear signal that it had been
bypassed, which caused genuine confusion this session (MJSullivan
brought its "Open Questions" back as if they were still live). Left
in place, clearly marked, rather than silently removed.

**If any of this ever becomes worth reconsidering for real** (the
`LinkNote`/`Evidence` merge question in particular still has some
underlying merit, per the 2026-08-13 architecture discussion that
independently arrived at a compatible but not identical conclusion —
see that session's entry higher in this doc) — treat it as a fresh
design question informed by how the graph has ACTUALLY evolved since,
not as resuming this abandoned thread where it left off.

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


## CONVENTION CHANGE (2026-08-13): everything ABOVE this point is in
## latest-first order (per the 2026-07-13 convention); everything BELOW
## is in true chronological order, oldest-to-newest, per MJSullivan's
## 2026-08-13 preference reversal (see this doc's own top-of-file
## note). New entries append at the BOTTOM from here forward. The
## existing sections above have NOT been physically reordered — see
## `[2026-08-13-8]` below for that tracked, not-yet-done task.

## SESSION WRAP-UP (2026-08-13): schema audit + fixes, alternate-term
## thesaurus mechanism, first real show-notes-to-graph conversion pass —
## and the tgs_store loading saga that ate a good chunk of the session

**Context**: this session picked up after Claude Code's Herrington
bootstrap + LinkNote/Evidence/Relationship/CrosswalkNote naming retrofit
(see the entry below). Split roughly into four threads: an architecture
discussion (discusses/LinkNote-as-generic-crosswalk, resolved by NOT
over-formalizing), a full schema audit with real fixes, a new thesaurus
mechanism (AlternateTerm), and the first real pass converting an
episode's official show notes into graph content. Plus a genuinely
instructive infrastructure failure late in the session, worth its own
lessons-learned section below. **Going forward, a session write-up like
this one should happen at the end of every session, not just when
something goes wrong or gets asked for explicitly** — MJSullivan made
this a standing practice this session, not a one-off.

### Thread 1: discusses / generic-crosswalk architecture decision

MJSullivan raised: while still learning what Nate's content actually
covers, don't over-model — stay mostly flat, use a generic
confidence-bearing crosswalk mechanism, formalize specific relationship
types only once a real shape reveals itself from the data. Resolved:

- `thinkr:discusses` (Episode->Concept) stays a plain direct triple,
  NOT retrofitted to Evidence-backed treatment despite an earlier
  session's recommendation to do so — deliberately deferred, not
  decided against permanently.
- The "generic crosswalk with confidence and metadata" MJSullivan asked
  for ALREADY EXISTS: `thinkr:LinkNote`'s `aboutSubject`/`aboutObject`
  have zero range restriction — genuinely any-entity-to-any-entity
  already, just never used that way since every existing instance
  happens to involve a Concept. No new class needed. Rejected: a
  parallel new "Crosswalk" class (would itself be over-modeling — 3
  overlapping mechanisms instead of 1 reused one) and moving Evidence
  to blank nodes (would lose real, working functionality — named
  Evidence individuals are independently queryable and already proven;
  blank nodes fit the disposable, never-reused PodcastAppearance
  pattern, not this one).
- A full relationship-type inventory was produced by extracting every
  `owl:ObjectProperty`'s actual domain/range directly from the live
  schema (not from memory) — surfaced 2 genuinely dead properties (see
  Thread 2) as a byproduct.

### Thread 2: full schema/data audit, real fixes

Triggered by the relationship-inventory work above surfacing 2
suspicious properties. Given the full real `data/seed/` (uploaded fresh
this session — the working set had drifted from what Claude Code had
actually committed), ran a comprehensive audit rather than spot-fixing:

- **`thinkr:discussedIn` and `thinkr:hostedBy` removed** — both
  confirmed via grep across every file to have ZERO real usage as
  predicates, only appearing inside comments explaining their own
  historical deprecation. Genuine leftover schema that outlived the
  decisions that superseded them. The reasoning stayed discoverable —
  folded into `discusses`'s own comment rather than lost when the
  declarations disappeared.
- **Full parse check**: all 20 files clean, individually and combined.
- **Zero dangling references** across the whole graph (every object
  referenced is a properly typed subject somewhere) — checked before
  AND after every subsequent change this session, never assumed to
  still hold.
- **Naming convention (`{Subject}_{Object}`) audit**: zero violations
  across all of `Relationship` (19), `LinkNote` (18), `CrosswalkNote`
  (42), `Evidence` (20, including the documented `_TGS_NNN` suffix
  cases) — confirms the earlier retrofit held up against the full real
  dataset, not just the examples checked at the time.
- **`has*Relationship` family found genuinely `Persona`-only**, despite
  real non-Persona parties existing in the graph. Widened all 5
  properties' domain to `thinkr:NamedEntity`. Full audit (not just the
  one known `MangaroaFarms`/`BiomeTrust` case) found **12 distinct
  entities across 14 relationships** needing backfill — TheOilDrum,
  PostCarbonInstitute, MangaroaFarms, BiomeTrust, SchneiderElectric,
  ClubOfRome, StopStraatintimidatie, UniversityOfVermont,
  UniversityOfMinnesota (both Academic and Professional, matching its
  dual-typed Relationship), HarvardUniversity, PeakOilMovement. Verified
  via exact triple-count math (+15, matching the count of backfilled
  pointers precisely) and a full re-run of the symmetric-indexing query
  confirming zero remaining gaps.
- Class-purity re-run clean throughout — only the 2 already-known,
  deliberately-unfixed violations (`episodes.ttl`/Series,
  `subjects.ttl`/ConceptScheme) ever appeared.

### Thread 3: AlternateTerm thesaurus mechanism (new)

MJSullivan's insight: `skos:altLabel` can't carry relationship TYPE
(exact/close/broad/narrow/related/antonym), provenance, or independent
identity — a real gap for serendipitous discovery, since most people
will search using their own field's terminology, not Hagens' own
coinages. Built:

- `thinkr:AlternateTerm` class, `thinkr:hasAlternateTerm` (domain
  Concept), `thinkr:hasAlternateTermType`, `thinkr:AlternateTermType`
  (Category-marked, 6 individuals: ExactMatch/CloseMatch/BroadMatch/
  NarrowMatch/Related/Antonym) — the first 5 deliberately reuse SKOS's
  own thesaurus vocabulary rather than inventing parallel terms; Antonym
  is the one genuine addition, since SKOS has no native opposition
  relation. Open question, not resolved: whether Antonym should instead
  defer to the already-existing `thinkr:contrastsWith` — flagged,
  pending a real antonym case to test against.
- MJSullivan's own proposed pattern preserved exactly: a term can be an
  anonymous blank node (context-bound, first appearance) OR a named
  individual (promoted once reused across multiple Concepts or once it
  earns independent citable history) — same property either way, so
  promotion never requires touching the schema.
- **Pilot case, real not hypothetical**: `Concept.Wetware`'s own
  `skos:prefLabel` was found to be a compound string ("Human 'Wetware' /
  Evolutionary Mismatch") — two real terms jammed into one label, the
  exact anti-pattern this mechanism exists to fix. Split cleanly:
  `prefLabel` now just "Human 'Wetware'", "Evolutionary Mismatch" now a
  properly `ExactMatch`-typed `AlternateTerm` blank node.
- **A real bug caught and fixed mid-build, worth remembering**: first
  draft put `AlternateTermType`'s 6 individuals directly inside
  `tgs-core.ttl`, violating this project's own established rule
  (tgs-core.ttl holds classes/properties only, zero NamedIndividuals —
  the exact reason `ScenarioDimension` got its own file weeks ago).
  Caught via an ACTUAL PARSE FAILURE, not a style review — tgs-core.ttl
  has never declared the `tgs:` prefix, since it was never meant to
  reference tgs:-namespaced individuals. Fixed by moving everything to
  a new `alternatetermtypes.ttl`, matching the `scenariodimensions.ttl`
  precedent exactly. Lesson: even careful work benefits from an actual
  parse check, not just re-reading the text — this mistake would have
  been easy to miss by eye.
- `alternatetermtypes.ttl` joins `scenariodimensions.ttl` as a SECOND
  file that belongs in `enumerations.ttl` once that file is safely
  editable again — worth consolidating both together in one future
  pass, not as two separate cleanups.

### Thread 4: first real show-notes-to-graph conversion (TGS_138)

MJSullivan discovered Nate's team maintains structured, timestamped
show-notes pages per episode (thegreatsimplification.com/frankly-
original/...) — confirmed via direct fetch to be clean, consistent,
WordPress-generated HTML, not just unstructured video description text.
Far stronger extraction source than transcript-reading or generic NER:
official editorial curation, not inference. MJSullivan did a rough
manual first-pass categorization of TGS_138's full show-notes list
(marked with his own bracket notation); this session triaged and built
it into the graph:

- **7 new Concepts minted**: TerrorManagementTheory (3rd independent
  confirmation across sessions — flagging again the still-unresolved
  Becker/Pyszczynski verification from an earlier session's Solomon
  transcript investigation), ShortfallRisk (doubly confirmed, an
  earlier by-hand pilot AND this official source both surfaced it —
  the official description explicitly calls it connective tissue across
  the whole series), ScenarioThinking (has a real citable external
  source, not yet independently verified enough to mint as a Work),
  MoreThanHumanPredicament (explicit OPEN QUESTION flagged in its own
  scopeNote — may be the same idea as the existing HumanPredicament
  under different framing, deliberately not silently merged or
  duplicated), NarrativeAsActiveInference, Rebuildables (Hagens' own
  reframing of "renewable" energy infrastructure — first real
  AlternateTerm pilot beyond Wetware, "Renewables" linked as
  CloseMatch, not ExactMatch, since the whole point is a meaningful
  distinction in connotation, not a neutral synonym), ComplexSystems
  Thinking (deliberately a general cluster stub, not split into 4+
  separate concepts for each named sub-idea — related to but NOT
  formally linked to existing ComplexityCollapse/Metacrisis, flagged in
  prose rather than prematurely formalized).
- **2 new Works**: the Cilliers book, the Global Tipping Points Report
  2025 — both cited directly by the official show notes, author/details
  not independently re-verified this session (taken from an already-
  authoritative source).
- **TGS_138 fully rebuilt**: real dates (created 2026-04-11, issued
  2026-04-17) and Subject tags pulled directly from the fetched page;
  real definition; 9 `discusses` links; 7 `dct:references` (an
  Organization, 2 new minimal episode stubs for cross-referenced
  Franklys #129/#132, 2 existing McGilchrist episodes, the 2 new
  Works). **Also fixed 2 real bugs that had been sitting in this stub
  since an earlier session**: `hasCanonicalSource` had been used twice
  (violates its own documented cardinality-one scopeNote — the essay
  link now correctly uses the general `dct:source` instead) and was
  typed as an `xsd:anyURI` string literal rather than a proper linked
  resource (the property is declared `owl:ObjectProperty`, range should
  be a bare IRI, matching every other use of it in the graph).
- **Deliberately NOT modeled**, per an explicit triage before building
  anything: real-world current events (Iran War 2026, the Hormuz
  situation's sub-threats), generic term definitions (Recession vs.
  Depression, portfolio management basics, nuclear taboo/game theory),
  and the "Oil 101-301" series mention (too little information — no
  episode numbers — to responsibly stub).
- **Scope honestly limited**: this is ONE episode's show notes,
  converted and validated end-to-end as a real proof of the method —
  NOT a comprehensive pass. The same triage-and-build process needs to
  repeat for the other 5 parts of this series, and eventually the rest
  of the real corpus, before this is anything close to comprehensive.

### Lessons learned: the tgs_store loading saga

A real, multi-step infrastructure failure worth remembering as a
pattern, not just a one-off annoyance — THREE separate, unrelated
problems stacked on top of each other, each one masking the next until
diagnosed individually:

1. **"Address already in use"** — a previous `oxigraph serve` process
   was still running and had never actually been stopped, holding port
   7878. Diagnosed via `lsof -i :7878` to get the real PID before
   killing anything, rather than guessing.
2. **A load that appeared to complete but produced an empty store** —
   traced to `load_oxigraph.sh` having LOST ITS EXECUTE PERMISSION at
   some point (likely a side effect of how an updated copy was saved
   onto disk in an earlier session, not an intentional change) — meaning
   `./load_oxigraph.sh` had been silently failing with "Permission
   denied" and no one had been reading the actual terminal output
   closely enough to notice, for possibly multiple prior reload
   attempts. Fixed with `chmod +x`.
3. **Even after fixing both of the above, the triple count still came
   back short** (2377 instead of an expected 2392) — traced to the
   local `data/seed/` files simply being STALE relative to what had
   actually been posted in chat a few messages earlier (a real fix's
   files were never actually downloaded/replacing the old ones on
   disk).

**The actual lesson, worth carrying forward explicitly**: a "successful-
looking" reload is not the same claim as a correct one. The right
diagnostic sequence when something's off — confirm no server is running
(`lsof`), confirm the load script actually has permission to run and
actually completes without silent errors (read its real output, don't
just check the exit code), confirm the files on disk are actually the
current ones (grep for a specific expected string) — caught every one
of these in turn, but only because each step was verified independently
rather than assumed. A single "did the count match" check would have
caught SOMETHING was wrong, but not which of three unrelated things.

### Explicitly NOT done this session, next-session starting points

**PILOT (2026-08-13): hierarchical IDs on this list, per MJSullivan's
question about whether findings/todos should get unique identifiers.**
Format: `[YYYY-MM-DD-N]`, matching the date-prefixed section-header
convention already in use elsewhere in this doc, extended down to
individual item level rather than only section level. Piloted here
specifically (not retrofitted across the whole document's history) to
see whether it's actually useful before deciding to apply it broadly —
same "let's see what the data tells us before committing" instinct
already used repeatedly for the graph's own schema decisions.

1. `[2026-08-13-1]` Consolidate `scenariodimensions.ttl` and
   `alternatetermtypes.ttl` into `enumerations.ttl` once that file is
   safely accessible.
2. `[2026-08-13-2]` Resolve `MoreThanHumanPredicament` vs.
   `HumanPredicament` — same idea reframed, or a genuine deliberate
   broadening?
3. `[2026-08-13-3]` Resolve whether `AlternateTermType.Antonym` should
   defer to the existing `thinkr:contrastsWith` instead of being a
   separate relation.
4. `[2026-08-13-4]` Independently verify the "Scenario Thinking" book
   citation enough to mint it as a real Work.
5. `[2026-08-13-5]` Continue the show-notes-to-graph conversion for the
   other 5 parts of the "How to Think About the Future" series, then
   beyond it.
6. `[2026-08-13-6]` The still-open Becker/Pyszczynski verification from
   the Solomon transcript investigation, now flagged a second time via
   TerrorManagementTheory's own scopeNote.
7. `[2026-08-13-7]` The 2 pre-existing, still-unfixed class-purity
   violations (`episodes.ttl`/Series, `subjects.ttl`/ConceptScheme) —
   untouched again this session, deliberately out of scope each time
   so far.
8. `[2026-08-13-8]` Physically reorder this document's existing ~25
   sections into true chronological order, matching the new convention
   established above this entry — deliberately NOT done in this same
   pass, given the real risk of a manual reshuffle at this scale; needs
   a scripted, verified transformation (this doc's own stated
   discipline), not hand-editing.

