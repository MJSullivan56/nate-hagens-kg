import rdflib,glob,collections,sys
from rdflib.namespace import SKOS,RDF,RDFS
g=rdflib.Graph(); [g.parse(f) for f in glob.glob(sys.argv[1]+'/*.ttl')]
schemes=set(g.subjects(RDF.type,SKOS.ConceptScheme))
issues=collections.defaultdict(list)
for sc in schemes:
    mem=set(g.subjects(SKOS.inScheme,sc)); name=str(sc).split('#')[1]
    if not mem: continue
    labels=collections.defaultdict(list)
    for c in mem:
        pl=[l for l in g.objects(c,SKOS.prefLabel) if getattr(l,'language',None)=='en']
        if len(pl)!=1: issues['prefLabel count'].append((name,c))
        for l in pl: labels[str(l).lower()].append(c)
        br=set(g.objects(c,SKOS.broader)); top=(c,SKOS.topConceptOf,sc) in g
        if top and br: issues['top concept has broader'].append(c)
        if not top and not br: issues['orphan (no broader, not top)'].append((name,c))
        for b in br:
            if (b,SKOS.inScheme,sc) not in g: issues['broader outside scheme'].append((c,b))
        for m in g.objects(c,SKOS.relatedMatch):
            if (m,SKOS.inScheme,sc) in g: issues['relatedMatch within scheme'].append((c,m))
            if m in br: issues['relatedMatch clashes with broader'].append((c,m))
        if top and (sc,SKOS.hasTopConcept,c) not in g: issues['topConceptOf without hasTopConcept'].append(c)
    for l,cs in labels.items():
        if len(cs)>1: issues['duplicate prefLabel in scheme'].append((name,l,[str(x).split('#')[1] for x in cs]))
    print(name,len(mem),'members')
for s,c in g.subject_objects(SKOS.hasTopConcept):
    if (c,SKOS.topConceptOf,s) not in g: issues['hasTopConcept without topConceptOf'].append(c)
# mapping targets must be concepts
conceptClasses={SKOS.Concept}|set(g.transitive_subjects(RDFS.subClassOf,SKOS.Concept))
for s,o in g.subject_objects(SKOS.relatedMatch):
    if not any((o,RDF.type,cl) in g for cl in conceptClasses): issues['relatedMatch target not a skos:Concept'].append((s,o))
for k,v in issues.items(): print('ISSUE',k,len(v),v[:5])
print('issues:',sum(len(v) for v in issues.values()))
