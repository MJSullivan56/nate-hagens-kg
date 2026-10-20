#!/usr/bin/env python3
"""
Computes rdfs:label for every thinkr:Human and thinkr:Persona individual
that has a skos:prefLabel, disambiguating the two by appending "(human)"
or "(persona)" — needed because a real person in this graph is modeled as
TWO individuals (a Human and a Persona linked via thinkr:actsThrough),
both legitimately carrying the same skos:prefLabel, which makes Protege's
default individual list (and anything else that renders by prefLabel)
show every person's name twice with no way to tell the entries apart.
DERIVED — never hand-write these. Re-run after adding any new Human or
Persona individual, and commit the result.

Written and tested 2026-08-22, matching the exact discipline
scripts/compute_relationships.py already established for this project:
- Text surgery on the SAME file where each individual is already
  declared (data/seed/humans.ttl for Human, data/seed/personas.ttl for
  Persona) — never a new central file, matching the project's own
  one-class-per-file convention.
- Literal-protected regex substitution, NOT rdflib's Graph.serialize()
  — that round-trip is confirmed (see compute_confidence.py's own
  docstring, 2026-07-15 incident) to silently strip hand-authored
  section comments and skos:scopeNotes on serialization.
- Self-verification: after writing, re-parse from disk and confirm the
  written file actually matches the desired state — a clean run is not
  trusted as proof of correctness on its own.

Usage:
    python compute_disambiguating_labels.py            # apply and write back
    python compute_disambiguating_labels.py --dry-run  # preview only
"""
import argparse
import glob
import re
import rdflib
from rdflib import Graph, Namespace, RDF

TGS = Namespace("http://example.org/tgs#")
THINKR = Namespace("http://example.org/thinkr#")
SKOS = Namespace("http://www.w3.org/2004/02/skos/core#")
RDFS = Namespace("http://www.w3.org/2000/01/rdf-schema#")

TARGETS = {
    THINKR.Human: ("data/seed/humans.ttl", "human"),
    THINKR.Persona: ("data/seed/personas.ttl", "persona"),
}

LITERAL_RE = re.compile(r'"(?:[^"\\]|\\.)*"(?:@[a-zA-Z-]+|\^\^[\w:]+)?')


def local(uri):
    return str(uri).split('#')[-1]


def short_name(local_name, class_local):
    """Bare individual name with the class-prefix stripped, matching what
    find_individual_blocks() captures from the TTL text itself. Every dict
    keyed by individual must use this, not local() alone — confirmed the
    hard way tonight (the QuadrantNode-facet linking script hit the exact
    same key-mismatch bug earlier this session)."""
    prefix = class_local + "."
    return local_name[len(prefix):] if local_name.startswith(prefix) else local_name


def load_full_graph():
    g = Graph()
    for f in glob.glob('data/seed/**/*.ttl', recursive=True):
        g.parse(f, format='turtle')
    return g


def compute_desired(g):
    """cls -> {individual_local_name: desired_label_text}"""
    desired = {}
    for cls, (_, suffix) in TARGETS.items():
        for indiv in g.subjects(RDF.type, cls):
            if isinstance(indiv, rdflib.BNode):
                continue
            pref_labels = list(g.objects(indiv, SKOS.prefLabel))
            if not pref_labels:
                continue  # nothing to disambiguate without a real prefLabel to base it on
            base_text = str(pref_labels[0])
            desired.setdefault(cls, {})[short_name(local(indiv), local(cls))] = f"{base_text} ({suffix})"
    return desired


def compute_current(g):
    current = {}
    for cls in TARGETS:
        for indiv in g.subjects(RDF.type, cls):
            if isinstance(indiv, rdflib.BNode):
                continue
            labels = list(g.objects(indiv, RDFS.label))
            if labels:
                current.setdefault(cls, {})[short_name(local(indiv), local(cls))] = str(labels[0])
    return current


def diff(desired, current):
    changes = []
    for cls in TARGETS:
        d, c = desired.get(cls, {}), current.get(cls, {})
        for name in sorted(set(d) | set(c)):
            if d.get(name) != c.get(name):
                changes.append((cls, name, d.get(name), c.get(name)))
    return changes


def protect_literals(text):
    lookup = []

    def repl(m):
        lookup.append(m.group(0))
        return f'\x00LIT{len(lookup) - 1}\x00'

    return LITERAL_RE.sub(repl, text), lookup


def restore_literals(text, lookup):
    def repl(m):
        return lookup[int(m.group(1))]
    return re.sub(r'\x00LIT(\d+)\x00', repl, text)


def find_individual_blocks(text, class_local):
    """Yields (name, start, end) for each individual's block, matching
    'tgs:<ClassLocal>.<Name> a thinkr:<ClassLocal>' declarations."""
    pattern = re.compile(r'tgs:' + class_local + r'\.(\w+)\s+a\s+thinkr:' + class_local + r'\b')
    starts = [(m.group(1), m.start()) for m in pattern.finditer(text)]
    blocks = []
    for i, (name, start) in enumerate(starts):
        end = starts[i + 1][1] if i + 1 < len(starts) else len(text)
        blocks.append((name, start, end))
    return blocks


PREFLABEL_RE = re.compile(r'([ \t]*)skos:prefLabel\s+\x00LIT\d+\x00\s*([;.])\n?')


def escape_turtle_literal(text):
    """Escape backslashes and double-quotes for safe inclusion in a new
    Turtle string literal — needed because rdflib returns the UNESCAPED
    string value from a parsed Literal (e.g. 'Clemence "CC" Currie', not
    'Clemence \\"CC\\" Currie'), and writing that straight into a fresh
    quoted literal without re-escaping produces invalid Turtle syntax.
    Confirmed the hard way: this exact case broke the first write attempt."""
    return text.replace('\\', '\\\\').replace('"', '\\"')


def insert_label(block_text, label_text):
    """Insert thinkr rdfs:label right after skos:prefLabel, matching the
    project's own established property-ordering convention."""
    escaped_label = escape_turtle_literal(label_text)
    m = PREFLABEL_RE.search(block_text)
    if not m:
        return block_text, False  # no prefLabel line found to anchor on — leave untouched, flagged by caller
    indent, terminator = m.group(1), m.group(2)
    if terminator == '.':
        # prefLabel was the terminal predicate — label becomes the new terminal instead
        new_prefLabel_line = block_text[m.start():m.end()].rstrip()
        if new_prefLabel_line.endswith('.'):
            new_prefLabel_line = new_prefLabel_line[:-1].rstrip() + ' ;\n'
        insertion = new_prefLabel_line + f'{indent}rdfs:label "{escaped_label}"@en .\n'
    else:
        insertion = block_text[m.start():m.end()] + f'{indent}rdfs:label "{escaped_label}"@en ;\n'
    new_text = block_text[:m.start()] + insertion + block_text[m.end():]
    return new_text, True


def apply_changes(desired, file_path, class_local, changed_names):
    with open(file_path, 'r') as f:
        raw_text = f.read()

    safe_text, lookup = protect_literals(raw_text)
    blocks = find_individual_blocks(safe_text, class_local)

    skipped = []
    for name, start, end in sorted(blocks, key=lambda b: -b[1]):
        if name not in changed_names:
            continue
        block = safe_text[start:end]
        label_text = desired[name]
        new_block, ok = insert_label(block, label_text)
        if not ok:
            skipped.append(name)
            continue
        safe_text = safe_text[:start] + new_block + safe_text[end:]

    final_text = restore_literals(safe_text, lookup)
    with open(file_path, 'w') as f:
        f.write(final_text)
    return skipped


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    g = load_full_graph()
    desired = compute_desired(g)
    current = compute_current(g)
    changes = diff(desired, current)

    if not changes:
        print("No changes needed — every Human/Persona individual's rdfs:label already matches its desired disambiguated form.")
        return

    print(f"{len(changes)} label(s) needed:\n")
    by_cls_names = {}
    for cls, name, want, have in changes:
        by_cls_names.setdefault(cls, set()).add(name)
        arrow = f'"{have}"' if have else "(none)"
        print(f"  {local(cls)}.{name}: {arrow} -> \"{want}\"")

    if args.dry_run:
        print("\n[DRY RUN] No files written.")
        return

    all_skipped = []
    for cls, (file_path, _suffix) in TARGETS.items():
        names = by_cls_names.get(cls)
        if not names:
            continue
        skipped = apply_changes(desired[cls], file_path, local(cls), names)
        all_skipped += [(cls, n) for n in skipped]

    if all_skipped:
        print(f"\nWARNING — {len(all_skipped)} individual(s) had no skos:prefLabel line to anchor on, skipped:")
        for cls, n in all_skipped:
            print(f"  {local(cls)}.{n}")

    # Self-verify: re-parse from disk, confirm the written files actually match `desired`.
    g2 = load_full_graph()
    current2 = compute_current(g2)
    remaining = diff(desired, current2)
    # Skipped individuals are expected to still show as a remaining diff — don't fail on those specifically.
    genuine_remaining = [c for c in remaining if (c[0], c[1]) not in all_skipped]
    if genuine_remaining:
        print(f"\nVERIFICATION FAILED — {len(genuine_remaining)} mismatch(es) still present after writing:")
        for cls, name, want, have in genuine_remaining:
            print(f"  {local(cls)}.{name}: wanted \"{want}\", found {have!r}")
        raise SystemExit(1)

    print(f"\nDone — verified against a fresh re-parse. {len(changes) - len(all_skipped)} label(s) written.")


if __name__ == "__main__":
    main()
