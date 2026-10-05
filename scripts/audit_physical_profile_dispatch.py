"""Whole acyclic current-metadata populations with independent coordinates."""
from collections import deque
from dataclasses import replace,asdict
from generic_chess.core.coordinates import Square
from generic_chess.core.movement import LeapAtom
from generic_chess.core.pieces import Piece,PieceType
from generic_chess.rules.schema import RuleGeometrySpec,RuleReplaceSelector
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.core.transition import initial_state
from generic_chess.core.semantic_executor import semantic_engine_for
import hashlib,json,sys
from pathlib import Path
from time import monotonic
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.promotion_mobility_micro import build as parent
from scripts.physical_profile_event_cubes import PhysicalProfileEventCubes,ContactUnsupported
from scripts.physical_promotion_contact_cubes import PhysicalPromotionContactCubes
from scripts.shared_contact_prefix import Profile
from scripts.native_cube_contact_closure import cube_contact_census
from scripts.research_record import write_record
OUT=ROOT/'docs/research/data/physical_profile_dispatch_20261006.json'
SOURCES=('scripts/audit_physical_profile_dispatch.py','scripts/physical_profile_event_cubes.py','docs/research/PHYSICAL_PROFILE_DISPATCH_PROTOCOL.md','scripts/promotion_mobility_micro.py','scripts/shared_contact_prefix.py','scripts/intrinsic_action_events.py','scripts/native_cube_contact_closure.py')

def build(none=False,names=('opaque_initial','opaque_changed','opaque_final')):
    a,b,c=names;rules=parent(a,b,live=True);offsets=((1,1),(1,-1),(-1,1),(-1,-1))
    types=tuple(replace(t,is_promotable=True,promotion_target_ids=(c,)) if t.type_id==b else t for t in rules.piece_types)+(PieceType(c,c,tuple(LeapAtom(v) for v in offsets)),)
    actions=tuple(replace(p,promotion_mode='none') if none and p.type_ids==(b,) else p for p in rules.semantic_actions);extra=[]
    for relation in ('empty','enemy'):
        original=next(p for p in actions if p.type_ids==(b,) and p.target_relation==relation)
        for i,offset in enumerate(offsets):extra.append(replace(original,name=c+relation+str(i),type_ids=(c,),geometry=RuleGeometrySpec('leap',offset=offset),promotion_mode='inherit_compiled_masks',composition='replace_legacy',replace_selector=RuleReplaceSelector((c,),'board',relation,geometry_kind='leap',replace_all_matching=True)))
    return replace(rules,piece_types=types,semantic_actions=actions+tuple(extra),promotion_allowed=dict(rules.promotion_allowed,**{b:rules.promotion_allowed[a]}),promotion_forced=dict(rules.promotion_forced,**{b:rules.promotion_forced[a]}),drop_allowed=dict(rules.drop_allowed,**{c:((False,)*9,)*2}))

def profiles(names=('opaque_initial','opaque_changed','opaque_final')):
    a,b,c=names;return Profile(a,a),Profile(a,b,True),Profile(b,b),Profile(b,c,True)

def steps(source,mode,owner,none=False):
    if owner:
        for d,v in steps(8-source,mode,0,none):yield 8-d,v
        return
    offsets=((0,1),) if mode==0 else ((1,0),(-1,0),(0,1),(0,-1)) if mode in (1,2) else ((1,1),(1,-1),(-1,1),(-1,-1))
    for df,dr in offsets:
        f,r=source%3+df,source//3+dr
        if not(0<=f<3 and 0<=r<3):continue
        choices=(mode,)
        if mode in (0,2) and not(none and mode==2) and r>=1:
            changed=1 if mode==0 else 3;choices=(changed,) if r==2 else (mode,changed)
        for choice in choices:yield f+3*r,choice

def distance(source,target,blocker,mode,owner,none=False):
    queue=deque([(source,mode,0)]);seen={(source,mode)}
    while queue:
        s,m,n=queue.popleft()
        for d,v in steps(s,m,owner,none):
            if d==target:return n+1
            if d==blocker or (d,v) in seen:continue
            seen.add((d,v));queue.append((d,v,n+1))
    return 0

if __name__=='__main__':
    if OUT.exists():raise FileExistsError('frozen population no rerun')
    start=monotonic();r=dict(complete=False,rows=[],controls=[],worlds=0,candidates=0,enumerated=0,public_transitions=0,source_queries=0,source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES})
    def check():
        if monotonic()-start>=15:raise TimeoutError('whole15sec cap')
        if r['candidates']+r['enumerated']>5000:raise ValueError('whole enumeration cap')
    try:
        pp=profiles()
        for none in (False,True):
            compiled=compile_ruleset_for_execution(build(none));engine=semantic_engine_for(compiled);initial=initial_state(compiled).position
            for owner in (0,1):
                kernel=PhysicalProfileEventCubes(compiled,pp,owner=owner,checkpoint=check);r['candidates']+=kernel.stats['canonical_candidates'];digests={p:[hashlib.sha256(),hashlib.sha256()] for p in pp};mismatch=[]
                def observe(p,s,t,b,value):
                    mode=pp.index(p);expected=distance(s,t,b,mode,owner,none);r['worlds']+=1
                    prefix=f'{s},{t},{b}:';digests[p][0].update(f'{prefix}{value};'.encode());digests[p][1].update(f'{prefix}{expected};'.encode())
                    if value!=expected and not mismatch:mismatch.append(dict(profile=asdict(p),source=s,target=t,blocker=b,value=value,coordinate=expected))
                census=cube_contact_census(kernel,world_observer=observe)['rows']
                for p in pp:r['rows'].append(dict(none=none,owner=owner,profile=asdict(p),census=census[p],cube_sha256=digests[p][0].hexdigest(),coordinate_sha256=digests[p][1].hexdigest(),first_mismatch=mismatch[0] if mismatch else None))
                write_record(OUT,r)
                if mismatch:raise ValueError('whole physical-profile mismatch')
                for mode,p in enumerate(pp):
                    for s,t,b in ((0,1,8),(3,6,0),(3,0,8),(4,5,0),(7,8,0)):
                        if owner:s,t,b=8-s,8-t,8-b
                        board=[None]*9;board[s]=Piece(owner,p.base,p.current,p.promoted);board[t]=Piece(1-owner,'target','target');board[b]=Piece(owner,'blocker','blocker')
                        acts=engine.legal_actions(replace(initial,board=tuple(board),side_to_move=owner),checkpoint=check);r['enumerated']+=len(acts)
                        actual=sorted(set((a.target,pp.index(Profile(p.base,a.promotion_target_id,True)) if a.promotion_target_id else mode) for a in acts if a.source==s));expected=sorted(set((d,v) for d,v in steps(s,mode,owner,none) if d!=b))
                        r['controls'].append(dict(none=none,owner=owner,profile=asdict(p),source=s,target=t,blocker=b,actual=actual,coordinate=expected,all_actions=[asdict(a) for a in acts]));write_record(OUT,r)
                        if actual!=expected or len(acts)>128:raise ValueError('complete profile action-list mismatch')
        renamed=('renamed_a','renamed_b','renamed_c');kernel=PhysicalProfileEventCubes(compile_ruleset_for_execution(build(names=renamed)),profiles(renamed),checkpoint=check);r['candidates']+=kernel.stats['canonical_candidates'];r['renamed']=[row for row in cube_contact_census(kernel)['rows'].values()]
        assert r['renamed']==[x['census'] for x in r['rows'][:4]]
        try:PhysicalPromotionContactCubes(compiled,pp,checkpoint=check)
        except ContactUnsupported as error:r['previous_rejection']=str(error)
        r['complete']=len(r['rows'])==16 and len(r['controls'])==80 and r['worlds']==8064 and bool(r.get('previous_rejection'));check()
    except Exception as error:r['error']=f'{type(error).__name__}: {error}'
    r['seconds']=monotonic()-start;r['source_hashes_unchanged']=all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==pin for p,pin in r['source_sha256'].items());write_record(OUT,r);print(json.dumps({k:v for k,v in r.items() if k not in ('rows','controls','renamed','source_sha256')}))
