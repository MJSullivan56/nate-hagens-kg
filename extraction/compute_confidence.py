"""
Computes thinker:calculatedConfidence for every thinker:LinkNote from its thinker:Evidence
set. This value is DERIVED — never hand-write it into a TTL file. Re-run this
script after adding, editing, or reviewing any Evidence, and commit the result.

Rule (see ontology/schema.ttl's ConfidenceLevel individuals for the canonical
definitions, and CLAUDE.md's backlog section for the full design rationale):

1. Only Curated (human-reviewed) Evidence counts toward anything.
2. Evidence from an Unreliable-tier Source is excluded entirely, regardless
   of polarity — stored as an audit trail, but no effect on the score.
3. Evidence that is the OBJECT of another Evidence's prov:wasRevisionOf
   (i.e. has been superseded) is excluded entirely, regardless of tier,
   polarity, or volume.
4. Any remaining Curated + Contests evidence from a Reputable-or-better
   source -> Disputed. This overrides Corroborated even if supporting
   evidence also exists — a serious rebuttal shouldn't be outvoted.
5. Otherwise: >=2 INDEPENDENT (different Source, or no Source at all counts
   as at most one "unsourced" slot) Curated + Supports evidence from
   Reputable-or-better -> Corroborated. Exactly 1 -> Curated.
   Unverified-tier support alone can never reach Corroborated, regardless
   of count.
6. No qualifying evidence at all -> Candidate (the floor state).
7. Mentions-polarity evidence never affects the score.

Evidence with no explicit thinker:aboutSource (direct curator/maintainer
reasoning, not a citation to an external publication) is treated as
Reputable tier for this calculation — see thinker:aboutSource's rdfs:comment
in the schema for why.

Usage:
    python scripts/compute_confidence.py            # apply and write back
    python scripts/compute_confidence.py --dry-run  # preview only
"""

import argparse
import glob
import rdflib
from rdflib import Graph, Namespace, RDF
from rdflib.namespace import DCTERMS

TGS = Namespace("http://example.org/tgs#")
THINKER = Namespace("http://example.org/thinker#")
PROV = Namespace("http://www.w3.org/ns/prov#")

CURATED = THINKER["ConfidenceLevel.Curated"]
CANDIDATE = THINKER["ConfidenceLevel.Candidate"]
CORROBORATED = THINKER["ConfidenceLevel.Corroborated"]
DISPUTED = THINKER["ConfidenceLevel.Disputed"]

REPUTABLE = THINKER["ReliabilityTier.Reputable"]
AUTHORITATIVE = THINKER["ReliabilityTier.Authoritative"]
UNVERIFIED = THINKER["ReliabilityTier.Unverified"]
UNRELIABLE = THINKER["ReliabilityTier.Unreliable"]
REPUTABLE_OR_BETTER = {REPUTABLE, AUTHORITATIVE}

SUPPORTS = THINKER["EvidencePolarity.Supports"]
CONTESTS = THINKER["EvidencePolarity.Contests"]


def load_full_graph():
    g = Graph()
    for f in glob.glob('**/*.ttl', recursive=True):
        g.parse(f, format='turtle')
    return g


def evidence_tier(g, ev):
    """Reliability tier for one Evidence, applying the unsourced-defaults-to-Reputable rule."""
    sources = list(g.objects(ev, THINKER.aboutSource))
    if not sources:
        return REPUTABLE
    tiers = list(g.objects(sources[0], THINKER.reliabilityTier))
    return tiers[0] if tiers else REPUTABLE


def is_superseded(g, ev):
    return (None, PROV.wasRevisionOf, ev) in g


def compute_for_note(g, note):
    evidences = list(g.objects(note, THINKER.hasEvidence))
    qualifying_supports_sources = set()  # None allowed once (unsourced), else Source URIs
    unsourced_support_seen = False
    has_disputing = False
    has_unverified_support = False

    for ev in evidences:
        conf = list(g.objects(ev, THINKER.confidence))
        if not conf or conf[0] != CURATED:
            continue  # rule 1: only Curated evidence counts
        if is_superseded(g, ev):
            continue  # rule 3
        tier = evidence_tier(g, ev)
        if tier == UNRELIABLE:
            continue  # rule 2
        polarity = list(g.objects(ev, THINKER.evidencePolarity))
        polarity = polarity[0] if polarity else None

        if polarity == CONTESTS and tier in REPUTABLE_OR_BETTER:
            has_disputing = True
        elif polarity == SUPPORTS:
            if tier in REPUTABLE_OR_BETTER:
                sources = list(g.objects(ev, THINKER.aboutSource))
                if sources:
                    qualifying_supports_sources.add(sources[0])
                else:
                    unsourced_support_seen = True
            elif tier == UNVERIFIED:
                has_unverified_support = True
        # Mentions and anything else: no effect (rule 7)

    if has_disputing:
        return DISPUTED  # rule 4, overrides everything else

    independent_count = len(qualifying_supports_sources) + (1 if unsourced_support_seen else 0)
    if independent_count >= 2:
        return CORROBORATED
    elif independent_count == 1:
        return CURATED
    else:
        # rule 6: floor state, even if only Unverified-tier support exists
        return CANDIDATE


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    g = load_full_graph()
    notes = list(g.subjects(RDF.type, THINKER.LinkNote))
    print(f"Computing calculatedConfidence for {len(notes)} LinkNotes...\n")

    results = {}
    for note in notes:
        result = compute_for_note(g, note)
        results[note] = result
        label = str(note).split('#')[-1]
        print(f"  {label}: {str(result).split('#')[-1]}")

    if args.dry_run:
        print("\n[DRY RUN] No files written.")
        return

    # Write results back into whichever file actually contains each LinkNote
    import glob as globmod
    for path in globmod.glob('**/*.ttl', recursive=True):
        file_g = Graph()
        file_g.parse(path, format='turtle')
        changed = False
        for note, result in results.items():
            if (note, RDF.type, THINKER.LinkNote) in file_g:
                # remove any stale calculatedConfidence, set the fresh one
                for old_val in list(file_g.objects(note, THINKER.calculatedConfidence)):
                    file_g.remove((note, THINKER.calculatedConfidence, old_val))
                file_g.add((note, THINKER.calculatedConfidence, result))
                changed = True
        if changed:
            file_g.serialize(destination=path, format='turtle')
            print(f"Updated {path}")


if __name__ == "__main__":
    main()
