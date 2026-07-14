# Sidecar Cleanup — Handoff Doc

**Status: BACKLOG, NOT YET EXECUTED.** Reordered 2026-07-13 into
chronological order, LATEST FIRST, per MJSullivan's request. Section
dates are preserved in each header. Within a single date, sub-ordering
is a best-effort reconstruction from internal cross-references — flag
anything that reads out of order.

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
