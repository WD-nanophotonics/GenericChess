"""Grouped legacy geometry qualification; no values or transitions."""
from dataclasses import asdict,replace
import hashlib,json,sys
from pathlib import Path
from time import monotonic
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from generic_chess.core.movement import LeapAtom
from generic_chess.core.pieces import Piece,PieceType
from generic_chess.core.transition import initial_state
from generic_chess.core.semantic_executor import semantic_engine_for
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.schema import RuleSet,RuleSemanticAction,RuleGeometrySpec,RuleActionEffect,RuleSquareRef,RuleReplaceSelector
from scripts.sparse_contact_cubes import SparseContactCubes,Profile
from scripts.typed_sparse_contact_cubes import TypedSparseContactCubes
OUT=ROOT/'docs/research/data/contact_typed_geometry_valid_20261005.json'
SOURCES=('scripts/audit_contact_typed_geometry_valid.py','scripts/audit_contact_typed_geometry_anchored.py','docs/research/data/contact_typed_geometry_anchored_20261005.json','docs/research/CONTACT_TYPED_GEOMETRY_VALID_COMPILE_SCOPE.md','scripts/audit_contact_typed_geometry.py','docs/research/data/contact_typed_geometry_20261005.json','docs/research/CONTACT_TYPED_GEOMETRY_ANCHOR_SCOPE.md','scripts/typed_sparse_contact_cubes.py',
 'scripts/sparse_contact_cubes.py','docs/research/CONTACT_TYPED_GEOMETRY_PROTOCOL.md',
 'generic_chess/rules/compiler.py','generic_chess/core/semantic_executor.py')


from scripts.audit_contact_typed_geometry import build as original_build

def build():
    failed=json.loads((ROOT/'docs/research/data/contact_typed_geometry_20261005.json').read_text())
    if failed['canonical_candidates'] or failed['enumerated'] or failed['complete']:
        raise ValueError('preserved zero-observation compile failure required')
    root=original_build()
    initial=[[None]*3 for _ in range(3)]
    initial[0][0]=Piece(0,'K','K');initial[2][2]=Piece(1,'K','K')
    return replace(root,piece_types=root.piece_types+(PieceType('K','K',(LeapAtom((0,1)),),is_anchor=True),),
                   initial_position=tuple(tuple(row) for row in initial),
                   drop_allowed=root.drop_allowed)


if __name__=='__main__':
    if OUT.exists():raise FileExistsError('typed-geometry qualifier never rerun')
    start=monotonic();out=dict(complete=False,rows=[],canonical_candidates=0,enumerated=0,public_transitions=0,goal_queries=0,virtual_materializations=0,
      source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES})
    def check():
        if monotonic()-start>=15:raise TimeoutError('15sec typed scope cap')
    try:
        c=compile_ruleset_for_execution(build());e=semantic_engine_for(c);initial=initial_state(c).position
        out['compiled_patterns']=[asdict(p) for p in c.ir.patterns]
        for owner in (0,1):
            profiles=(Profile('X','X'),Profile('Y','Y'))
            old=SparseContactCubes(c,profiles,owner=owner,checkpoint=check);new=TypedSparseContactCubes(c,profiles,owner=owner,checkpoint=check)
            out['canonical_candidates']+=old.stats['canonical_candidates']+new.stats['canonical_candidates']
            if out['canonical_candidates']>5000:raise ValueError('combined canonical cap')
            for t in ('X','Y'):
                for target in (5,7):
                    s,d,b=(4,target,0) if not owner else (4,8-target,8)
                    board=[None]*9;board[s]=Piece(owner,t,t);board[d]=Piece(1-owner,'Y','Y');board[b]=Piece(owner,'X','X')
                    p=replace(initial,board=tuple(board),side_to_move=owner);a=e.legal_actions(p,checkpoint=check);out['enumerated']+=len(a)
                    if len(a)>128 or out['enumerated']>5000:raise ValueError('full root action cap')
                    actual=any(x.source==s and x.target==d for x in a);old_direct=bool(old.pair_success(Profile(t,t),s,d)[0]&(1<<b));new_direct=bool(new.pair_success(Profile(t,t),s,d)[0]&(1<<b))
                    out['rows'].append(dict(owner=owner,type=t,source=s,target=d,blocker=b,all_actions=[asdict(x) for x in a],actual=actual,old_direct=old_direct,typed_direct=new_direct))
                    if new_direct!=actual:raise ValueError('typed projection still mismatches')
        out['old_mismatches']=sum(x['actual']!=x['old_direct'] for x in out['rows'])
        out['complete']=len(out['rows'])==8
    except Exception as error:out['error']=f'{type(error).__name__}: {error}'
    out['seconds']=monotonic()-start;out['source_hashes_unchanged']=all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in out['source_sha256'].items())
    OUT.write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps({k:v for k,v in out.items() if k not in ('rows','compiled_patterns','source_sha256')}))
