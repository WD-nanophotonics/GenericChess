"""Frozen small BFS controls plus read-only aggregate comparison."""
import hashlib,json,sys
from collections import deque,Counter
from pathlib import Path
from time import monotonic
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.soldier_distance_closed_form import histogram,pair_counts
from scripts.research_record import write_record
OUT=ROOT/'docs/research/data/soldier_distance_closed_form_20261006.json'
SOURCES=('scripts/audit_soldier_distance_closed_form.py','scripts/soldier_distance_closed_form.py',
 'docs/research/SOLDIER_DISTANCE_CLOSED_FORM_PROTOCOL.md',
 'docs/research/data/diagnostic_native_contact_mirrored_20261005.json',
 'generic_chess/rules/xiangqi_diagnostic.py')
PAIRS=((0,1),(0,2),(0,3),(0,4),(0,5),(0,6),(0,7),(0,8),(0,9),
 (0,10),(0,11),(3,5),(3,9),(3,11),(6,8),(6,9),(9,11),(11,0))

def distance(width,height,river,source,target,blocker,check):
    q=deque([(source,0)]);seen={source}
    while q:
        here,cost=q.popleft();check()
        directions=[(0,1)]
        if here//width>=river:directions.extend(((1,0),(-1,0)))
        for df,dr in directions:
            f,r=here%width+df,here//width+dr
            if not 0<=f<width or not 0<=r<height:continue
            square=r*width+f
            if square==blocker:continue
            if square==target:return cost+1
            if square not in seen:seen.add(square);q.append((square,cost+1))
    return 0

if __name__=='__main__':
    if OUT.exists():raise FileExistsError('closed small-control study')
    start=monotonic();pins={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES}
    r=dict(complete=False,source_sha256=pins,rows=[],worlds=0,expanded_nodes=0,
      compilations=0,canonical_geometry_candidates=0,public_transitions=0,runtime_pushes=0,source_queries=0)
    def check():
        r['expanded_nodes']+=1
        if r['expanded_nodes']>5000 or monotonic()-start>=15:raise RuntimeError('5000 nodes/15sec cap')
    try:
        for width,height,river,selected in ((3,3,1,None),(3,4,1,PAIRS)):
            area=width*height;pairs=selected or tuple((s,d) for s in range(area) for d in range(area) if s!=d)
            row=dict(width=width,height=height,river=river,complete=False,pairs=[],worlds=0)
            r['rows'].append(row);aggregate=Counter()
            for source,target in pairs:
                counts=Counter()
                for blocker in range(area):
                    if blocker in (source,target):continue
                    tau=distance(width,height,river,source,target,blocker,check)
                    counts[tau]+=1;aggregate[tau]+=1;r['worlds']+=1;row['worlds']+=1
                    assert r['worlds']<=684
                expected=pair_counts(width,height,river,source//width,target//width,abs(source%width-target%width))
                # Zero-sized distance classes may occur in the analytic partition.
                assert dict(counts)=={t:n for t,n in expected.items() if n},(source,target,counts,expected)
                row['pairs'].append(dict(source=source,target=target,histogram=dict(counts)))
                write_record(OUT,r)
            row['histogram']={t:n for t,n in sorted(aggregate.items()) if t};row['unreachable']=aggregate[0]
            if selected is None:
                full=histogram(width,height,river)
                assert row['histogram']==full['histogram'] and row['unreachable']==full['unreachable']
            row['complete']=True;write_record(OUT,r)
        saved=json.loads((ROOT/SOURCES[3]).read_text())
        assert saved['complete'] and saved['source_hashes_unchanged']
        for path,pin in saved['source_sha256'].items():assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==pin
        soldier=next(x for x in saved['rows'] if x['profile']['current']=='S')
        full=histogram(9,10,5)
        assert full['histogram']=={int(t):n for t,n in soldier['histogram'].items()} and full['unreachable']==soldier['unreachable']
        r['full_analytic']=full;r['saved_full_match']=True;r['complete']=True
    except Exception as error:r['error']=f'{type(error).__name__}: {error}'
    r['seconds']=monotonic()-start
    r['source_hashes_unchanged']=all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in pins.items())
    write_record(OUT,r);print(json.dumps({k:v for k,v in r.items() if k not in ('source_sha256','rows')}))
