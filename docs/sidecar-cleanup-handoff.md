# Sidecar Cleanup — Handoff Doc

**Status: BACKLOG, NOT YET EXECUTED — AND NOT YET SUFFICIENT AS
DOCUMENTATION EITHER.** See the caveat immediately below before treating
anything in this document as settled or ready to build from.

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
