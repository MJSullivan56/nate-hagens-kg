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
