"""
Promotes APPROVED rows from the DuckDB staging tables into RDF triples,
following the exact pattern used in data/seed/links.ttl (a relation triple
+ a tgs:LinkNote carrying rationale and confidence).

Nothing here is auto-marked "curated" just because it's in the graph —
that's still true; what changes is confidence goes from unset (staging) to
whatever you choose at promotion time. Default is "curated" because the act
of approving the row in the DuckDB review step *is* the review — if you want
a lighter-touch promotion that stays "candidate" pending a second pass, use
--confidence candidate.

Usage:
    python extraction/promote_to_rdf.py                  # promotes concepts + links, marks curated
    python extraction/promote_to_rdf.py --confidence candidate
    python extraction/promote_to_rdf.py --dry-run
"""

import argparse
import re
import duckdb
from rdflib import Graph, Namespace, RDF, RDFS, Literal, URIRef
from rdflib.namespace import DCTERMS, SKOS, OWL

TGS = Namespace("http://example.org/tgs#")
DB_PATH = "extraction/staging.duckdb"
GENERATED_CONCEPTS = "data/generated/concepts.ttl"
GENERATED_LINKS = "data/generated/links.ttl"

VALID_PREDICATES = {"echoesIdeaOf", "influencedBy", "contrastsWith", "appliesTo"}


def slugify(label: str) -> str:
    """Turn a human label into a URI-safe local name, matching the style
    used elsewhere in the repo (e.g. 'The Great Simplification' -> GreatSimplification)."""
    words = re.findall(r"[A-Za-z0-9]+", label)
    return "".join(w.capitalize() for w in words)


def load_existing_labels(seed_dir="data/seed"):
    """So we can validate candidate_links reference real existing entities
    before promoting — catches typos instead of silently creating orphan URIs."""
    g = Graph()
    g.parse(f"{seed_dir}/concepts.ttl", format="turtle")
    g.parse(f"{seed_dir}/people.ttl", format="turtle")
    label_to_uri = {}
    for s, o in g.subject_objects(SKOS.prefLabel):
        label_to_uri[str(o)] = s
    return label_to_uri


def promote_concepts(con, g, confidence, dry_run):
    rows = con.execute(
        "SELECT id, proposed_label, proposed_def, source_note FROM candidate_concepts WHERE status = 'approved'"
    ).fetchall()
    for cid, label, definition, source_note in rows:
        uri = TGS[f"Concept.{slugify(label)}"]
        g.add((uri, RDF.type, TGS.Concept))
        g.add((uri, RDF.type, OWL.NamedIndividual))
        g.add((uri, SKOS.prefLabel, Literal(label, lang="en")))
        g.add((uri, SKOS.definition, Literal(definition, lang="en")))
        if source_note:
            g.add((uri, DCTERMS.description, Literal(f"Source note: {source_note}")))
        print(f"{'[DRY RUN] ' if dry_run else ''}Promoting concept: {label} -> {uri}")


def promote_links(con, g, label_to_uri, confidence, dry_run):
    rows = con.execute(
        "SELECT id, subject_label, predicate, object_label, rationale FROM candidate_links WHERE status = 'approved'"
    ).fetchall()
    for lid, subj_label, predicate, obj_label, rationale in rows:
        if predicate not in VALID_PREDICATES:
            print(f"SKIP link id={lid}: unknown predicate '{predicate}' (must be one of {VALID_PREDICATES})")
            continue
        # Fallback naming for unmatched labels defaults to Concept.<slug> — this is a
        # best guess only; unmatched labels always print a warning below, so review
        # the resulting URI's class assertion manually if you see one.
        subj_uri = label_to_uri.get(subj_label) or TGS[f"Concept.{slugify(subj_label)}"]
        obj_uri = label_to_uri.get(obj_label) or TGS[f"Concept.{slugify(obj_label)}"]
        if subj_label not in label_to_uri:
            print(f"WARNING link id={lid}: subject '{subj_label}' not found in existing seed data — check for a typo.")
        if obj_label not in label_to_uri:
            print(f"WARNING link id={lid}: object '{obj_label}' not found in existing seed data — check for a typo.")

        g.add((subj_uri, TGS[predicate], obj_uri))
        note_uri = TGS[f"LinkNote.{slugify(subj_label)}{slugify(obj_label)}"]
        g.add((note_uri, RDF.type, TGS.LinkNote))
        g.add((note_uri, RDF.type, OWL.NamedIndividual))
        g.add((note_uri, TGS.aboutSubject, subj_uri))
        confidence_uri = TGS[f"ConfidenceLevel.{confidence.capitalize()}"]
        g.add((note_uri, TGS.aboutObject, obj_uri))
        g.add((note_uri, DCTERMS.description, Literal(rationale, lang="en")))
        g.add((note_uri, TGS.confidence, confidence_uri))
        print(f"{'[DRY RUN] ' if dry_run else ''}Promoting link: {subj_label} --{predicate}--> {obj_label} [{confidence}]")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--confidence", default="curated", choices=["curated", "candidate"])
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    import os
    os.makedirs("data/generated", exist_ok=True)

    con = duckdb.connect(DB_PATH)
    label_to_uri = load_existing_labels()

    concepts_g = Graph()
    concepts_g.bind("tgs", TGS)
    promote_concepts(con, concepts_g, args.confidence, args.dry_run)

    links_g = Graph()
    links_g.bind("tgs", TGS)
    promote_links(con, links_g, label_to_uri, args.confidence, args.dry_run)

    if not args.dry_run:
        if len(concepts_g) > 0:
            concepts_g.serialize(destination=GENERATED_CONCEPTS, format="turtle")
            print(f"Wrote {GENERATED_CONCEPTS} ({len(concepts_g)} triples)")
        if len(links_g) > 0:
            links_g.serialize(destination=GENERATED_LINKS, format="turtle")
            print(f"Wrote {GENERATED_LINKS} ({len(links_g)} triples)")

        con.execute("UPDATE candidate_concepts SET status = 'promoted' WHERE status = 'approved'")
        con.execute("UPDATE candidate_links SET status = 'promoted' WHERE status = 'approved'")
    else:
        print("\n[DRY RUN] No files written, no DB rows updated.")

    con.close()


if __name__ == "__main__":
    main()
