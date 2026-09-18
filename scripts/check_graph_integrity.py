#!/usr/bin/env python3
"""
check_graph_integrity.py

Pre-commit/pre-PR gate for the nate-hagens-kg ontology. Checks two real,
distinct graph-health properties across every S P O triple:

  ORPHANS (hard failure, blocks the commit):
      An object O that is itself a tgs: individual, but never appears
      anywhere in the graph as a subject -- meaning it's referenced but
      was never actually declared/typed. This is the exact bug pattern
      found and fixed by hand on 2026-09-11 (9 real cases: guessed IRIs
      that didn't match what was actually built, a false "already
      built" claim in prose, two self-flagged-uncertain guesses left
      pointing at nothing).

  STRANDED (informational only, never blocks):
      A subject S that is itself a tgs: individual, but never appears
      anywhere in the graph as an object -- meaning nothing else points
      TO it. This is NOT necessarily a bug: a freshly-added Concept
      nobody has cross-referenced yet, or an intentional root entity
      (Nate Hagens himself, a top-level Subject), will legitimately
      never be pointed to. Reported for awareness, not enforced.

Scope: only checks individuals in the tgs: namespace (real content --
episodes, humans, concepts, etc.). Deliberately excludes:
  - Blank nodes (used for AlternateTerm, PodcastAppearance interaction
    records, etc. -- legitimate anonymous inline structures, not bugs)
  - Literals (strings, dates -- can't be checked as S or O this way)
  - External URIs (owl:sameAs targets like Wikipedia links -- these
    will never appear as a subject in THIS graph, by design)
  - The thinkr: core vocabulary itself (classes/properties, not content)

Usage:
    python3 check_graph_integrity.py /path/to/ttl/directory/
    python3 check_graph_integrity.py /path/to/ttl/directory/ --strict

Exit code 0 if no orphans found (stranded entities never affect exit
code). Exit code 1 if any orphans found. --strict also fails on any
stranded entity -- use sparingly, since many stranded entities are
expected and fine.
"""

import sys
import glob
import argparse
import rdflib

TGS_NS = "http://example.org/tgs#"


def load_graph(ttl_dir: str) -> rdflib.Graph:
    g = rdflib.Graph()
    ttl_files = sorted(glob.glob(f"{ttl_dir}/*.ttl"))
    if not ttl_files:
        raise SystemExit(f"No .ttl files found in {ttl_dir}")
    for f in ttl_files:
        g.parse(f, format="turtle")
    return g


def find_orphans_and_stranded(g: rdflib.Graph):
    subjects = set()
    objects = set()

    for s, p, o in g:
        if isinstance(s, rdflib.URIRef) and str(s).startswith(TGS_NS):
            subjects.add(str(s))
        if isinstance(o, rdflib.URIRef) and str(o).startswith(TGS_NS):
            objects.add(str(o))

    orphans = sorted(objects - subjects)
    stranded = sorted(subjects - objects)
    return orphans, stranded


def short_name(uri: str) -> str:
    return uri.split("#")[-1]


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("ttl_dir", help="Directory containing .ttl files")
    parser.add_argument("--strict", action="store_true",
                         help="Also fail on stranded entities (off by default)")
    args = parser.parse_args()

    g = load_graph(args.ttl_dir)
    orphans, stranded = find_orphans_and_stranded(g)

    print(f"Loaded {len(g)} triples from {args.ttl_dir}")
    print()

    if orphans:
        print(f"ORPHANS FOUND ({len(orphans)}) -- referenced but never declared:")
        for o in orphans:
            # Show what's pointing at each orphan, for easier fixing
            citing = [short_name(str(s)) for s, p in g.subject_predicates(rdflib.URIRef(o))]
            print(f"  {short_name(o)}  <-- cited by: {', '.join(citing)}")
        print()
    else:
        print("No orphans found.")
        print()

    print(f"Stranded entities (informational, {len(stranded)} total, "
          f"never referenced by anything else):")
    if len(stranded) <= 20:
        for s in stranded:
            print(f"  {short_name(s)}")
    else:
        print(f"  ({len(stranded)} entities -- showing first 20)")
        for s in stranded[:20]:
            print(f"  {short_name(s)}")
    print()

    if orphans:
        print("RESULT: FAIL -- orphans must be fixed before commit.")
        sys.exit(1)
    elif args.strict and stranded:
        print("RESULT: FAIL (--strict mode) -- stranded entities present.")
        sys.exit(1)
    else:
        print("RESULT: PASS")
        sys.exit(0)
