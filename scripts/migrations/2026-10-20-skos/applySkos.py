import re
B='build/'
def rd(f): return open(B+f,encoding='utf-8').read()
def wr(f,t): open(B+f,'w',encoding='utf-8').write(t)
def app(f,txt): wr(f,rd(f).rstrip('\n')+'\n\n'+txt.strip('\n')+'\n')
# 1. classes -> subClassOf skos:Concept
C=rd('tgs-core.ttl')
for cl in ['InterventionFront','InterventionSubdomain','PracticeCluster','PracticeTerm','BiogeographicRealm','BioregionalRealm','BioregionalSubrealm','Bioregion']:
    s=f'thinkr:{cl} a owl:Class ;\n'; assert C.count(s)==1,cl
    if f'thinkr:{cl} a owl:Class ;\n    rdfs:subClassOf skos:Concept ;' not in C: C=C.replace(s,s+'    rdfs:subClassOf skos:Concept ;\n')
wr('tgs-core.ttl',C)
# 2. insert lines after subject line
def tag(f,pattern,lines_fn):
    t=rd(f); out=[]; n=0
    for line in t.split('\n'):
        out.append(line)
        m=re.match(pattern,line)
        if m:
            assert line.rstrip().endswith(';'),line
            for x in lines_fn(m.group(1)): out.append('    '+x)
            n+=1
    wr(f,'\n'.join(out)); return n
SCH={'BE':'tgs:ConceptScheme.BioregioningEarth','OES':'tgs:ConceptScheme.OneEarthSolutions','OEB':'tgs:ConceptScheme.OneEarthBioregions2023','SF':'tgs:ConceptScheme.SixFrontsOfIntervention'}
roots={k:[] for k in SCH}
def practice(iri):
    s=SCH['OES'] if '.OneEarth_' in iri else SCH['BE']
    L=[f'skos:inScheme {s} ;']
    if iri.startswith('tgs:PracticeCluster.'):
        L.append(f'skos:topConceptOf {s} ;'); roots['OES' if '.OneEarth_' in iri else 'BE'].append(iri)
    return L
n1=tag('initiatives.ttl',r'^(tgs:Practice(?:Cluster|Term)\.\S+) a ',practice)
n2=tag('solutions.ttl',r'^(tgs:Practice(?:Cluster|Term)\.\S+) a ',practice)
def bio(iri):
    L=[f'skos:inScheme {SCH["OEB"]} ;']
    if iri.startswith('tgs:BiogeographicRealm.'): L.append(f'skos:topConceptOf {SCH["OEB"]} ;'); roots['OEB'].append(iri)
    return L
n3=tag('bioregions.ttl',r'^(tgs:(?:BiogeographicRealm|BioregionalRealm|BioregionalSubrealm|Bioregion)\.\S+) a ',bio)
# six fronts: front->subdomain broader
F=rd('interventionfronts.ttl'); sub2front={}
for m in re.finditer(r'^(tgs:InterventionFront\.\S+) a .*?thinkr:hasSubdomain\s+(.*?)\s;',F,re.S|re.M):
    for s in re.findall(r'tgs:InterventionSubdomain\.\w+',m.group(2)): sub2front[s]=m.group(1)
assert len(sub2front)==30,len(sub2front)
def fronts(iri):
    L=[f'skos:inScheme {SCH["SF"]} ;']
    if iri.startswith('tgs:InterventionFront.'): L.append(f'skos:topConceptOf {SCH["SF"]} ;'); roots['SF'].append(iri)
    else: L.append(f'skos:broader {sub2front[iri]} ;')
    return L
n4=tag('interventionfronts.ttl',r'^(tgs:Intervention(?:Front|Subdomain)\.\S+) a ',fronts)
print(n1,n2,n3,n4,{k:len(v) for k,v in roots.items()})
# 3. Doughnut mapping -> seeAlso
I=rd('initiatives.ttl')
old='    skos:relatedMatch tgs:InterventionSubdomain.PostGrowthInstitutions, tgs:SchoolOfThought.DoughnutEconomics ;'
assert old in I
I=I.replace(old,'    skos:relatedMatch tgs:InterventionSubdomain.PostGrowthInstitutions ;\n    rdfs:seeAlso tgs:SchoolOfThought.DoughnutEconomics ;'); wr('initiatives.ttl',I)
# 4. scheme individuals
def scheme(key,label,comment,src,creator,extra=''):
    tops=',\n        '.join(sorted(roots[key]))
    return f'''{SCH[key]} a skos:ConceptScheme, owl:NamedIndividual ;
    skos:prefLabel "{label}"@en ;
    skos:definition "{comment}"@en ;
    dcterms:source {src} ;
    dcterms:creator {creator} ;{extra}
    skos:hasTopConcept
        {tops} ;
    .
'''
app('initiatives.ttl',scheme('BE','Bioregioning Earth Ontology','Activity taxonomy of Bioregioning Earth: ten practice clusters and their 69 practice terms, used to tag on-the-ground initiatives. Mapped to the Six Fronts by skos:relatedMatch.','tgs:Work.BioregioningEarthOntology','"Bioregioning Earth"'))
app('solutions.ttl',scheme('OES','One Earth Solutions','One Earth\'s taxonomy of 76 climate and biodiversity solutions in three pillars and twelve sub-pillars, with seven levers of change and seven intersectional themes. Mapped to the Six Fronts by skos:relatedMatch.','tgs:Work.OneEarthSolutions','"One Earth"'))
app('bioregions.ttl',scheme('OEB','One Earth Bioregions 2023','One Earth\'s hierarchy of 8 biogeographic realms, 14 realm divisions, 53 subrealms and 185 bioregions.','tgs:Work.OneEarthBioregions2023','"Karl Burkart, One Earth"','\n    dcterms:license <https://creativecommons.org/licenses/by-nc/4.0/> ;\n    skos:scopeNote "Attribution: One Earth (oneearth.org). Data licensed CC BY-NC 4.0."@en ;'))
app('interventionfronts.ttl',scheme('SF','Six Fronts of Intervention','Nate Hagens\' action framework from Frankly_132: six fronts of intervention and their thirty subdomains. The hub that the outside taxonomies map to.','tgs:Monologue.Frankly_132_FrameworkForAction','tgs:Human.NateHagens'))
P=rd('provenance.ttl').rstrip('\n')+'''

tgs:RevisionEvent.SKOSSchemes_2026_10_20 a thinkr:RevisionEvent ;
    thinkr:affects tgs:ConceptScheme.BioregioningEarth, tgs:ConceptScheme.OneEarthSolutions, tgs:ConceptScheme.OneEarthBioregions2023, tgs:ConceptScheme.SixFrontsOfIntervention ;
    thinkr:revisionDate "2026-10-20"^^xsd:date ;
    thinkr:revisionKind thinkr:RevisionKindType.InitialBuild ;
    thinkr:revisionNote "At MJSullivan's request, brought the imported taxonomies up to SKOS best practice for sharing: four skos:ConceptScheme individuals (Bioregioning Earth, One Earth Solutions, One Earth Bioregions 2023, and Nate's Six Fronts of Intervention), skos:inScheme on every member, skos:hasTopConcept / skos:topConceptOf on the roots, and the eight taxonomy classes made rdfs:subClassOf skos:Concept, following the precedent of the subject schemes in subjects.ttl. The Six Fronts subdomains gain explicit skos:broader to their front (alongside thinkr:hasSubdomain) so plain SKOS tools see the hierarchy. One mapping that pointed at a SchoolOfThought (Doughnut Assessment) became rdfs:seeAlso, so skos:relatedMatch links concepts only. Applied by applySkos.py, which should be re-run after regenerating any of these files."@en ;
    .
'''
wr('provenance.ttl',P)
