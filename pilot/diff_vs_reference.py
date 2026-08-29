#!/usr/bin/env python3
"""diff_vs_reference.py — compare produced output against a hand-built reference.

Deliberately a REPORTER, not a reconciler. The instruction for this run was to
report divergence explicitly rather than silently reconcile, so nothing here
mutates either side; it prints what differs and, where the reference itself
documents a known limitation, says so instead of scoring it as a failure.

The reference (`pilot/example/TGS-127_chunked_example.json`) is explicitly
"proof of shape, not a literal template" — it carries scaffolding that is NOT
expected in real output:
  * `DUMMY_PLACEHOLDER_*` ner types (chunks 2, 3, 8)
  * `_note` fields explaining hand-construction reasoning
  * `cost_tracking: null` throughout (no LLM call was ever made)
  * only 8 of ~60 chunks present at all
So chunk-count and NER differences on those chunks are expected. What SHOULD
match is the metadata block, and the structural fields of the chunks the
reference does populate.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

META_FIELDS = [
    "episode_iri", "transcript_source_type", "title", "webpage_url",
    "youtube_url", "duration_seconds", "published_date", "recorded_date",
    "keywords", "host", "guests", "description", "transcript_speakers",
    "chunking_method", "source_sha256",
]


def _norm(v):
    if isinstance(v, str):
        return " ".join(v.split())
    return v


def diff_report(produced: dict, reference: dict) -> dict:
    out = {"metadata": [], "chunks": [], "notes": []}
    print(f"\n{'='*72}\nDIFF vs HAND-BUILT REFERENCE\n{'='*72}")

    # ---- metadata ----
    print("\n1. METADATA BLOCK")
    same = 0
    for f in META_FIELDS:
        p, r = _norm(produced.get(f)), _norm(reference.get(f))
        if p == r:
            same += 1
            continue
        out["metadata"].append({"field": f, "produced": p, "reference": r})
        print(f"  DIFFERS  {f}")
        print(f"    produced : {str(p)[:88]}")
        print(f"    reference: {str(r)[:88]}")
    print(f"  {same}/{len(META_FIELDS)} metadata fields match exactly")

    # ---- chunk counts ----
    pc, rc = produced.get("chunks") or [], reference.get("chunks") or []
    print(f"\n2. CHUNK COUNTS")
    print(f"  produced  {len(pc)} chunks")
    print(f"  reference {len(rc)} chunks  "
          f"(hand-built sample; its own _remaining_chunks_summary says the real "
          f"count is larger)")

    # ---- per-chunk structural comparison, matched on start_seconds ----
    print(f"\n3. CHUNKS THE REFERENCE POPULATES — structural comparison")
    pby = {c["start_seconds"]: c for c in pc}
    for r in rc:
        key = r["start_seconds"]
        p = pby.get(key)
        rid = r["chunk_id"]
        if p is None:
            print(f"  MISSING  {rid} (start={key}s) has no produced chunk at that start")
            out["chunks"].append({"chunk": rid, "issue": "no produced chunk at start"})
            continue
        probs = []
        if p["chunk_type"] != r["chunk_type"]:
            probs.append(f"type {p['chunk_type']} vs {r['chunk_type']}")
        if p["end_seconds"] != r["end_seconds"]:
            probs.append(f"end_seconds {p['end_seconds']} vs {r['end_seconds']}")
        if _norm(p.get("topic_label")) != _norm(r.get("topic_label")):
            probs.append(f"topic_label {str(p.get('topic_label'))[:40]!r} vs "
                         f"{str(r.get('topic_label'))[:40]!r}")
        pl = [(l.get("label"), l.get("url")) for l in (p.get("curated_links") or [])]
        rl = [(l.get("label"), l.get("url")) for l in (r.get("curated_links") or [])]
        if pl != rl:
            probs.append(f"curated_links {len(pl)} vs {len(rl)}")
        # turns: compare (speaker, start_seconds) only — the reference truncates
        # some turn text with editorial markers like "[continues into ...]".
        pt = [(t["speaker"], t["start_seconds"]) for t in (p.get("turns") or [])]
        rt = [(t["speaker"], t["start_seconds"]) for t in (r.get("turns") or [])]
        if pt != rt:
            probs.append(f"turns {pt} vs {rt}")
        if probs:
            print(f"  DIFFERS  {rid} (start={key}s)")
            for x in probs:
                print(f"    - {x}")
            out["chunks"].append({"chunk": rid, "issues": probs})
        else:
            print(f"  match    {rid} (start={key}s)")

    # ---- turn text spot-check on the chunks the reference fully populated ----
    print(f"\n4. TURN TEXT — exact-prefix check where the reference is verbatim")
    for r in rc:
        p = pby.get(r["start_seconds"])
        if not p or not r.get("turns") or not p.get("turns"):
            continue
        for rt in r["turns"]:
            pt = next((t for t in p["turns"]
                       if t["start_seconds"] == rt["start_seconds"]), None)
            if pt is None:
                continue
            a, b = _norm(pt["text"]), _norm(rt["text"])
            if a == b:
                print(f"  identical  {r['chunk_id']} {rt['speaker']}@{rt['start_seconds']}s "
                      f"({len(a)} chars)")
            elif b.rstrip(" ]") and a.startswith(b[:120]):
                print(f"  prefix-ok  {r['chunk_id']} {rt['speaker']}@{rt['start_seconds']}s "
                      f"(produced {len(a)} chars, reference {len(b)} — reference truncated)")
            else:
                print(f"  DIFFERS    {r['chunk_id']} {rt['speaker']}@{rt['start_seconds']}s")
                print(f"    produced : {a[:100]}")
                print(f"    reference: {b[:100]}")
                out["chunks"].append({"chunk": r["chunk_id"], "issue": "turn text differs"})

    # ---- scaffolding the reference itself says to ignore ----
    dummy = sum(1 for c in rc for n in (c.get("ner_candidates") or [])
                if "DUMMY_PLACEHOLDER" in str(n.get("type_guess")))
    print(f"\n5. REFERENCE SCAFFOLDING (expected, not a divergence)")
    print(f"  DUMMY_PLACEHOLDER ner candidates in reference: {dummy}")
    print(f"  reference cost_tracking model_used: "
          f"{(reference.get('cost_tracking') or {}).get('model_used')}")
    print(f"  chunks carrying a hand-written _note: "
          f"{sum(1 for c in rc if c.get('_note'))}")
    return out


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: diff_vs_reference.py PRODUCED.json REFERENCE.json", file=sys.stderr)
        return 2
    diff_report(json.loads(Path(sys.argv[1]).read_text(encoding="utf-8")),
                json.loads(Path(sys.argv[2]).read_text(encoding="utf-8")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
