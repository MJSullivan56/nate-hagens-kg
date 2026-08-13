#!/usr/bin/env bash
# Loads the ontology + seed data into a local Oxigraph store.
# Assumes the `oxigraph` CLI is installed (cargo install oxigraph-cli
# or the prebuilt binary). Adjust STORE_PATH as needed.
#
# STORE_PATH CHANGED 2026-07-14: was "./tgs_store" (nested under
# scripts/, an artifact of this script's own original relative-path
# choice, never a deliberate architectural decision) — moved to
# "../tgs_store" (repo root, alongside data/) since tgs_store is a
# materialized, fully-derived view of data/seed/*.ttl — conceptually
# data, not tooling, so it belongs at the repo root next to data/, not
# nested inside the scripts/ folder. Real, gitignored, artifact either
# way — this is a navigability decision, not a version-control one.
# Triggered by a real incident: a stray duplicate tgs_store had
# accumulated at the repo root from an earlier accidental wrong-directory
# run, alongside the real one under scripts/ — see
# docs/sidecar-cleanup-handoff.md for the full incident. This script
# still must be RUN FROM scripts/ (unchanged) — only the store's own
# location moved.

set -euo pipefail

STORE_PATH="${1:-../tgs_store}"

echo "Creating/loading Oxigraph store at ${STORE_PATH}"

for f in ../data/seed/*.ttl; do
    echo "Loading $f ..."
    oxigraph load --location "${STORE_PATH}" --file "$f"
done

echo "Done. Query it with:"
echo "  oxigraph query --location ${STORE_PATH} --query-file ../scripts/query_examples.sparql"
echo "Or serve it over HTTP with:"
echo "  oxigraph serve --location ${STORE_PATH} --bind 127.0.0.1:7878"
