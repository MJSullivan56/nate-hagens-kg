# nate-hagens-kg: 3-Month Project Plan (2026-08-21 → ~2026-11-21)

Built from the workstream map discussed in chat the same day. Tool tags
(**Chat** / **Code**) reflect real constraints hit this session, not
preference: **Chat** cannot reach the live Oxigraph endpoint, cannot
operate on the full 348-episode corpus at true scale, and cannot commit to
the real git repo. Everything else genuinely can happen in Chat, including
several things that look like they should need Code.

This is a proposed *sequence*, not a guaranteed calendar — it assumes
roughly one substantial Code session per month given the real budget
constraint hit this session ("a month's budget in one afternoon"). Adjust
pacing to your actual Code cadence; the *dependencies* below are the real
constraint, not the month labels.

---

## Dependency map (plain-language, not a diagram)

- **TBOX axioms** (Chat: draft) → must exist before a **reasoner run
  against the full corpus** means anything real, and before **inverse/
  symmetric materialization** (Code) can be built correctly — the
  materialization script needs to know which properties actually declare
  `owl:inverseOf`/`owl:SymmetricProperty`.
- **YAML loader** (Chat: draft + test on samples) → must exist before
  **DuckDB gets populated** (Code: run at scale) → which must happen
  before **curation queries** (Chat or Code, either can write SQL) can
  run against anything real → which must happen before **bio/identity
  reconciliation** (Chat: design: done; final calls: human judgment) can
  proceed with real candidates instead of hypothetical ones.
- **Bio-bleed fix** (Chat: done) → should run **before or alongside** the
  YAML load, since loading raw bio-bleed junk into `guest_bios_raw` is
  fine (that's the point of the raw layer) but reconciliation work should
  wait until the fix has at least been applied in a `guest_bios_clean`
  view — reconciling junk wastes real review time.
- **Transcript chunking algorithm** (Chat: designed, tested, refined) →
  running it at corpus scale (Code) requires DuckDB already populated
  (needs a place to write `transcript_by_topic` rows) → which unlocks the
  **not-yet-scoped embedding/vectorization workstream** (new — this is
  the actual stated end goal of chunking, "create a vector for that
  chunk," raised in passing earlier this session but never given its own
  line item until now. Needs: an embedding model/API decision, a vector
  index choice, and a decision on whether `(unlinked transition)` chunks
  get embedded at all — flagged as open in the last handoff doc).
- **RDF-side importer** (`rdf_to_duckdb.py`, Chat: written and tested) —
  no further Chat-side dependency, ready to run whenever Code has live
  Oxigraph access. Real caveat: if TBOX axioms get added to `tgs-core.ttl`
  after this first runs, it should be re-run — the DuckDB copy would
  otherwise reflect a stale schema.
- **Export (DuckDB → RDF)** (Code: not yet built, Phase 5 of the
  migration prompt) is the capstone of the whole DuckDB detour — it
  depends on curation/reconciliation being meaningfully done first, or
  it just exports the same raw mess back out.
- **Ongoing scraping** (Code) sits at the front of everything — without
  it continuing, the "100% show-notes extraction" claim quietly decays
  as new episodes release, and every downstream workstream is working
  against an increasingly stale snapshot.

---

## Month 1 — Chat-only prep (no Code budget spent)

Goal: get everything that *can* be ready and tested before touching Code,
so Code time is spent executing rather than designing or debugging.

| Task | Tool | Depends on |
|---|---|---|
| Draft the concrete TBOX axiom list (cardinality, real disjointness, inverses) in plain language, reviewed together | Chat | — |
| Draft + test the YAML→DuckDB loader against the real sample records already in hand | Chat | — |
| Continue rich ABOX building for high-value episodes (uploaded transcripts) | Chat | — |
| Continue reasoner validation against graph snapshots — resume the second, still-unresolved inconsistency (the bisection script's real logic bug needs fixing first) | Chat | — |
| Verify real transcript-download coverage against the site's own episode archive/RSS (resolve the "95%, unsure what's missing" uncertainty) | Chat (can attempt) or Code | — |

**End-of-month checkpoint**: axiom list finalized and reviewed; YAML
loader tested and working on samples; a real, current count of what
transcripts are actually still missing.

---

## Month 2 — First Code session(s): execute the tested backlog

Goal: spend Code budget running things that are already designed and
verified, not writing new logic from scratch.

| Task | Tool | Depends on |
|---|---|---|
| Commit finalized TBOX axioms to the real schema | Manual (MJSullivan, by hand) | Month 1 axiom list |
| Run `rdf_to_duckdb.py` against the live Oxigraph | Code | Axioms committed by hand |
| Run the YAML loader against the full 358-record corpus | Code | Month 1 loader |
| Run the bio-bleed fix across the full corpus | Code | Chat's tested fix |
| Run the transcript-chunking algorithm across the full corpus, write `transcript_by_topic` to DuckDB | Code | DuckDB populated |
| Run HermiT against the full live graph (not a snapshot), materialize confirmed real fixes | Code | Axioms committed |

**End-of-month checkpoint**: DuckDB genuinely populated with raw +
lightly-cleaned data across the whole corpus; a real, current count of
remaining reasoner inconsistencies against the live graph, not a
snapshot.

---

## Month 3 — Curation, reconciliation, and the first real export

Goal: turn populated-but-raw DuckDB data into something that can flow
back into the graph responsibly.

| Task | Tool | Depends on |
|---|---|---|
| Run curation queries (missing links, illogical relationships, duplicate personas) | Chat or Code — pure SQL, either works | Month 2 DuckDB population |
| Bio/identity reconciliation — review queue, alias resolution (`Art Berman`/`Arthur Berman`-style), canonical bio decisions | Chat-assisted, human final call | Bio-bleed fix already applied |
| Build the DuckDB → RDF export script (Phase 5, not yet built) | Code | Curation/reconciliation reasonably complete |
| First real export back into Oxigraph + regenerated seed files | Code | Export script working |
| Scope the embedding/vectorization workstream properly (model choice, vector store, placeholder-chunk decision) | Chat (design) → Code (build) | Chunking done at scale |

**End-of-month checkpoint**: a real, curated export has round-tripped
back into the live graph at least once; the embedding workstream has a
real spec instead of being an open question.

---

## Explicitly not scheduled — genuinely open-ended

- **Ongoing scraping of new episodes.** Needs to become a recurring Code
  task, not a one-time item, or every checkpoint above starts decaying
  the moment it's reached.
- **The still-unresolved second reasoner inconsistency** — real
  diagnostic groundwork exists (the datatype-stripping approach, the
  owlready2 invocation), but the bisection logic itself needs a real fix
  before it converges on real evidence rather than a guess.
