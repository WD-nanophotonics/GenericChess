"""Fresh native micro controls and independent ordered contact distances."""
from collections import Counter,deque
from dataclasses import replace,asdict
import hashlib,json,sys
from pathlib import Path
from time import monotonic
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from generic_chess.core.movement import LeapAtom
from generic_chess.core.pieces import Piece,PieceType
from generic_chess.core.transition import initial_state
from generic_chess.core.semantic_executor import semantic_engine_for
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.schema import RuleSet,RuleSemanticAction,RuleGeometrySpec,RuleActionEffect,RuleSquareRef,RulePathConstraint,RuleStateGuard,RuleTypeRef,RuleSpatialSelector
from scripts.shared_contact_prefix import Profile
from scripts.native_cube_contact_closure import NativeCubeKernel,cube_contact_census
from scripts.research_record import write_record
OUT=ROOT/'docs/research/data/native_cube_contact_closure_20261005.json'
SOURCES=('scripts/audit_native_cube_contact_closure.py','scripts/native_cube_contact_closure.py','docs/research/NATIVE_CUBE_CONTACT_CLOSURE_PROTOCOL.md','scripts/typed_sparse_contact_cubes.py','scripts/sparse_contact_cubes.py','scripts/intrinsic_action_events.py','scripts/intrinsic_occupancy_cubes.py','scripts/rule_neutral_contact_constructor.py')

def build(family,actor='unnamed_actor'):
    n=4;rows=[[None]*n for _ in range(n)];rows[1][0]=Piece(0,'anchor','anchor');rows[2][3]=Piece(1,'anchor','anchor')
    actions=[];ref=lambda kind:RuleSquareRef(kind)
    offsets=([(df,dr) for df,dr in ((1,0),(-1,0),(0,1),(0,-1))] if family=='C' else
             [(df,dr) for df in (-2,-1,1,2) for dr in (-2,-1,1,2) if abs(df)+abs(dr)==3] if family=='H' else
             [(df,dr) for df in (-2,2) for dr in (-2,2)])
    for relation in ('empty','enemy'):
        for i,(df,dr) in enumerate(offsets):
            geometry=RuleGeometrySpec('ray',direction=(df,dr),min_steps=1) if family=='C' else RuleGeometrySpec('leap',offset=(df,dr))
            guards=()
            if family!='C':
                offset=(df//2,dr//2) if family=='E' else ((1 if df>0 else -1,0) if abs(df)==2 else (0,1 if dr>0 else -1))
                operand=RuleSquareRef('offset_from_source',offset=offset)
                guards=(RuleStateGuard('count','any',RuleTypeRef('any'),'current','any','board',RuleSpatialSelector('exact',refs=(operand,)),comparison='eq',value=0,subject_ref=operand),)
            effects=(RuleActionEffect('move',from_ref=ref('source'),to_ref=ref('target')),)
            if relation=='enemy':effects=(RuleActionEffect('remove',square_ref=ref('target'),piece_owner='opponent',disposition='remove_from_game'),)+effects
            path=(RulePathConstraint('path_clear'),) if family=='C' and relation=='empty' else (RulePathConstraint('path_count_eq',count=1),) if family=='C' else ()
            actions.append(RuleSemanticAction('opaque_'+relation+str(i),(actor,),geometry,relation,path_constraints=path,state_guards=guards,effects=effects))
    types=(PieceType(actor,actor,()),PieceType('target','target',()),PieceType('blocker','blocker',()),PieceType('anchor','anchor',(LeapAtom((0,1)),),is_anchor=True))
    return RuleSet(board_size=n,piece_types=types,initial_position=tuple(tuple(row) for row in rows),
        drop_allowed={p.type_id:((False,)*16,)*2 for p in types if not p.is_anchor},semantic_actions=tuple(actions),capture_disposition='remove_from_game')

def moves(family,source,target,blocker,owner,*,capture):
    n=4;sf,sr=source%n,source//n;sign=1 if owner==0 else -1
    if family=='C':
        for df,dr in ((1,0),(-1,0),(0,1),(0,-1)):
            f,r=sf+df,sr+dr;occupied=0
            while 0<=f<n and 0<=r<n:
                dest=f+n*r
                if capture and dest==target and occupied==1:yield dest
                if not capture and dest not in (target,blocker) and occupied==0:yield dest
                if dest in (target,blocker):occupied+=1
                f+=df;r+=dr
        return
    offsets=([(df,dr) for df in (-2,-1,1,2) for dr in (-2,-1,1,2) if abs(df)+abs(dr)==3] if family=='H' else [(df,dr) for df in (-2,2) for dr in (-2,2)])
    for df,dr in offsets:
        f,r=sf+df*sign,sr+dr*sign
        if not (0<=f<n and 0<=r<n):continue
        leg=(df//2,dr//2) if family=='E' else ((1 if df>0 else -1,0) if abs(df)==2 else (0,1 if dr>0 else -1))
        eye=(sf+leg[0]*sign)+n*(sr+leg[1]*sign);dest=f+n*r
        if eye in (target,blocker):continue
        if capture and dest==target:yield dest
        if not capture and dest not in (target,blocker):yield dest

def coordinate_distance(family,source,target,blocker,owner):
    queue=deque([(source,0)]);seen={source}
    while queue:
        here,cost=queue.popleft()
        if any(True for _ in moves(family,here,target,blocker,owner,capture=True)):return cost+1
        for nxt in moves(family,here,target,blocker,owner,capture=False):
            if nxt not in seen:seen.add(nxt);queue.append((nxt,cost+1))
    return 0

if __name__=='__main__':
    if OUT.exists():raise FileExistsError('new native cube closure never rerun')
    start=monotonic();r=dict(complete=False,rows=[],controls=[],canonical_candidates=0,enumerated=0,public_transitions=0,source_queries=0,
        source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES})
    def check():
        if monotonic()-start>=15:raise TimeoutError('15sec entire cube study')
    try:
        for family in ('C','H','E'):
            for owner in (0,1):
                check();c=compile_ruleset_for_execution(build(family));p=Profile('unnamed_actor','unnamed_actor')
                kernel=NativeCubeKernel(c,(p,),owner=owner,checkpoint=check);r['canonical_candidates']+=kernel.stats['canonical_candidates']
                digest=hashlib.sha256();independent=hashlib.sha256();counts=Counter();worlds=[0];mismatch=[]
                def observe(target,blocker,profile,source,distance):
                    check();oracle=coordinate_distance(family,source,target,blocker,owner);worlds[0]+=1;counts[oracle]+=1
                    prefix=f'{target},{blocker},{source}:'
                    digest.update((prefix+str(distance)+';').encode());independent.update((prefix+str(oracle)+';').encode())
                    if oracle!=distance and not mismatch:mismatch.append(dict(source=source,target=target,blocker=blocker,oracle=oracle,cube=distance))
                census=cube_contact_census(kernel,world_observer=observe)['rows'][p]
                row=dict(family=family,owner=owner,census=census,worlds=worlds[0],ordered_cube_sha256=digest.hexdigest(),ordered_coordinate_sha256=independent.hexdigest(),first_mismatch=mismatch[0] if mismatch else None)
                r['rows'].append(row);write_record(OUT,r)
                if worlds[0]!=3360 or mismatch or census['histogram']!={t:n for t,n in counts.items() if t} or census['unreachable']!=counts[0]:raise ValueError('ordered distance mismatch')
                engine=semantic_engine_for(c);initial=initial_state(c).position
                cases=((0,2,1),(0,3,1)) if family=='C' else ((0,6,1),(0,6,5)) if family=='H' else ((0,10,5),(0,10,1))
                for source,target,blocker in cases:
                    if owner:source,target,blocker=15-source,15-target,15-blocker
                    board=[None]*16;board[source]=Piece(owner,'unnamed_actor','unnamed_actor');board[target]=Piece(1-owner,'target','target');board[blocker]=Piece(owner,'blocker','blocker')
                    position=replace(initial,board=tuple(board),side_to_move=owner);actions=engine.legal_actions(position,checkpoint=check);r['enumerated']+=len(actions)
                    if len(actions)>128 or r['canonical_candidates']+r['enumerated']>5000:raise ValueError('unchanged candidate/entry cap')
                    actual=any(a.source==source and a.target==target for a in actions);expected=any(True for _ in moves(family,source,target,blocker,owner,capture=True))
                    r['controls'].append(dict(family=family,owner=owner,source=source,target=target,blocker=blocker,actual=actual,coordinate=expected,all_actions=[asdict(a) for a in actions]));write_record(OUT,r)
                    if actual!=expected:raise ValueError('virtual semantic membership mismatch')
        renamed=NativeCubeKernel(compile_ruleset_for_execution(build('C','renamed_token')),(Profile('renamed_token','renamed_token'),),checkpoint=check)
        r['canonical_candidates']+=renamed.stats['canonical_candidates'];r['renamed_census']=cube_contact_census(renamed)['rows'][Profile('renamed_token','renamed_token')]
        r['complete']=len(r['rows'])==6 and len(r['controls'])==12 and r['renamed_census']==r['rows'][0]['census'] and r['canonical_candidates']+r['enumerated']<=5000
    except Exception as error:r['error']=f'{type(error).__name__}: {error}'
    r['seconds']=monotonic()-start;r['source_hashes_unchanged']=all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in r['source_sha256'].items())
    write_record(OUT,r);print(json.dumps({k:v for k,v in r.items() if k not in ('rows','controls','source_sha256','renamed_census')}))
