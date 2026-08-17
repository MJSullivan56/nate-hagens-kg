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
