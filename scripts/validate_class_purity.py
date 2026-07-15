"""
Confirms every file in data/seed/ holds instances of exactly one class
(its own titular class) and nothing else — the rule established
2026-07-14 after the same mistake happened twice (Concept-lineage facts
landing in linknotes.ttl instead of concepts.ttl, mid-task, on two
separate occasions). See docs/sidecar-cleanup-handoff.md for the full
incident and scratch.ttl's own header for the staging convention this
script exists to enforce alongside.

WHAT THIS CHECKS:
For every data/seed/*.ttl file (except scratch.ttl, checked separately
below), every named tgs:-namespaced subject's class prefix (the part of
its local name before the first ".", e.g. "Concept" in
"tgs:Concept.Overshoot") must match exactly one value across the whole
file. thinkr:-namespaced subjects (schema: classes, properties) are
NOT checked here — a class living in its own instances' file (e.g.
thinkr:Relationship declared inside relationships.ttl, alongside its
own tgs:Relationship.* individuals) is the established, correct
pattern in this project, not a violation. Blank nodes are always
ignored — they're nested/anonymous and belong wherever their
containing statement puts them (e.g. PodcastAppearance interactions
inside a Relationship), not top-level file-organization subjects.

WHAT THIS DOES NOT CHECK (yet — real gaps, not silently claimed to be
covered): SHACL shape conformance, cross-file dangling-reference
checks, confidence-value enumeration validity, or anything
compute_confidence.py is responsible for. This script has ONE job.

Usage:
    python scripts/validate_class_purity.py
    python scripts/validate_class_purity.py --seed-dir data/seed
    python scripts/validate_class_purity.py --check-scratch-empty

Exit code 0 if clean, 1 if any violation found (or if
--check-scratch-empty was passed and scratch.ttl has content) — safe to
wire into a pre-commit hook or CI once one exists for this repo (none
confirmed to exist yet as of 2026-07-14, see the handoff doc).
"""

import argparse
import sys
from pathlib import Path

import rdflib

TGS_NS = "http://example.org/tgs#"


def class_prefixes_in_file(path):
    """Returns {class_prefix: [local_names]} for every named tgs:-namespaced
    subject in the file. Skips blank nodes and thinkr:-namespaced subjects
    entirely — see module docstring for why both are out of scope."""
    g = rdflib.Graph()
    g.parse(str(path), format="turtle")

    by_prefix = {}
    for s in set(g.subjects()):
        if isinstance(s, rdflib.BNode):
            continue
        s_str = str(s)
        if not s_str.startswith(TGS_NS):
            continue
        local = s_str[len(TGS_NS):]
        if "." not in local:
            continue
        prefix = local.split(".", 1)[0]
        by_prefix.setdefault(prefix, []).append(local)
    return by_prefix


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed-dir", default="data/seed",
                         help="Path to the seed directory (default: data/seed)")
    parser.add_argument("--check-scratch-empty", action="store_true",
                         help="Also fail if scratch.ttl has any real content beyond its own header")
    args = parser.parse_args()

    seed_dir = Path(args.seed_dir)
    if not seed_dir.is_dir():
        print(f"ERROR: {seed_dir} is not a directory. Run from the repo root, "
              f"or pass --seed-dir explicitly.")
        sys.exit(1)

    violations = []
    files_checked = 0

    for f in sorted(seed_dir.glob("*.ttl")):
        if f.name == "scratch.ttl":
            continue
        files_checked += 1
        try:
            by_prefix = class_prefixes_in_file(f)
        except Exception as e:
            print(f"PARSE ERROR: {f} — {e}")
            violations.append((f.name, "PARSE ERROR", str(e)))
            continue

        if len(by_prefix) > 1:
            violations.append((f.name, by_prefix, None))
            print(f"*** {f.name}: MULTIPLE class prefixes found: {sorted(by_prefix.keys())} ***")
            for prefix, names in sorted(by_prefix.items()):
                sample = names[:3]
                print(f"    {prefix}: {len(names)} subject(s) — e.g. {sample}")
        else:
            prefix = next(iter(by_prefix), "(none)")
            print(f"OK   {f.name}: {prefix}")

    print(f"\n{files_checked} file(s) checked, {len(violations)} violation(s).")

    scratch_path = seed_dir / "scratch.ttl"
    if args.check_scratch_empty and scratch_path.exists():
        g = rdflib.Graph()
        g.parse(str(scratch_path), format="turtle")
        # The header's own ontology declaration is expected (3 triples:
        # rdf:type, owl:imports, rdfs:comment) — anything beyond that
        # means real content is still parked here.
        if len(g) > 3:
            print(f"\n*** scratch.ttl is NOT empty: {len(g)} triples "
                  f"(expect 3, just the header's ontology declaration). "
                  f"Sweep its contents to their real destination files "
                  f"before considering this task done. ***")
            violations.append(("scratch.ttl", "not empty", len(g)))
        else:
            print("\nOK   scratch.ttl is empty (just its header).")

    if violations:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
