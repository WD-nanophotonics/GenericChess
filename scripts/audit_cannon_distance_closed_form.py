"""Fresh small-coordinate controls and read-only saved full census comparison."""
import hashlib,json,sys
from collections import deque,Counter
from pathlib import Path
from time import monotonic
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.cannon_distance_closed_form import histogram
from scripts.research_record import write_record
OUT=ROOT/'docs/research/data/cannon_distance_closed_form_20261006.json'
SOURCES=('scripts/audit_cannon_distance_closed_form.py','scripts/cannon_distance_closed_form.py',
 'docs/research/CANNON_DISTANCE_CLOSED_FORM_PROTOCOL.md',
 'docs/research/data/diagnostic_native_contact_mirrored_20261005.json',
 'docs/research/data/diagnostic_contact_independent_20261005.json',
 'generic_chess/rules/xiangqi_diagnostic.py')

def coordinate_distance(width,height,source,target,blocker,checkpoint):
    # No alignment/source-class shortcut from the theorem under test.
    q=deque([(source,0)]);seen={source}
    while q:
        here,cost=q.popleft();checkpoint()
        for df,dr in ((1,0),(-1,0),(0,1),(0,-1)):
            file,rank=here%width+df,here//width+dr;screen=0
            while 0<=file<width and 0<=rank<height:
                square=rank*width+file
                if square==target:
                    if screen==1:return cost+1
                    screen+=1
                elif square==blocker:screen+=1
                elif screen==0 and square not in seen:
                    seen.add(square);q.append((square,cost+1))
                if screen>=2:break
                file+=df;rank+=dr
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
        for width,height in ((3,3),(4,2)):
            row=dict(width=width,height=height,worlds=0,complete=False,histogram={},unreachable=0)
            r['rows'].append(row);hist=Counter();area=width*height
            for source in range(area):
                for target in range(area):
                    if target==source:continue
                    for blocker in range(area):
                        if blocker in (source,target):continue
                        tau=coordinate_distance(width,height,source,target,blocker,check)
                        hist[tau]+=1;row['worlds']+=1;r['worlds']+=1
                        assert r['worlds']<=840
                row.update(histogram={t:hist[t] for t in range(1,5)},unreachable=hist[0]);write_record(OUT,r)
            expected=histogram(width,height)
            assert row['histogram']==expected['histogram'] and row['unreachable']==expected['unreachable'] and row['worlds']==expected['total']
            row['complete']=True;write_record(OUT,r)
        saved=json.loads((ROOT/SOURCES[3]).read_text());ind=json.loads((ROOT/SOURCES[4]).read_text())
        for raw in (saved,ind):
            assert raw['complete'] and raw['source_hashes_unchanged']
            for path,pin in raw['source_sha256'].items():assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==pin
        cannon=next(row for row in saved['rows'] if row['profile']['current']=='C')
        full=histogram(9,10)
        assert full['histogram']=={int(t):n for t,n in cannon['histogram'].items()} and full['unreachable']==cannon['unreachable']
        r['full_analytic']=full;r['saved_full_match']=True;r['complete']=True
    except Exception as error:r['error']=f'{type(error).__name__}: {error}'
    r['seconds']=monotonic()-start
    r['source_hashes_unchanged']=all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in pins.items())
    write_record(OUT,r);print(json.dumps({k:v for k,v in r.items() if k!='source_sha256'}))
