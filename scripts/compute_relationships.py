"""
Computes thinkr:has{Personal,Professional,Academic,Intellectual,Legal}Relationship
on every thinkr:Persona from the thinkr:Relationship individuals it's a party to
(thinkr:hasSubject or thinkr:hasObject), driven entirely by each Relationship's own
thinkr:hasRelationshipType. DERIVED — never hand-write these. Re-run after adding,
editing, or retyping any Relationship, and commit the result.

Rule: for a Relationship R with hasRelationshipType value(s) T, every party to R
(subject and/or object) that is itself a thinkr:Persona gets R asserted under
has<T>Relationship — once per T value, so a Relationship with multiple types
(e.g. Academic+Personal+Professional) legitimately appears under multiple
properties on the same Persona. A non-Persona party (Organization,
AcademicInstitution, SchoolOfThought) never gets one, since has*Relationship's
domain is thinkr:Persona only. Symmetric: both the subject's and the object's
Persona get it, when both are Personas.

Unlike scripts/compute_confidence.py, this script does NOT reserialize files via
rdflib's Graph.serialize() — that round-trip strips every hand-authored section
comment and skos:scopeNote (confirmed happening to linknotes.ttl on 2026-07-15
when compute_confidence.py ran). Instead it does targeted, literal-safe text
surgery on data/seed/personas.ttl directly: string literals (which can contain
";"/"."/"," — confirmed via grep before writing this) are placeholdered out
before any structural regex runs, so the substitution can never accidentally
match inside a scopeNote's prose. Every comment and every other predicate is
left byte-for-byte untouched.

Also follows CLAUDE.md's multi-value-per-line ground rule: a freshly emitted
property with 2+ values gets one value per line so an editor can tell at a
glance it's multi-valued; exactly 1 value stays on the same line as the
predicate. Caught 2026-07-15 as a real gap — this script's first version
always emitted single-line comma-joined values regardless of count, which
would have silently regressed the formatting the next time it actually had
something to write (it hadn't yet, since the graph already matched by hand).

Usage:
    python scripts/compute_relationships.py            # apply and write back
    python scripts/compute_relationships.py --dry-run  # preview only
"""

import argparse
import glob
import re
import rdflib
from rdflib import Graph, Namespace, RDF

TGS = Namespace("http://example.org/tgs#")
THINKR = Namespace("http://example.org/thinkr#")

PERSONAS_FILE = "data/seed/personas.ttl"

TYPE_TO_PROP = {
    "RelationshipType.Personal": "hasPersonalRelationship",
    "RelationshipType.Professional": "hasProfessionalRelationship",
    "RelationshipType.Academic": "hasAcademicRelationship",
    "RelationshipType.Intellectual": "hasIntellectualRelationship",
    "RelationshipType.Legal": "hasLegalRelationship",
}
PROP_NAMES = sorted(TYPE_TO_PROP.values())
PROP_ALTERNATION = "|".join(p[len("has"):-len("Relationship")] for p in PROP_NAMES)

LITERAL_RE = re.compile(r'"(?:[^"\\]|\\.)*"(?:@[a-zA-Z-]+|\^\^[\w:]+)?')
PROP_CHUNK_RE = re.compile(
    r'[ \t]*thinkr:has(?:' + PROP_ALTERNATION + r')Relationship'
    r'\s+(?:tgs:Relationship\.\w+\s*,\s*)*tgs:Relationship\.\w+\s*([;.])\n?'
)
ACTS_THROUGH_RE = re.compile(r'(thinkr:actsThrough\s+tgs:Human\.\w+\s*;\n)')
PERSONA_START_RE = re.compile(r'tgs:Persona\.(\w+)\s+a\s+thinkr:Persona\b')


def local(uri):
    return str(uri).split('#')[-1]


def persona_local(uri):
    """Bare individual name with the 'Persona.' class prefix stripped, matching
    what find_persona_blocks() captures from the TTL text itself (group 1 of
    PERSONA_START_RE never includes 'Persona.' — it's consumed by the regex
    before the capture group starts). Every dict in this script that's keyed
    by a Persona must use this, not local(), or block lookups in
    apply_changes() silently fail to match — confirmed the hard way via the
    sandbox test in this file's own development, caught by inspecting the
    written output rather than trusting the script's own success message."""
    loc = local(uri)
    return loc[len("Persona."):] if loc.startswith("Persona.") else loc


def load_full_graph():
    g = Graph()
    for f in glob.glob('data/seed/**/*.ttl', recursive=True):
        g.parse(f, format='turtle')
    return g


def compute_desired(g):
    """persona_local -> {prop_name: set(relationship_local)}"""
    desired = {}
    for rel in g.subjects(RDF.type, THINKR.Relationship):
        subj = next(g.objects(rel, THINKR.hasSubject), None)
        obj = next(g.objects(rel, THINKR.hasObject), None)
        types = list(g.objects(rel, THINKR.hasRelationshipType))
        for party in (subj, obj):
            if party is None or (party, RDF.type, THINKR.Persona) not in g:
                continue
            for t in types:
                prop = TYPE_TO_PROP.get(local(t))
                if prop:
                    desired.setdefault(persona_local(party), {}).setdefault(prop, set()).add(local(rel))
    return desired


def compute_current(g):
    current = {}
    for prop_name in PROP_NAMES:
        for persona, rel in g.subject_objects(THINKR[prop_name]):
            current.setdefault(persona_local(persona), {}).setdefault(prop_name, set()).add(local(rel))
    return current


def diff(desired, current):
    changes = []
    for p in sorted(set(desired) | set(current)):
        d, c = desired.get(p, {}), current.get(p, {})
        for prop in sorted(set(d) | set(c)):
            added, removed = d.get(prop, set()) - c.get(prop, set()), c.get(prop, set()) - d.get(prop, set())
            if added or removed:
                changes.append((p, prop, added, removed))
    return changes


def protect_literals(text):
    """Replace every string literal with a placeholder so ';'/','/'.' inside
    prose can never be mistaken for Turtle structure. Returns (safe_text, lookup)."""
    lookup = []

    def repl(m):
        lookup.append(m.group(0))
        return f'\x00LIT{len(lookup) - 1}\x00'

    return LITERAL_RE.sub(repl, text), lookup


def restore_literals(text, lookup):
    def repl(m):
        return lookup[int(m.group(1))]
    return re.sub(r'\x00LIT(\d+)\x00', repl, text)


def rewrite_block(block_text, desired_for_persona):
    """block_text has literals already placeholdered. Returns the rewritten block."""
    matches = list(PROP_CHUNK_RE.finditer(block_text))
    had_terminal = any(m.group(1) == '.' for m in matches)

    # Strip every existing has*Relationship chunk.
    new_text = PROP_CHUNK_RE.sub('', block_text)

    fresh_lines = []
    for prop in PROP_NAMES:
        rels = sorted(desired_for_persona.get(prop, set()))
        if not rels:
            continue
        if len(rels) == 1:
            # Single value: one line, per this project's convention that an
            # editor should be able to tell multi- vs single-valued apart at
            # a glance (CLAUDE.md ground rules) — reserve the multi-line
            # shape for when there's actually more than one value to see.
            fresh_lines.append(f"    thinkr:{prop} tgs:{rels[0]} ;\n")
        else:
            values = ",\n".join(f"        tgs:{r}" for r in rels)
            fresh_lines.append(f"    thinkr:{prop}\n{values} ;\n")

    if fresh_lines:
        insertion = "".join(fresh_lines)
        m = ACTS_THROUGH_RE.search(new_text)
        if m:
            new_text = new_text[:m.end()] + insertion + new_text[m.end():]
        else:
            new_text = insertion + new_text

    if had_terminal:
        # The removed chunk(s) included the block's own terminator. Whatever
        # predicate is now last must end in '.' instead of ';'. Find the
        # final ' ;' in the block (ignoring trailing whitespace) and swap it.
        stripped = new_text.rstrip()
        if stripped.endswith(';'):
            new_text = stripped[:-1].rstrip() + " .\n"
        # else: a freshly-inserted has*Relationship line is already the
        # terminal-safe case doesn't apply since we always emit ';' for those
        # (they're never last — inserted right after actsThrough).

    return new_text


def find_persona_blocks(text):
    """Yields (name, start, end) for each Persona individual's full block,
    bounded by the next 'tgs:Persona.' occurrence or end of string."""
    starts = [(m.group(1), m.start()) for m in PERSONA_START_RE.finditer(text)]
    blocks = []
    for i, (name, start) in enumerate(starts):
        end = starts[i + 1][1] if i + 1 < len(starts) else len(text)
        blocks.append((name, start, end))
    return blocks


def apply_changes(desired, changed_personas):
    with open(PERSONAS_FILE, 'r') as f:
        raw_text = f.read()

    safe_text, lookup = protect_literals(raw_text)
    blocks = find_persona_blocks(safe_text)

    # Rebuild back-to-front so earlier offsets stay valid.
    for name, start, end in sorted(blocks, key=lambda b: -b[1]):
        if name not in changed_personas:
            continue
        block = safe_text[start:end]
        new_block = rewrite_block(block, desired.get(name, {}))
        safe_text = safe_text[:start] + new_block + safe_text[end:]

    final_text = restore_literals(safe_text, lookup)
    with open(PERSONAS_FILE, 'w') as f:
        f.write(final_text)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    g = load_full_graph()
    desired = compute_desired(g)
    current = compute_current(g)
    changes = diff(desired, current)

    if not changes:
        print("No changes needed — has*Relationship already matches every Relationship's hasRelationshipType, both directions.")
        return

    print(f"{len(changes)} persona/property change(s) needed:\n")
    changed_personas = set()
    for persona, prop, added, removed in changes:
        changed_personas.add(persona)
        if added:
            print(f"  + {persona} {prop}: add {sorted(added)}")
        if removed:
            print(f"  - {persona} {prop}: remove {sorted(removed)}")

    if args.dry_run:
        print("\n[DRY RUN] No files written.")
        return

    apply_changes(desired, changed_personas)

    # Self-verify: re-parse from disk and confirm the written file actually
    # matches `desired` exactly. Never trust "the script ran without an
    # error" as proof it worked — see persona_local()'s own docstring for
    # why that distinction matters in this exact script.
    g2 = load_full_graph()
    current2 = compute_current(g2)
    remaining = diff(desired, current2)
    if remaining:
        print(f"\nVERIFICATION FAILED — {len(remaining)} mismatch(es) still present after writing:")
        for persona, prop, added, removed in remaining:
            if added:
                print(f"  still missing: {persona} {prop} {sorted(added)}")
            if removed:
                print(f"  still stale:   {persona} {prop} {sorted(removed)}")
        raise SystemExit(1)

    print(f"\nUpdated {PERSONAS_FILE} ({len(changed_personas)} Persona block(s) rewritten) — verified against a fresh re-parse.")


if __name__ == "__main__":
    main()
