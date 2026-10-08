---
name: nate-hagens-ontology
description: Working knowledge for the nate-hagens-kg ontology project (The Great Simplification podcast knowledge graph). Use this skill at the start of every Claude Code session on this repo, and whenever performing reasoner/HermiT work, TTL authoring, running or writing derivation scripts, or making architectural decisions about the schema. Captures real, hard-won gotchas — several bit multiple scripts independently before being recognized as a pattern.
---

# nate-hagens-ontology — working knowledge

## What this repo is

A personal knowledge graph (RDF/OWL, `tgs:`/`thinkr:` namespaces) covering
Nate Hagens' "The Great Simplification" podcast — episodes, guests,
relationships, concepts, and a 4-dimension/16-facet scenario framework.
Built by hand across many Claude chat sessions: read a transcript, verify
facts, write Turtle, validate. Real, live Oxigraph store at
`http://127.0.0.1:7878`, loaded from `data/seed/*.ttl` via
`scripts/load_oxigraph.sh`.

## Repo structure

```
nate-hagens-kg/
├── docs/               backlog.md (design history/decisions), CLAUDE.md
│                        (ground rules), sidecar-cleanup-handoff.md
├── data/seed/*.ttl      the real source of truth — 31 files
├── data/inferred/       materialized reasoner output — see below,
│                        DELIBERATELY separate from data/seed/
├── tgs_store/            materialized Oxigraph store — derived, gitignored
├── extraction/           the separate episode-scraping pipeline (unrelated
│                        codebase, different concerns — see its own docs)
└── scripts/
    ├── load_oxigraph.sh              loads data/seed/*.ttl into tgs_store
    ├── compute_relationships.py      derives Persona has*Relationship
    │                                 props — ONLY writes personas.ttl
    ├── compute_confidence.py         derives LinkNote calculatedConfidence
    ├── validate_class_purity.py      enforces one-class-per-file, with a
    │                                 real, precise allowlist for 3 known
    │                                 exceptions (see below)
    ├── merge_for_protege.py          combines all seed files into one
    │                                 file for Protégé/HermiT — NOT
    │                                 owl:imports, see reasoning below
    ├── compute_disambiguating_labels.py   rdfs:label for Human vs.
    │                                 Persona individuals (same prefLabel)
    ├── cleanup_misplaced_relationships.py  removes has*Relationship
    │                                 assertions on non-Persona individuals
    │                                 — closes a real gap compute_
    │                                 relationships.py can detect but not
    │                                 fix (see below)
    └── materialize_inferences.py     runs HermiT, writes ONLY inferred
                                       class + property assertions to
                                       data/inferred/ (not data/seed/)
```

## Real gotchas — each one cost real debugging time before being caught

**1. `rdflib.Graph.serialize()` strips hand-authored comments and
`scopeNote`s on round-trip.** Confirmed incident, 2026-07-15, against
`linknotes.ttl`. Every derivation script must use targeted,
literal-protected text surgery instead (`protect_literals`/
`restore_literals`, matching `compute_relationships.py`'s own pattern) —
never parse-modify-reserialize a whole file.

**2. The class-prefix key-mismatch bug bit THREE independently-written
scripts in one session.** `compute_disambiguating_labels.py`, the
`QuadrantNode`-to-`ScenarioFacet` linking code, and
`cleanup_misplaced_relationships.py` all independently made the same
mistake: using an individual's *full* local name (`Human.FritjofCapra`,
including the class prefix) as a dict/set key, while the regex that
finds an individual's block in the TTL text only captures the *short*
name (`FritjofCapra`). Always strip the class prefix explicitly
(`short_name()` helper) before using an individual's name as a lookup
key anywhere near text-surgery code.

**3. Turtle literal escaping**: rdflib's parsed `Literal` value is
*unescaped* (`Clemence "CC" Currie`, not `Clemence \"CC\" Currie`).
Writing that straight into a freshly-constructed Turtle literal without
re-escaping quotes/backslashes produces invalid syntax. Always escape
before building a new literal string by hand.

**4. HermiT (via `owlready2`) doesn't support `xsd:date` or
`xsd:gYear`** — not optional, it crashes the reasoner entirely. Strip
both (literal values AND any `rdfs:range` declarations pointing at
them) before serializing for HermiT. Irrelevant to what's actually being
tested (structural/logical consistency), safe to drop for reasoning
purposes only.

**5. HermiT crashes with "unable to create default IRI base" if the
`.owl` file being loaded sits directly under `/tmp`.** Real, reproducible,
confirmed by testing the identical file from two different directories.
Write reasoner input files anywhere else.

**6. A plain literal (`"CD"`) and an explicit `xsd:string` literal
(`"CD"^^xsd:string`) are the SAME value under RDF semantics but are
NOT equal under `rdflib`'s own `==`/`hash`.** HermiT's re-serialization
adds the explicit type marker even where source Turtle never wrote one
— any diff between pre- and post-reasoning graphs must normalize
literals first, or every already-asserted string property looks like a
fresh "inference."

**7. `merge_for_protege.py`'s output must never land inside the
directory it globs.** If `merged_for_protege.ttl` sits in `data/seed/`
and the script runs again, it picks up its own prior output as an
input — harmless for named-IRI content (rdflib's Graph naturally
deduplicates identical triples) but genuinely doubles any blank-node-
based content (e.g. `owl:AllDifferent` blocks), since every blank-node
parse mints a fresh identity. Fixed: the script now excludes its own
output filename from the glob. Don't reintroduce this by writing output
into `data/seed/`.

**8. `owlready2`'s `world.as_rdflib_graph()` returns a usable
`rdflib.Graph` directly** — don't round-trip it through
`serialize(format="xml")` then reparse. That round-trip can crash on
blank-node IDs that don't satisfy XML's NCName syntax rules, which
HermiT's own output doesn't always respect.

**9. Every new interview's own show notes bio section must be captured
into the guest's Human/Persona entry, not just used to write the
episode's own summary.** Standing instruction from MJSullivan,
2026-09-08. This is easy to skip under time pressure since the episode
build succeeds without it — but the guest bio is often the only real,
direct source for institutional affiliations, prior roles, and
credentials that never come up again in the transcript itself. Verify
the bio section is actually about the named guest before using it: at
least one real show notes file (TGS-233, Roman Yampolskiy) had a
different guest's (Charles Eisenstein's) bio pasted in by mistake in
the source document — a sanity check (does this bio's subject match
the episode's own guest name and topic?) is worth doing before writing
anything into the Human entry, not after.

**10. Confirm the FULL `data/seed/` directory (all ~31 files) has
actually been provided before treating any session's picture of the
schema as complete.** Real, direct incident, 2026-09-10: an entire
session (dozens of episode/concept builds) ran on only 8 of the real
31 seed files — the 8 that happen to get uploaded piecemeal as
individual episode transcripts get processed (concepts, episodes,
humans, organizations, personas, relationships, scenariofacets,
works). Never surfaced as a build error, since Turtle syntax doesn't
require class/property definitions to be present to parse correctly —
it was caught only by accident, when MJSullivan pasted a local shell
script that referenced `../data/seed/*.ttl` and its own output listed
31 filenames. The missing 23 files include real, foundational
material never seen that session: `tgs-core.ttl` (the actual
class/property definitions everything else assumes), `subjects.ttl`,
`enumerations.ttl` (RelationshipType.Academic/Legal/Intellectual,
ProfessionalRole, EpisodeType — real enumerated values that existed
the whole time and were simply never used), `alternatetermtypes.ttl`,
`episodesegments.ttl`, `linknotes.ttl`/`evidences.ttl`/`sources.ttl`
(a whole formal Evidence/Source provenance model, never engaged with
— scopeNote prose was used instead all session), and more. Nothing
built that session was actually broken, but real opportunities were
missed (Concept-to-Persona relationship types like
`thinkr:influencedBy`/`echoesIdeaOf` that existed and went unused;
Organization-side reverse-index relationship properties, widened to
apply beyond Persona back in August, never applied to any Organization
built that session). **Standing practice going forward: at the start
of any new session on this repo, explicitly ask for (or confirm receipt
of) the complete `data/seed/` directory — not just whatever files
happen to arrive with the first task — before doing substantive schema
or content work.** A `seed.zip` of the whole directory is the
practical way to satisfy this in one upload rather than 31 individual
files. Also worth knowing: this same skill file itself was found, on
2026-09-11, to have reverted to an earlier version (missing gotchas 9
and 10, both re-added at that point) — real cause confirmed as a Code
session from several weeks prior that had written its own, different
content here and was never reconciled with later chat-session edits,
not a live concurrent-editing conflict. If a future session finds this
file missing content it expects, check for the same cause before
assuming corruption.

**11. A referential-integrity gate (`check_graph_integrity.py`,
`scripts/`) should run before any commit/PR, checking every S P O
triple for two distinct conditions.** Proposed by MJSullivan,
2026-09-11, directly prompted by a real incident the same day: a
manual pass through 9 genuinely broken cross-references (guessed IRIs
that didn't match what was actually built, one false "already built"
claim sitting in prose) took real, substantial effort to find by hand,
and several were caught only by accident once a full integrity check
was finally run. Two distinct checks, NOT symmetric in severity:
- **Orphans (hard failure, blocks commit)**: an object that's a real
  `tgs:` individual but never appears anywhere as a subject — meaning
  it's referenced but never actually declared. Always a real bug.
- **Stranded entities (informational only, never blocks)**: a subject
  that's a real `tgs:` individual but never appears anywhere as an
  object — meaning nothing else points to it. Often completely fine
  (a freshly-added Concept nobody's cross-referenced yet, or an
  intentional root like Nate himself) — blocking on this would create
  constant false-positive noise, so it's reported for awareness only,
  with a `--strict` flag for anyone who wants it enforced anyway.
Confirmed to work correctly two ways: first run against only 8 of the
31 real seed files falsely flagged 54 "orphans" — the exact gotcha #10
failure mode, not a real bug — confirming the script needs the
complete seed directory to mean anything, same as every other
validation in this repo. Second run, against the complete 32-file set,
correctly returned zero orphans, confirming both that the script works
and that the manual fixes it was built to catch were genuinely
complete.

**12. Having the complete seed directory extracted isn't the same as
having actually looked inside every file in it — check for a file
named after the episode's own real subject matter before assuming
something is unbuilt.** Real, direct incident, 2026-09-13: told
MJSullivan "none of the 27 archetypes were minted" for Frankly-58,
based on that episode's own scopeNote — then built a redundant,
structurally inferior duplicate (a new `thinkr:Archetype` class, a
wrapper Concept, 9 individuals) under the exact same real IRIs already
in use. The real, complete 27-archetype system had been sitting in
`archetypes.ttl` since 2026-08-13 — the same complete seed directory
gotcha #10 already flagged, extracted and available the entire
session, simply never opened. Worse, the real, pre-existing version
was more sophisticated than what got duplicated: it already had
`thinkr:morphsInto` (business-as-usual archetypes to their real
decline-counterparts) and `thinkr:activeInPhase` (all 27 archetypes
linked directly to the already-built `thinkr:ResponsePhase` system).
**Gotcha #10 said "confirm the complete seed has been provided" —
this is the sharper, more specific version: before minting anything
new for a specific episode or topic, check for a seed file whose own
name matches that subject** (`archetypes.ttl` for archetype content,
the same way `subjects.ttl` holds Subject individuals) **— a directory
listing alone doesn't count as having checked; the file has to
actually be opened.** Real, honest note on the fix: removing the
duplicate was straightforward (the added content was clearly
delimited, so it could be cleanly excised), but the deeper fix — a
real, generic way to check "does something like this already exist"
before building anything new — is still open; see the NER/search-
mechanism discussion the same day this gotcha was written.

**That search mechanism now exists**: `scripts/entity_search.sparql`
(built and tested 2026-09-13, same day). Run it — editing the search
term at the top for whatever's about to be built — before minting
anything new, not after. This is the concrete, standing step gotcha
#12 itself was missing when it happened: opening the complete seed
directory once at the start of a session isn't the same as checking
whether a specific thing already exists right before building it.

**13. `episodes.ttl` is deprecated. All TGS content goes in
`episodes-tgs.ttl` — not by convention, by hard requirement, and this
has already been violated once.** Real, direct incident, 2026-09-16:
built a complete new episode (TGS-234, Sarah Wilson — Human, Persona,
Relationship, Concept, and Episode entities) entirely inside the old
`episodes.ttl`, the exact file the 2026-09-12 TGS/RR/Frankly split was
built to retire. The real root cause was pure habit — `episodes.ttl`
is where every episode in this graph's history up to 2026-09-12 lived,
and nothing about the act of appending new content to it felt wrong
in the moment; the split happened in a single session and nothing
about the *filename itself* signals "do not write here" to a future
session (or a future turn in the same session) that isn't holding the
full split history in mind. Caught only because MJSullivan noticed
the file name in what was handed back, not because anything in the
build process itself flagged it. The real fix was mechanical but
required care: the new block had a clean, findable boundary (its own
`##### ADDED 2026-09-16 #####` header), so it could be extracted
byte-for-byte, removed from `episodes.ttl` (confirmed via triple-count
match against the pre-edit state), and re-appended to
`episodes-tgs.ttl` — with a full graph-wide integrity check run
afterward to confirm the relocated entity's own cross-references
(Human/Persona/Relationship/Concept, all built in the same pass) still
resolved correctly once anchored to the right file.
**Standing practice going forward, worth checking explicitly before
the first write of any session that touches episode content:
`episodes.ttl` is read-only, full stop — real content for TGS goes in
`episodes-tgs.ttl`, RR in `episodes-rr.ttl`, Frankly in
`episodes-fr.ttl`, and the animated-video class in
`episodes-animated.ttl`.** If a task ever seems to call for editing
`episodes.ttl` directly, that itself is the signal something is
probably wrong with the plan, not a legitimate use case — the file's
only remaining real purpose is as the historical, byte-for-byte record
of what the graph looked like before the split, and even that framing
assumes it stays frozen exactly as it was on 2026-09-12.

**14. Upgrading a stub to a full build means editing that entity's
own declaration in place, at its correct numerical position — never
appending the new version to the end of the file.** Real, direct
incident, 2026-09-16, immediately following gotcha #13's own fix:
correctly moved a new TGS-230 build into `episodes-tgs.ttl`, but
appended it to the end of the file instead of replacing the existing
stub sitting at its own correct position between TGS-229 and TGS-231
— leaving two real declarations of the same subject in one file, one
a stale stub, one the real build, in the wrong relative order to each
other and to everything else. RDF doesn't error on this (a second
declaration of the same subject just unions in more triples), which
is exactly why it's dangerous — nothing breaks, so nothing forces a
second look. Caught only because MJSullivan was reading the file
directly and noticed the duplicate. **Standing rule, strict
compliance going forward: every episode file stays sorted by episode
number at all times. Updating an existing entity — stub to full
build, or any other real revision — means finding its current
declaration and replacing it there, not writing the new version
somewhere else in the file and dealing with the old one later.**
Before writing anything, check whether the entity already has a
declaration in the target file (`grep -n` for its own real IRI is
enough); if it does, that's where the edit happens, full stop — a
second declaration appearing anywhere else in the file, even
temporarily mid-edit, is the bug this gotcha exists to prevent.

**15. When a Frankly's own spoken transcript and its later companion
Substack essay genuinely disagree on a factual detail, trust the
Substack version.** Standing rule, MJSullivan, 2026-09-16: Frankly
monologues are recorded extemporaneously; the Substack essay comes
later, with real editorial cleanup, and is the more reliable of the
two when they conflict. First, real, direct case: Frankly-156's own
spoken transcript says the majority of dog breeds developed within
"a hundred and fifty years" of the Carbon Pulse; its own companion
Substack essay ('What The Great Simplification Means for Pets') says
"the past 200 years" for the same real claim. 200 years was taken as
the authoritative figure; the spoken variant is kept as a footnote in
the entity's own scopeNote, not asserted as equally reliable. This
doesn't mean the transcript is disposable — it's still the real,
primary source for content the Substack version doesn't cover at all
— only that the Substack wins specifically where the two genuinely
disagree on a fact. Worth checking for a companion Substack essay
(usually linked in the episode's own real show notes, "Essay version
of this Frankly") whenever a Frankly's own numbers feel
worth double-checking, not just when one happens to be provided.

**16. Every real Series individual (`thinkr:Series`) belongs at the
very top of its episode file, grouped with the others already
there — never appended at the end.** Real, direct incident,
2026-09-16: minted `Series.UncomfortableQuestionsForUnsettledTimes`
correctly in content, but appended it at the end of
`episodes-fr.ttl` instead of placing it with the four existing
Series already grouped at the top — directly contradicting that
file's own header comment, which explicitly documents this
convention and the real, deliberate merge-time work (2026-09-12)
that established it. Caught only because MJSullivan gave a direct
standing reminder while handing off the next episode to build. Fixed
by moving the Series block itself (not rewriting it) to sit
immediately after the last of the existing top-grouped Series, and
updating the file's own header comment to name the addition and why
it moved. **Standing rule, no exception: when building or updating
any Series individual, check the target file's own header comment
first — it names where the existing Series sit — and place the new
or edited one there, never wherever happens to be convenient at
write time.**

**17. `dct:references` only goes forward in time — a later work
citing an earlier one — never backward.** Real, direct incident,
2026-09-16: while building Frankly-34 (June 2023), added
`dct:references Frankly-153` because Frankly-153 (2026) usefully
confirmed a real, precise mapping back to Frankly-34's own content
— but Frankly-34 cannot have "referenced" something three years
before it existed. The same mistake had already happened at least
once more in the other direction (Frankly-115 → Frankly-153).
MJSullivan's own real, direct fix, standing as of this gotcha:
**use `dct:isReferencedBy` for the backward case — a later work
citing or extending this one — and reserve `dct:references` for
this episode's own real, direct citations, chronologically valid
only.** Applied retroactively to Frankly-34 specifically (now
`dct:isReferencedBy tgs:Monologue.Frankly_153_WhenTruthBecomesHazardous`);
the handful of other existing reversed instances are left as a
known, documented quirk rather than hunted down and fixed — the
clean convention applies going forward, not retroactively across
everything already built tonight. Before adding any
`dct:references` connecting two episodes, check which one is
chronologically earlier (`dct:created`/`dct:issued`) and put the
property on that one; if the connection only makes sense from the
later episode's own real perspective, it belongs as
`dct:isReferencedBy` on the earlier one instead. **Scope confirmed
2026-09-16, same day, when building Frankly-159: this applies to
every entity a new episode's own `dct:references` list points at,
regardless of type** — not just other episodes. Frankly-159
referenced 17 real episodes and one real Work
(`tgs:Work.BottlenecksOf21stCentury`); all 18 got the matching
`dct:isReferencedBy` back, the Work included, so that any entity
— Interview, Monologue, Work, and presumably Human or Concept too
if a future episode cites one directly that way — can be queried
for which later episodes point back at it, not just episodes
querying each other. When adding real content for a new episode,
walk its own full `dct:references` list afterward and add
`dct:isReferencedBy <this episode>` to every target on it, one
file at a time, validating each file after its own batch — this
is a real, standing step for every new episode build, not a
one-off cleanup.

## Real architectural decisions worth knowing before changing anything

**RDF grid comparison uses precomputed Euclidean lookup
(`thinkr:QuadrantNode`), not live cosine similarity.** This superseded
an earlier, real design (recentering the coordinate system specifically
to make cosine mathematically elegant) — read `backlog.md`'s full
multi-entry thread on this before "fixing" it back. Current scheme:
`hasXPosition`/`hasYPosition` range `0-6`, origin `(0,0)` at the
**lower-left corner** (not centered). `ScenarioFacet` and `QuadrantNode`
share these two properties with NO `rdfs:domain` restriction — a domain
restriction would force every `QuadrantNode` to be incorrectly inferred
as a `ScenarioFacet`.

**`has*Relationship` properties belong ONLY on `thinkr:Persona`
individuals, never on `Organization`/`AcademicInstitution`/
`SchoolOfThought`.** `compute_relationships.py` derives and enforces
this on `personas.ttl` specifically; `cleanup_misplaced_relationships.py`
handles the same rule for the 3 files that script doesn't touch. If a
real Org/Institution/SchoolOfThought relationship needs modeling, it
needs its own real property — don't route it through `has*Relationship`.

**`validate_class_purity.py`'s `KNOWN_MULTI_CLASS_FILES` allowlist is
precise, not permissive.** `episodes.ttl`, `interventionfronts.ttl`, and
`subjects.ttl` are allowed to hold specific, *exact* class sets (each
mapped explicitly in the script) because they're genuine, deliberate
parent-child/family groupings — not a blanket "this file is exempt"
flag. If an allowlisted file's actual classes ever stop matching its
expected set exactly, that's still a real, flagged violation. Verified
directly: a fake foreign class injected into `subjects.ttl` was still
caught correctly before this was trusted.

**Materialized reasoner inferences live in `data/inferred/`, never
`data/seed/`.** Deliberately scoped to only 2 of Protégé's 5 export
categories (inferred class assertions, inferred property assertions) —
the other 3 are either empty for this schema currently or actively
unwanted (equivalent-individual inferences are the exact thing the
`owl:AllDifferent` blocks exist to prevent). Full reasoning in
`backlog.md`.

**`owl:imports` is deliberately NOT used to assemble the multi-file
graph.** `load_oxigraph.sh` already solves this for Oxigraph via a
plain per-file loop; `owl:imports` would only help Protégé, and this
graph's namespace (`http://example.org/tgs#`) isn't a real, resolvable
domain, so reliable import resolution would need extra catalog
infrastructure for no real benefit over the existing merge script.

## Before making any schema change

1. Run `scripts/merge_for_protege.py` to get a fresh combined file.
2. Load it into Protégé or HermiT (via `owlready2`, matching this
   project's established toolchain) — real reasoning, not just a
   parse check.
3. If inconsistent, use Protégé's own "Explain" feature on the
   inconsistency FIRST — it gives a real logical justification,
   dramatically faster than manual bisection (confirmed the hard way:
   an hour of bisection vs. five minutes once the explanation panel
   was actually used).
4. Run `scripts/validate_class_purity.py` — expect exit code 0.
