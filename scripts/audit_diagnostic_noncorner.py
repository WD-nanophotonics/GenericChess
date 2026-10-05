"""Independent fixed-target distances, reused lossless native cube cache."""
from collections import Counter,deque
import hashlib,json,sys
from pathlib import Path
from time import monotonic
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.sparse_contact_cubes import blocker_mask
from scripts.diagnostic_contact_coordinate_oracle import distance
from scripts.research_record import write_record
OUT=ROOT/'docs/research/data/diagnostic_noncorner_20261005.json'
SOURCES=('scripts/audit_diagnostic_noncorner.py','docs/research/DIAGNOSTIC_NONCORNER_PROTOCOL.md','docs/research/data/diagnostic_native_contact_kernel_20261005.json','docs/research/data/diagnostic_native_contact_mirrored_20261005.json','scripts/diagnostic_contact_coordinate_oracle.py','scripts/sparse_contact_cubes.py')
def fixed_target_maps(cache,target):
    edges={t:[] for t in ('A','C','E','H','R','S')};captures={t:[] for t in edges}
    for kind in ('quiet','capture'):
        for row in cache[kind]:
            source=row['source'];mode=row['profile']['current']
            dest=row['destination'] if kind=='quiet' else row['target']
            if source==target or (kind=='quiet' and dest==target) or (kind=='capture' and dest!=target):continue
            mask=0
            for cube in row['cubes']:mask|=blocker_mask(cube,area=90,source=source,target=dest,enemy=target)
            if mask:(edges[mode] if kind=='quiet' else captures[mode]).append((source,dest,mask))
    return edges,captures
def blocker_distances(edges,captures,blocker):
    reverse=[[] for _ in range(90)];values=[0]*90;queue=deque();bit=1<<blocker
    for source,dest,mask in edges:
        if mask&bit:reverse[dest].append(source)
    for source,_,mask in captures:
        if mask&bit:values[source]=1;queue.append(source)
    while queue:
        dest=queue.popleft()
        for source in reverse[dest]:
            if values[source]==0:values[source]=values[dest]+1;queue.append(source)
    return values
if __name__=='__main__':
    if OUT.exists():raise FileExistsError('fixed noncorner study never rerun')
    start=monotonic();r=dict(complete=False,rows=[],new_worlds=0,canonical_candidates=0,enumerated=0,public_transitions=0,virtual_materializations=0,source_queries=0,source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES})
    def check():
        if monotonic()-start>=15:raise TimeoutError('15sec selected diagnostic slabs')
    try:
        cache=json.loads((ROOT/SOURCES[2]).read_text());saved=json.loads((ROOT/SOURCES[3]).read_text())
        assert saved['complete'] and cache['area']==90
        for p,h in saved['source_sha256'].items():assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h
        for target in (13,40,60):
            check();edges,captures=fixed_target_maps(cache,target)
            slab=next(x for x in saved['completed_target_slabs'] if x['target']==target)
            for mode in edges:
                counts=Counter();digests=(hashlib.sha256(),hashlib.sha256());mismatches=[]
                for blocker in range(90):
                    if blocker==target:continue
                    check();actual=blocker_distances(edges[mode],captures[mode],blocker)
                    for source in range(90):
                        if source in (target,blocker):continue
                        check();expected=distance(mode,source,target,blocker);value=actual[source];counts[value]+=1;r['new_worlds']+=1
                        prefix=f'{blocker},{source}:';digests[0].update(f'{prefix}{value};'.encode());digests[1].update(f'{prefix}{expected};'.encode())
                        if value!=expected and not mismatches:mismatches.append(dict(blocker=blocker,source=source,actual=value,coordinate=expected))
                old=next(x['counts'] for x in slab['rows'] if x['profile']['current']==mode)
                row=dict(target=target,mode=mode,owner=0,worlds=sum(counts.values()),counts=dict(sorted(counts.items())),saved_counts=old,cube_sha256=digests[0].hexdigest(),coordinate_sha256=digests[1].hexdigest(),first_mismatch=mismatches[0] if mismatches else None)
                r['rows'].append(row);write_record(OUT,r)
                if mismatches or row['worlds']!=7832 or {str(k):v for k,v in counts.items()}!=old:raise ValueError('fixed whole-mode world mismatch')
        r['complete']=len(r['rows'])==18 and r['new_worlds']==140976
    except Exception as error:r['error']=f'{type(error).__name__}: {error}'
    r['seconds']=monotonic()-start;r['source_hashes_unchanged']=all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in r['source_sha256'].items());write_record(OUT,r)
    print(json.dumps({k:v for k,v in r.items() if k not in ('rows','source_sha256')}))
