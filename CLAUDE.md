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
(the `ConfidenceType`/`ReliabilityType`/`PolarityType` enum members —
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
all construct vocabulary URIs via `TGS["ConfidenceType.Curated"]`-style
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
    `schoolsofthought.ttl`, `organizations.ttl`, `academicinstitutions.ttl`,
    `linknotes.ttl`, `evidences.ttl`, `subjects.ttl`. Small
    supporting/controlled-vocabulary classes (`ConfidenceType`,
    `ReliabilityType`, `PolarityType`) and ALL property declarations
    live together in `tgs-core.ttl` — MJSullivan's framing: `tgs-core.ttl`
    is the direct successor to the old `ontology/schema.ttl`, which can be
    thought of as its rough prototype. Classes with zero instances yet
    (`Work`, `Episode`, `Source`) stay declared in `tgs-core.ttl` until
    their first real instance, at which point they should be promoted to
    their own file. External resource mappings get their own dedicated
    file too (`crosswalknotes.ttl` as of 2026-07-11, replacing separate
    `dbpedia_links.ttl`/`wikidata_links.ttl` — see the CrosswalkNote
    design decision below) — this same
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

0b. **Governance principle (2026-07-11): OWL class depth capped at 2-3
    levels; deeper refinement is SKOS's job, not OWL's; category classes
    end in "Type" or "Kind."** Stated explicitly by MJSullivan after the
    `NamedEntity`/`PersonEntityType` restructure. Concretely: OWL
    `rdfs:subClassOf` chains stay shallow (`NamedEntity` -> `Person` is 2
    levels; `NamedEntityType` -> `PersonEntityType` is 2 levels — both
    compliant as built). If a class needs genuine hierarchical NUANCE
    beyond that depth, the right tool is SKOS `skos:broader`/`narrower`
    between INDIVIDUALS of a category class (exactly how `Subject`
    already works — official subjects and derived sub-topics are both
    `skos:Concept` individuals related via `skos:broader`, not nested OWL
    subclasses) — not deeper OWL subclassing. Refinement per subclass
    happens via a dedicated Categorization pattern (a class ending in
    "Type"/"Kind", paired with a `has*Type` property that's
    `rdfs:subPropertyOf` a more general one) — this is exactly the
    `PersonEntityType`/`hasPersonEntityType` pattern just built, and the
    template for any future subclass's equivalent (e.g. a hypothetical
    `OrganizationEntityType`/`hasOrganizationEntityType`).
    RETROACTIVE NAMING QUESTION, NOT YET ANSWERED: `ConfidenceType`,
    `ReliabilityType`, `PolarityType` predate this rule and don't end
    in "Type"/"Kind." Renaming them would be a large, disruptive job —
    they're referenced throughout every `LinkNote`/`Evidence`/`Source`
    and in `compute_confidence.py`'s core logic. Flagged, not resolved —
    do NOT rename these without an explicit go-ahead, this is a
    meaningfully bigger change than anything done under this rule so far.
    GOOD SIGN, not a fix needed: `thinkr:Subject`'s design already
    followed the "taxonomy belongs in SKOS" half of this principle before
    it was ever stated as a formal rule — worth noting as validation the
    instinct was already right.

0c. **Governance principle (2026-07-11): crosswalk assertions need their
    own provenance — `thinkr:CrosswalkNote`.** A bare `owl:sameAs` triple
    has nowhere to record WHEN it was verified or WHAT caveats apply —
    real problem, not hypothetical: this session hit two cases (Nate
    Hagens' Wikidata entry actually being a different person; Iain
    McGilchrist's name needing correction from what NER extracted) where
    that context mattered and had nowhere structured to live except a
    giant prose comment. Fix: reuse the already-proven `thinkr:LinkNote`
    sidecar pattern rather than invent something new — keep the actual
    `owl:sameAs` triple direct and reasoner-compatible (nesting the
    relationship inside a blank node would have broken its formal
    semantics), and add a separate `thinkr:CrosswalkNote` individual
    referencing the same entity+URI pair via `thinkr:aboutEntity`/
    `thinkr:aboutExternalURI`, carrying `thinkr:crosswalkSource`
    (DBpedia/Wikidata), `thinkr:verifiedOn` (date), and `skos:scopeNote`
    (reused directly, not redeclared — same property already used for
    superclass/superproperty documentation).
    FILE-ORGANIZATION QUESTION RESOLVED AS A SIDE EFFECT: this superseded
    an earlier live discussion about splitting `dbpedia_links.ttl`/
    `wikidata_links.ttl` by SUBJECT class (`PersonCrosswalk.ttl`,
    `SchoolCrosswalk.ttl`, etc.) instead of by TARGET database. Once
    `CrosswalkNote` became a real class with real substantive content
    (not just a bare triple), the natural home was its own single file —
    `crosswalknotes.ttl` — same "one class, one file" reasoning as why
    `linknotes.ttl` bundles its relation triples rather than splitting by
    Concept vs Person vs School. Both `dbpedia_links.ttl` and
    `wikidata_links.ttl` fully dissolved into it, all 37 existing
    `owl:sameAs` triples (32 DBpedia + 5 Wikidata) retrofitted with real
    `CrosswalkNote`s in one scripted pass, tested via a live query
    (Iain McGilchrist's DBpedia+Wikidata crosswalks, both correctly
    surfacing his name-correction scopeNote) before shipping.

0d. **Naming convention, SUPERSEDED then finalized (2026-07-11):
    `Source_Number_TitleFragment`, prefixed by the generic EpisodeType,
    not the source's own branding.** Full pattern:
    `tgs:<EpisodeTypeName>.<SourceAcronym>_<Number>_<TitleFragment>` —
    e.g. `tgs:Interview.TGS_226_CanMoneyServeLife`,
    `tgs:Monologue.TGS_134_AWorldAtTheEdgeOfChange`.
    THREE separate corrections stacked into this final form, each worth
    understanding:
    (1) Original version used `Episode`/`Frankly` as the local-name
    prefix — `Frankly` being TGS's own branding for the Monologue format.
    This directly contradicted the reason `thinkr:EpisodeType` was built
    generic in the first place (TGS-specific terms belong in
    `skos:altLabel` only, e.g. "frankly"/"roundtable" — see the
    EpisodeType section above). Fixed by using the EpisodeType's own name
    (`Interview`/`Monologue`/`PanelDiscussion`) as the prefix instead —
    `thinkr:Episode` stays the actual `rdf:type` regardless; this is
    purely about what the IRI itself looks like.
    (2) MINTING COLLISION RISK, identified same day once it became clear
    other sources (podcasts, vlogs, books, TED talks, PhD theses, etc.)
    will eventually get modeled too: a bare episode NUMBER has no
    uniqueness guarantee across sources — confirmed concretely the same
    session when Matthew Monahan's own show ("The Regeneration Will Be
    Funded") surfaced as a second real source with its own numbering.
    Fixed by requiring a SourceAcronym component (`TGS`, and eventually
    others as they get modeled) — uniqueness comes from
    `SourceAcronym + Number` alone, the title fragment is PURE human
    readability and can be shortened or dropped without breaking
    anything. No GUIDs (every component stays human-mnemonic), but no
    silent collision risk either.
    (3) Source acronyms need to be a genuinely controlled list, not an ad
    hoc string each session invents fresh — currently just documented
    here (`TGS`), not yet backed by a formal registry or tied to real
    `thinkr:Source` individuals. Revisit if/when this actually causes a
    real collision or confusion, not before — same "don't build ahead of
    real need" instinct as everything else tonight.
    Applied retroactively to all 7 existing Episode individuals same
    session (cheap now, would only get more expensive later) — see the
    3-step rename in `episodes.ttl`'s git history if the exact mechanics
    are ever needed again.

0e. **Design decision (2026-07-11): `thinkr:School` split into
    `SchoolOfThought`/`Organization`/`AcademicInstitution`.** Raised by
    MJSullivan as genuinely overloaded, confirmed by checking the actual
    data rather than assuming — all 12 existing `School` individuals
    split cleanly into intellectual movements (7: `Stoicism`,
    `DoughnutEconomics`, `PeakOilMovement`, `BehavioralEconomics`,
    `DegrowthMovement`, `SystemsEcology`, `CivilRightsMovement`) and real
    legal entities (5: `TheOilDrum`, `PostCarbonInstitute`, `MaEarth`,
    `BiomeTrust`, `ConsilienceProject`). Third category,
    `AcademicInstitution`, added on MJSullivan's own concrete test — "an
    Organization might sponsor Nate, an Academic Institution never would"
    — genuinely different relationship verbs, not just a stylistic
    split. First real `AcademicInstitution` instances: University of
    Vermont, University of Chicago, University of Minnesota — previously
    only ever in prose inside `Person.NateHagens`'s own comment, never
    modeled as individuals. All three new classes `rdfs:subClassOf
    thinkr:NamedEntity` (exactly the extension point that class was
    built to support), siblings of each other and of `Person`, NOT
    nested — `AcademicInstitution` under `Organization` would have
    blurred the exact distinction that motivated splitting them.
    `memberOf`'s range widened from `thinkr:School` to a `owl:unionOf`
    the three new classes. Executed as one scripted, verified pass — 32
    cross-file references renamed via text substitution (safe here,
    each old name a distinct non-overlapping string), confirmed zero
    stray references remained, confirmed the `convergesWith` bidirectional
    link (which specifically referenced `DoughnutEconomics`) still
    resolved after the rename, confirmed via live query that the 7/5/3
    split landed exactly as counted beforehand.

0. **Emerging principle (2026-07-11, not yet fully tested): OWL for formal
   relationships, SKOS for informal ones.** Named explicitly by MJSullivan
   after noticing the pattern already forming — `thinkr:Person`/`Concept`/
   `Evidence`/`Source`/`ConfidenceType` etc. are OWL classes with strict,
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
   `tgs:ConfidenceType.Curated` or `tgs:ConfidenceType.Candidate` (see
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
   actively maintained and has its own SPARQL endpoint. 5 of ~26
   people/schools have verified Wikidata links as of 2026-07-11 (EOWilson,
   Marcus Aurelius, Post Carbon Institute, Iain McGilchrist, Daniel
   Schmachtenberger) — see `data/seed/crosswalknotes.ttl` (filter by
   `thinkr:crosswalkSource thinkr:CrosswalkSource.Wikidata`). CRITICAL: Wikidata
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

## Current data state (as of 2026-07-11, post-convergesWith)
- 719 triples total (`make validate` should confirm this exactly)
- 19 Concepts, 21 People (added Kate Raworth), 7 Schools (added Doughnut
  Economics), 15 LinkNotes (14 curated, 1 deliberately-marked candidate as
  a review-queue example), 15 Evidence individuals, 1 Source individual
  (the CalDEC California Doughnut Report — first real use, was empty until
  2026-07-11), 1 Work individual (same report — also first real use), 12
  Subject individuals (6 official + 6 derived sub-topics, all 19 Concepts
  tagged)
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
and `tgs:Source` classes, `tgs:ReliabilityType` (Authoritative/Reputable/
Unverified/Unreliable) and `tgs:PolarityType` (Supports/Contests/Mentions)
enumerations, `ConfidenceType` expanded to 4 values (added Corroborated,
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
cheapest to do while the graph is small (719 triples).

**DONE 2026-07-11 — Cross-tradition "convergent parallel" property.** Built
as `thinkr:convergesWith` (`owl:ObjectProperty, owl:SymmetricProperty`) in
`tgs-core.ttl`. First real use: `tgs:Concept.Overshoot` ↔
`tgs:SchoolOfThought.DoughnutEconomics` (Kate Raworth's framework, applied
regionally by CalDEC — see their CC-BY-licensed 2025 California Doughnut
Report, which independently uses "overshoot" as a technical term). `Work`
and `Source` — both declared since the original schema but empty until now
— got their first real instances and were promoted to their own files
(`works.ttl`, `sources.ttl`) per the one-class-one-file governance
principle. Full Evidence-backed provenance chain built: `LinkNote` →
`Evidence` (Curated, Supports) → `Source` (Authoritative tier, DOI-
registered) → correctly derives `calculatedConfidence: Curated` via
`compute_confidence.py`, tested end-to-end.
CORRECTION CAUGHT DURING BUILD: `owl:SymmetricProperty` is a FORMAL OWL
semantic — it does NOT make the reverse direction queryable without a
reasoner. Verified empirically: querying from `School.DoughnutEconomics`
side returned zero results until the reverse triple was added by hand.
The property's own original comment claimed the opposite ("no need to
assert both directions") — wrong, and corrected in `tgs-core.ttl` once
caught. **Both directions must be explicitly asserted for every future
`convergesWith` use** — this will not be automatic no matter how many
times it's tempting to assume OWL semantics mean SPARQL will "just know."
Case chosen (Stoicism ↔ Bhagavad Gita) was NOT what ended up triggering the
build — CalDEC/Doughnut Economics came up first in practice. Stoicism ↔
Gita remains a good candidate for the second use of this property whenever
it comes up again, same reasoning as originally logged.

**CORRECTION LOGGED 2026-07-10 — blank nodes are NOT the right tool for
either item above.** Blank nodes were briefly proposed for provenance —
this would be a mistake. They have no stable identity across file
re-saves/merges/different-tool-loads, which is exactly why `tgs:LinkNote`
was deliberately built as a NAMED individual in the first place (the
curated/candidate review workflow depends on referencing one specific claim
reliably over time — approve it in DuckDB, promote it, audit it later, diff
it cleanly in git). Blank nodes remain fine for genuinely anonymous
structural scaffolding only — e.g. the existing `owl:oneOf` list inside
`ConfidenceType`'s enumeration, which nothing will ever need to reference
by identity.

**MEDIUM — Source reliability isn't a single fixed scalar (expanded 2026-07-11).**
Three related gaps, all really the same underlying insight — a Source's
standing isn't one static number, it varies by domain, by time, and by
relationship to the specific subject:
  1. DOMAIN-SCOPED (original note): one fixed `ReliabilityType` per
     `Source` doesn't fit real epistemics — Hagens is plausibly `Reputable`
     generally but arguably `Authoritative` on his own stated influences;
     Richardson would plausibly be `Authoritative` specifically on
     American political history.
  2. TEMPORAL DECAY: `prov:wasRevisionOf` already handles explicit
     supersession (built and tested — the Neanderthal-taxonomy case), but
     evidence that's simply OLD, with nothing specifically superseding it,
     currently counts identically to evidence from yesterday. Recency
     itself should matter, not just explicit supersession. Source standing
     can also change over time independent of any specific claim (a
     source assessed as Authoritative in 2010 might not hold that
     assessment in 2026).
  3. SOURCE-SUBJECT BIAS: distinct from both of the above and from
     `PolarityType` — a Source can be reliable in general while having
     a demonstrated, patterned bias toward one SPECIFIC subject.
     Concrete example given: if a source has repeatedly, demonstrably
     shown antagonism specifically toward Nate Hagens, that source's
     negative claims ABOUT Hagens specifically warrant discount (or
     inversion — "it should inflate them, but that's another story" — a
     real, separate future consideration, not resolved here) — without
     blanket-downgrading that same source's reliability on unrelated
     subjects, which a flat `ReliabilityType.Unreliable` on the Source
     would incorrectly do. This is a Source-Subject RELATIONSHIP, not a
     property of either alone.
     IMPORTANT DISTINCTION FROM THE CONTRIBUTOR/MENTION DESIGN: this is
     NOT asking the system to detect stance from text (that's the hard
     NLP problem already deliberately avoided in the Contributor rule).
     This is recording a stance a HUMAN has already determined — a
     genuinely more tractable problem, just not yet designed.
ALL THREE deliberately deferred, consistently, same reasoning each time:
exactly ONE `Source` individual exists in the entire graph as of this
writing, and zero real multi-period or biased-relationship examples to
design any of these mechanisms against. Designing blind risks guessing the
shape instead of discovering it — same trap the Concept-evolution-over-time
item and the OWL/SKOS "let's see what the data tells us" principle were
both meant to avoid. Revisit once real Source data with an actual
multi-period or biased-relationship case exists.
CONSTRAINT TO HOLD FIRM ON WHENEVER THIS IS BUILT: stays ORDINAL, not
numeric — this project has repeatedly and explicitly rejected manufactured-
precision scoring (see e.g. the confidence aggregation rule's own
reasoning). A weighted numeric decay formula would be a real regression,
not an enhancement, however tempting it looks on paper.

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

**MEDIUM — Social/professional graph layer ("who knows who").** Proposed
2026-07-11: a parallel layer tracking real-world professional/social
connections between people in the TGS/Doughnut world — starting with
everyone Nate Hagens has had on the show or mentioned. SCOPE NARROWED same
day: not full employment history — specifically publications contributed
to and credentials relevant to TGS/Doughnut Economics. This actually needs
little new schema: `thinkr:Work` already exists (see `works.ttl`, first
real instance already built for the CalDEC report) and Dublin Core's
`dct:creator`/`dct:contributor` already cover "who contributed to this
publication" — pure reuse, no new classes needed for that half. Credentials
specifically still needs a real example before designing the property
("Policy Lead, CalDEC" vs "PhD Ecological Economics" probably want
different shapes) — same "let's see what the data tells us" principle as
the OWL/SKOS split, not designed in the abstract.
LINKEDIN, RESOLVED: manual login-and-screenshot is fine, meaningfully
different from automated scraping (which remains off-limits per LinkedIn's
ToS). Most published authors have CVs elsewhere too, so LinkedIn ends up
being one manual source among several, not the sole one. Privacy judgment
call is about what gets PUBLISHED in the graph, not how it was gathered —
still worth per-person consideration for non-public-figure guests even
though the collection method itself is now clean.
CLASSIFICATION RULE RESOLVED 2026-07-11: Contributor IFF their publications
align with the TGS/Doughnut movement; otherwise, just a "mention." Cleaner
than the ally/critic axis first proposed — sidesteps sentiment/stance
detection entirely (a hard NLP problem, not worth bolting onto the rough
`extraction/index_named_entities.py` triage tool) by grounding the
classification in something objective and already-scoped: does this
Person have a `thinkr:Work` (via `dct:creator`/`dct:contributor`) that
actually aligns? Elon Musk correctly falls out as "mention" — no aligned
publications, no stance-detection needed. Also correctly handles the
mirror case (someone with publications explicitly ARGUING AGAINST
degrowth/limits thinking) without a separate "critic" category — they
simply don't qualify as Contributor either.
OPEN WORLD ASSUMPTION CORRECTION, same day: the rule as first stated is a
CLOSED-world rule and would be wrong if implemented literally in RDF —
absence of a Work in the graph doesn't mean absence of one in reality, it
might just mean it hasn't been catalogued yet. Fix, reusing a pattern
already proven elsewhere in this project (`ConfidenceType.Candidate` as
an epistemic floor state, not a confirmed negative — same shape as
`Disputed` needing to be an ACTIVE assertion, not a default): `Contributor`
must be a positively-asserted status, made true only when a qualifying
`Work` is actually confirmed. "Mention" is NOT a status to assert at
all — it's just the absence of a `Contributor` assertion. Anyone with a
`Person` individual lacking that assertion is honestly "not yet
established as Contributor," freely upgradable the moment a real
publication surfaces, rather than a claim that would ever need retracting.
Known, accepted consequence of the underlying rule (unaffected by the OWA
fix): a genuine personal/professional connection with no aligned
publications (a collaborator, an activist without formal writing) also
never gets a `Contributor` assertion — consistent with narrowing this
layer to publications-and-credentials rather than broader social
proximity.
THIRD STATUS ADDED 2026-07-11: `InvitedGuest`, proposed for people Nate has
personally had on the show who may lack a citable aligned publication (a
guest with no formal CV is unlikely but possible). Fits the same
positively-asserted, OWA-safe pattern as `Contributor` — NOT a rung between
Contributor and Mention on a ladder, an independent fact with its own
evidence. Not mutually exclusive with Contributor — someone can hold both.
Precision worth keeping: WHETHER someone was a specific episode's featured
guest is objectively checkable (in `download_manifest.csv`'s episode
metadata) and can be Authoritative-tier reliable; the SIGNIFICANCE of being
invited is Nate's own editorial judgment, which the graph can report as a
fact about his selection process but can't itself verify — same
reliability/significance split the ReliabilityType/PolarityType model
already handles elsewhere.
PRACTICAL SHORTCUT: likely mostly derivable from data already downloaded,
not new manual research — every `type=interview` episode's title in
`download_manifest.csv` typically has the guest's name baked in
(`224-rob-hopkins`, `226-matthew-monahan`). Frankly episodes (solo) don't
apply; this is an interview/roundtable-type signal specifically.
Still open: does this deserve its own file/data layer, given it's a
different research question than the idea-linking work? Not started —
logged for discussion, not build-ready yet.

**MEDIUM — Sidecar naming/structure cleanup.** Proposed 2026-07-11 by
MJSullivan. Full details, worked examples, and — critically — the real
open questions NOT yet resolved, in `docs/sidecar-cleanup-handoff.md`.
Confirmed conventions: underscore between the two cross-referenced
entities, person/org always first, drop the "Note" suffix from class
names, stop using "Crosswalk" terminology (reserve it for a genuine
future cross-ontology alignment concept). NOT confirmed, needs real
decisions before execution: whether `hasSubject`/`hasObject`/
`hasRelationshipType` describes a renamed `LinkNote` or an actual
merge of `LinkNote`+`Evidence`; whether `hasRelationshipType` replaces
the current multiple-specific-relation-properties design
(`echoesIdeaOf`/`influencedBy`/etc.) with one generic property + type
value (a real architectural change, not just a rename); the exact
replacement names for `LinkNote`, `CrosswalkNote`, and the not-yet-built
`AffiliationNote`. Scope: 67 individuals across `linknotes.ttl` (15),
`evidences.ttl` (15), `crosswalknotes.ttl` (37) as of this writing.
Execute the same way as every other large rename this session — scripted
and verified, not manual — once the open questions are actually settled.
ESCALATED same day: `Subject_Object` naming assumes at most one
relationship-instance per entity pair, which is often false (Aristotle
may have discussed money in multiple works; Nate's UMN affiliation may
be multiple distinct periods/roles, not one continuous thing). Genuinely
harder than the naming cleanup above — no comprehensive solution yet per
MJSullivan's own assessment. Full candidate directions in the handoff
doc's own "ESCALATION" section. Do not resolve in the abstract — wait
for a real case needing it and design against that.
ALSO RESOLVED same day, fold into the same rework: drop the direct
`owl:sameAs` triple on CrosswalkNote-linked entities entirely, rely
solely on `aboutExternalURI` — `owl:sameAs` formally implies full
bidirectional property inheritance under a reasoner (the well-known
"sameAs problem"), not something actually meant here; `skos:exactMatch`
considered and rejected as formally Concept-scoped. See handoff doc's
"4b" for full reasoning.
CRITICAL CAVEAT, MJSullivan's own words: "not 'seeing' how real data
should look while leveraging the pattern developed... need a concrete
set of inter-related examples to finally 'get it'. At the moment, I
don't." The handoff doc's isolated before/after examples, discussed one
at a time, have NOT achieved actual clarity — a genuinely narrative,
multi-sidecar worked example (ideally confronting the multi-instance
problem with real values, not placeholders) is still needed before this
document should be treated as execution-ready. See the doc's own CAVEAT
section, placed prominently at the top for exactly this reason.

**MEDIUM — Wikidata verification.** ~21 of ~26 people/schools still need
verified Wikidata `owl:sameAs` links (pattern established in
`data/seed/crosswalknotes.ttl`, just needs the per-entity verification
legwork — see design decision #5 above; Q-numbers are NOT mnemonic and
guessing from memory is genuinely risky).

**MEDIUM — Primary-source verification.** Concept/School definitions are
first-draft paraphrases (design decision #6), never checked against actual
Hagens transcripts/book text. Not urgent, but a real accuracy gap.

**DONE 2026-07-11 — `tgs:Episode` now has real instances.** 7 total, all
`EpisodeType.Interview` so far, promoted to `episodes.ttl` — see the
naming-convention section above for the full minting-scheme story. Trigger
was making explicit how bootstrapped guests relate to `Person.NateHagens`
directly (`dct:creator`/`dct:contributor`), not left implicit via
`PersonEntityType.Guest` alone. `Monologue`-type (Frankly) and
`PanelDiscussion`-type (Reality Roundtable) instances still don't exist —
same "no concrete trigger yet" status as before, just narrower in scope
now that Interview-type is resolved.

**LOW — `tgs:memberOf` consistency question.** Doesn't chain up to
`tgs:relatesTo` the way the concept-to-person properties do
(`echoesIdeaOf`, `influencedBy`, etc. all do). Flagged once, never
resolved either way — low stakes, revisit whenever convenient.

**LOW — `foaf:firstName`/`foaf:family_name` deliberately deferred.** Proposed
2026-07-11 during Person bootstrapping — deferred, not rejected. Vocabulary
already available for free (Person already subclasses foaf:Person), so
this costs nothing structurally whenever it's actually needed. NOT added
now because "obvious" breaks down fast on people already in the graph:
Marcus Aurelius (Roman praenomen/nomen, not modern first/last), William R.
Catton Jr. (suffix breaks a clean split), Aristotle (single name, no split
exists), Nate Hagens (is "Nate" the name to record, or "Nathan" with Nate
as how he's known — a judgment call, not a mechanical split). Adding it
now only for easy modern names would create inconsistent coverage that
looks like an oversight, not a deliberate choice. Trigger for actually
building it: a real downstream need (sortable/alphabetized browse view,
name-based dedup — which would also need to solve the "Nate" vs "Nate
Hagens" alias problem already flagged from the entity index).

**LOW — LLM extraction plan never run for real.** `extraction/README.md`'s
aspirational Steps 3-6 (LLM concept/link mining, distinct from the
transcript-download and entity-triage infrastructure documented in the
same file, which IS built and working) has only been tested end-to-end
with fake staging data to confirm the DuckDB→promote_to_rdf.py→graph
pipeline mechanically works — never run against actual transcripts yet.

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

REUSABILITY GOAL RESTATED 2026-07-11, worth keeping visible: this
methodology should generalize beyond Hagens (the original thinkr:/tgs:
namespace split was specifically for this — see the "Reusable methodology"
section near the top of this file), and it should stay HUMAN-IN-THE-LOOP —
not a fully-automated pipeline. Every real verification step this session
(search before trusting memory, check a hit is actually the right entity
before linking it, distinguish "confirmed absent" from "not yet checked")
was a human-guided judgment call, not something safe to fully automate.

FIRST-DRAFT "BOOTSTRAP A NEW PERSON" PROCEDURE, extracted 2026-07-11 from
actually doing this for real (Nate Hagens himself — see persons.ttl,
schools.ttl). Not yet a formal Skill, just the pattern worth generalizing
once there's a second real example (ideally a genuinely different
person/context) to test it against:
  1. Search to confirm real, verifiable identity and key affiliations —
     never from memory alone, this project's rule throughout.
  2. Check for a genuine Wikipedia page — verify it's actually THIS
     person, not a same-named different individual (hit exactly this trap
     today: the only Wikidata match for "Nate Hagens" was an unrelated
     ORCID researcher) or a non-canonical mirror site (EverybodyWiki is
     not Wikipedia, hit this today too).
  3. If real: get DBpedia URI (mirrors the Wikipedia title) AND
     separately verify the Wikidata QID directly — don't assume, check
     for disambiguation-page traps (the earlier Marcus Aurelius case).
  4. If NO real Wikipedia page exists: say so explicitly in the
     individual's own definition/comment, don't just silently omit the
     link — a future session needs to know "checked, confirmed absent"
     versus "nobody got around to checking yet," these are different
     states worth distinguishing (same epistemic-honesty principle as the
     Contributor/Mention OWA fix).
  5. Identify key affiliations (organizations, schools of thought) and
     verify EACH ONE'S own legitimacy before creating it as a School —
     don't inherit unverified trust from the person onto their affiliations.
  6. Add `memberOf` links connecting the Person to each verified
     affiliation.
  7. Add credentials per the established scope (publications/credentials,
     not full employment history — see the social graph backlog item).
  8. Test: run a real query confirming every new link actually resolves
     before considering the bootstrap done — not just "the file parses."

## Ground rules for changes in this repo
- **Never point a `tgs:LinkNote`'s `tgs:confidence` at
  `tgs:ConfidenceType.Curated` without a human having actually reviewed
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
  `data/seed/persons.ttl`/`schoolsofthought.ttl` for examples).
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

- **`owl:SymmetricProperty` does NOT make the reverse direction queryable
  without a reasoner.** Built `thinkr:convergesWith` as formally symmetric
  and wrote a comment claiming "no need to assert both directions" —
  wrong. Plain SPARQL triple matching (what this project's tooling
  actually uses, no reasoner in the loop) only finds what's literally
  asserted. Caught by testing the reverse-direction query and getting
  zero results despite the forward triple being present. Fixed by adding
  the reverse triple explicitly and correcting the property's own
  comment. Any future symmetric property needs BOTH directions asserted
  as real triples, full stop — this is the same underlying lesson as
  always explicitly typing `owl:NamedIndividual` instead of relying on
  `rdfs:subClassOf` inference, just a different OWL feature tripping the
  same wire.

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
  URIs embedded in Python code** (`TGS["ConfidenceType.Curated"]`-style
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
make validate         # parse-check every .ttl file (expect 719 triples)
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
