import re,glob,rdflib,collections
from rdflib.namespace import RDF,SKOS,DCTERMS
B='build/'; T=rdflib.Namespace('http://example.org/thinkr#'); G='http://example.org/tgs#'
def rd(f): return open(B+f,encoding='utf-8').read()
def wr(f,t): open(B+f,'w',encoding='utf-8').write(t)
def app(f,txt): wr(f,rd(f).rstrip('\n')+'\n\n'+txt.strip('\n')+'\n')
q=lambda u:'tgs:'+str(u).split('#')[1]
g=rdflib.Graph(); [g.parse(f) for f in glob.glob(B+'*.ttl')]
# --- class changes
def rep1(f,old,new):
    t=rd(f); assert t.count(old)==1,(f,old); wr(f,t.replace(old,new))
rep1('earthsystemcomponents.ttl','thinkr:EarthSystemComponent a owl:Class ;\n    rdfs:subClassOf thinkr:Concept ;','thinkr:EarthSystemComponent a owl:Class ;\n    rdfs:subClassOf skos:Concept ;')
rep1('earthsystemcomponents.ttl','tgs:EarthSystemComponent.AMOC a thinkr:EarthSystemComponent, thinkr:Concept, owl:NamedIndividual ;','tgs:EarthSystemComponent.AMOC a thinkr:EarthSystemComponent, owl:NamedIndividual ;')
rep1('indicatorcategories.ttl','thinkr:IndicatorCategory a owl:Class ;\n    rdfs:subClassOf thinkr:Concept ;','thinkr:IndicatorCategory a owl:Class ;\n    rdfs:subClassOf skos:Concept ;')
rep1('indicators.ttl','thinkr:Indicator a owl:Class ;\n    rdfs:subClassOf thinkr:Concept ;','thinkr:Indicator a owl:Class ;\n    rdfs:subClassOf skos:Concept ;')
for f in ['indicators.ttl','indicatorcategories.ttl']:
    t=rd(f); n=t.count(', thinkr:Concept, owl:NamedIndividual'); t=t.replace(', thinkr:Concept, owl:NamedIndividual',', owl:NamedIndividual'); wr(f,t); print(f,'untyped thinkr:Concept on',n)
rep1('schoolsofthought.ttl','thinkr:SchoolOfThought a owl:Class ;\n    rdfs:subClassOf thinkr:NamedEntity ;','thinkr:SchoolOfThought a owl:Class ;\n    rdfs:subClassOf thinkr:NamedEntity, skos:Concept ;')
rep1('doughnuthalves.ttl','thinkr:DoughnutHalf a owl:Class, thinkr:Category ;','thinkr:DoughnutHalf a owl:Class, thinkr:Category ;\n    rdfs:subClassOf skos:Concept ;')
rep1('tgs-core.ttl','thinkr:hasAlternateTerm a owl:ObjectProperty ;\n    rdfs:domain thinkr:Concept ;','thinkr:hasAlternateTerm a owl:ObjectProperty ;\n    rdfs:domain skos:Concept ;')
# CrudeOil broader -> dcterms:subject already present; drop skos:broader
rep1('concepts.ttl','    dcterms:subject tgs:Subject.EnergySystems ;\n    skos:broader tgs:Subject.EnergySystems ;','    dcterms:subject tgs:Subject.EnergySystems ;')
# --- membership
cls=lambda c:{q(s) for s in g.subjects(RDF.type,c)}
TGSC=sorted(cls(T.Concept)-cls(T.Indicator)-cls(T.IndicatorCategory)-cls(T.EarthSystemComponent))
IND,CAT,HALF=sorted(cls(T.Indicator)),sorted(cls(T.IndicatorCategory)),sorted(cls(T.DoughnutHalf))
ESC,SOT=sorted(cls(T.EarthSystemComponent)),sorted(cls(T.SchoolOfThought))
print(len(TGSC),len(IND),len(CAT),len(HALF),len(ESC),len(SOT))
def insert(f,iri,lines):
    t=rd(f); i=t.index('\n'+iri+' a ')+1; j=t.index(';\n',i)+2
    wr(f,t[:j]+''.join('    '+l+'\n' for l in lines)+t[j:])
S={'TC':'tgs:ConceptScheme.TGSConcepts','CD':'tgs:ConceptScheme.CaliforniaDoughnutIndicators','ES':'tgs:ConceptScheme.EarthSystemComponents','SO':'tgs:ConceptScheme.SchoolsOfThought'}
for c in TGSC: insert('concepts.ttl',c,[f'skos:inScheme {S["TC"]} ;',f'skos:topConceptOf {S["TC"]} ;'])
for c in HALF: insert('doughnuthalves.ttl',c,[f'skos:inScheme {S["CD"]} ;',f'skos:topConceptOf {S["CD"]} ;'])
for c in CAT:
    h=q(g.value(rdflib.URIRef(G+c[4:]),T.hasDoughnutHalf)); insert('indicatorcategories.ttl',c,[f'skos:inScheme {S["CD"]} ;',f'skos:broader {h} ;'])
for c in IND:
    k=q(g.value(rdflib.URIRef(G+c[4:]),T.hasIndicatorCategory)); insert('indicators.ttl',c,[f'skos:inScheme {S["CD"]} ;',f'skos:broader {k} ;'])
for c in ESC: insert('earthsystemcomponents.ttl',c,[f'skos:inScheme {S["ES"]} ;',f'skos:topConceptOf {S["ES"]} ;'])
sotb={q(s):q(o) for s,o in g.subject_objects(SKOS.broader) if q(s) in SOT}
for c in SOT:
    insert('schoolsofthought.ttl',c,[f'skos:inScheme {S["SO"]} ;']+([] if c in sotb else [f'skos:topConceptOf {S["SO"]} ;']))
def scheme(key,label,d,src,tops,extra=''):
    return f'''{S[key]} a skos:ConceptScheme, owl:NamedIndividual ;
    skos:prefLabel "{label}"@en ;
    skos:definition "{d}"@en ;{src}{extra}
    skos:hasTopConcept
        '''+',\n        '.join(tops)+' ;\n    .\n'
app('concepts.ttl',scheme('TC','TGS Concepts',"Ideas discussed on The Great Simplification: Nate Hagens' own concepts (see tgs:Collection.HagensConcepts) and the theories of guests and others that the show treats as central. Flat by design: Nate states few broader/narrower relations, so every concept is a top concept, and browsing groups are given as skos:Collection by site subject and by analytical lens.",'\n    dcterms:source <https://www.thegreatsimplification.com> ;\n    dcterms:creator "Compiled by MJSullivan from The Great Simplification" ;',TGSC))
app('doughnuthalves.ttl',scheme('CD','California Doughnut Indicators',"The Doughnut's two halves, the 21 indicator categories and 42 indicators of the California Doughnut Snapshot and Report.",'\n    dcterms:source tgs:Work.CaliforniaDoughnutReport2025 ;\n    dcterms:license <https://creativecommons.org/licenses/by/4.0/> ;',HALF))
app('earthsystemcomponents.ttl',scheme('ES','Earth System Components',"Real, physical components of Earth's climate and ecological system that TGS episodes discuss as evidence (e.g. the AMOC). Third-party science, not TGS concepts.",'\n    dcterms:source tgs:Interview.TGS_124_LevkeCaesar ;',ESC))
app('schoolsofthought.ttl',scheme('SO','Schools of Thought',"Intellectual traditions, movements and positions that TGS draws on, contrasts with or opposes, including the opposition camps (see thinkr:OppositionType).",'',[c for c in SOT if c not in sotb]))
# --- collections
SUBJ={}  # concept -> site subject
site={q(s) for s in g.subjects(SKOS.inScheme,rdflib.URIRef(G+'ConceptScheme.TGSSiteSubjects'))}
up={q(s):q(o) for s,o in g.subject_objects(SKOS.broader) if str(s).startswith(G+'Subject.')}
col=collections.defaultdict(set); lens=collections.defaultdict(set)
for c in TGSC:
    u=rdflib.URIRef(G+c[4:])
    for s in g.objects(u,DCTERMS.subject):
        s=q(s); s=s if s in site else up.get(s)
        if s: col[s].add(c)
    for l in g.objects(u,T.hasAnalyticalLens): lens[str(l).split('.')[-1]].add(c)
hag=sorted(cls(T.HagensConcept))
L=[f'''tgs:Collection.HagensConcepts a skos:Collection, owl:NamedIndividual ;
    skos:prefLabel "Nate Hagens' own concepts"@en ;
    skos:definition "Concepts Nate Hagens originated or reframed (thinkr:HagensConcept), as distinct from others' ideas discussed on the show."@en ;
    skos:member '''+',\n        '.join(hag)+' ;\n    .\n']
for s,ms in sorted(col.items()):
    lab=str(g.value(rdflib.URIRef(G+s[4:]),SKOS.prefLabel))
    L.append(f'''tgs:Collection.Subject_{s.split('.')[1]} a skos:Collection, owl:NamedIndividual ;
    skos:prefLabel "TGS concepts: {lab}"@en ;
    dcterms:subject {s} ;
    skos:member '''+',\n        '.join(sorted(ms))+' ;\n    .\n')
for l,ms in sorted(lens.items()):
    L.append(f'''tgs:Collection.Lens_{l} a skos:Collection, owl:NamedIndividual ;
    skos:prefLabel "TGS concepts: {re.sub('([a-z])([A-Z])',r'\1 \2',l)} lens"@en ;
    skos:member '''+',\n        '.join(sorted(ms))+' ;\n    .\n')
app('concepts.ttl','\n'.join(L))
print('collections:',{k:len(v) for k,v in col.items()},{k:len(v) for k,v in lens.items()},'hagens',len(hag))
# --- skos:related materialized for concept-to-concept links
members=set(TGSC)|set(SOT)|set(ESC)
rel=set()
for p in [T.complements,T.contrastsWith,T.convergesWith,T.relatesTo,T.challenges]:
    for s,o in g.subject_objects(p):
        a,b=q(s),q(o)
        if a in members and b in members and a!=b: rel.add(tuple(sorted((a,b))))
broader=set(tuple(sorted((q(s),q(o)))) for s,o in g.subject_objects(SKOS.broader))
rel-=broader
byfile=collections.defaultdict(list)
fileof=lambda c:'concepts.ttl' if c in TGSC else ('schoolsofthought.ttl' if c in SOT else 'earthsystemcomponents.ttl')
for a,b in sorted(rel): byfile[fileof(a)].append((a,b))
# write as separate statements block per file (symmetric property; one direction is enough)
for f,pairs in byfile.items():
    app(f,'# skos:related, materialized 2026-10-20 from thinkr:complements/contrastsWith/convergesWith/relatesTo/challenges\n# where both ends are SKOS concepts (applySkos2.py). Not a subproperty axiom, because those\n# properties also link concepts to Personas, Organizations and ScenarioFacets.\n'+''.join(f'{a} skos:related {b} .\n' for a,b in pairs))
print('skos:related pairs',len(rel))
# --- altLabels from ExactMatch / Abbreviation alternate terms
alt=collections.defaultdict(list); allpref={str(o).lower() for o in g.objects(None,SKOS.prefLabel)}
for c,bn in g.subject_objects(T.hasAlternateTerm):
    ty=str(g.value(bn,T.hasAlternateTermType))
    if ty.endswith(('ExactMatch','Abbreviation')) and q(c) in members|set(CAT):
        lab=g.value(bn,SKOS.prefLabel)
        if str(lab).lower() in allpref: print('skip altLabel clash',c,lab); continue
        if (c,SKOS.altLabel,lab) not in g: alt[q(c)].append(lab)
for c,labs in alt.items():
    f=fileof(c) if c in members else 'indicatorcategories.ttl'
    insert(f,c,[f'skos:altLabel "'+str(l).replace('"','\\"')+f'"@{l.language or "en"} ;' for l in labs])
print('altLabels added',sum(len(v) for v in alt.values()))
app('provenance.ttl','''tgs:RevisionEvent.SKOSSchemes2_2026_10_20 a thinkr:RevisionEvent ;
    thinkr:affects tgs:ConceptScheme.TGSConcepts, tgs:ConceptScheme.CaliforniaDoughnutIndicators, tgs:ConceptScheme.EarthSystemComponents, tgs:ConceptScheme.SchoolsOfThought ;
    thinkr:revisionDate "2026-10-20"^^xsd:date ;
    thinkr:revisionKind thinkr:RevisionKindType.InitialBuild ;
    thinkr:revisionNote "Second SKOS pass, at MJSullivan's direction, so the whole graph can be shared as SKOS. Four more schemes: TGS Concepts (flat; every member a top concept), California Doughnut Indicators (2 halves > 21 categories > 42 indicators, via new skos:broader from hasDoughnutHalf / hasIndicatorCategory), Earth System Components, and Schools of Thought. At MJSullivan's correction, third-party classes stop being TGS concepts: thinkr:EarthSystemComponent, thinkr:IndicatorCategory and thinkr:Indicator are now rdfs:subClassOf skos:Concept instead of thinkr:Concept, and their members lose explicit thinkr:Concept typing (matching the EarthSystemComponent class's own original rationale); thinkr:SchoolOfThought and thinkr:DoughnutHalf also become skos:Concept subclasses; thinkr:hasAlternateTerm's domain widened from thinkr:Concept to skos:Concept. Browsing collections: Nate's own concepts (thinkr:HagensConcept), one per TGS site subject, one per analytical lens. skos:related materialized for concept-to-concept pairs of complements/contrastsWith/convergesWith/relatesTo/challenges (not as a subproperty axiom, since those properties also reach Personas, Organizations and ScenarioFacets). Plain skos:altLabel added from ExactMatch and Abbreviation alternate terms. Concept.CrudeOil's cross-scheme skos:broader to Subject.EnergySystems dropped (its dcterms:subject already says the same)."@en ;
    .
''')
print('ok')
