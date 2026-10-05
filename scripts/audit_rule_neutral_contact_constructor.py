"""New micro populations and ordered worldwise semantic qualification."""
from collections import Counter,deque
from dataclasses import asdict
from fractions import Fraction as F
import hashlib,json,sys
from pathlib import Path
from time import monotonic
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from generic_chess.core.movement import LeapAtom
from generic_chess.core.pieces import Piece,PieceType
from generic_chess.rules.schema import RuleSet,RuleSemanticAction,RuleGeometrySpec,RuleActionEffect,RuleSquareRef,RulePathConstraint
from generic_chess.rules.compiler import compile_ruleset_for_execution
from scripts.rule_neutral_contact_constructor import construct_contact,ContactUnsupported,deadline_moment
from scripts.shared_contact_prefix import Profile
from scripts.audit_contact_target_type_qualified import qualified_build
from scripts.research_record import write_record
OUT=ROOT/'docs/research/data/rule_neutral_contact_constructor_20261005.json'
SOURCES=('scripts/audit_rule_neutral_contact_constructor.py','scripts/rule_neutral_contact_constructor.py','docs/research/RULE_NEUTRAL_CONTACT_CONSTRUCTOR_PROTOCOL.md','scripts/typed_shared_contact_prefix.py','scripts/shared_contact_prefix.py','scripts/full_contact_distances.py','scripts/target_aware_contact_distances.py','scripts/audit_contact_target_type_qualified.py')

def build(family,*,actor='opaque_actor'):
    rows=[[None]*3 for _ in range(3)];rows[1][0]=Piece(0,'anchor','anchor');rows[1][2]=Piece(1,'anchor','anchor')
    actions=[];ref=lambda kind:RuleSquareRef(kind)
    for relation in ('empty','enemy'):
        if family=='S':specs=[RuleGeometrySpec('leap',offset=(x,0)) for x in (-1,1)]
        elif family=='A':specs=[RuleGeometrySpec('leap',offset=(x,0) if relation=='empty' else (0,x)) for x in (-1,1)]
        elif family=='M':specs=[RuleGeometrySpec('leap',offset=(1,0)),RuleGeometrySpec('ray',direction=(-1,0),min_steps=2,max_steps=2)]
        else:raise ValueError('explicit frozen family required')
        for i,spec in enumerate(specs):
            effects=(RuleActionEffect('move',from_ref=ref('source'),to_ref=ref('target')),)
            if relation=='enemy':effects=(RuleActionEffect('remove',square_ref=ref('target'),piece_owner='opponent',disposition='remove_from_game'),)+effects
            actions.append(RuleSemanticAction('arbitrary_'+relation+str(i),(actor,),spec,relation,
                path_constraints=(RulePathConstraint('path_clear'),) if spec.kind=='ray' else (),effects=effects))
    types=(PieceType(actor,actor,()),PieceType('opaque_target','opaque_target',()),PieceType('opaque_blocker','opaque_blocker',()),PieceType('anchor','anchor',(LeapAtom((0,1)),),is_anchor=True))
    return RuleSet(board_size=3,piece_types=types,initial_position=tuple(tuple(row) for row in rows),
        drop_allowed={p.type_id:((False,)*9,)*2 for p in types if not p.is_anchor},semantic_actions=tuple(actions),capture_disposition='remove_from_game')

def coordinate_moves(family,source,owner,kind):
    f,r=source%3,source//3;sign=1 if owner==0 else -1
    if family=='S':steps=[(-1,0),(1,0)]
    elif family=='A':steps=[(-1,0),(1,0)] if kind=='empty' else [(0,-1),(0,1)]
    else:steps=[(1,0),(-2,0)]
    for df,dr in steps:
        destf,destr=f+df*sign,r+dr*sign
        if not (0<=destf<3 and 0<=destr<3):continue
        path=() if abs(df)!=2 else ((f-sign)+3*r,)
        yield destf+3*destr,path

def coordinate_distance(family,source,target,blocker,owner):
    todo=deque([(source,0)]);seen={source}
    while todo:
        here,cost=todo.popleft()
        if any(dest==target and blocker not in path for dest,path in coordinate_moves(family,here,owner,'enemy')):return cost+1
        for dest,path in coordinate_moves(family,here,owner,'empty'):
            if dest in (target,blocker) or target in path or blocker in path or dest in seen:continue
            seen.add(dest);todo.append((dest,cost+1))
    return 0

def kernel_distance(kernel,profile,source,target,blocker,*,target_free=False):
    todo=deque([(profile,source,0)]);seen={(profile,source)}
    while todo:
        p,here,cost=todo.popleft()
        if not target_free and any(not mask&(1<<blocker) for mask in kernel.capture[p,here].get(target,())):return cost+1
        for dest,mask,nxt in kernel.quiet[p,here]:
            if dest==blocker or mask&(1<<blocker):continue
            if target_free and dest==target:return cost+1
            if not target_free and (dest==target or mask&(1<<target)):continue
            if (nxt,dest) not in seen:seen.add((nxt,dest));todo.append((nxt,dest,cost+1))
    return 0

if __name__=='__main__':
    if OUT.exists():raise FileExistsError('new constructor study never rerun')
    start=monotonic();r=dict(complete=False,rows=[],public_transitions=0,source_queries=0,enumerated=0,canonical_candidates=0,
        source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES})
    def check():
        if monotonic()-start>=15:raise TimeoutError('15sec complete micro study')
    try:
        for family in ('S','A','M'):
            for owner in (0,1):
                check();c=compile_ruleset_for_execution(build(family));p=Profile('opaque_actor','opaque_actor')
                result=construct_contact(c,(p,),owner=owner,checkpoint=check);r['canonical_candidates']+=result.kernel.stats['geometry_candidates']
                if r['canonical_candidates']>5000:raise ValueError('canonical candidate cap')
                census=result.census()[p];oracle=Counter();kdigest=hashlib.sha256();odigest=hashlib.sha256();worlds=0;first_mismatch=None
                for source in range(9):
                    for target in range(9):
                        for blocker in range(9):
                            if len({source,target,blocker})!=3:continue
                            check();a=coordinate_distance(family,source,target,blocker,owner);b=kernel_distance(result.kernel,p,source,target,blocker,target_free=result.algorithm=='target_free')
                            worlds+=1;oracle[a]+=1
                            kdigest.update(f'{source},{target},{blocker}:{b};'.encode());odigest.update(f'{source},{target},{blocker}:{a};'.encode())
                            if a!=b and first_mismatch is None:first_mismatch=dict(source=source,target=target,blocker=blocker,coordinate=a,kernel=b)
                row=dict(family=family,owner=owner,algorithm=result.algorithm,qualification=result.first_hit_qualification,worlds=worlds,
                    census=census,oracle_histogram={t:n for t,n in oracle.items() if t},oracle_zero=oracle[0],ordered_kernel_sha256=kdigest.hexdigest(),ordered_oracle_sha256=odigest.hexdigest(),first_mismatch=first_mismatch)
                r['rows'].append(row);write_record(OUT,r)
                if worlds!=504 or first_mismatch or census['histogram']!={t:n for t,n in oracle.items() if t} or census['unreachable']!=oracle[0]:raise ValueError('worldwise/census mismatch')
                if family=='M':
                    s,t,b=(2,1,4) if owner==0 else (6,7,4)
                    row['prefix_witness']=dict(source=s,target=t,blocker=b,invalid_target_free=kernel_distance(result.kernel,p,s,t,b,target_free=True),correct_target_aware=kernel_distance(result.kernel,p,s,t,b))
        renamed=construct_contact(compile_ruleset_for_execution(build('A',actor='renamed_symbol')),(Profile('renamed_symbol','renamed_symbol'),),checkpoint=check)
        r['canonical_candidates']+=renamed.kernel.stats['geometry_candidates'];r['renamed']=dict(algorithm=renamed.algorithm,census=renamed.census()[Profile('renamed_symbol','renamed_symbol')])
        guard_rejected=False
        try:construct_contact(compile_ruleset_for_execution(qualified_build(True)),(Profile('X','X'),),checkpoint=check)
        except ContactUnsupported as error:r['guard_rejection']=str(error);guard_rejected=True
        r['complete']=len(r['rows'])==6 and guard_rejected and r['renamed']['census']==r['rows'][2]['census'] and r['canonical_candidates']<=5000
    except Exception as error:r['error']=f'{type(error).__name__}: {error}'
    r['seconds']=monotonic()-start;r['source_hashes_unchanged']=all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in r['source_sha256'].items())
    write_record(OUT,r);print(json.dumps({k:v for k,v in r.items() if k not in ('rows','source_sha256','renamed')}))
