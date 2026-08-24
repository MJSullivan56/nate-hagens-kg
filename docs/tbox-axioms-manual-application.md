# TBOX Axioms — Ready to Apply by Hand

Each block below: **what it means in plain terms**, **why it's safe to add now**,
the **exact TTL to paste**, and **where**. Everything here was either directly
tested against the real 7,358-triple graph (the functional-property candidates —
confirmed zero violations via direct query) or is purely additive with no way to
conflict with existing data (the `AllDifferent` blocks). Nothing here is a guess.

After adding each block, it's worth re-parsing the file with `rdflib` (or just
watching for a Turtle syntax error in whatever editor you're using) to confirm
nothing broke — a single missing `.` or `;` is the most likely mistake, not
anything conceptual.

---

## Part 1 — Functional properties (in `tgs-core.ttl`)

**Plain meaning**: "functional" means a subject can have *at most one* value
for this property. This is what actually encodes "every Episode has exactly
one host" as a real, checkable rule — right now that's only true as a
sentence in a comment, invisible to any reasoner.

**Why these five, and why now**: all five were directly checked against the
real graph earlier this session — zero subjects currently have more than one
value for any of them. Safe to declare functional; nothing to fix first.

Add each line directly under the property's own existing declaration.

**`hasHost`** — find this in `tgs-core.ttl`:
```turtle
thinkr:hasHost a owl:ObjectProperty ;
```
Change to:
```turtle
thinkr:hasHost a owl:ObjectProperty, owl:FunctionalProperty ;
```

**`hasXPosition`** — find:
```turtle
thinkr:hasXPosition a owl:DatatypeProperty ;
```
Change to:
```turtle
thinkr:hasXPosition a owl:DatatypeProperty, owl:FunctionalProperty ;
```

**`hasYPosition`** — same pattern:
```turtle
thinkr:hasYPosition a owl:DatatypeProperty, owl:FunctionalProperty ;
```

**`hasScenarioDimension`** — find:
```turtle
thinkr:hasScenarioDimension a owl:ObjectProperty ;
```
Change to:
```turtle
thinkr:hasScenarioDimension a owl:ObjectProperty, owl:FunctionalProperty ;
```

**`hasEpisodeType`** — find:
```turtle
thinkr:hasEpisodeType a owl:ObjectProperty ;
```
Change to:
```turtle
thinkr:hasEpisodeType a owl:ObjectProperty, owl:FunctionalProperty ;
```

*(If any of these properties' actual current line looks slightly different
from what's shown above — e.g. has other type declarations already on the
same line — just add `, owl:FunctionalProperty` to whatever's already
there, in the same `a ...` list, rather than replacing the whole line.)*

---

## Part 2 — Distinctness for enumeration values (in `enumerations.ttl`)

**Plain meaning**: without this, a reasoner is not required to treat
`EpisodeType.Interview` and `EpisodeType.Monologue` as different things —
OWL doesn't assume two differently-named individuals are distinct unless
told so. This closes that gap for the four real enumeration families in
the graph.

**Why safe**: purely additive. It can only ever *rule things out*
(two individuals secretly being the same thing) — it can't conflict with
any data that already exists, since nothing in the graph currently asserts
any of these are the same as each other.

Add each block anywhere in `enumerations.ttl` — doesn't matter exactly
where, as long as it's after all four/five/seven individuals it references
are already declared (so simplest: at the very end of the file).

**EpisodeType** (4 real values, confirmed):
```turtle
[] a owl:AllDifferent ;
   owl:distinctMembers ( thinkr:EpisodeType.Interview thinkr:EpisodeType.PanelDiscussion
                          thinkr:EpisodeType.Monologue thinkr:EpisodeType.AnimatedVideo ) .
```

**RelationshipType** (5 real values, confirmed):
```turtle
[] a owl:AllDifferent ;
   owl:distinctMembers ( thinkr:RelationshipType.Professional thinkr:RelationshipType.Personal
                          thinkr:RelationshipType.Academic thinkr:RelationshipType.Legal
                          thinkr:RelationshipType.Intellectual ) .
```

**ProfessionalRole** (7 real values, confirmed):
```turtle
[] a owl:AllDifferent ;
   owl:distinctMembers ( thinkr:ProfessionalRole.Educator thinkr:ProfessionalRole.InstituteExecutive
                          thinkr:ProfessionalRole.Blogger thinkr:ProfessionalRole.Author
                          thinkr:ProfessionalRole.Politician thinkr:ProfessionalRole.Environmentalist
                          thinkr:ProfessionalRole.Physicist ) .
```

**The three closed `oneOf` classes** (`ConfidenceType`, `PolarityType`,
`ReliabilityType`) — worth adding here too, even though they're already
"closed" via `owl:oneOf`. Closing a class's membership list is a *different*
claim than saying its members are pairwise distinct from each other — without
this, nothing technically stops a reasoner from treating two of them as
secretly the same individual:

```turtle
[] a owl:AllDifferent ;
   owl:distinctMembers ( thinkr:ConfidenceType.Curated thinkr:ConfidenceType.Candidate
                          thinkr:ConfidenceType.Corroborated thinkr:ConfidenceType.Disputed ) .

[] a owl:AllDifferent ;
   owl:distinctMembers ( thinkr:PolarityType.Supports thinkr:PolarityType.Contests
                          thinkr:PolarityType.Mentions ) .

[] a owl:AllDifferent ;
   owl:distinctMembers ( thinkr:ReliabilityType.Authoritative thinkr:ReliabilityType.Reputable
                          thinkr:ReliabilityType.Unverified thinkr:ReliabilityType.Unreliable ) .
```

---

## Part 3 — What's deliberately NOT here, and why

**No `owl:disjointWith` between classes yet.** This needs a real, separate
conversation about which classes should actually be mutually exclusive —
e.g., should `Concept` and `ScenarioFacet` be formally disjoint, given they
were deliberately split apart earlier this session precisely because
they're conceptually different things? That's a real modeling decision
worth its own discussion, not something to bundle into a "safe, tested"
batch like this one.

**No `owl:inverseOf` yet.** Real candidates were discussed (`hasGuest` ↔
`appearedInEpisode`, `hasScenarioDimension` ↔ a Dimension-side pointer to
its Facets, `actsThrough` ↔ a Human-side pointer back to Persona) — but
adding an inverse means creating a *new* property that doesn't exist yet,
which is a bigger step than the purely-additive work in Parts 1-2. Worth
its own pass once these are in and confirmed working.

**No new `owl:disjointWith` on `diagonallyDisjointWith` or its siblings.**
Reminder, since it's an easy mistake to reach for later: these properties
represent real logical incompatibility between specific *individuals*
(e.g. `MadMax` vs. `GreenGrowth`), which is a completely different thing
from `owl:disjointWith` between *classes*. Don't conflate the two — the
existing `thinkr:xAxisDivergentFrom`/`yAxisDivergentFrom`/
`diagonallyDisjointWith` design already handles the individual-level case
correctly; there's nothing to add here.

---

## After applying: quick self-check

Once Parts 1 and 2 are pasted in, this Python snippet (run from wherever
`rdflib` is available — including right here in Chat, if you paste the
resulting files back) confirms nothing broke:

```python
import rdflib
g = rdflib.Graph()
g.parse("tgs-core.ttl", format="turtle")
g.parse("enumerations.ttl", format="turtle")
print("Parsed OK —", len(g), "triples")
```

If that runs without an error, the syntax is valid. Real semantic
validation (does HermiT actually accept it, does it still find the
graph consistent once the earlier `ReliabilityTier` fix is also in place)
is worth doing as a follow-up in Chat once these are applied — that's
free to check here, no Code needed.
