# Backlog — nate-hagens-kg

Real ideas explicitly NOT being worked on yet, captured so they don't
get lost between sessions. This file is git-versioned specifically so
backlog items have their own visible history (added, refined, resolved)
separate from `docs/sidecar-cleanup-handoff.md`'s session-by-session
narrative.

**Convention: APPEND-ONLY, matching the handoff doc's own discipline.**
An item's status changes get noted INLINE, directly under the item —
never delete or silently rewrite existing text. When an item moves from
backlog into active work, leave it here with a `RESOLVED`/`IN PROGRESS`
marker and a pointer to the relevant `sidecar-cleanup-handoff.md` entry,
rather than removing it — the git history plus the inline marker
together tell the full story of an idea's lifecycle.

**Split out of `sidecar-cleanup-handoff.md` on 2026-08-13** — the 4
items below existed there first; moved here directly, content
unchanged, so `git log` on this file starts clean from that point
forward.

---


**GUI / public product roadmap (raised 2026-07-14).** End goal
confirmed: a real public-facing product ("my contribution to the world
of TGS"), not just a personal research tool — but explicitly PHASED,
timeline confirmed as "many months away," and Nate's approval is a
confirmed hard requirement before anything goes public (his brand/IP,
built entirely from his show's content — this should mean reaching out
to him or his team BEFORE launch, not after it's already public).
MJSullivan is the sole beta user for the foreseeable near term — build
accordingly, don't over-invest in public-launch infrastructure yet.

Two explicit phases, don't blur them:
- PHASE 1 (now, sole-beta-user): local tool, hits Oxigraph directly at
  127.0.0.1:7878, same trust model as everything else currently in this
  project. No API layer, no auth, no SPARQL-hiding needed yet — that's
  real, but premature, work for later.
- PHASE 2 (public launch, months out, gated on Nate's approval): SPARQL
  can NOT be exposed directly to a public audience (DoS/cost vector, no
  query-level auth) — needs a real API layer in front of Oxigraph, a
  curated set of endpoints, not raw passthrough. Confidence-tier
  visual distinction (Candidate vs. Curated) goes from nice-to-have to
  necessary — an unreviewed Candidate claim read by a stranger as
  established fact about a real person is a real liability, not just an
  epistemic nicety. Privacy posture needs to be MORE conservative for
  public-facing profiles than for the working graph — a podcast guest
  consenting to a recorded conversation is different from, e.g., a
  Discord community member surfaced via the social-media discovery idea
  above; not everyone bootstrapped into the graph should necessarily
  get a public page.

Proposed views, once GUI work actually starts (Phase 1):
- Encyclopedic view (per-entity page, all triples where the entity is
  subject/object) — likely the highest-value FIRST view: most legible
  entry point for the eventual students/casual-users audience from the
  gamification idea above, and matches MJSullivan's own stated
  editorial/flattened-entity-view preference from the sibling UWOM
  project.
- Concept graph view — natural fit for the actual RDF shape
  (influencedBy/echoesIdeaOf/contrastsWith/convergesWith as edges).
  Confidence tier should be visually distinct from day one, not
  retrofitted later.
- Social graph view — fully supported by today's Relationship/
  subjectRole/objectRole work already, but payoff scales with the
  person-bootstrap queue — not very interesting yet at 27 Personas,
  sequence behind bootstrapping, not ahead of it.
- Confidence/evidence-transparency view (4th view, not in MJSullivan's
  original list) — click any claim, see its LinkNote->Evidence->Source
  chain. Real potential point of differentiation from a typical wiki,
  not just a debug tool, given how much of this project's actual value
  is "here's how we know this and how confident we are."

Real prior art worth reviewing before designing any of this fresh: the
sibling UWOM project already has a working `browse.html` GUI
(`visualize_subgraph.py`, PyVis/vis.js) — interactive graph viz, hidden
bidirectional peer edges, physics tuned per hop-count, a client-side
color palette as single source of truth, L2 domain subdivisions for
oversized groups. Same underlying problems (dense graphs get
unreadable past a node-count threshold, physics defaults don't scale)
will recur here — worth knowing what worked/needed fixing there first.

**Architectural input from MJSullivan (2026-07-14): much of that other
interface is driven by static JSON-LD with lightweight presentation
wrappers, NOT live queries against a running triplestore.** This
significantly simplifies the Phase 2 security posture noted above — a
static JSON-LD export has no live SPARQL surface to attack at all, so
the "needs an API layer with auth in front of Oxigraph" concern mostly
evaporates if the public interface works this way instead. Concrete
implications, none yet built:
- Needs a real, repeatable export/build step (Oxigraph -> static
  JSON-LD snapshot) — does NOT exist yet; `load_oxigraph.sh` only goes
  the other direction (.ttl -> live store). Given how fast this graph
  is currently changing, this should be scripted from day one, not done
  by hand.
- Gives a clean, concrete enforcement mechanism for the
  Candidate-vs-Curated concern above: the export step itself can
  exclude/flag non-Curated LinkNotes, which is a stronger guarantee
  than relying on frontend styling alone (can't be bypassed by a UI
  bug).
- A JSON-LD `@context` document (mapping thinkr:/tgs: URIs to
  consumption-friendly terms) is real, undone design work, not
  something that falls out for free.
- DECIDED (2026-07-14): assume the PATTERNS are reusable (the overall
  static-export-plus-thin-wrapper architecture, the general shape of
  going from a live triplestore to a JSON-LD snapshot, presentation
  conventions), NOT the code itself — UWOM's export logic is written
  around units-of-measure classes with no overlap with this project's
  Persona/Concept/LinkNote structure, so a fresh build for this
  project's own classes is the right expectation, following UWOM's
  proven approach rather than inventing the pattern from scratch.

**Action-item "gamified knowledge" layer (raised 2026-07-14).**
MJSullivan's idea: as a user encounters a `Concept` via some future
interface, surface a list of concrete, checkable real-world actions
related to it (local/state/national), with progress tracking and
awards — making the graph's content accessible to students/casual
users who won't engage with the full intellectual content directly.

Real design forks discussed, not yet decided:
- This is a DIFFERENT epistemic character than everything else in the
  graph — descriptive/verifiable (Evidence, Candidate->Curated) vs.
  prescriptive (no citation makes "you should do this" true or false).
  Leaning toward a genuinely separate namespace/layer (maybe even a
  separate store), bridged to Concept via something like the existing
  `thinkr:convergesWith` pattern, rather than folding it into `thinkr:`
  proper alongside LinkNote/Evidence.
- Content-ops burden is real and different: local specifics (phone
  numbers, org contact info, program status) rot fast, unlike anything
  else in this graph so far. Leaning toward NOT trying to be the
  source of truth for hyper-local facts — model durable action
  TEMPLATES ("find your nearest X via [org]'s own directory") that
  point outward at organizations who already own that freshness
  problem, rather than storing the volatile specifics directly.
- Gamification itself: real, not just a footnote — extrinsic
  rewards (points/badges) can crowd out intrinsic motivation, and this
  project has been deliberately non-trivializing about the underlying
  ideas throughout. Whatever gets built should be intentional about
  what the points actually reinforce, not just "engagement for its own
  sake."
- Proposed rough shape if/when this gets built: an `ActionItem` class
  in its OWN namespace (e.g. `civic:`, not `thinkr:`), a
  `relatesToConcept` bridge back to `Concept`, a scope/specificity
  level (local/state/national — different verification burdens), a
  freshness timestamp forcing periodic re-verification. Actual
  gamification STATE (who's checked what, point totals) is user-account
  application data, not knowledge-graph content — belongs in a separate
  app database referencing ActionItems by ID, not inside the graph
  itself.
- Genuinely undecided: whether this becomes its own project reading off
  `nate-hagens-kg`, or an extension folded into it.

**Discovery channel: boots-on-the-ground organizations implementing
these concepts, not necessarily connected to/influenced by Nate at all
(raised 2026-07-14).** MJSullivan's framing: there must be hundreds of
real organizations independently practicing what a given Concept
describes (community land trusts for CircleOfTrustLocalism/localism,
Transition Towns for de-growth-adjacent resilience work, etc.) — a
different, complementary discovery channel from mining Nate's own
content.
- Fits the EXISTING schema close to for free: `Organization`/
  `SchoolOfThought`/`AcademicInstitution` already exist as classes, and
  `thinkr:convergesWith` is ALREADY defined for exactly this epistemic
  shape ("independently converges on a similar idea, no claim of direct
  influence") — likely just needs new individuals, not new schema.
- Obvious non-cold-start starting point: Post Carbon Institute
  (already `Organization.PostCarbonInstitute`, already linked to Nate)
  runs/ran resilience.org, which has historically cataloged exactly
  this kind of local-initiative network — check this first before
  researching from scratch.
- Real candidate movements with their own existing directories (so the
  graph never has to own hyper-local freshness): Transition Network,
  TimeBanks.org, Repair Café Foundation, Grounded Solutions Network,
  solidarity-economy/mutual-aid networks.
- Same "search, verify, don't inherit unverified trust" discipline as
  person-bootstrapping applies here too, just applied to organizations
  — confirm real/active/legitimately-connected before modeling, same
  wrong-person-trap instinct.
- Undecided: research broadly (many movement-types, each thin) vs.
  deeply (pilot 2-3 movements end-to-end first) — same fork as the
  person-bootstrap queue, likely same answer (pilot first).

**Discovery channel: Nate's social media presence — TikTok, LinkedIn,
Twitter/X, Substack, Instagram, Discord (raised 2026-07-14).**
Scrapers reportedly exist for each; NOT yet evaluated individually, and
they are NOT one uniform bucket — each platform is a genuinely
different problem:
- Substack is the strong lead candidate — `extraction/` already has
  `substack_summaries_raw/`, `substack_text_cache/`, and
  `match_substack_summaries.py` (built for a different original
  purpose, matching Substack summaries against episode transcripts, but
  structurally close to what mining his own long-form writing for
  entities/concepts would need). Closest thing to "another transcript,"
  most naturally continuous with the existing, proven pipeline.
- LinkedIn and Twitter/X both explicitly prohibit scraping in their ToS
  — LinkedIn has pursued real litigation over this (hiQ v. LinkedIn is
  the well-known case). Worth confirming current legal/ToS status
  before building anything, not after.
- Discord flagged as a DIFFERENT kind of concern, not just legal: a
  privacy-posture question, not a ToS one. Everything mined so far
  (podcast transcripts, presumably Substack) involves public figures
  who consented to a recorded, published conversation. A Discord
  community — even publicly joinable — is casual conversation with a
  very different expectation of privacy/permanence. Cataloguing
  individual community members by name from chat logs would be a real
  departure from this project's practice so far, worth deciding
  deliberately rather than backing into because a scraper exists.
- TikTok/Instagram: primarily short-form video/engagement metrics —
  would likely need video transcription (a new pipeline stage, not a
  small extension of the existing text-based one) to be useful for
  entity/concept extraction at all.
- The wrong-person-trap discipline from the bootstrap procedure needs
  to get STRICTER here, not stay the same — a podcast guest credit is
  close to unambiguous; a social handle is not (impersonation accounts,
  common-name collisions, pseudonymous handles are the norm on every
  one of these platforms, not the exception).


**`data/seed/relationships/` subfolder (raised 2026-08-13).**
MJSullivan's observation: the "connective tissue" layer — currently 4
separate files, each already obeying one-class-one-file
(`relationships.ttl`, `linknotes.ttl`, `evidences.ttl`,
`crosswalknotes.ttl`) — is going to become the LARGEST section of this
ontology by volume as person-bootstrapping and concept-mining scale up,
given every real relationship/citation/lineage claim needs its own
`Relationship`, `LinkNote`+`Evidence`, or `CrosswalkNote` individual.
Grouping these related files under their own subfolder rather than
leaving them flat alongside dozens of unrelated class files in
`data/seed/` would keep the directory navigable as this grows.

Important: this is PURELY a directory-organization question — grouping
existing, already-correct files into a subfolder — NOT a proposal to
merge or restructure the classes themselves. Explicitly NOT the same
question as the abandoned 2026-07-11 `LinkNote`/`Evidence`/`Relationship`
merge design (see the SUPERSEDED marker in
`sidecar-cleanup-handoff.md`) — worth keeping these two ideas clearly
separate given how easily they could get conflated by a future reader,
since they sound adjacent but are unrelated: one is about where files
live on disk, the other was about whether the classes themselves should
combine.

Real technical dependencies this would trigger, not yet actioned:
- `scripts/load_oxigraph.sh`'s file discovery (`../data/seed/*.ttl`) is
  NOT recursive — would silently stop loading these 4 files the moment
  they moved into a subfolder, with no error, just quietly-missing data
  (the exact "looked successful, wasn't" failure mode from the
  `tgs_store` loading saga a few sessions back). Needs either a
  recursive glob (`**/*.ttl` with `globstar` enabled) or an explicit
  second loop over the subfolder.
- `scripts/validate_class_purity.py`'s `Path.glob("*.ttl")` has the
  same non-recursive limitation — would need `rglob` instead, or an
  explicit walk, to keep checking files inside the new subfolder.
- Whether `alternatetermtypes.ttl` belongs in this new folder too (it's
  Concept-adjacent connective tissue, arguably relationship-shaped, but
  is a `Category` enumeration rather than a relationship RECORD) is a
  real judgment call for whoever executes this, not decided here.

**Not urgent** — worth doing once volume actually justifies it (matching
this project's standing "don't reorganize ahead of real need" instinct),
not preemptively. A natural trigger point: whenever the person-bootstrap
queue resumes at real scale and these 4 files start actually feeling
unwieldy in the flat directory, not before.

**Externality pricing for Scenario/EarthSystems/Doughnut indicators
(raised 2026-08-13).** MJSullivan's framing: eventually put a real
monetary value on the externalities this graph currently represents
biophysically (climate stress, biosphere health, the 42 Doughnut
indicators, etc.), on the premise that money is the register most
people actually respond to.

Real economic frameworks this would draw from, not invent from scratch:
"social cost of carbon" (used in actual policy), natural capital
accounting, and ecosystem-services valuation (Costanza et al.'s 1997
attempt to price the entire biosphere's services is the classic,
still-debated reference point).

Worth taking seriously as a genuinely CONTESTED methodological choice,
not a settled one, if this ever gets built — the tension: pricing a
functioning biosphere implicitly treats it as tradeable against other
dollar amounts, which can undercut the argument that some things aren't
actually substitutable at any price. This is a live disagreement within
ecological economics itself, not a fringe objection — the graph should
probably represent that tension rather than silently pick a side.

Real, already-existing precedent worth reconciling with: the CalDEC
Doughnut taxonomy already in this graph (indicatorcategories.ttl/
indicators.ttl) deliberately does NOT monetize most of its 42
indicators — Ecological Footprint, Ozone Layer, At-Risk Species are all
biophysical, not dollar figures.

DECIDED 2026-08-13, per MJSullivan: PARALLEL, not replacement — the
monetary layer sits ALONGSIDE the biophysical framing, never instead of
it, because the audiences are genuinely different (some people respond
to "ecological footprint acres," others to "$47B in externalized
costs") and neither framing is simply "more correct" than the other.
Same underlying move already proven in this graph's own
thinkr:AlternateTerm mechanism — EROI/"Energy Return on Investment"
coexist as parallel, typed, audience-dependent framings of the same
referent, rather than one being demoted in favor of the other. A
monetary valuation next to a biophysical measure is structurally the
same idea, just applied to values instead of names.

Practical schema question for whenever this is picked up: a bare new
property (e.g. thinkr:hasEstimatedExternalityCost) is NOT enough on its
own, for two compounding reasons — (1) it needs to coexist with the
biophysical measure, per the parallel-not-replacement decision above,
and (2) "none of these have simple answers" cuts deeper than just
biophysical-vs-monetary: different PRICING methodologies (social cost
of carbon vs. ecosystem-services accounting vs. others) can produce
genuinely different dollar figures for the SAME indicator, so even
within the monetary layer a single bare number would be dishonest.
Likely needs the same Evidence/LinkNote-style separation between "the
claim" and "the sourced methodology behind the claim" already used
elsewhere in this graph — possibly multiple coexisting valuations per
indicator, not one.

**Not urgent, not scoped** — captured here so the idea isn't lost,
matching every other backlog item's "don't build ahead of real need"
treatment.

**"Through Nate's Glasses" iPhone app (raised 2026-08-18).** MJSullivan's
idea, arrived at in a dream: an iPhone app that takes a news article
(via share extension — Apple News has no public API for reading
content or injecting actions into it directly, so "point at an
article inside Apple News" isn't achievable as originally imagined)
and explains how its topic aligns on the TGS scenario axes, backed by
links to substantiating articles/podcasts/papers, plus a concrete
per-article action item (call your senator, attend a local board
meeting, etc.). Proposed name: "Through Nate's Glasses — how to make
sense of the world." Planned monetization: in-app fees for
multi-language and webpage/URL support, layered on top of a free core.

**Action-item register refined (2026-08-19), not just directive
civic actions**: MJSullivan flagged the closing lines of a real
episode description (Frankly #47) as the actual kind of "call to
action" wanted — "Is it possible to focus less on productivity and
more on awareness and reflection? Can we effectively change the
consciousness of those in power?" — open, reflective questions aimed
at the reader's own awareness, in Nate's own real voice, not directive
commands. This points toward a better design than generating action
items fresh per article: RETRIEVE a real closing question from Nate's
own back catalog (~230+ episode descriptions, each with real authored
reflective lines), matched by topic/register to the article being
read, rather than having the on-device model invent a reflective
question in his style. Retrieval avoids two real risks generation
carries: hallucinating a plausible-sounding "Nate-style" line he never
actually said, and the authenticity problem of ventriloquizing him at
all — the app would be quoting him, not imitating him. Both registers
likely belong in the final design, not one replacing the other: the
original "call your senator" framing and this reflective-question
framing are both real, drawn from different real episodes' actual
tone, and a given article's classified register (civic/political vs.
personal/existential) could determine which pool gets retrieved from.
Not yet decided how the retrieval corpus itself gets built — likely a
straightforward extension of the Tier 2 show-notes-row work already
scoped, since episode descriptions are similarly short, curated units.

DECIDED: local-first architecture, no cloud server, at least for the
initial build — MJSullivan doesn't currently have funds for one, and
more importantly, the "optional personal info for more salient action
items" feature only works if users trust nothing leaves the phone.
This is being treated as a genuine product differentiator, not just a
budget constraint, since a cloud-based competitor can't credibly offer
the same trust story.

**Two-tier vector design, worked out across this conversation:**
- Tier 1 — KG neighborhood vectors (`Persona`, `Concept`,
  `ScenarioFacet`, `SchoolOfThought`, `Episode`-as-node). NOT a
  per-entity embedding of its own literals alone — MJSullivan's
  correction was that a literal-only vector per entity is rarely
  useful; what's needed is a vector representing the entity's 1-hop
  neighborhood (both incoming and outgoing edges), so retrieval
  returns a coherent subgraph rather than isolated nodes that happen
  to rank nearby. This tier produces the axis "vector" claim itself.
  Real open design questions, not yet decided:
  - Hop depth should probably vary per class, not be fixed globally —
    sparse classes (e.g. `ScenarioFacet`, which may only have one
    `favorsFacet` link at 1 hop) likely need 2 hops to be
    distinguishable from their neighbors on the matrix; dense classes
    (e.g. `Persona.NateHagens`, host of every episode) would get
    drowned in noise at 2 hops and need to stay capped at 1.
  - High-degree nodes need either a neighbor cap, a weighting scheme
    favoring higher-value properties (`dct:references`,
    `favorsFacet`) over generic ones (`rdf:type`), or both — otherwise
    the aggregate vector dilutes into mush for exactly the entities
    (like Nate himself) most likely to matter.
  - Aggregation method undecided between two real options: text-concat
    (build one text blob of entity + neighbor labels/definitions,
    embed once — simple, human-debuggable) vs. vector-pooling (embed
    entity and each neighbor separately, then mean/weighted-pool the
    vectors — more like a one-layer GNN, better control over
    per-neighbor weight, doesn't let one verbose neighbor dominate a
    text blob). Leaning toward pooling since the extra cost is a
    one-time offline batch job, not a runtime cost.
- Tier 2 — show-notes-row vectors. RESOLVED that this is NOT full
  transcript chunking — MJSullivan pointed out the show-notes tables
  built throughout this session (timestamp + topic + curated URLs,
  produced episode-by-episode this session specifically as raw
  material for this) are already the right semantic unit: a human
  already decided each row is one coherent topic, with its
  substantiating links already attached by hand. This tier produces
  the "links to articles/podcasts/papers" part of the original pitch.

**Staging vs. runtime split, RESOLVED:** DuckDB is authoring/batch-time
only, never shipped on-device — chosen for its native vector-similarity
extension, letting embeddings, text, and metadata live in one queryable
row without a separate vector store to keep in sync. Sketch:
`episodes(episode_iri PK, webpage_url, title, summary)`,
`transcript_segments(segment_id PK, episode_iri FK, start_time,
speaker, text, embedding)`, `show_notes(note_id PK, episode_iri FK,
timestamp, topic, links, embedding)` — `episode_iri` is the literal
join key back to the RDF graph's own `Episode` IRIs, requiring no new
RDF properties or a new `Transcript` class (resolves the earlier open
question of whether transcripts should be modeled as ontology nodes —
they don't need to be; DuckDB rows reference the graph by IRI string,
one direction only, and the graph doesn't need to know DuckDB exists).
Full transcript segments (naturally pre-divided in MJSullivan's source
files by dashed dividers) are staged for potential deeper drill-down
past a Tier-2 match, distinct from the curated show-notes rows that
are the actual Tier-2 embedding source.

At runtime, DuckDB's output gets exported to a lightweight on-device
store (SQLite + a vector BLOB column, both native to iOS, no new
dependency) — brute-force cosine similarity across a few thousand
vectors is sub-millisecond on-device, no ANN index needed at this
scale. The on-device small LLM (Apple's on-device model, available
starting with the A17 Pro chip — iPhone 15 Pro/Pro Max and newer, NOT
the base iPhone 15 as originally assumed) embeds the incoming article
and generates the explanation + action item from the retrieved Tier-1/
Tier-2 context, rather than free-generating a claim — deliberately
reducing hallucination risk since the substantive content is retrieved
KG/show-notes text, not invented per-article.

**Not urgent, not scoped for build** — captured here as an architecture
worth mulling over, matching every other backlog item's "don't build
ahead of real need" treatment. Real open items before this moves to
active work: verify current on-device model APIs/framework naming
directly against Apple's docs (has shifted recently); think through
action-item liability/accuracy now that the app would be telling
people what to do, not just explaining a claim; keep article-claim
text in paraphrase, not excerpt, for the same copyright reasons
already observed elsewhere.

**Alternate terms as retrieval bait for the TNG app (raised 2026-08-19)
— HIGH IMPORTANCE, keep visible.** Unlike most of this backlog,
flagged as something to actively stay aware of rather than pure
mulling-over, because it's load-bearing for whether the app's core
retrieval mechanism (see the "Through Nate's Glasses" entry above)
works at all. A random news article will almost never use this
graph's own academic/precise vocabulary ("techno-optimism") — it'll
use casual, slang, or journalistic phrasing instead ("hopium" for a
concrete real example, added to `SchoolOfThought.TechnoOptimism` as a
`BroadMatch` alternate term this session). Without that alternate
term sitting on the node, the article's embedding and the KG node's
embedding never land close enough to match, regardless of real
conceptual closeness — the alternate term isn't there for a human
reader, it's bait for the embedding space, and it's the only thing
that makes the "random article → nearest node → subgraph" entry point
into this graph (see the Tier-1/Tier-3 discussion in the TNG app
entry) actually work in practice rather than in theory.

Two concrete requirements this surfaces, not yet acted on:
- The eventual batch embedding job (Tier 1) MUST traverse
  `thinkr:hasAlternateTerm` blank nodes and include their
  `skos:prefLabel` values when building each node's neighborhood text
  — not just the parent's own `skos:definition`/`rdfs:comment`. Easy
  to build the pipeline without this step and have every alternate
  term added so far sit inert, doing nothing for retrieval despite
  looking like it should.
- Real tension with the earlier-flagged high-degree-node dilution
  problem: a good retrieval-bait term (broad, generic, colloquial) is
  almost the opposite shape of a good disambiguating term. Piling on
  too many broad alternate terms per node risks pulling its vector
  toward a less distinctive point in the embedding space — easier to
  lexically match, worse to semantically match. Argues for being
  deliberate (does a real news article plausibly use this exact
  phrasing?) rather than exhaustively chasing every loosely-related
  synonym per Concept/SchoolOfThought.

Not scoped for active work yet — captured here so it isn't lost, and
because whenever ontology work resumes, watching for this kind of
casual/slang register gap across other Concepts and SchoolsOfThought
(the way "hopium" surfaced for techno-optimism) is worth doing
opportunistically as it comes up, not as a dedicated pass.

**Editorially-added real-world exemplars — a real gap in evidentiary
provenance (raised 2026-08-19) — MUST NOT LOSE SIGHT OF, same tier as
the alternate-terms item above.** Different problem from alternate
terms: that one was about vocabulary for a referent already in the
graph; this is about a referent (a person, likely also applicable to
other classes) that may never appear in the primary source at all, no
matter how central they are to real-world discourse around a Concept
this graph already has. Concrete example: Elon Musk is fairly certain
to never be directly named/linked in TGS's own show notes, yet he's a
constant presence in exactly the kind of news coverage the TNG app
needs to classify onto ScenarioFacets — and he's a real, substantive
exemplar of both `SchoolOfThought.TechnoOptimism` and (not yet built
in this graph) technofeudalism. TGS editors choosing not to link
someone — deliberately or not — becomes a real blind spot for the
app's retrieval, not just a documentation gap.

The real tension: every `Persona` built this session rests on genuine
primary-source evidence (a guest appearance, a direct quote, an
independently-confirmed episode) — that evidentiary discipline is a
core reason this graph is trustworthy. Musk, added because he's
thematically associated with a Concept in general discourse rather
than because Nate or a guest ever said his name, is a DIFFERENT KIND
of fact — editorial judgment about real-world relevance, not
primary-source citation. Reusing the existing guest-Persona pattern
(`hasProfessionalRelationship`, `hasInteraction`, `discusses`,
`hasGuest`) for this would silently erase that distinction — anyone
querying the graph later couldn't tell "TGS actually engaged with
this person" from "the graph curator added this person because the
app needed the bridge."

Real open design questions, not yet resolved:
- Needs its own modeling pattern, not a reuse of the existing guest
  pattern — likely a clear provenance flag on the Persona (or a
  narrower dedicated class) marking it as editorially-added for
  real-world retrieval bridging, checkable at a glance and never
  conflated with TGS-sourced appearances.
- Needs a different property than `discusses`/`favorsFacet` for how
  it connects to a SchoolOfThought/Concept — something like "is a
  real-world exemplar of," since the existing properties currently
  imply the show itself engaged with the connection.
- Needs a real, bounded answer to "who clears the bar" — Musk is an
  obvious extreme case, but the same logic could justify adding
  hundreds of loosely-associated public figures to any Concept in
  this graph. Without a bound, "editorially-added exemplar" risks
  becoming a low-discipline catch-all category rather than a
  deliberate, sparingly-used bridge.

Not scoped for active work yet, same as the alternate-terms item —
but architecturally significant enough that it shouldn't get resolved
casually inside an unrelated build session. A real fork in how this
graph distinguishes "what TGS actually said" from "what the app needs
to work," and needs to be decided as its own deliberate pass.

**External authoritative taxonomies — a real source of news-register
vocabulary (raised 2026-08-19) — related to both the alternate-terms
and editorially-added-exemplars items above, same importance tier.**
Two concrete examples given as a starting point, and checked directly
rather than assumed:
- The **EU Taxonomy for Sustainable Activities** (Regulation
  2020/852/EU) — real, binding EU law in force since 2020, six formal
  environmental objectives (climate mitigation, climate adaptation,
  water/marine resources, circular economy, pollution prevention,
  biodiversity), activity-level criteria set by an ongoing series of
  delegated acts. Durable and authoritative enough to justify real
  investment, but not a static target — actively amended through 2025,
  with a March 2026 call for feedback on revising criteria again.
- The **Climate Bonds Resilience Taxonomy** — a different kind of
  thing entirely: an industry/NGO framework, explicitly labeled
  "interim" on its own page, distributed as an Excel spreadsheet plus
  PDF methodology docs, still being finalized by a working group
  before it's even folded into Climate Bonds' own permanent taxonomy.
  No legal force, no stable structure yet — lower confidence to invest
  heavily against right now versus waiting for the finalized version.

MJSullivan flagged there are certainly others beyond these two, and
wants this treated as an ONGOING SEARCH, not a closed two-item list —
actively watching for other taxonomies/classification systems whose
own terminology might be exactly what real news organizations use for
a topic Nate's own concepts already cover, surfaced opportunistically
as they come up (same practice already adopted for the alternate-terms
slang-register gap) rather than as a dedicated one-time pass.

Real pattern worth expecting generally, confirmed by both examples
here: authoritative external taxonomies are unlikely to publish a
ready-made SKOS/RDF vocabulary with stable term URIs we could just
`owl:sameAs`/`skos:exactMatch` against. Both of these require real,
nontrivial extraction work (Excel/PDF parsing at minimum) — worth
assuming that's the norm, not the exception, when scoping any future
taxonomy-adoption work.

Connects directly to both items above rather than sitting apart from
them:
- Same provenance question as the editorially-added-exemplars item —
  a Concept minted from an external taxonomy needs a clear
  "externally-sourced regulatory/industry taxonomy" tag, never
  silently blended with TGS-sourced content.
- A genuine opportunity for the alternate-terms item — official
  taxonomy terminology (EU Taxonomy activity names, Climate Bonds
  categories) is close to the register real finance/policy news
  articles actually use, making these taxonomies a real source of
  retrieval-bait vocabulary for Nate's existing Concepts, not just a
  separate parallel structure to link at arm's length.

Not scoped for active work yet, same as the other two — captured here
so the search itself doesn't get lost, not just these two examples.

**Kestrel Resilience Taxonomy for US Infrastructure — third real
taxonomy example, surfaces a useful 3-way source typology (raised
2026-08-19).** A genuinely distinct thing from both taxonomies above,
not a duplicate — Kestrel ESG (a private commercial ESG-data/analytics
firm for the US municipal bond market, and separately a Climate Bonds
Initiative Approved Verifier since 2017, a real institutional link
back to the CBRT entry above) released its own "Resilience Taxonomy
for US Infrastructure" on 2026-01-06 — genuinely recent. Real
empirical grounding: built from benchmarking 15,000+ municipal bond
series (~$3 trillion par amount), methodology cites IPCC AR6 and
ASCE/Institute for Sustainable Infrastructure Envision protocols.
Scope is US-specific (the $4.3T municipal bond market) rather than
CBRT's global scope or the EU Taxonomy's EU scope.

This third example makes a useful pattern explicit — three genuinely
different TYPES of taxonomy source, each with different reliability/
stability/access characteristics, worth using to scope any future
integration work rather than treating "external taxonomy" as one
uniform category:
1. **Regulatory/binding** (EU Taxonomy) — most durable and
   authoritative, but a moving target via ongoing legal amendment.
2. **Nonprofit/NGO** (Climate Bonds Resilience Taxonomy) — variable
   maturity (this one explicitly "interim"), moderate authority.
3. **Private commercial** (Kestrel's taxonomy) — tied to one
   company's proprietary methodology and business model, potentially
   the most volatile (could change or be discontinued at the
   company's own discretion), narrowest scope — but also, precisely
   because these firms shape financial/ESG journalism's vocabulary
   directly, potentially the richest source of the exact terms real
   news articles use.

Real access barrier initially found: kestrelesg.com disallows automated
access to its entire site via robots.txt — the PDF couldn't be fetched
directly through this session's own tools. MJSullivan supplied the PDF
directly afterward (it is genuinely public), which surfaced something
more important than the access question: **a real, explicit licensing
blocker, not just ordinary copyright caution.** The document's own
Notice & Disclaimer (last page) states the Information "may not be
used, modified, reverse-engineered, reproduced, disseminated in whole
or in part, used to create derivative works, INDEXES, DATABASES, risk
models, analytics, software... without Kestrel's express permission."
That's a direct, specific prohibition on exactly this use case — minting
this taxonomy's categories as Concept individuals in the graph would be
building a database from it. Structure was confirmed (5 Sustainable
Finance Principles, a general benchmarking methodology, per-sector
resilience-indicator lists for 10 named sectors) without reproducing
any of the actual substantive content, per this graph's own copyright
discipline — the restriction here goes beyond the usual
paraphrase-don't-quote practice into a flat "no databases without
permission" clause.

Real, concrete next step if this taxonomy is ever worth integrating:
the document itself supplies direct contacts for exactly this kind of
request — Monica Reid (CEO) and April Strid (Head of Research), both
with real emails in the document, closing with "get in touch if there
is something we can do for you." Asking Kestrel directly for permission
is the actual path here, not working around the restriction. Worth
treating this as the template going forward: CHECK EACH TAXONOMY'S OWN
LICENSING TERMS before assuming any of them are integration-ready, not
just their access/robots.txt status — a taxonomy can be fully public and
still contractually block exactly this use.

Same status as the other taxonomy entries: not scoped for active work,
captured so it isn't lost, part of the same ongoing search MJSullivan
asked to keep active.

**Batch of candidate sources from Gemini research (added 2026-08-19)
— folded into the external-taxonomies search above, not a new
entry.** MJSullivan shared a Gemini-produced list of public
terminology/ontology sources for NER and news-scanning use. Spot-check
before trusting the list wholesale, per this graph's own established
practice: the two most specific, novel-sounding claims — named
academic ontologies "EIFF-O" (EIFFEL Climate Change Ontology) and
"CCTL" (Climate Change TimeLine Ontology) — were independently
verified as genuinely real, peer-reviewed, published works, each with
a real GitHub repo of OWL/TTL files and a real permissive license
(Apache 2.0 for EIFF-O, CC-BY 4.0 for CCTL — a real, welcome contrast
to the Kestrel taxonomy's explicit no-database-without-permission
restriction above). One real mischaracterization caught in the same
pass, not just imprecise wording: EIFF-O's actual documented purpose is
linking Earth Observation satellite datasets to metadata for
scientific discoverability, not "tracking how real-world environmental
events map to global news" as the summary claimed — a genuine
overstatement of relevance to this specific use case. The remaining
links (FEMA glossary, EPA Substance Registry Services, W3C DCAT,
PreventionWeb DRR terminology, NCA5 appendix) are well-established
government/international resources, high independent confidence
without individually verifying each one the way the two named academic
ontologies warranted.

Worth carrying forward: the list's own "Recommended Pipeline Strategy"
proposes a 3-tier structure (High Level / Operational / Structural)
that independently converges on something close to the
regulatory/nonprofit/private-commercial typology already built out for
the EU Taxonomy/CBRT/Kestrel entries above — a real, useful
cross-check that the typology is a sound way to organize this ongoing
search, not just this session's own invention. CCTL's explicit
separation of climate terms by "Perspective" (scientific vs. social vs.
political vs. technological) is also worth keeping in mind for how
this graph's own Concepts might eventually want to tag which register
a given alternate term belongs to, connecting back to the
alternate-terms-as-retrieval-bait entry above.

**EPA Substance Registry Services (SRS) — real, live, queryable API;
higher confidence than the PDF/Excel-based taxonomies above (raised
2026-08-19).** Surfaced from the Gemini batch above, checked properly
rather than taken at face value. Confirmed genuinely real and live: a
documented OpenAPI/Swagger 3.0 spec exists, a real Postman collection
shows working endpoints (e.g. `autoComplete/casSearch`), and it's
already wrapped by a published R package (`webchem::srs_query`) that
confirms the real shape of a returned record — 22 fields per
substance, including CAS number, IUPAC name, molecular formula,
InChI/SMILES notation, synonyms, classifications, and relationships.
Genuinely different in kind from the EU Taxonomy/CBRT/Kestrel entries
above: a live, queryable API rather than a PDF or spreadsheet requiring
scraping/parsing, and (not yet explicitly confirmed via SRS's own terms
page, but a reasonable working assumption for a US federal government
system) likely free of the kind of explicit no-database licensing
restriction that blocked the Kestrel taxonomy.

Real correction to the Gemini summary's framing, not just imprecise
wording: SRS is specifically EPA's chemical/biological SUBSTANCE
identity registry (its own documentation example: resolving "toluene,"
"methyl benzene," and "phenyl methane" as the same substance) — not a
general "Glossary of Climate Change Terms" as described. EPA's own
System of Registries lists a separate, distinct registry — "TS:
Terminology Services — Terms, Acronyms and Definitions, Glossaries,
Taxonomies" — sitting alongside SRS, which is the more likely real
match for general climate/environmental terminology. Not yet checked;
worth following up directly given the SRS/TS naming mixup here.

MJSullivan's own instinct going in was that EPA terms would support
some already-built episode content — correct and worth acting on: this
graph already has real, built material around specific chemicals (BPA,
phthalates, PFAS, endocrine disruptors from the RR-15 and RR-23
builds). SRS's own synonym lists are a genuine, authoritative source
of real alternate-term candidates for exactly that existing content —
the same retrieval-bait logic as the "Hopium" case, but for chemical-
name variants specifically, and lower-risk to pursue than the taxonomy
sources above given the live-API, presumably-public-domain nature of
the source.

**Real, concrete confirmation (2026-08-19), not speculative anymore**:
MJSullivan pulled a real SRS record — Internal Tracking Number
1647635, "Particulate matter with an aerodynamic diameter less than or
equal to 2.5 micrometers" (PM2.5). This resolved the open question
from the prior turn directly: PM2.5 is modeled as its own real entry,
not decomposed into component chemicals — but the key detail is HOW:
`Substance Type: Physical Property`, `CAS Number` field blank. This
confirms SRS's schema is NOT limited to CAS-numbered chemical
compounds the way the toluene/benzene framing implied — it explicitly
supports non-chemical "Physical Property" substance types like
particle-size classes, a real broadening of what this resource can
cover beyond what was assumed. The record also demonstrates the
synonym/retrieval-bait value concretely rather than theoretically: six
real variant forms across different regulatory contexts — "PM2.5,"
"PM 2.5," "PM fine 0-2.5um STP," "Particulate Matter - Pm2.5,"
"Particulate matter < 2.5 um," "PM2.5 - Local Conditions" — each tied
to a real EPA system (AQS, WQX, ICIS-Air) or regulation (40 CFR 58, 40
CFR 53). One correction to the BPA/phthalates connection claimed
earlier in this entry: this graph does not yet have a built Concept for
PM2.5/particulate pollution specifically — this connects to a
potential future addition, not existing built content the way the
EDC/plastics material from RR-15/RR-23 does.

**Second concrete target added (2026-08-19)**: the six-fronts action
taxonomy built from Frankly_132 includes
tgs:InterventionSubdomain.PlasticAndChemicalHazards, which directly
cross-references RR-23 — meaning SRS's real chemical-synonym data (CAS
numbers, IUPAC names, regulatory-context synonym variants, per the
PM2.5 example above) could enrich this Subdomain's own definition the
same way it would the RR-15/RR-23 episode content, once real API
access exists. Two real, concrete pieces of already-built content now
identified as SRS enrichment targets, not just a general "this seems
useful" note.

Same status as the rest of this thread: not scoped for active work,
captured so it isn't lost, part of the same ongoing search.

**Nate's Hylo community as a "real world" knowledge source — a fourth
distinct provenance category, and a genuine extension of the Tier-3
architecture (raised 2026-08-19).** MJSullivan shared a real Hylo
thread from the "Great Simplification" group — a firsthand account of
real 2026 drought/wildfire disruption in Wales, explicitly connecting
it to Vanessa Andreotti's work (already a real, built Persona in this
graph) and the concept of modernity's "separation." Concretely
verified and acted on already: the post referenced a real, newly
published Andreotti book, "Outgrowing Modernity" (August 2025, the
real sequel to "Hospicing Modernity"), independently confirmed and
added to this graph as a real Work.

This is a genuinely different kind of source from everything else in
this thread — not TGS primary content, not an external authoritative
institution/taxonomy, but an individual community member's personal
reflection. That distinction matters for what's safe to do with it:

- **Low-risk, already demonstrated**: mining threads for factual
  enrichment candidates (new books, related concepts, real-world
  events) to extend existing graph content — nothing about the
  original poster's identity or exact words travels with the
  extracted fact. This is fine to keep doing opportunistically.
- **Higher-consideration, NOT yet resolved**: MJSullivan's own further
  idea — vectorizing and indexing thread text itself as a genuine
  Tier-3-adjacent bridge (a random news article, e.g. about Scotland,
  landing near this thread's own vector, then routing by extension
  into TGS's ontology via the thread's own explicit TGS references).
  Architecturally this is a real, valuable extension — arguably a
  *better* bridge than curated external links, since it's written in
  contemporary, news-adjacent language while explicitly using TGS's
  own vocabulary. But it's a different weight of use than fact-mining:
  it means a private individual's personal writing becomes retrievable
  content served inside a consumer app. Real open questions, not
  assumed away: whether this fits Hylo's own terms of service for
  member content, and whether someone posting in what's likely
  experienced as a smaller, more intimate group space would reasonably
  expect their words to surface that way. Worth resolving deliberately
  before building, not defaulting into either direction.

One refinement discussed, worth keeping precise rather than overstating:
vectors would be built at the THREAD level, not the individual post
level — genuine, structural mitigation for a real multi-person
discussion, since several people's contributions blend into one vector
with no single author's words cleanly separable. But MJSullivan's own
observation stands: many threads (including the Wales example this
whole entry is built on) have exactly one post, where thread-level and
post-level are identical — the granularity choice doesn't reach the
underlying question in that common case. Also discussed: only
persisting the resulting link ("this input maps near this TGS entity")
rather than the source text or vector itself, discarding both after
use — real hygiene against the raw content ever leaking back out, but
it addresses retention, not whether analyzing an individual's post for
this purpose is itself fine in the first place; that's a question about
the processing, not the storage, and forgetting the source afterward
doesn't reach back to resolve it.

**Marked TBD deliberately** — genuine possibilities here, worth keeping
open rather than either committing to build it or ruling it out.

Same status as the rest of the external-source-search thread: not
scoped for active work, captured so it isn't lost, part of the same
ongoing search.

**Euclidean, not cosine, for grid-position matching — a real algorithm
decision for the TNG app's core retrieval mechanism (raised
2026-08-19).** MJSullivan asked whether cosine similarity could compare
an arbitrary news article's classified grid position against the
established ScenarioFacet corners (e.g. a query point of (3,1) against
(2,2)/(2,4)/(4,2)/(4,4)). Worked the actual numbers rather than
reasoning abstractly, and cosine fails concretely: for query point
(3,1), cosine similarity scores tgs:ScenarioFacet.TheGreatSimplification
(2,2) and tgs:ScenarioFacet.Mordor (4,4) EXACTLY EQUAL (≈0.894) — the
two facets this session built as thinkr:diagonallyDisjointWith each
other, the strongest possible opposition in the whole framework.
Cosine only measures the angle swept from the origin, and since all
four grid corners sit in a small, strictly-positive cluster far from
(0,0), it's structurally blind to exactly the distinction that matters
most here. Plain Euclidean distance in the grid's own (X,Y) coordinate
space gets it right: (3,1) comes out equidistant from
TheGreatSimplification and MadMax (both Y=2, both real contraction
facets) and correctly far from GreenGrowth/Mordor (both Y=4, growth)
— matching real intuition for an article about a contracting world,
genuinely ambiguous between managed and chaotic contraction. This is
really the same xAxisDivergentFrom/yAxisDivergentFrom/
diagonallyDisjointWith structure already built this session, just
generalized from discrete grid points to a continuous query point
rather than a new mechanism.

Genuinely interesting secondary finding, MJSullivan's own observation:
the exact center point (3,3) is in mild opposition to ALL FOUR corners
simultaneously — not coincidence, real geometry. (3,3) shares neither
axis value with any corner (3 ≠ 2, 3 ≠ 4 on both axes), so under the
same discrete framework it reads as diagonally divergent from every
corner at once, just at half the magnitude of a true corner-to-corner
thinkr:diagonallyDisjointWith. A clean geometric picture of what "no
clear signal yet" looks like for an unclassified or genuinely
ambiguous article — worth keeping in mind as a real edge case the
matching algorithm needs to handle gracefully, not as an error state.

Directly relevant to the "Through Nate's Glasses" app entry above —
this is the actual math for the "classify article's position, then
find nearest facet" step of that whole pipeline. Not scoped for active
implementation yet, captured so the analysis isn't lost before the
app's real build phase.
