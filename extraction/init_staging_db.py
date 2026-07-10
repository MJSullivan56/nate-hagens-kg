"""
Initializes the DuckDB staging database used as a review queue between
LLM-assisted extraction (extraction/README.md steps 3-4) and the RDF graph.

Why DuckDB here and not straight into Turtle: reviewing a batch of
LLM-proposed candidate links is a "look at a row, accept/reject/edit it"
workflow — that's a SQL table with a status column, not a text-editing task.
Once a row is approved here, promote_to_rdf.py turns it into a proper triple
with a tgs:LinkNote, matching the pattern in data/seed/links.ttl.

Usage:
    python extraction/init_staging_db.py
"""

import duckdb

DB_PATH = "extraction/staging.duckdb"


def main():
    con = duckdb.connect(DB_PATH)

    con.execute("""
        CREATE TABLE IF NOT EXISTS candidate_concepts (
            id              INTEGER PRIMARY KEY,
            episode_id      VARCHAR,          -- e.g. "TGS-224"
            proposed_label  VARCHAR NOT NULL,
            proposed_def    VARCHAR NOT NULL,
            source_note     VARCHAR,          -- short pointer, e.g. timestamp/section — not a long quote
            status          VARCHAR DEFAULT 'pending', -- pending | approved | rejected
            reviewer_notes  VARCHAR,
            created_at      TIMESTAMP DEFAULT current_timestamp
        )
    """)

    con.execute("""
        CREATE TABLE IF NOT EXISTS candidate_links (
            id              INTEGER PRIMARY KEY,
            subject_label   VARCHAR NOT NULL,   -- must match an existing tgs:Concept rdfs:label
            predicate       VARCHAR NOT NULL,   -- one of: echoesIdeaOf | influencedBy | contrastsWith | appliesTo
            object_label    VARCHAR NOT NULL,   -- must match an existing tgs:Person / tgs:School rdfs:label
            rationale       VARCHAR NOT NULL,
            status          VARCHAR DEFAULT 'pending', -- pending | approved | rejected
            reviewer_notes  VARCHAR,
            created_at      TIMESTAMP DEFAULT current_timestamp
        )
    """)

    con.execute("""
        CREATE SEQUENCE IF NOT EXISTS candidate_concepts_id_seq START 1
    """)
    con.execute("""
        CREATE SEQUENCE IF NOT EXISTS candidate_links_id_seq START 1
    """)

    con.close()
    print(f"Staging DB ready at {DB_PATH}")
    print("Tables: candidate_concepts, candidate_links (both start empty)")


if __name__ == "__main__":
    main()
