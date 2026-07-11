.PHONY: venv validate load-oxigraph init-db promote-dry promote clean

venv:
	python3 -m venv .venv
	.venv/bin/pip install --upgrade pip
	.venv/bin/pip install -r requirements.txt
	@echo "Activate with: source .venv/bin/activate"

# Same check CI runs — good to run before committing
validate:
	.venv/bin/python -c "\
import glob, rdflib; \
g = rdflib.Graph(); \
[print('OK', f) for f in sorted(glob.glob('**/*.ttl', recursive=True)) if g.parse(f, format='turtle') is not None]; \
print('Total triples:', len(g))"

# Requires: brew tap oxigraph/oxigraph && brew install oxigraph
load-oxigraph:
	cd scripts && ./load_oxigraph.sh

init-db:
	.venv/bin/python extraction/init_staging_db.py

promote-dry:
	.venv/bin/python extraction/promote_to_rdf.py --dry-run

promote:
	.venv/bin/python extraction/promote_to_rdf.py

clean:
	rm -rf scripts/tgs_store extraction/staging.duckdb data/generated
