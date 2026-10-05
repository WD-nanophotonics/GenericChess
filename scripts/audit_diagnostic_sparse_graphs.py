"""Independent sparse coordinate graphs, not compiled full-world enumeration."""
import hashlib,json,sys
from collections import Counter,deque
from pathlib import Path
from time import monotonic
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.research_record import write_record
OUT=ROOT/'docs/research/data/diagnostic_sparse_graphs_20261006.json'
SOURCES=('scripts/audit_diagnostic_sparse_graphs.py','docs/research/DIAGNOSTIC_SPARSE_GRAPH_PROTOCOL.md',
 'docs/research/data/diagnostic_native_contact_mirrored_20261005.json',
 'generic_chess/rules/xiangqi_diagnostic.py')

def elephant_graph():
    nodes=set(range(45));edges={s:[] for s in nodes}
    for source in nodes:
        f,r=source%9,source//9
        for df in (-2,2):
            for dr in (-2,2):
                target_file,target_rank=f+df,r+dr
                if 0<=target_file<9 and 0<=target_rank<5:
                    edges[source].append((target_rank*9+target_file,(r+dr//2)*9+f+df//2))
    return edges

def component(edges,source):
    seen={source};todo=[source]
    while todo:
        for dest,_ in edges[todo.pop()]:
            if dest not in seen:seen.add(dest);todo.append(dest)
    return seen

def distances(edges,source,blocker,check):
    reached={source:0};queue=deque([source])
    while queue:
        here=queue.popleft();check()
        for dest,eye in edges[here]:
            if blocker in (dest,eye) or dest in reached:continue
            reached[dest]=reached[here]+1;queue.append(dest)
    return reached

if __name__=='__main__':
    if OUT.exists():raise FileExistsError('closed sparse aggregate study')
    start=monotonic();r=dict(complete=False,source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES},
      rows=[],classes=0,expanded_nodes=0,compilations=0,canonical_geometry_candidates=0,
      runtime_pushes=0,public_transitions=0,source_queries=0)
    def check():
        r['expanded_nodes']+=1
        if r['expanded_nodes']>5000 or monotonic()-start>=15:raise RuntimeError('5000 node/15sec cap')
    try:
        edges=elephant_graph();all_squares=set(range(90));hist=Counter({0:45*89*88})
        components=[];remaining=set(edges)
        while remaining:
            comp=component(edges,min(remaining));remaining-=comp
            eyes={eye for s in comp for _,eye in edges[s]}
            undirected={tuple(sorted((s,d))) for s in comp for d,_ in edges[s]}
            assert not comp&eyes
            entry=dict(vertices=sorted(comp),eyes=sorted(eyes),edges=len(undirected))
            components.append(entry)
            for source in sorted(comp):
                generic=all_squares-comp-eyes
                cases=[(b,1) for b in sorted((comp-{source})|eyes)]+[(None,len(generic))]
                assert sum(n for _,n in cases)==89
                row=dict(source=source,cases=[],complete=False);r['rows'].append(row)
                for blocker,multiplicity in cases:
                    reached=distances(edges,source,blocker,check);counts=Counter(reached.values());counts.pop(0,None)
                    # Every blocker case has88 admissible target choices.
                    counts[0]=88-(len(reached)-1)
                    assert sum(counts.values())==88
                    for tau,count in counts.items():hist[tau]+=multiplicity*count
                    row['cases'].append(dict(blocker=blocker,multiplicity=multiplicity,histogram=dict(counts)))
                    r['classes']+=1;assert r['classes']<=1000
                row['complete']=True;write_record(OUT,r)
        assert sorted(len(c['vertices']) for c in components)==[4,4,5,5,6,6,7,8]
        full=dict(E=dict(histogram={t:n for t,n in sorted(hist.items()) if t},unreachable=hist[0],total=sum(hist.values())),
                  A=dict(histogram={1:16*88,2:16*88-12},unreachable=704880-(32*88-12),total=704880))
        assert full['E']['total']==704880
        saved=json.loads((ROOT/SOURCES[2]).read_text());assert saved['complete'] and saved['source_hashes_unchanged']
        for path,pin in saved['source_sha256'].items():assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==pin
        for mode,counts in full.items():
            old=next(x for x in saved['rows'] if x['profile']['current']==mode)
            assert counts['histogram']=={int(t):n for t,n in old['histogram'].items()} and counts['unreachable']==old['unreachable']
        r.update(components=components,full_aggregate=full,saved_full_match=True,complete=True)
    except Exception as error:r['error']=f'{type(error).__name__}: {error}'
    r['seconds']=monotonic()-start
    r['source_hashes_unchanged']=all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==pin for p,pin in r['source_sha256'].items())
    write_record(OUT,r);print(json.dumps({k:v for k,v in r.items() if k not in ('source_sha256','rows','components')}))
