#!/usr/bin/env bash
# Loads the ontology + seed data into a local Oxigraph store.
# Assumes the `oxigraph` CLI is installed (cargo install oxigraph-cli
# or the prebuilt binary). Adjust STORE_PATH as needed.

set -euo pipefail

STORE_PATH="${1:-./tgs_store}"

echo "Creating/loading Oxigraph store at ${STORE_PATH}"

for f in ../data/seed/*.ttl; do
    echo "Loading $f ..."
    oxigraph load --location "${STORE_PATH}" --file "$f"
done

echo "Done. Query it with:"
echo "  oxigraph query --location ${STORE_PATH} --query-file ../scripts/query_examples.sparql"
echo "Or serve it over HTTP with:"
echo "  oxigraph serve --location ${STORE_PATH} --bind 127.0.0.1:7878"
