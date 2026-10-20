#!/usr/bin/env python3
"""
Runs HermiT against the full graph and materializes ONLY the two
inference categories with real, demonstrated value for this project —
inferred class assertions (rdf:type) and inferred property assertions
(object/datatype property triples) — into a SEPARATE file, deliberately
kept OUTSIDE data/seed/ so none of the three existing scripts that glob
that directory (load_oxigraph.sh, validate_class_purity.py,
merge_for_protege.py) pick it up implicitly. See docs/backlog.md for the
full reasoning behind scoping to just these two categories.

DERIVED — never hand-write this file's contents. Re-run whenever the
schema or data changes meaningfully, and reload the inferred file into
Oxigraph as its OWN named graph (not merged into the default one), so a
query can explicitly include or exclude inferred facts rather than have
them silently blurred with asserted ones — the same reasoning that led
to using an is_inferred column for the DuckDB side of this project.

Method: snapshot the graph before reasoning, run HermiT (via owlready2,
the same toolchain used throughout tonight's reasoner investigation),
export the post-reasoning state, and take the set difference — filtered
to triples where every part (subject, predicate, object) is a real,
named URI, never a blank node. This deliberately excludes the messier
categories (new subClassOf axioms, disjoint-class inferences,
equivalent-individual/sameAs inferences) which are either empty for
this schema currently or actively unwanted (the AllDifferent blocks
exist specifically to PREVENT same-individual inferences, not produce
them).

Usage:
    python materialize_inferences.py
Writes to: data/inferred/materialized.ttl
"""
import glob
import rdflib
from pathlib import Path
from owlready2 import get_ontology, sync_reasoner_hermit

SEED_DIR = "data/seed"
OUTPUT_DIR = "data/inferred"
OUTPUT_FILE = f"{OUTPUT_DIR}/materialized.ttl"


def load_asserted_graph():
    g = rdflib.Graph()
    for f in sorted(glob.glob(f"{SEED_DIR}/*.ttl")):
        g.parse(f, format="turtle")
    return g


def strip_unsupported_datatypes(g):
    """xsd:date and xsd:gYear are outside HermiT's OWL 2 datatype map —
    confirmed earlier tonight; stripping them is required for HermiT to
    run at all, not optional. These come back automatically since we
    diff against the ORIGINAL asserted graph, not this stripped copy."""
    XSD_DATE, XSD_GYEAR = rdflib.XSD.date, rdflib.XSD.gYear
    to_remove = [t for t in g if
                 (isinstance(t[2], rdflib.Literal) and t[2].datatype in (XSD_DATE, XSD_GYEAR)) or
                 (t[2] in (XSD_DATE, XSD_GYEAR))]
    g2 = rdflib.Graph()
    for t in g:
        if t not in to_remove:
            g2.add(t)
    return g2


def run_reasoner_and_get_result(stripped_graph):
    stripped_graph.serialize(destination="/tmp/for_reasoner.owl", format="xml")
    onto = get_ontology("file:///tmp/for_reasoner.owl").load()
    with onto:
        sync_reasoner_hermit(infer_property_values=True)
    # as_rdflib_graph() already returns a real, usable rdflib.Graph directly —
    # no need to round-trip through RDF/XML serialization, which has strict
    # blank-node-ID syntax rules (NCName validity) that owlready2's own output
    # doesn't always satisfy. Confirmed the hard way: this exact round-trip
    # crashed on a bare-digit blank node ID during the first real test run.
    return onto.world.as_rdflib_graph()


def normalize_literal(o):
    """A plain literal ('CD', datatype=None) and an explicit xsd:string
    literal ('CD'^^xsd:string) are the SAME value under RDF semantics,
    but rdflib's own == and hash treat them as genuinely unequal —
    confirmed directly, not assumed. HermiT's re-serialization adds the
    explicit xsd:string marker even for values whose source Turtle never
    wrote one, which silently produced false-positive "new" triples in
    the first real test run (any already-asserted string property looked
    like a fresh inference). Normalize both to the same plain form before
    any comparison."""
    if isinstance(o, rdflib.Literal) and o.datatype == rdflib.XSD.string:
        return rdflib.Literal(str(o))
    return o


def normalize_triple(t):
    return (t[0], t[1], normalize_literal(t[2]))


def is_real_named_triple(t):
    """True only if subject, predicate, and object are all real, named
    URIs — never a blank node. This is what naturally excludes complex
    class-expression artifacts (unionOf lists, restriction blank nodes)
    and keeps only genuinely simple, queryable class/property
    assertions. ALSO excludes two real noise categories found by
    inspecting actual output from the first real run — not theoretical:
    the anonymous-ontology bookkeeping triple HermiT/owlready2 always
    introduces, and "X a owl:Thing" assertions, which are trivially
    true of every URI in existence and carry zero real information."""
    s, p, o = t
    if s == rdflib.URIRef("http://anonymous"):
        return False
    if o == rdflib.OWL.Thing:
        return False
    return (isinstance(s, rdflib.URIRef) and isinstance(p, rdflib.URIRef)
            and isinstance(o, (rdflib.URIRef, rdflib.Literal)))


def main():
    print("Loading asserted graph...")
    asserted = load_asserted_graph()
    print(f"  {len(asserted)} asserted triples")

    stripped = strip_unsupported_datatypes(asserted)
    print(f"  {len(stripped)} after stripping unsupported datatypes for HermiT")

    print("Running HermiT (this can take a while)...")
    post_reasoning = run_reasoner_and_get_result(stripped)
    print(f"  {len(post_reasoning)} triples after reasoning")

    # The delta: everything new that wasn't in the (stripped) asserted graph.
    # Compare on NORMALIZED triples (see normalize_triple's own docstring for
    # why this is required, not optional) to avoid false positives from
    # plain-vs-explicit-xsd:string literal representation differences.
    stripped_normalized = set(normalize_triple(t) for t in stripped)
    delta = [t for t in post_reasoning if normalize_triple(t) not in stripped_normalized]
    print(f"  {len(delta)} new triples from reasoning")

    named_only = [t for t in delta if is_real_named_triple(t)]
    print(f"  {len(named_only)} of those are real, named-URI class/property assertions (keeping)")
    print(f"  {len(delta) - len(named_only)} involve blank nodes or complex expressions (discarding)")

    class_assertions = [t for t in named_only if t[1] == rdflib.RDF.type]
    property_assertions = [t for t in named_only if t[1] != rdflib.RDF.type]
    print(f"  -> {len(class_assertions)} inferred class assertions, {len(property_assertions)} inferred property assertions")

    Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
    out = rdflib.Graph()
    for prefix, ns in asserted.namespaces():
        out.bind(prefix, ns)
    for t in named_only:
        out.add(normalize_triple(t))

    header = (
        "# MATERIALIZED INFERENCES — DERIVED, DO NOT HAND-EDIT.\n"
        "# Generated by scripts/materialize_inferences.py. Contains ONLY\n"
        "# inferred class assertions and inferred property assertions —\n"
        "# see the script's own docstring and docs/backlog.md for why\n"
        "# these two categories specifically, not the other three\n"
        "# Protege also offers to export.\n"
        "# Deliberately kept OUTSIDE data/seed/ — see script docstring.\n\n"
    )
    body = out.serialize(format="turtle")
    with open(OUTPUT_FILE, "w") as f:
        f.write(header + body)

    print(f"\nWrote {OUTPUT_FILE}")

    # Self-verify: re-parse and confirm the counts match what we intended to write.
    # Compare against the DEDUPLICATED count, not len(named_only) directly —
    # owlready2's world export can yield the same triple twice from different
    # internal contexts during iteration (confirmed the hard way: a first run
    # showed 624 vs 622, traced to exactly this, not a real data problem).
    expected_distinct = len(set(named_only))
    check = rdflib.Graph()
    check.parse(OUTPUT_FILE, format="turtle")
    if len(check) != expected_distinct:
        print(f"\nVERIFICATION FAILED — expected {expected_distinct} distinct triples but file re-parses to {len(check)}")
        raise SystemExit(1)
    print(f"Verified via fresh re-parse: {len(check)} distinct triples, matches expected count.")


if __name__ == "__main__":
    main()
