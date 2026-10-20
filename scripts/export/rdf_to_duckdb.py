#!/usr/bin/env python3
"""
RDF -> DuckDB one-time backfill.

Design: hybrid schema.
  - Core tables for the entity types that are actually queried by date,
    name, or URL (episodes, personas, humans, relationships,
    interactions, works). These are the ones worth real columns.
  - One generic `facts` table for everything else (Concept, Archetype,
    InterventionFront/Subdomain, ScenarioFacet, PersonalIntervention,
    Indicator, IndicatorCategory, Evidence, CrosswalkNote, LinkNote,
    schema-level classes/properties, and any future new entity type)
    so a newly-added class never requires a schema migration before
    it's queryable.
  - Blank nodes (hasInteraction, hasAlternateTerm) get a synthetic
    stable ID (sha1 of their own triples) since they have no IRI —
    deterministic, so re-running the import produces the same IDs.

This is purely additive/staging: nothing here modifies the .ttl files.
Curation happens via SQL against DuckDB; export back to Turtle is a
separate script.
"""
import duckdb
import rdflib
import hashlib
from pathlib import Path

SEED_DIR = Path("/home/claude/seed_full/seed")
DB_PATH = "/home/claude/tgs_backfill.duckdb"
SPARQL_ENDPOINT = "http://127.0.0.1:7878/query"  # real Oxigraph instance — set to None to force file-parsing

TGS = "http://example.org/tgs#"
THINKR = "http://example.org/thinkr#"

def load_graph():
    """Load from the live Oxigraph SPARQL endpoint if reachable (preferred —
    it's the actual system of record), else fall back to parsing the .ttl
    files directly (useful for one-off snapshots or if the store isn't
    running). NOT relying on a directory glob as the only path matters:
    file-globbing gave a false surprise this session (real, dated TGS
    content in doughnuthalves.ttl/indicators.ttl/etc. that looked at a
    glance like it might belong to a different project) purely because
    nobody had surveyed the full file list recently — querying the live
    store directly sidesteps that whole category of mistake."""
    if SPARQL_ENDPOINT:
        try:
            import urllib.request, urllib.parse
            q = "CONSTRUCT {?s ?p ?o} WHERE {?s ?p ?o}"
            req = urllib.request.Request(
                SPARQL_ENDPOINT + "?" + urllib.parse.urlencode({"query": q}),
                headers={"Accept": "text/turtle"},
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = resp.read()
            g = rdflib.Graph()
            g.parse(data=data, format="turtle")
            print(f"Loaded {len(g)} triples from live SPARQL endpoint ({SPARQL_ENDPOINT})")
            return g
        except Exception as e:
            print(f"SPARQL endpoint unreachable ({e}) — falling back to file parsing.")
    g = rdflib.Graph()
    for f in sorted(SEED_DIR.glob("*.ttl")):
        g.parse(str(f), format="turtle")
    print(f"Loaded {len(g)} triples from {len(list(SEED_DIR.glob('*.ttl')))} local .ttl files")
    return g

def local_name(uri):
    """Strip a URI down to its local name for readability, keep full URI too."""
    s = str(uri)
    if "#" in s:
        return s.split("#")[-1]
    return s.rsplit("/", 1)[-1]

def bnode_id(bnode, graph, scope=""):
    """Deterministic synthetic ID for a blank node from its own triples,
    plus an optional scope (e.g. the owning Relationship's IRI) — needed
    because two DIFFERENT interactions (different guests on the same
    panel episode) can have IDENTICAL literal properties (same episode,
    same date, same Host/Guest roles) and would otherwise collide."""
    triples = sorted(f"{p}={o}" for p, o in graph.predicate_objects(bnode))
    return "bn_" + hashlib.sha1((scope + "|" + "|".join(triples)).encode()).hexdigest()[:12]

def main():
    g = load_graph()

    con = duckdb.connect(DB_PATH)
    con.execute("PRAGMA threads=4")

    # ---------- Core tables ----------
    con.execute("""
        CREATE OR REPLACE TABLE episodes (
            iri TEXT PRIMARY KEY, local_name TEXT, episode_type TEXT,
            pref_label TEXT, definition TEXT, discussion_summary TEXT,
            scope_note TEXT, created_date DATE, issued_date DATE,
            canonical_source TEXT, transcript_url TEXT, replay_url TEXT,
            host_iri TEXT
        )
    """)
    con.execute("""
        CREATE OR REPLACE TABLE episode_guests (episode_iri TEXT, guest_iri TEXT)
    """)
    con.execute("""
        CREATE OR REPLACE TABLE episode_subjects (episode_iri TEXT, subject_iri TEXT)
    """)
    con.execute("""
        CREATE OR REPLACE TABLE episode_discusses (episode_iri TEXT, target_iri TEXT)
    """)
    con.execute("""
        CREATE OR REPLACE TABLE episode_references (episode_iri TEXT, target TEXT)
    """)
    con.execute("""
        CREATE OR REPLACE TABLE personas (
            iri TEXT PRIMARY KEY, local_name TEXT, pref_label TEXT,
            acts_through_iri TEXT, scope_note TEXT
        )
    """)
    con.execute("""
        CREATE OR REPLACE TABLE persona_professional_roles (persona_iri TEXT, role_iri TEXT)
    """)
    con.execute("""
        CREATE OR REPLACE TABLE humans (
            iri TEXT PRIMARY KEY, local_name TEXT, pref_label TEXT,
            comment TEXT, same_as TEXT
        )
    """)
    con.execute("""
        CREATE OR REPLACE TABLE relationships (
            iri TEXT PRIMARY KEY, local_name TEXT, pref_label TEXT,
            subject_iri TEXT, object_iri TEXT, scope_note TEXT
        )
    """)
    con.execute("""
        CREATE OR REPLACE TABLE relationship_types (relationship_iri TEXT, type_iri TEXT)
    """)
    con.execute("""
        CREATE OR REPLACE TABLE interactions (
            id TEXT PRIMARY KEY, relationship_iri TEXT, episode_iri TEXT,
            interaction_type TEXT, subject_role TEXT, object_role TEXT,
            interaction_date DATE
        )
    """)
    con.execute("""
        CREATE OR REPLACE TABLE works (
            iri TEXT PRIMARY KEY, local_name TEXT, pref_label TEXT,
            comment TEXT, issued TEXT, same_as TEXT
        )
    """)
    con.execute("""
        CREATE OR REPLACE TABLE work_creators (work_iri TEXT, creator TEXT)
    """)
    # Generic catch-all for every other type / predicate not modeled above
    con.execute("""
        CREATE OR REPLACE TABLE facts (
            subject_iri TEXT, subject_type TEXT, predicate TEXT,
            object_value TEXT, object_is_iri BOOLEAN, source_file TEXT
        )
    """)

    dct = rdflib.Namespace("http://purl.org/dc/terms/")
    skos = rdflib.Namespace("http://www.w3.org/2004/02/skos/core#")
    thinkr = rdflib.Namespace(THINKR)

    def val(o):
        return str(o) if o is not None else None

    # ---------- Episodes ----------
    print("Extracting episodes...")
    ep_rows, guest_rows, subj_rows, disc_rows, ref_rows = [], [], [], [], []
    for ep in g.subjects(rdflib.RDF.type, thinkr.Episode):
        if isinstance(ep, rdflib.BNode):
            continue
        etype = next(g.objects(ep, thinkr.hasEpisodeType), None)
        host = next(g.objects(ep, thinkr.hasHost), None)
        ep_rows.append((
            str(ep), local_name(ep), local_name(etype) if etype else None,
            val(next(g.objects(ep, skos.prefLabel), None)),
            val(next(g.objects(ep, skos.definition), None)),
            val(next(g.objects(ep, thinkr.hasDiscussionSummary), None)),
            val(next(g.objects(ep, skos.scopeNote), None)),
            val(next(g.objects(ep, dct.created), None)),
            val(next(g.objects(ep, dct.issued), None)),
            val(next(g.objects(ep, thinkr.hasCanonicalSource), None)),
            val(next(g.objects(ep, thinkr.hasTranscript), None)),
            val(next(g.objects(ep, thinkr.hasReplay), None)),
            str(host) if host else None,
        ))
        for guest in g.objects(ep, thinkr.hasGuest):
            guest_rows.append((str(ep), str(guest)))
        for subj in g.objects(ep, dct.subject):
            subj_rows.append((str(ep), str(subj)))
        for d in g.objects(ep, thinkr.discusses):
            disc_rows.append((str(ep), str(d)))
        for r in g.objects(ep, dct.references):
            ref_rows.append((str(ep), str(r)))

    con.executemany("INSERT INTO episodes VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", ep_rows)
    con.executemany("INSERT INTO episode_guests VALUES (?,?)", guest_rows)
    con.executemany("INSERT INTO episode_subjects VALUES (?,?)", subj_rows)
    con.executemany("INSERT INTO episode_discusses VALUES (?,?)", disc_rows)
    con.executemany("INSERT INTO episode_references VALUES (?,?)", ref_rows)
    print(f"  {len(ep_rows)} episodes, {len(guest_rows)} guest links, {len(disc_rows)} discusses, {len(ref_rows)} references")

    # ---------- Personas ----------
    print("Extracting personas...")
    p_rows, role_rows = [], []
    for p in g.subjects(rdflib.RDF.type, thinkr.Persona):
        if isinstance(p, rdflib.BNode):
            continue
        acts = next(g.objects(p, thinkr.actsThrough), None)
        p_rows.append((
            str(p), local_name(p),
            val(next(g.objects(p, skos.prefLabel), None)),
            str(acts) if acts else None,
            val(next(g.objects(p, skos.scopeNote), None)),
        ))
        for role in g.objects(p, thinkr.hasProfessionalRole):
            role_rows.append((str(p), str(role)))
    con.executemany("INSERT INTO personas VALUES (?,?,?,?,?)", p_rows)
    con.executemany("INSERT INTO persona_professional_roles VALUES (?,?)", role_rows)
    print(f"  {len(p_rows)} personas, {len(role_rows)} professional-role tags")

    # ---------- Humans ----------
    print("Extracting humans...")
    h_rows = []
    for h in g.subjects(rdflib.RDF.type, thinkr.Human):
        if isinstance(h, rdflib.BNode):
            continue
        h_rows.append((
            str(h), local_name(h),
            val(next(g.objects(h, skos.prefLabel), None)),
            val(next(g.objects(h, rdflib.RDFS.comment), None)),
            val(next(g.objects(h, rdflib.OWL.sameAs), None)),
        ))
    con.executemany("INSERT INTO humans VALUES (?,?,?,?,?)", h_rows)
    print(f"  {len(h_rows)} humans")

    # ---------- Relationships + Interactions ----------
    print("Extracting relationships and interactions...")
    rel_rows, reltype_rows, inter_rows = [], [], []
    for rel in g.subjects(rdflib.RDF.type, thinkr.Relationship):
        if isinstance(rel, rdflib.BNode):
            continue
        rel_rows.append((
            str(rel), local_name(rel),
            val(next(g.objects(rel, skos.prefLabel), None)),
            val(next(g.objects(rel, thinkr.hasSubject), None)),
            val(next(g.objects(rel, thinkr.hasObject), None)),
            val(next(g.objects(rel, skos.scopeNote), None)),
        ))
        for rt in g.objects(rel, thinkr.hasRelationshipType):
            reltype_rows.append((str(rel), str(rt)))
        for inter in g.objects(rel, thinkr.hasInteraction):
            iid = bnode_id(inter, g, scope=str(rel))
            itype = next(g.objects(inter, rdflib.RDF.type), None)
            inter_rows.append((
                iid, str(rel),
                val(next(g.objects(inter, thinkr.episode), None)),
                local_name(itype) if itype else None,
                val(next(g.objects(inter, thinkr.subjectRole), None)),
                val(next(g.objects(inter, thinkr.objectRole), None)),
                val(next(g.objects(inter, dct.date), None)),
            ))
    con.executemany("INSERT INTO relationships VALUES (?,?,?,?,?,?)", rel_rows)
    con.executemany("INSERT INTO relationship_types VALUES (?,?)", reltype_rows)
    con.executemany("INSERT OR IGNORE INTO interactions VALUES (?,?,?,?,?,?,?)", inter_rows)
    print(f"  {len(rel_rows)} relationships, {len(inter_rows)} interactions")

    # ---------- Works ----------
    print("Extracting works...")
    w_rows, wc_rows = [], []
    for w in g.subjects(rdflib.RDF.type, thinkr.Work):
        if isinstance(w, rdflib.BNode):
            continue
        w_rows.append((
            str(w), local_name(w),
            val(next(g.objects(w, skos.prefLabel), None)),
            val(next(g.objects(w, rdflib.RDFS.comment), None)),
            val(next(g.objects(w, dct.issued), None)),
            val(next(g.objects(w, rdflib.OWL.sameAs), None)),
        ))
        for c in g.objects(w, dct.creator):
            wc_rows.append((str(w), str(c)))
    con.executemany("INSERT INTO works VALUES (?,?,?,?,?,?)", w_rows)
    con.executemany("INSERT INTO work_creators VALUES (?,?)", wc_rows)
    print(f"  {len(w_rows)} works")

    # ---------- Generic facts (everything else) ----------
    print("Extracting generic facts (all other triples)...")
    core_subjects = set()
    for tbl_query in [
        "SELECT iri FROM episodes", "SELECT iri FROM personas",
        "SELECT iri FROM humans", "SELECT iri FROM relationships",
        "SELECT iri FROM works",
    ]:
        core_subjects |= {r[0] for r in con.execute(tbl_query).fetchall()}

    fact_rows = []
    seen_bnodes = set()
    for s, p, o in g:
        if isinstance(s, rdflib.BNode):
            # only capture blank nodes NOT already handled as interactions
            bid = bnode_id(s, g)
            if bid in [r[0] for r in inter_rows]:
                continue
            s_repr = bid
            seen_bnodes.add(bid)
        else:
            s_repr = str(s)
            if s_repr in core_subjects and str(p) not in (str(rdflib.RDF.type),):
                continue  # already captured in a core table
        stype = next((str(t) for t in g.objects(s, rdflib.RDF.type)), None) if not isinstance(s, rdflib.BNode) else None
        fact_rows.append((
            s_repr, local_name(stype) if stype else None, local_name(p),
            str(o), isinstance(o, (rdflib.URIRef,)), None
        ))
    con.executemany("INSERT INTO facts VALUES (?,?,?,?,?,?)", fact_rows)
    print(f"  {len(fact_rows)} generic facts (covers Concept, Archetype, InterventionFront/Subdomain, ScenarioFacet, PersonalIntervention, Indicator, IndicatorCategory, Evidence, CrosswalkNote, LinkNote, and all schema-level Class/Property definitions)")

    con.close()
    print(f"\nDone. Database at {DB_PATH}")

if __name__ == "__main__":
    main()
