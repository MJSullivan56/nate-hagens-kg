import glob,rdflib,collections
from rdflib.namespace import RDF,SKOS
B='build/'; T=rdflib.Namespace('http://example.org/thinkr#')
g=rdflib.Graph(); [g.parse(f) for f in glob.glob(B+'*.ttl')]
q=lambda u:'tgs:'+str(u).split('#')[1]
schemes=set(g.subjects(RDF.type,SKOS.ConceptScheme))
inscheme={c:sc for c,sc in g.subject_objects(SKOS.inScheme)}
pref=collections.defaultdict(set)
for c,sc in inscheme.items():
    for l in g.objects(c,SKOS.prefLabel): pref[sc].add(str(l).lower())
def rd(f): return open(B+f,encoding='utf-8').read()
def wr(f,t): open(B+f,'w',encoding='utf-8').write(t)
def insert(f,iri,lines):
    t=rd(f); i=t.index('\n'+iri+' a ')+1; j=t.index(';\n',i)+2
    wr(f,t[:j]+''.join('    '+l+'\n' for l in lines)+t[j:])
files={}
for f in glob.glob(B+'*.ttl'):
    gg=rdflib.Graph(); gg.parse(f)
    for s in gg.subjects(RDF.type,None): files.setdefault(s,f.split('/')[-1])
n=0
for c,bn in g.subject_objects(T.hasAlternateTerm):
    ty=str(g.value(bn,T.hasAlternateTermType)); sc=inscheme.get(c)
    if not sc or not ty.endswith(('ExactMatch','Abbreviation')): continue
    lab=g.value(bn,SKOS.prefLabel); own={str(l).lower() for l in g.objects(c,SKOS.prefLabel)}
    if str(lab).lower() in pref[sc]-own or str(lab).lower() in own: print('skip clash',q(c),lab); continue
    if (c,SKOS.altLabel,lab) in g: continue
    insert(files[c],q(c),['skos:altLabel "'+str(lab).replace('"','\\"')+'"@'+(lab.language or 'en')+' ;']); n+=1; print('alt',q(c),lab)
print('added',n)
