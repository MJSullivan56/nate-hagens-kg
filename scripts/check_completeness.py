#!/usr/bin/env python3
"""check_completeness.py — PILOT, 2026-08-24.

Runs the SHACL completeness shapes in data/shacl_shapes/ against the
real seed data in data/seed/ and writes a markdown deltas report.

THIS IS A COMPLETENESS SIGNAL, NOT A VALIDATION GATE. Every check in
the current shapes is sh:Warning severity (see data/shacl_shapes/
concept-shape.ttl's own header comment for why) — the only thing that
can make this script exit non-zero is a genuine sh:Violation, and
right now none of the checks are declared at that severity except
skos:prefLabel on Concept (100% real coverage already, so it should
never actually fire). Nothing in this repo's own load/merge/validate
pipeline (load_oxigraph.sh, merge_for_protege.py,
validate_class_purity.py) calls this script — it is a separate,
manually-run reporting pass, matching the SAME reasoning that already
keeps data/inferred/ out of data/seed/'s own glob: this is derived
output, not source of truth, and nothing should pick it up implicitly.

PILOT STATUS: only one shape exists so far (tgs:ConceptShape /
tgs:ConceptProvenanceShape, targeting thinkr:Concept). Not yet run as
part of any regular workflow. Extend by dropping additional
<class>-shape.ttl files into data/shacl_shapes/ — this script globs
that whole directory, no registration step needed.

Usage:
    python3 scripts/check_completeness.py
    python3 scripts/check_completeness.py --data-dir data/seed --shapes-dir data/shacl_shapes
    python3 scripts/check_completeness.py --output reports/completeness/custom-name.md

Requires: pyshacl, rdflib  (pip install pyshacl --break-system-packages)
"""

import argparse
import datetime
import glob
import os
import sys
from collections import defaultdict

import rdflib
import pyshacl

SH = rdflib.Namespace("http://www.w3.org/ns/shacl#")


def load_graph(directory, pattern="*.ttl"):
    g = rdflib.Graph()
    files = sorted(glob.glob(os.path.join(directory, pattern)))
    if not files:
        print(f"WARNING: no {pattern} files found in {directory}", file=sys.stderr)
    for f in files:
        g.parse(f, format="turtle")
    return g, files


def run_validation(data_graph, shapes_graph):
    conforms, results_graph, results_text = pyshacl.validate(
        data_graph=data_graph,
        shacl_graph=shapes_graph,
        inference="none",
        abort_on_first=False,
        meta_shacl=False,
        advanced=True,
    )
    return conforms, results_graph, results_text


def summarize(results_graph):
    """Group ValidationResults by (severity, focus node's local name),
    collecting messages. Returns a dict keyed by severity ->
    {local_name: [messages]}."""
    by_severity = defaultdict(lambda: defaultdict(list))
    total = 0
    for res in results_graph.subjects(rdflib.RDF.type, SH.ValidationResult):
        focus = results_graph.value(res, SH.focusNode)
        msg = results_graph.value(res, SH.resultMessage)
        sev = results_graph.value(res, SH.resultSeverity)
        sev_label = str(sev).rsplit("#", 1)[-1] if sev else "Unknown"
        focus_label = str(focus).rsplit("#", 1)[-1] if focus else str(focus)
        by_severity[sev_label][focus_label].append(str(msg) if msg else "(no message)")
        total += 1
    return by_severity, total


def write_report(path, conforms, by_severity, total, data_files, shape_files, target_summary):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

    lines = []
    lines.append("# Completeness report (PILOT)")
    lines.append("")
    lines.append(
        "**This is a pilot.** Only the `thinkr:Concept` shape exists so far. "
        "Severity is `Warning` throughout except one true `Violation`-level "
        "check (`skos:prefLabel`, which nothing currently fails). This "
        "report is a completeness signal — what looks under-modeled — not "
        "a data-quality gate. Nothing in the real load/merge/validate "
        "pipeline runs this automatically yet."
    )
    lines.append("")
    lines.append(f"Generated: {now}")
    lines.append(f"Conforms: **{conforms}**")
    lines.append(f"Data files loaded ({len(data_files)}): " + ", ".join(os.path.basename(f) for f in data_files))
    lines.append(f"Shape files loaded ({len(shape_files)}): " + ", ".join(os.path.basename(f) for f in shape_files))
    lines.append("")

    lines.append("## Summary")
    lines.append("")
    lines.append(f"Total results: {total}")
    for sev in sorted(by_severity.keys()):
        n_individuals = len(by_severity[sev])
        n_hits = sum(len(v) for v in by_severity[sev].values())
        lines.append(f"- **{sev}**: {n_hits} hits across {n_individuals} individuals")
    for cls, count in target_summary.items():
        flagged = len({node for sev in by_severity.values() for node in sev.keys()})
        lines.append(f"- {cls}: {flagged} of {count} instances flagged (at least one hit)")
    lines.append("")

    for sev in sorted(by_severity.keys()):
        lines.append(f"## {sev}")
        lines.append("")
        for focus_label in sorted(by_severity[sev].keys()):
            lines.append(f"### `{focus_label}`")
            for msg in by_severity[sev][focus_label]:
                lines.append(f"- {msg}")
            lines.append("")

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--data-dir", default="data/seed", help="Directory of source .ttl files (default: data/seed)")
    parser.add_argument("--shapes-dir", default="data/shacl_shapes", help="Directory of SHACL shape .ttl files (default: data/shacl_shapes)")
    parser.add_argument("--output", default=None, help="Report output path (default: reports/completeness/<timestamp>.md)")
    args = parser.parse_args()

    data_graph, data_files = load_graph(args.data_dir)
    shapes_graph, shape_files = load_graph(args.shapes_dir)

    if not shape_files:
        print("No shape files found — nothing to check. Exiting.", file=sys.stderr)
        sys.exit(0)

    print(f"Loaded {len(data_graph)} data triples from {len(data_files)} files.")
    print(f"Loaded {len(shapes_graph)} shape triples from {len(shape_files)} files.")

    conforms, results_graph, results_text = run_validation(data_graph, shapes_graph)
    by_severity, total = summarize(results_graph)

    # Count real instances per target class actually checked, for context
    # in the summary. NOTE: this counts raw rdf:type thinkr:Concept, which
    # is NOT the same population ConceptShape actually targets (it uses a
    # SPARQLTarget excluding Indicator/IndicatorCategory/EarthSystemComponent
    # multi-typed individuals — see that shape's own rdfs:comment for why).
    # Kept as a labeled approximation, not asserted as exact, until this
    # script has real per-shape target introspection.
    thinkr = rdflib.Namespace("http://example.org/thinkr#")
    concept_raw = set(data_graph.subjects(rdflib.RDF.type, thinkr.Concept))
    indicator_family = set(data_graph.subjects(rdflib.RDF.type, thinkr.Indicator)) \
        | set(data_graph.subjects(rdflib.RDF.type, thinkr.IndicatorCategory)) \
        | set(data_graph.subjects(rdflib.RDF.type, thinkr.EarthSystemComponent))
    concept_scoped = concept_raw - indicator_family
    target_summary = {
        "thinkr:Concept (narrative, as actually targeted)": len(concept_scoped)
    }

    if args.output:
        out_path = args.output
    else:
        ts = datetime.datetime.now().strftime("%Y-%m-%d")
        out_path = f"reports/completeness/{ts}.md"

    write_report(out_path, conforms, by_severity, total, data_files, shape_files, target_summary)
    print(f"\nReport written to {out_path}")
    print(f"Conforms: {conforms}")

    # Exit non-zero ONLY on a real Violation — Warnings never fail the
    # build, matching this shape's own "signal, not gate" design.
    if "Violation" in by_severity:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
