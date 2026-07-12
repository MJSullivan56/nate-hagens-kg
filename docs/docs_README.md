# docs/

Cross-cutting design and handoff documents — material that doesn't
belong to any single code folder, as distinct from folder-local READMEs
(`extraction/README.md` documents just the scripts sitting next to it;
this folder is for things that span multiple files/folders at once, or
that need more room than a backlog bullet in `CLAUDE.md`).

Convention established 2026-07-11: `CLAUDE.md` stays the single source
of truth for backlog items and load-bearing design decisions (numbered,
dated, with reasoning). A doc lands here instead of directly in
`CLAUDE.md` when it's substantial enough to need its own file — worked
examples, open questions requiring real back-and-forth to resolve,
material that would otherwise bloat `CLAUDE.md` past readability. Every
doc here should still get a short pointer entry in `CLAUDE.md`'s backlog
so it isn't undiscoverable.

An `archive/` subfolder for superseded docs is a reasonable future
addition (matching how `CLAUDE.md` marks old reasoning `SUPERSEDED`
rather than deleting it) — deliberately not created yet, per this
project's general instinct to build folder structure only once there's
real content that needs it, not speculatively.

## Currently here

- `sidecar-cleanup-handoff.md` — naming/structure cleanup for the
  `LinkNote`/`Evidence`/`CrosswalkNote`/(proposed)`AffiliationNote`
  family, plus the escalated multi-instance-relationship problem and the
  `thinkr:School` overloading discussion. Backlog, not yet executed —
  see its own status line for the full picture, including an explicit
  caveat that its examples aren't yet concrete enough to build from.
