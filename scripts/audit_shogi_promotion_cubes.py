"""Fixed real-Shogi profile slabs and independently specified coordinate graph."""
from collections import Counter,deque
from dataclasses import asdict,replace
import hashlib,json,sys
from pathlib import Path
from time import monotonic
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from generic_chess.core.pieces import Piece
from generic_chess.core.transition import initial_state
from generic_chess.core.semantic_executor import semantic_engine_for
from scripts.physical_promotion_contact_cubes import PhysicalPromotionContactCubes
from scripts.shared_contact_prefix import Profile
from scripts.sparse_contact_cubes import blocker_mask
from scripts.research_record import write_record
OUT=ROOT/'docs/research/data/shogi_promotion_cubes_20261005.json'
SOURCES=('scripts/audit_shogi_promotion_cubes.py','docs/research/SHOGI_PROMOTION_CUBE_PROTOCOL.md','scripts/physical_promotion_contact_cubes.py','scripts/promotable_contact_cubes.py','scripts/typed_sparse_contact_cubes.py','scripts/sparse_contact_cubes.py','scripts/intrinsic_action_events.py','generic_chess/rules/standard_shogi.py')
PROFILES=(Profile('P','P'),Profile('N','N'),Profile('P','TP',True),Profile('N','TN',True))
def coordinate_steps(source,mode,owner):
    if owner:
        for dest,nxt in coordinate_steps(80-source,mode,0):yield 80-dest,nxt
        return
    offsets=((0,1),) if mode==0 else ((-1,2),(1,2)) if mode==1 else ((0,1),(-1,1),(1,1),(-1,0),(1,0),(0,-1))
    for df,dr in offsets:
        f,r=source%9+df,source//9+dr
        if not (0<=f<9 and 0<=r<9):continue
        result=(mode,) if mode>=2 else (mode+2,) if r>=8-mode else (mode,mode+2) if source//9>=6 or r>=6 else (mode,)
        for nxt in result:yield f+9*r,nxt
def maps(kernel,target):
    edges=[];captures=[];indices={p:i for i,p in enumerate(PROFILES)}
    for p,i in indices.items():
        for source in range(81):
            if source==target:continue
            for (dest,nxt),cubes in kernel.quiet[p,source].items():
                if dest==target:continue
                mask=0
                for cube in cubes:mask|=blocker_mask(cube,area=81,source=source,target=dest,enemy=target)
                if mask:edges.append((i*81+source,indices[nxt]*81+dest,mask))
            mask=0
            for cube in kernel.capture[p,source].get(target,()):mask|=blocker_mask(cube,area=81,source=source,target=target,enemy=target)
            if mask:captures.append((i*81+source,mask))
    return edges,captures
def reverse_distances(edges,captures,blocker):
    reverse=[[] for _ in range(324)];values=[0]*324;todo=deque();bit=1<<blocker
    for source,dest,mask in edges:
        if mask&bit:reverse[dest].append(source)
    for source,mask in captures:
        if mask&bit and values[source]==0:values[source]=1;todo.append(source)
    while todo:
        dest=todo.popleft()
        for source in reverse[dest]:
            if values[source]==0:values[source]=values[dest]+1;todo.append(source)
    return values
def coordinate_distances(target,blocker,owner):
    edges=[];captures=[];bit=1<<blocker
    for mode in range(4):
        for source in range(81):
            if source in (target,blocker):continue
            for dest,nxt in coordinate_steps(source,mode,owner):
                if dest==blocker:continue
                if dest==target:captures.append((mode*81+source,bit))
                else:edges.append((mode*81+source,nxt*81+dest,bit))
    return reverse_distances(edges,captures,blocker)
if __name__=='__main__':
    if OUT.exists():raise FileExistsError('prospective real-Shogi slabs never rerun')
    start=monotonic();r=dict(complete=False,rows=[],controls=[],worlds=0,canonical_candidates=0,enumerated=0,public_transitions=0,source_queries=0,source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES})
    def check():
        if monotonic()-start>=15:raise TimeoutError('15sec real-Shogi selected slabs')
    try:
        compiled=compile_ruleset_for_execution(build_standard_shogi_ruleset());r['fingerprint']=compiled.fingerprint
        for owner in (0,1):
            kernel=PhysicalPromotionContactCubes(compiled,PROFILES,owner=owner,checkpoint=check);r['canonical_candidates']+=kernel.stats['canonical_candidates']
            if r['canonical_candidates']>5000:raise ValueError('whole geometry cap')
            for target in (8,40,72):
                edges,captures=maps(kernel,target);counts=[Counter() for _ in PROFILES];digests=[(hashlib.sha256(),hashlib.sha256()) for _ in PROFILES];mismatch=[]
                for blocker in range(81):
                    if blocker==target:continue
                    check();actual=reverse_distances(edges,captures,blocker);expected=coordinate_distances(target,blocker,owner)
                    for mode,p in enumerate(PROFILES):
                        for source in range(81):
                            if source in (target,blocker):continue
                            value,want=actual[mode*81+source],expected[mode*81+source];counts[mode][value]+=1;r['worlds']+=1
                            prefix=f'{blocker},{source}:';digests[mode][0].update(f'{prefix}{value};'.encode());digests[mode][1].update(f'{prefix}{want};'.encode())
                            if value!=want and not mismatch:mismatch.append(dict(profile=asdict(p),blocker=blocker,source=source,actual=value,coordinate=want))
                for mode,p in enumerate(PROFILES):r['rows'].append(dict(owner=owner,target=target,profile=asdict(p),counts=dict(sorted(counts[mode].items())),worlds=sum(counts[mode].values()),cube_sha256=digests[mode][0].hexdigest(),coordinate_sha256=digests[mode][1].hexdigest(),first_mismatch=mismatch[0] if mismatch else None))
                write_record(OUT,r)
                if mismatch:raise ValueError('real-Shogi promotion world mismatch')
            engine=semantic_engine_for(compiled);initial=initial_state(compiled).position
            for source,mode in ((49,0),(67,0),(49,1),(58,1),(40,2),(40,3)):
                target,blocker=80,0
                if owner:source,target,blocker=80-source,80-target,80-blocker
                p=PROFILES[mode];board=[None]*81;board[source]=Piece(owner,p.base,p.current,p.promoted);board[target]=Piece(1-owner,'G','G');board[blocker]=Piece(owner,'G','G')
                acts=engine.legal_actions(replace(initial,board=tuple(board),side_to_move=owner),checkpoint=check);r['enumerated']+=len(acts)
                actual=sorted(set((a.target,mode if a.promotion_target_id is None else mode+2) for a in acts if a.source==source))
                expected=sorted(set((d,nxt) for d,nxt in coordinate_steps(source,mode,owner) if d!=blocker))
                r['controls'].append(dict(owner=owner,source=source,profile=asdict(p),actual=actual,expected=expected,all_actions=[asdict(a) for a in acts]));write_record(OUT,r)
                if actual!=expected or len(acts)>128 or r['enumerated']>5000:raise ValueError('complete virtual promotion list mismatch')
        r['complete']=len(r['rows'])==24 and len(r['controls'])==12 and r['worlds']==151680
    except Exception as error:r['error']=f'{type(error).__name__}: {error}'
    r['seconds']=monotonic()-start;r['source_hashes_unchanged']=all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in r['source_sha256'].items());write_record(OUT,r);print(json.dumps({k:v for k,v in r.items() if k not in ('rows','controls','source_sha256')}))
