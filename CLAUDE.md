# Nate Hagens Knowledge Graph — Claude Code context

## What this project is
An RDF knowledge graph connecting Nate Hagens' "Great Simplification"
framework to philosophers, scientists, and activists. See README.md for
the full picture — this file is the condensed version for session start.

## Stack
- RDF/Turtle as source of truth (`ontology/`, `data/seed/`)
- Oxigraph as the query engine (CLI installed via `brew tap oxigraph/oxigraph`)
- DuckDB as a staging/review database for LLM-proposed candidate links
  (`extraction/staging.duckdb`, not committed)
- Python venv (`make venv`) for all scripting

## Ground rules for changes in this repo
- **Never mark a `tgs:LinkNote` as `tgs:confidence "curated"` without a human
  having actually reviewed the specific claim.** This is the most important
  rule in the repo. Auto-promoting LLM-proposed links defeats the entire
  point — see README.md's "Design choices" section.
- Concept definitions in `data/seed/concepts.ttl` are paraphrases, not
  verbatim Hagens quotes — keep it that way (copyright + accuracy).
- Every `.ttl` file must parse individually and combined — run `make validate`
  before considering an edit done. CI (`.github/workflows/validate.yml`)
  enforces this on push too.
- Avoid bare DBpedia `dbr:` prefixed names for people whose surface form ends
  in a period-adjacent token (e.g. "Jr.") — Turtle parses a trailing `.` as
  end-of-statement. Use the full `<http://dbpedia.org/resource/...>` IRI in
  those cases (see `data/seed/people.ttl` for examples).
- `data/generated/` is the output of `extraction/promote_to_rdf.py` — don't
  hand-edit it; edit the DuckDB staging rows and re-run the promote script.

## Common commands
```bash
make validate       # parse-check every .ttl file
make load-oxigraph   # load everything into a local Oxigraph store
make init-db         # set up the DuckDB review-queue tables
make promote-dry     # preview what promote_to_rdf.py would write
make promote          # write approved staging rows into data/generated/
```

## This is a separate project from other Claude Code work
This repo is its own git repository and should stay that way — don't nest it
inside another project's directory or reference files outside this repo's
tree unless explicitly asked to.
