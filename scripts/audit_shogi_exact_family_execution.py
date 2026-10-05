"""69 real children qualify a leaf-scope gap; keep old noncheck policy intact."""
from collections import Counter
from dataclasses import replace
from fractions import Fraction as F
import hashlib,json,sys
from pathlib import Path
from time import monotonic
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from generic_chess.core.pieces import Piece
from generic_chess.core.position import Hands
from generic_chess.core.transition import initial_state
from generic_chess.core.semantic_executor import semantic_engine_for
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from scripts.audit_exchange_custody import synthetic_state
from scripts.public_goal_intervals import PublicGame
from scripts.research_record import record_value,write_record
from scripts.resource_mode_context import resource_ledger
from scripts.shogi_exact_twenty_family import exact_twenty_intervals,exact_twenty_choice
from scripts.shogi_contact_interval_choice import shogi_contact_choice
from scripts.material_leaf_choice import material_score,one_ply_choice
OUT=ROOT/'docs/research/data/shogi_exact_family_execution_20261005.json'
SOURCES=('scripts/audit_shogi_exact_family_execution.py','scripts/audit_shogi_exact_family_check_scope.py','docs/research/SHOGI_EXACT_FAMILY_EXECUTION_SCOPE.md','docs/research/data/shogi_exact_family_check_scope_20261005.json','docs/research/SHOGI_EXACT_FAMILY_CHECK_SCOPE_PROTOCOL.md',
 'scripts/shogi_exact_twenty_family.py','scripts/shogi_contact_interval_choice.py','scripts/material_leaf_choice.py',
 'scripts/public_goal_intervals.py','scripts/resource_mode_context.py','generic_chess/rules/standard_shogi.py')
if __name__=='__main__':
    if OUT.exists():raise FileExistsError('frozen69-child scope check')
    start=monotonic();r=dict(complete=False,public_transitions=0,enumerated=0,source_queries=0,children={},
      source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES})
    def check():
        if monotonic()-start+0.11000000010244548>=15:raise TimeoutError('15sec actual root cap')
    write_record(OUT,r)
    try:
        c=compile_ruleset_for_execution(build_standard_shogi_ruleset());g=PublicGame(c);e=semantic_engine_for(c)
        board=[None]*81
        for square,owner,current in ((1,0,'K'),(39,0,'P'),(80,1,'K')):board[square]=Piece(owner,current,current)
        stock=Counter(p.base_type_id for p in initial_state(c).position.board if p and p.base_type_id!='K')
        p=replace(initial_state(c).position,board=tuple(board),hands=(Hands((('P',1),)),Hands(tuple(sorted((stock-Counter(P=2)).items())))),side_to_move=0)
        root=synthetic_state(c,p);resource_ledger(c,p,'shogi');r['root']=record_value(root)
        actions={str(a):a for a in g.actions(root,check)};r['enumerated']=len(actions);r['all_actions']=list(actions);write_record(OUT,r)
        if len(actions)!=69:raise ValueError('prospective whole-root count differs')
        children={}
        for key,action in actions.items():
            check()
            if r['public_transitions']>=128 or r['enumerated']+len(actions)>5000:raise ValueError('unchanged cap')
            r['enumerated']+=len(actions);r['public_transitions']+=1
            child=g.successor(root,action);resource_ledger(c,child.position,'shogi');g.terminal(child)
            children[key]=child;r['children'][key]=record_value(child);write_record(OUT,r)
        r['checked_children']=[key for key,child in children.items() if e.in_check(child.position,child.position.side_to_move)]
        if any(g.terminal(child).is_terminal for child in children.values()):raise ValueError('unqualified predicted ongoing child')
        r['old_strict']=shogi_contact_choice(children,g,owner=0,duration='both',complete=True)
        r['new_strict']=exact_twenty_choice(children,g,owner=0,duration='both',complete=True)
        r['approximate_checked_ablation']={}
        for law in ('geometric_half','linear_mixture'):
            boxes=exact_twenty_intervals(law);weights={k:lo for k,(lo,hi) in boxes.items()}
            result=one_ply_choice(children,g,lambda state:material_score(state.position,weights,{'K'},38),owner=0,complete=True)
            r['approximate_checked_ablation'][law]=dict(result,tie_set=sorted(k for k,v in result['scores'].items() if v==result['score']))
        r['unit_ablation']=one_ply_choice(children,g,lambda state:material_score(state.position,{k:F(1) for k in exact_twenty_intervals('geometric_half')},{'K'},38),owner=0,complete=True)
        r['complete']=len(children)==69
    except Exception as error:r['error']=f'{type(error).__name__}: {error}'
    r['seconds']=monotonic()-start
    r['source_hashes_unchanged']=all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in r['source_sha256'].items())
    write_record(OUT,r);print(json.dumps({k:record_value(v) for k,v in r.items() if k not in ('source_sha256','root','children','all_actions','approximate_checked_ablation','unit_ablation')}))
