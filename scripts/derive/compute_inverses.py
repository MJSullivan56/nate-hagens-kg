#!/usr/bin/env python3
"""Write the missing direction of every inverse and symmetric relationship
into data/seed/, so the JSON-LD export carries both directions.

Each seed file gets one managed section at its end, between the markers
below. The script owns that section and rewrites it on every run, so it is
idempotent: run it after any build, the same way as compute_confidence.py.
It never parses-and-reserializes a file (gotcha #1); hand-authored content
outside the markers is left byte-for-byte as it was.

A derived triple goes into the file that declares (rdf:type) its subject.
Only tgs: subjects get triples; links to external IRIs (Wikipedia, DBpedia)
are not mirrored.

Usage:
    python scripts/derive/compute_inverses.py            # write changes
    python scripts/derive/compute_inverses.py --dry-run  # report only
    python scripts/derive/compute_inverses.py --check    # exit 1 if stale (CI)
"""
import argparse, collections, re, sys
from pathlib import Path
import rdflib
from rdflib.namespace import RDF

SEED = Path("data/seed")
EXCLUDE = {"merged_for_protege.ttl", "scratch.ttl"}
BEGIN = "# ===== BEGIN DERIVED INVERSES (scripts/derive/compute_inverses.py; do not edit by hand) ====="
END = "# ===== END DERIVED INVERSES ====="
TGS = "http://example.org/tgs#"
SKOS = "http://www.w3.org/2004/02/skos/core#"
DCT = "http://purl.org/dc/terms/"
THINKR = "http://example.org/thinkr#"

INVERSE_PAIRS = [
    (DCT + "references", DCT + "isReferencedBy"),
    (SKOS + "broader", SKOS + "narrower"),
    (SKOS + "broadMatch", SKOS + "narrowMatch"),
    (DCT + "hasPart", DCT + "isPartOf"),
    (SKOS + "hasTopConcept", SKOS + "topConceptOf"),
]
SYMMETRIC_BUILTIN = [SKOS + "related", SKOS + "relatedMatch", SKOS + "closeMatch", SKOS + "exactMatch"]

SECTION_RE = re.compile(r"\n*" + re.escape(BEGIN) + r".*?" + re.escape(END) + r"\n?", re.S)

def strip_section(text):
    return SECTION_RE.sub("\n", text).rstrip("\n") + "\n"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    files = sorted(p for p in SEED.glob("*.ttl") if p.name not in EXCLUDE)
    texts, graphs, g = {}, {}, rdflib.Graph()
    for p in files:
        t = strip_section(p.read_text(encoding="utf-8"))
        texts[p] = t
        fg = rdflib.Graph(); fg.parse(data=t, format="turtle", publicID=str(p))
        graphs[p] = fg
        for tr in fg: g.add(tr)

    # where each tgs: individual is declared
    home, multi = {}, collections.defaultdict(set)
    for p, fg in graphs.items():
        for s in set(fg.subjects(RDF.type)):
            if str(s).startswith(TGS) and str(s) != TGS:
                multi[s].add(p.name)
                home.setdefault(s, p)

    symmetric = set(SYMMETRIC_BUILTIN) | {str(s) for s in g.subjects(RDF.type, rdflib.OWL.SymmetricProperty)}
    rules = []  # (from_pred, to_pred)
    for a, b in INVERSE_PAIRS:
        rules += [(a, b), (b, a)]
    rules += [(p, p) for p in symmetric]

    derived = collections.defaultdict(set)   # file -> {(s,p,o)}
    skipped_external, orphans = 0, set()
    for frm, to in rules:
        P, Q = rdflib.URIRef(frm), rdflib.URIRef(to)
        for s, o in g.subject_objects(P):
            if not isinstance(o, rdflib.URIRef) or (o, Q, s) in g:
                continue
            if not str(o).startswith(TGS):
                skipped_external += 1; continue
            if o not in home:
                orphans.add(o); continue
            derived[home[o]].add((o, Q, s))

    total = sum(len(v) for v in derived.values())
    by_pred = collections.Counter(str(t[1]).split("/")[-1].split("#")[-1] for v in derived.values() for t in v)
    print(f"Derived triples needed: {total}")
    for k, n in by_pred.most_common(): print(f"  {k}: {n}")
    for p in files:
        if derived.get(p): print(f"  -> {p.name}: {len(derived[p])}")
    if skipped_external: print(f"Skipped {skipped_external} links whose object is external (not tgs:)")
    if orphans: print(f"WARNING: {len(orphans)} tgs: objects declared nowhere (orphans), e.g. {sorted(orphans)[:3]}")
    dup = {s: f for s, f in multi.items() if len(f) > 1}
    if dup: print(f"Note: {len(dup)} individuals are typed in more than one file; derived triples go to the first: e.g. {list(dup.items())[:2]}")

    changed = []
    for p in files:
        fg = graphs[p]
        orig = p.read_text(encoding="utf-8")
        new = texts[p] if BEGIN in orig else orig  # untouched unless it has or gets a derived section
        if derived.get(p):
            # only prefixes this file itself declares, so output always parses
            pfx = dict(re.findall(r"@prefix\s+([\w-]*):\s*<([^>]+)>", texts[p]))
            ns_sorted = sorted(pfx.items(), key=lambda kv: -len(kv[1]))
            def q(u):
                u = str(u)
                for pre, ns in ns_sorted:
                    if u.startswith(ns):
                        local = u[len(ns):]
                        if re.fullmatch(r"[A-Za-z_][\w.\-]*", local) and not local.endswith("."):
                            return f"{pre}:{local}"
                return f"<{u}>"
            bysub = collections.defaultdict(lambda: collections.defaultdict(list))
            for s, pr, o in derived[p]: bysub[s][pr].append(o)
            out = [BEGIN, "# Each triple below mirrors a hand-authored one elsewhere in data/seed/."]
            for s in sorted(bysub, key=str):
                preds = sorted(bysub[s], key=str)
                lines = [f"{q(s)}"]
                for i, pr in enumerate(preds):
                    objs = ", ".join(q(o) for o in sorted(bysub[s][pr], key=str))
                    lines.append(f"    {q(pr)} {objs}" + (" ." if i == len(preds) - 1 else " ;"))
                out.append("\n".join(lines))
            new = texts[p] + "\n" + "\n\n".join(out) + "\n" + END + "\n"
        if new != p.read_text(encoding="utf-8"):
            changed.append((p, new))

    if args.check:
        if changed:
            print(f"STALE: {len(changed)} seed files need compute_inverses.py: " + ", ".join(p.name for p, _ in changed))
            sys.exit(1)
        print("OK: all inverse and symmetric links are present."); return
    if args.dry_run:
        print(f"(dry run) would update {len(changed)} files"); return
    for p, new in changed:  # validate every file before writing any
        rdflib.Graph().parse(data=new, format="turtle", publicID=str(p))
    for p, new in changed:
        p.write_text(new, encoding="utf-8")
        print(f"Updated {p}")

if __name__ == "__main__":
    main()
