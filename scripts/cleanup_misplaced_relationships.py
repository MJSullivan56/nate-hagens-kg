#!/usr/bin/env python3
"""
Removes thinkr:has{Personal,Professional,Academic,Intellectual,Legal}Relationship
assertions from individuals that are NOT thinkr:Persona — a real data error found
during a clean-room, end-to-end pipeline verification 2026-08-22.

compute_relationships.py's own rule is explicit: has*Relationship's domain is
thinkr:Persona only, and a non-Persona party (Organization, AcademicInstitution,
SchoolOfThought) should never carry one. That script's own self-verification
correctly DETECTS this exact violation, but can't FIX it — it only writes to
data/seed/personas.ttl, and these stray assertions live in organizations.ttl,
academicinstitutions.ttl, and schoolsofthought.ttl. This script closes that gap.

DERIVED — never hand-write the absence of these properties back in. If a real
Organization/AcademicInstitution/SchoolOfThought relationship needs modeling,
it needs its own real property (this project doesn't have one yet — that's a
separate, real design decision, not something to route through has*Relationship).

Reuses the exact same literal-protected text-surgery approach and
PROP_CHUNK_RE-style pattern established in compute_relationships.py, applied
across the 3 additional files it doesn't touch.

Usage:
    python cleanup_misplaced_relationships.py            # apply and write back
    python cleanup_misplaced_relationships.py --dry-run  # preview only
"""
import argparse
import re
import rdflib
from rdflib import Graph, Namespace, RDF

TGS = Namespace("http://example.org/tgs#")
THINKR = Namespace("http://example.org/thinkr#")

TARGET_FILES = {
    THINKR.Organization: "data/seed/organizations.ttl",
    THINKR.AcademicInstitution: "data/seed/academicinstitutions.ttl",
    THINKR.SchoolOfThought: "data/seed/schoolsofthought.ttl",
}

PROP_NAMES = ["hasPersonalRelationship", "hasProfessionalRelationship",
              "hasAcademicRelationship", "hasIntellectualRelationship", "hasLegalRelationship"]
PROP_ALTERNATION = "|".join(p[len("has"):-len("Relationship")] for p in PROP_NAMES)

LITERAL_RE = re.compile(r'"(?:[^"\\]|\\.)*"(?:@[a-zA-Z-]+|\^\^[\w:]+)?')
PROP_CHUNK_RE = re.compile(
    r'[ \t]*thinkr:has(?:' + PROP_ALTERNATION + r')Relationship'
    r'\s+(?:tgs:Relationship\.\w+\s*,\s*)*tgs:Relationship\.\w+\s*([;.])\n?'
)


def local(uri):
    return str(uri).split('#')[-1]


def short_name(local_name, class_local):
    """Bare individual name with the class-prefix stripped, matching what
    find_individual_blocks() captures from the TTL text itself. This exact
    bug (using the full local name as a dict/set key) has now bitten THREE
    scripts written tonight — compute_disambiguating_labels.py, the
    QuadrantNode-facet linking script, and this one — worth remembering as
    a standing gotcha, not a one-off."""
    prefix = class_local + "."
    return local_name[len(prefix):] if local_name.startswith(prefix) else local_name


def load_full_graph():
    import glob
    g = Graph()
    for f in glob.glob('data/seed/**/*.ttl', recursive=True):
        g.parse(f, format='turtle')
    return g


def find_violations(g):
    """cls -> set(individual_local_names) currently carrying a stray
    has*Relationship property, in violation of the Persona-only rule."""
    violations = {}
    for cls in TARGET_FILES:
        for prop_name in PROP_NAMES:
            for indiv in g.subjects(THINKR[prop_name], None):
                if (indiv, RDF.type, cls) in g:
                    violations.setdefault(cls, set()).add(short_name(local(indiv), local(cls)))
    return violations


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
    pattern = re.compile(r'tgs:' + class_local + r'\.(\w+)\s+a\s+thinkr:' + class_local + r'\b')
    starts = [(m.group(1), m.start()) for m in pattern.finditer(text)]
    blocks = []
    for i, (name, start) in enumerate(starts):
        end = starts[i + 1][1] if i + 1 < len(starts) else len(text)
        blocks.append((name, start, end))
    return blocks


def strip_relationship_chunks(block_text):
    """Remove any has*Relationship chunk(s), fixing up the terminal '.'
    if the removed chunk was the block's own terminating predicate —
    same logic as compute_relationships.py's own rewrite_block()."""
    matches = list(PROP_CHUNK_RE.finditer(block_text))
    if not matches:
        return block_text, False
    had_terminal = any(m.group(1) == '.' for m in matches)
    new_text = PROP_CHUNK_RE.sub('', block_text)
    if had_terminal:
        stripped = new_text.rstrip()
        if stripped.endswith(';'):
            new_text = stripped[:-1].rstrip() + " .\n"
    return new_text, True


def apply_cleanup(file_path, class_local, names_to_fix):
    with open(file_path, 'r') as f:
        raw_text = f.read()
    safe_text, lookup = protect_literals(raw_text)
    blocks = find_individual_blocks(safe_text, class_local)

    fixed = []
    for name, start, end in sorted(blocks, key=lambda b: -b[1]):
        if name not in names_to_fix:
            continue
        block = safe_text[start:end]
        new_block, changed = strip_relationship_chunks(block)
        if changed:
            safe_text = safe_text[:start] + new_block + safe_text[end:]
            fixed.append(name)

    final_text = restore_literals(safe_text, lookup)
    with open(file_path, 'w') as f:
        f.write(final_text)
    return fixed


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    g = load_full_graph()
    violations = find_violations(g)

    total = sum(len(v) for v in violations.values())
    if not total:
        print("No violations found — every has*Relationship assertion is correctly on a Persona.")
        return

    print(f"{total} non-Persona individual(s) with stray has*Relationship properties:\n")
    for cls, names in violations.items():
        for name in sorted(names):
            print(f"  {local(cls)}.{name}")

    if args.dry_run:
        print("\n[DRY RUN] No files written.")
        return

    all_fixed = {}
    for cls, names in violations.items():
        file_path = TARGET_FILES[cls]
        fixed = apply_cleanup(file_path, local(cls), names)
        all_fixed[cls] = fixed
        print(f"\nUpdated {file_path} ({len(fixed)} individual(s) cleaned)")

    # Self-verify: re-parse and confirm no violations remain for what we targeted.
    g2 = load_full_graph()
    remaining = find_violations(g2)
    genuine_remaining = {cls: names & violations.get(cls, set()) for cls, names in remaining.items()}
    genuine_remaining = {cls: names for cls, names in genuine_remaining.items() if names}
    if genuine_remaining:
        print(f"\nVERIFICATION FAILED — violations still present after cleanup:")
        for cls, names in genuine_remaining.items():
            print(f"  {local(cls)}: {sorted(names)}")
        raise SystemExit(1)

    print(f"\nDone — verified against a fresh re-parse. {total} stray assertion(s) removed.")


if __name__ == "__main__":
    main()
