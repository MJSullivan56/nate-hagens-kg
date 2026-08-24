import rdflib
g = rdflib.Graph()
g.parse("tgs-core.ttl", format="turtle")
g.parse("enumerations.ttl", format="turtle")
print("Parsed OK —", len(g), "triples")
