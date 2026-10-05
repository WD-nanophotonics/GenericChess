"""New full tiny promotion worlds and independent coordinate/current oracle."""
from collections import Counter,deque
from dataclasses import asdict,replace
from fractions import Fraction as F
import hashlib,json,sys
from pathlib import Path
from time import monotonic
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from generic_chess.core.pieces import Piece,PieceType
from generic_chess.core.movement import LeapAtom
from generic_chess.core.transition import initial_state
from generic_chess.core.semantic_executor import semantic_engine_for
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.schema import RuleSet,RuleSemanticAction,RuleGeometrySpec,RuleActionEffect,RuleSquareRef,RuleStateGuard,RuleTypeRef,RuleSpatialSelector
from scripts.promotable_contact_cubes import PromotableContactCubes,ContactUnsupported
from scripts.native_cube_contact_closure import cube_contact_census
from scripts.shared_contact_prefix import Profile
from scripts.research_record import write_record
OUT=ROOT/'docs/research/data/promotable_cube_micro_20261005.json'
SOURCES=('scripts/audit_promotable_cube_micro.py','scripts/promotable_contact_cubes.py','docs/research/PROMOTABLE_CUBE_MICRO_PROTOCOL.md','scripts/typed_sparse_contact_cubes.py','scripts/sparse_contact_cubes.py','scripts/intrinsic_action_events.py','scripts/native_cube_contact_closure.py')
def build(native='opaque_initial',promoted='opaque_changed',*,none=False,guard=False,promoted_promotable=False):
    n=3;rows=[[None]*n for _ in range(n)];rows[0][0]=Piece(0,'anchor','anchor');rows[2][2]=Piece(1,'anchor','anchor')
    types=(PieceType(native,native,(),is_promotable=True,promotion_target_ids=(promoted,)),PieceType(promoted,promoted,(),is_promotable=promoted_promotable,promotion_target_ids=(native,) if promoted_promotable else ()),PieceType('target','target',()),PieceType('blocker','blocker',()),PieceType('anchor','anchor',(LeapAtom((0,1)),),is_anchor=True))
    actions=[];ref=lambda kind:RuleSquareRef(kind)
    for kind in (native,promoted):
        offsets=((0,1),) if kind==native else ((1,0),(-1,0),(0,1),(0,-1))
        for relation in ('empty','enemy'):
            for i,offset in enumerate(offsets):
                effects=(RuleActionEffect('move',from_ref=ref('source'),to_ref=ref('target')),)
                if relation=='enemy':effects=(RuleActionEffect('remove',square_ref=ref('target'),piece_owner='opponent',disposition='remove_from_game'),)+effects
                guards=(RuleStateGuard('count','self',RuleTypeRef('explicit',type_id=native),'base','no','board',RuleSpatialSelector('exact',refs=(ref('source'),)),comparison='eq',value=1,subject_ref=ref('source')),) if guard else ()
                actions.append(RuleSemanticAction(kind+relation+str(i),(kind,),RuleGeometrySpec('leap',offset=offset),relation,effects=effects,state_guards=guards,promotion_mode='none' if none else 'inherit_compiled_masks'))
    masks=tuple(frozenset(((sf,sr),(tf,tr)) for sf in range(3) for sr in range(3) for tf in range(3) for tr in range(3) if (tr>=1 if owner==0 else tr<=1)) for owner in (0,1))
    forced=tuple(frozenset((f,2 if owner==0 else 0) for f in range(3)) for owner in (0,1))
    return RuleSet(board_size=3,piece_types=types,initial_position=tuple(tuple(row) for row in rows),drop_allowed={p.type_id:((False,)*9,)*2 for p in types if not p.is_anchor},promotion_allowed={native:masks},promotion_forced={native:forced},semantic_actions=tuple(actions),capture_disposition='remove_from_game')
def coordinate_steps(source,current,owner):
    offsets=((0,1),) if current==0 else ((1,0),(-1,0),(0,1),(0,-1));sign=1 if owner==0 else -1
    for df,dr in offsets:
        f,r=source%3+df*sign,source//3+dr*sign
        if not(0<=f<3 and 0<=r<3):continue
        profiles=(1,) if current==1 else (1,) if r==(2 if owner==0 else 0) else (0,1) if r==1 else (0,)
        for result in profiles:yield f+3*r,result
def coordinate_distance(source,target,blocker,current,owner):
    queue=deque([(source,current,0)]);seen={(source,current)}
    while queue:
        here,mode,cost=queue.popleft()
        for dest,result in coordinate_steps(here,mode,owner):
            if dest==target:return cost+1
            if dest==blocker or (dest,result) in seen:continue
            seen.add((dest,result));queue.append((dest,result,cost+1))
    return 0
if __name__=='__main__':
    if OUT.exists():raise FileExistsError('prospective promotion family never rerun')
    start=monotonic();r=dict(complete=False,rows=[],controls=[],rejections={},canonical_candidates=0,enumerated=0,public_transitions=0,source_queries=0,source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES})
    def check():
        if monotonic()-start>=15:raise TimeoutError('15sec full promotion micro study')
    try:
        p0=Profile('opaque_initial','opaque_initial');p1=Profile('opaque_initial','opaque_changed',True)
        for owner in (0,1):
            c=compile_ruleset_for_execution(build());kernel=PromotableContactCubes(c,(p0,p1),owner=owner,checkpoint=check);r['canonical_candidates']+=kernel.stats['canonical_candidates']
            digests={p:(hashlib.sha256(),hashlib.sha256()) for p in (p0,p1)};counts={p:Counter() for p in (p0,p1)};first=[]
            def observe(target,blocker,p,source,distance):
                check();expected=coordinate_distance(source,target,blocker,int(p.promoted),owner);counts[p][expected]+=1
                prefix=f'{target},{blocker},{source}:';digests[p][0].update((prefix+str(distance)+';').encode());digests[p][1].update((prefix+str(expected)+';').encode())
                if expected!=distance and not first:first.append(dict(target=target,blocker=blocker,source=source,profile=asdict(p),actual=distance,expected=expected))
            census=cube_contact_census(kernel,world_observer=observe)['rows']
            for p in (p0,p1):
                row=dict(owner=owner,profile=asdict(p),worlds=sum(counts[p].values()),census=census[p],ordered_cube_sha256=digests[p][0].hexdigest(),ordered_coordinate_sha256=digests[p][1].hexdigest(),first_mismatch=first[0] if first else None);r['rows'].append(row);write_record(OUT,r)
                if row['worlds']!=504 or first or row['ordered_cube_sha256']!=row['ordered_coordinate_sha256']:raise ValueError('promotion worldwise mismatch')
            engine=semantic_engine_for(c);initial=initial_state(c).position
            for src,tgt,blk,p in ((0,1,8,p0),(3,6,0,p0),(3,0,8,p0),(4,5,0,p1)):
                if owner:src,tgt,blk=8-src,8-tgt,8-blk
                board=[None]*9;board[src]=Piece(owner,p.base,p.current,p.promoted);board[tgt]=Piece(1-owner,'target','target');board[blk]=Piece(owner,'blocker','blocker')
                acts=engine.legal_actions(replace(initial,board=tuple(board),side_to_move=owner),checkpoint=check);r['enumerated']+=len(acts)
                actual=sorted((a.target,int(a.promotion_type is not None or p.promoted)) for a in acts if a.source==src)
                expected=sorted((d,q) for d,q in coordinate_steps(src,int(p.promoted),owner) if d!=blk)
                r['controls'].append(dict(owner=owner,source=src,target=tgt,blocker=blk,profile=asdict(p),actual=actual,expected=expected,all_actions=[asdict(a) for a in acts]));write_record(OUT,r)
                if actual!=expected or len(acts)>128:raise ValueError('complete promotion semantic action mismatch')
        renamed=PromotableContactCubes(compile_ruleset_for_execution(build('renamed_initial','renamed_changed')),(Profile('renamed_initial','renamed_initial'),Profile('renamed_initial','renamed_changed',True)),checkpoint=check)
        r['canonical_candidates']+=renamed.stats['canonical_candidates'];r['renamed_census']={str(p.promoted):x for p,x in cube_contact_census(renamed)['rows'].items()}
        for control in ('none','guard','promoted_promotable'):
            try:PromotableContactCubes(compile_ruleset_for_execution(build(**{control:True})),(p0,p1),checkpoint=check)
            except ContactUnsupported as error:r['rejections'][control]=str(error)
        if r['canonical_candidates']>5000 or r['enumerated']>5000:raise ValueError('unchanged cost caps')
        r['complete']=len(r['rows'])==4 and len(r['controls'])==8 and len(r['rejections'])==3 and all(r['renamed_census'][str(p.promoted)]==r['rows'][i]['census'] for i,p in enumerate((p0,p1)))
    except Exception as error:r['error']=f'{type(error).__name__}: {error}'
    r['seconds']=monotonic()-start;r['source_hashes_unchanged']=all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in r['source_sha256'].items());write_record(OUT,r);print(json.dumps({k:v for k,v in r.items() if k not in ('rows','controls','source_sha256','renamed_census')}))
