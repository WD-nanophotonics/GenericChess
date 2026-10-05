"""Selected movement-only controls, no Xiangqi coefficient or human labels."""
from dataclasses import asdict,replace
import hashlib,json,sys
from pathlib import Path
from time import monotonic
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from generic_chess.core.pieces import Piece
from generic_chess.core.position import Hands
from generic_chess.core.transition import initial_state
from generic_chess.core.semantic_executor import semantic_engine_for
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.xiangqi_diagnostic import build_xiangqi_diagnostic_ruleset
from scripts.sparse_contact_cubes import SparseContactCubes,Profile
OUT=ROOT/'docs/research/data/sparse_contact_cube_controls_20261005.json'
SOURCES=('scripts/audit_sparse_contact_cube_controls.py','scripts/sparse_contact_cubes.py',
 'docs/research/SPARSE_CONTACT_CUBE_PROTOCOL.md','scripts/shared_contact_prefix.py','scripts/intrinsic_action_events.py',
 'scripts/intrinsic_occupancy_cubes.py','scripts/audit_static_semantic_material_prior_v2.py',
 'scripts/audit_static_semantic_material_prior_v2a.py','scripts/audit_static_semantic_material_prior_v2d.py',
 'generic_chess/rules/xiangqi_diagnostic.py','generic_chess/rules/compiler.py','generic_chess/core/semantic_executor.py')
# name,type,source,target,own-blocker,expected direct,expected exactly second.
CASES=(('cannon_screen','C',0,36,18,True,False),('cannon_off_screen','C',0,36,19,False,False),
 ('cannon_corner','C',0,30,28,False,True),('horse_leg','H',40,51,41,False,False),
 ('horse_clear','H',40,51,0,True,False),('elephant_eye','E',2,22,12,False,False),
 ('elephant_clear','E',2,22,0,True,False),('elephant_river','E',38,58,0,False,False),
 ('advisor_palace','A',13,23,0,True,False),('advisor_outside','A',0,10,89,False,False),
 ('soldier_before','S',40,41,0,False,False),('soldier_after','S',49,50,0,True,False))

if __name__=='__main__':
    if OUT.exists():raise FileExistsError('cube semantic producer never rerun')
    start=monotonic();out=dict(complete=False,rows=[],routes=[],enumerated=0,virtual_materializations=0,
      public_transitions=0,goal_queries=0,human_reference_imported=False,
      source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES})
    def check():
        if monotonic()-start>=15:raise TimeoutError('15sec total semantic cap')
    try:
        c=compile_ruleset_for_execution(build_xiangqi_diagnostic_ruleset());e=semantic_engine_for(c)
        base=initial_state(c).position;profiles=tuple(Profile(t,t) for t in ('A','C','E','H','R','S'))
        # Only one cached owner preprocessing. Owner1 has a separate reflected
        # compilation on demand below; cap includes BOTH canonical counts.
        kernels={0:SparseContactCubes(c,profiles,owner=0,checkpoint=check)}
        out['kernel_stats']=kernels[0].stats
        out['canonical_candidates']=kernels[0].stats['canonical_candidates']
        # Exact owner reflection of the compiled virtual task is checked via
        # direct engine controls, without doubling cached preprocessing budget.
        def position(t,s,d,b,owner):
            board=[None]*90
            for q,side,tid in ((s,owner,t),(d,1-owner,'R'),(b,owner,'A')):board[q]=Piece(side,tid,tid)
            return replace(base,board=tuple(board),side_to_move=owner,hands=(Hands.empty(),Hands.empty()))
        for name,t,s,d,b,direct,second in CASES:
            first_mask,second_mask=kernels[0].pair_success(Profile(t,t),s,d)
            if (bool(first_mask&(1<<b)),bool(second_mask&(1<<b)))!=(direct,second):raise ValueError(f'predeclared masks fail:{name}')
            for owner in (0,1):
                ss,dd,bb=(s,d,b) if not owner else (89-s,89-d,89-b)
                p=position(t,ss,dd,bb,owner);check();actions=e.legal_actions(p,checkpoint=check);out['enumerated']+=len(actions)
                row=dict(name=name,owner=owner,position=asdict(p),all_actions=[asdict(a) for a in actions],
                  source=ss,target=dd,blocker=bb,direct=direct,second=second,first_mask=first_mask,second_mask=second_mask)
                out['rows'].append(row)
                if len(actions)>128 or out['enumerated']>5000:raise ValueError('complete semantic action cap')
                actual=any(a.source==ss and a.target==dd for a in actions)
                if actual!=direct:raise ValueError(f'compiled membership disagrees:{name}/owner{owner}')
        # Named C(0,0)->(0,3)xR(3,3), with own A(1,3) as the screen.
        p=position('C',0,30,28,0)
        for source,target in ((0,27),(27,30)):
            check();actions=e.legal_actions(p,checkpoint=check);out['enumerated']+=2*len(actions)
            if len(actions)>128 or out['enumerated']>5000 or out['virtual_materializations']>=128:raise ValueError('route cap')
            match=[a for a in actions if a.source==source and a.target==target]
            if len(match)!=1:raise ValueError('named cannon route eligibility')
            raw=e.apply(p,match[0]);out['virtual_materializations']+=1
            out['routes'].append(dict(before=asdict(p),all_actions=[asdict(a) for a in actions],action=asdict(match[0]),raw_after=asdict(raw)))
            p=replace(raw,side_to_move=0)
        out['complete']=len(out['rows'])==24 and p.board[30].current_type_id=='C' and p.board[28].current_type_id=='A'
    except Exception as error:out['error']=f'{type(error).__name__}: {error}'
    out['seconds']=monotonic()-start;out['source_hashes_unchanged']=all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in out['source_sha256'].items())
    OUT.write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps({k:v for k,v in out.items() if k not in ('rows','routes','source_sha256')}))
