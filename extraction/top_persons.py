"""
Prints the top PERSON entities from extraction/entity_index.duckdb, ranked
by total mentions. Simple standalone script — no inline shell quoting to
mess up.

Usage:
    python extraction/top_persons.py
    python extraction/top_persons.py --limit 60
"""

import argparse
import duckdb

DB_PATH = "extraction/entity_index.duckdb"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=40)
    args = parser.parse_args()

    con = duckdb.connect(DB_PATH)
    rows = con.execute(
        """
        SELECT entity_text, SUM(occurrence_count) as total, COUNT(DISTINCT source_file) as docs
        FROM entities WHERE entity_type = 'PERSON'
        GROUP BY entity_text ORDER BY total DESC LIMIT ?
        """,
        [args.limit],
    ).fetchall()

    print(f"{'mentions':>8}  {'docs':>4}  name")
    for name, total, docs in rows:
        print(f"{total:>8}  {docs:>4}  {name}")

    con.close()


if __name__ == "__main__":
    main()
