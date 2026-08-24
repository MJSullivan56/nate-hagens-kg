#!/usr/bin/env python3
"""
Merges every .ttl file in data/seed/ into a single graph and writes it out
as one file, ready to open directly in Protege (or feed to HermiT/owlready2,
or any other single-file-expecting tool).

Deliberately NOT using owl:imports for this. Two real reasons:
  1. load_oxigraph.sh already solves the "assemble all files" problem for
     Oxigraph, via a simple loop over files -- it does not look at
     owl:imports at all, so adding imports to tgs-core.ttl wouldn't help
     the Oxigraph side of this project in any way.
  2. This graph's namespace (http://example.org/tgs#) is not a real,
     publicly-resolvable domain. Protege CAN follow owl:imports, but
     reliably resolving them would need a local import-catalog file --
     real, extra infrastructure -- for a mechanism that only helps this
     one tool. A plain merge script is simpler, already proven this
     session (used repeatedly for HermiT runs and cross-file validation),
     and tool-agnostic: the same output file works for Protege, HermiT,
     or anything else that just wants "the whole graph, one file."

Usage:
    python merge_for_protege.py [seed_dir] [output_file]

Defaults: seed_dir=data/seed, output_file=merged_for_protege.ttl
Also writes an OWL/XML copy alongside it (some reasoner tooling, including
the owlready2/HermiT combination used earlier this session, wants OWL/XML
rather than Turtle) unless --turtle-only is passed.
"""
import sys
import rdflib
from pathlib import Path

def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    turtle_only = "--turtle-only" in sys.argv

    seed_dir = Path(args[0]) if len(args) > 0 else Path("data/seed")
    output_file = Path(args[1]) if len(args) > 1 else Path("merged_for_protege.ttl")
    output_file.parent.mkdir(parents=True, exist_ok=True)

    if not seed_dir.is_dir():
        print(f"ERROR: {seed_dir} is not a directory. Run from the repo root, "
              f"or pass the seed directory explicitly.")
        sys.exit(1)

    ttl_files = sorted(seed_dir.glob("*.ttl"))
    # Real bug found and fixed 2026-08-22: if the output file lands in the
    # same directory being globbed (the natural way to run this), a SECOND
    # run picks up the FIRST run's own output as an input, silently
    # re-merging it. Named-IRI content self-deduplicates harmlessly in
    # rdflib's Graph (same triple twice collapses to one), but blank-node
    # content (e.g. owl:AllDifferent's "[]") does NOT -- every blank node
    # parse mints a fresh identity, so re-including a prior run's output
    # genuinely doubles any blank-node-based axioms. Confirmed via a real
    # symptom: 6 real AllDifferent blocks in the source enumerations.ttl,
    # 12 in a re-run's merged output. Fix: never treat the intended output
    # file (or any file matching common merge-output names) as an input.
    output_resolved = output_file.resolve()
    ttl_files = [f for f in ttl_files if f.resolve() != output_resolved
                 and not f.name.startswith("merged_for_protege")]
    if not ttl_files:
        print(f"ERROR: no .ttl files found in {seed_dir}")
        sys.exit(1)

    print(f"Merging {len(ttl_files)} files from {seed_dir}...")
    g = rdflib.Graph()
    for f in ttl_files:
        try:
            g.parse(str(f), format="turtle")
        except Exception as e:
            print(f"PARSE ERROR in {f.name}: {e}")
            sys.exit(1)
    print(f"  {len(g)} triples merged, zero parse errors.")

    g.serialize(destination=str(output_file), format="turtle")
    print(f"Wrote {output_file}")

    if not turtle_only:
        owl_file = output_file.with_suffix(".owl")
        g.serialize(destination=str(owl_file), format="xml")
        print(f"Wrote {owl_file} (OWL/XML, for HermiT/owlready2-style tooling)")

    print("\nOpen either file directly in Protege, or point HermiT at the .owl file.")

if __name__ == "__main__":
    main()
