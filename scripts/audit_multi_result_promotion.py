"""Whole multiple-result closure with partially alive forced alternatives."""
from collections import deque,Counter
from dataclasses import replace,asdict
import hashlib,json,sys
from pathlib import Path
from time import monotonic
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from generic_chess.core.pieces import Piece,PieceType
from generic_chess.core.movement import LeapAtom
from generic_chess.core.transition import initial_state
from generic_chess.core.semantic_executor import semantic_engine_for
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.schema import RuleReplaceSelector,RuleGeometrySpec
from scripts.promotion_mobility_micro import build as old_build
from scripts.physical_promotion_contact_cubes import PhysicalPromotionContactCubes
from scripts.shared_contact_prefix import Profile
from scripts.native_cube_contact_closure import cube_contact_census
from scripts.research_record import write_record
OUT=ROOT/'docs/research/data/multi_result_promotion_20261005.json'
SOURCES=('scripts/audit_multi_result_promotion.py','docs/research/MULTI_RESULT_PROMOTION_PROTOCOL.md','scripts/promotion_mobility_micro.py','scripts/physical_promotion_contact_cubes.py','scripts/native_cube_contact_closure.py','docs/research/data/promotion_completion_record_20261005.json')
PROFILES=(Profile('opaque_initial','opaque_initial'),Profile('opaque_initial','opaque_changed',True),Profile('opaque_initial','opaque_diagonal',True))
def build(live):
    rules=old_build(live=live);offsets=((-1,-1),(-1,1),(1,-1),(1,1))
    types=tuple(replace(t,promotion_target_ids=('opaque_changed','opaque_diagonal')) if t.type_id=='opaque_initial' else t for t in rules.piece_types)+(PieceType('opaque_diagonal','opaque_diagonal',tuple(LeapAtom(x) for x in offsets)),)
    additions=[]
    for relation in ('empty','enemy'):
        source=next(a for a in rules.semantic_actions if a.type_ids==('opaque_changed',) and a.target_relation==relation)
        for i,offset in enumerate(offsets):additions.append(replace(source,name='diagonal'+relation+str(i),type_ids=('opaque_diagonal',),geometry=RuleGeometrySpec('leap',offset=offset),composition='replace_legacy',replace_selector=RuleReplaceSelector(('opaque_diagonal',),'board',relation,geometry_kind='leap',replace_all_matching=True)))
    return replace(rules,piece_types=types,semantic_actions=rules.semantic_actions+tuple(additions),drop_allowed=dict(rules.drop_allowed,opaque_diagonal=((False,)*9,)*2))
def steps(source,mode,owner,live):
    if owner:
        for dest,nxt in steps(8-source,mode,0,live):yield 8-dest,nxt
        return
    offsets=((0,1),) if mode==0 else ((1,0),(-1,0),(0,1),(0,-1)) if mode==1 else ((1,1),(1,-1),(-1,1),(-1,-1))
    for df,dr in offsets:
        f,r=source%3+df,source//3+dr
        if not(0<=f<3 and 0<=r<3):continue
        if mode:results=(mode,)
        else:results=((0,) if r==1 else ())+((1,) if live else ())+(2,)
        for result in results:yield f+3*r,result
def distance(source,target,blocker,mode,owner,live):
    queue=deque([(source,mode,0)]);seen={(source,mode)}
    while queue:
        here,current,cost=queue.popleft()
        for dest,result in steps(here,current,owner,live):
            if dest==target:return cost+1
            if dest==blocker or (dest,result) in seen:continue
            seen.add((dest,result));queue.append((dest,result,cost+1))
    return 0
if __name__=='__main__':
    if OUT.exists():raise FileExistsError('new multiple-result family never rerun')
    start=monotonic();r=dict(complete=False,rows=[],controls=[],new_candidates=0,new_enumerated=0,worlds=0,public_transitions=0,source_queries=0,source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES})
    def check():
        if monotonic()-start+0.172>=15:raise TimeoutError('cumulative15sec multiple-result cap')
        if r['new_candidates']+144>5000 or r['new_enumerated']+27>5000:raise ValueError('cumulative5000 cap')
    try:
        for live in (False,True):
            compiled=compile_ruleset_for_execution(build(live))
            for owner in (0,1):
                kernel=PhysicalPromotionContactCubes(compiled,PROFILES,owner=owner,checkpoint=check);r['new_candidates']+=kernel.stats['canonical_candidates']
                counts={p:Counter() for p in PROFILES};digests={p:(hashlib.sha256(),hashlib.sha256()) for p in PROFILES};mismatch=[]
                def observe(target,blocker,p,source,value):
                    check();expected=distance(source,target,blocker,PROFILES.index(p),owner,live);counts[p][value]+=1;r['worlds']+=1
                    prefix=f'{target},{blocker},{source}:';digests[p][0].update(f'{prefix}{value};'.encode());digests[p][1].update(f'{prefix}{expected};'.encode())
                    if value!=expected and not mismatch:mismatch.append(dict(profile=asdict(p),source=source,target=target,blocker=blocker,value=value,coordinate=expected))
                census=cube_contact_census(kernel,world_observer=observe)['rows']
                for p in PROFILES:r['rows'].append(dict(live_B=live,owner=owner,profile=asdict(p),census=census[p],worlds=sum(counts[p].values()),cube_sha256=digests[p][0].hexdigest(),coordinate_sha256=digests[p][1].hexdigest(),first_mismatch=mismatch[0] if mismatch else None))
                write_record(OUT,r)
                if mismatch:raise ValueError('multiple-result closure mismatch')
                engine=semantic_engine_for(compiled);initial=initial_state(compiled).position
                for source,target,blocker,mode in ((0,1,8,0),(3,6,0,0),(3,0,8,0),(4,5,0,1),(4,8,1,2)):
                    if owner:source,target,blocker=8-source,8-target,8-blocker
                    p=PROFILES[mode];board=[None]*9;board[source]=Piece(owner,p.base,p.current,p.promoted);board[target]=Piece(1-owner,'target','target');board[blocker]=Piece(owner,'blocker','blocker')
                    acts=engine.legal_actions(replace(initial,board=tuple(board),side_to_move=owner),checkpoint=check);r['new_enumerated']+=len(acts)
                    actual=sorted(set((a.target,mode if a.promotion_target_id is None else 1 if a.promotion_target_id=='opaque_changed' else 2) for a in acts if a.source==source));expected=sorted(set((d,q) for d,q in steps(source,mode,owner,live) if d!=blocker))
                    r['controls'].append(dict(live_B=live,owner=owner,source=source,target=target,blocker=blocker,profile=asdict(p),actual=actual,coordinate=expected,all_actions=[asdict(a) for a in acts]));write_record(OUT,r)
                    if actual!=expected or len(acts)>128:raise ValueError('multiple-result complete physical list mismatch')
        r['complete']=len(r['rows'])==12 and len(r['controls'])==20 and r['worlds']==6048
    except Exception as error:r['error']=f'{type(error).__name__}: {error}'
    r['seconds']=monotonic()-start;r['cumulative_seconds']=r['seconds']+0.172;r['charged_candidates']=r['new_candidates']+144;r['charged_enumerated']=r['new_enumerated']+27;r['source_hashes_unchanged']=all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in r['source_sha256'].items());write_record(OUT,r);print(json.dumps({k:v for k,v in r.items() if k not in ('rows','controls','source_sha256')}))
