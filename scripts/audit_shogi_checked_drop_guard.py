"""One new full-stock guard witness; no successors or repeated root search."""
from dataclasses import asdict,replace
import hashlib,json
from pathlib import Path
import sys
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
from scripts.resource_mode_context import resource_ledger
OUT=ROOT/'docs/research/data/shogi_checked_drop_guard_20261005.json'
SOURCES=('scripts/audit_shogi_checked_drop_guard.py','docs/research/SHOGI_CHECKED_DROP_GUARD_PROTOCOL.md',
 'scripts/audit_exchange_custody.py','scripts/public_goal_intervals.py','scripts/resource_mode_context.py',
 'generic_chess/rules/standard_shogi.py','generic_chess/rules/compiler.py','generic_chess/core/semantic_executor.py')

if __name__=='__main__':
    if OUT.exists():raise FileExistsError('frozen witness never rerun')
    start=monotonic();r=dict(complete=False,public_transitions=0,goal_queries=0,
        source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES})
    def check():
        if monotonic()-start>=15:raise TimeoutError('15sec total root cap')
    try:
        c=compile_ruleset_for_execution(build_standard_shogi_ruleset());check()
        board=[None]*81
        for sq,owner,t in ((4,0,'K'),(27,0,'P'),(76,1,'R'),(80,1,'K')):board[sq]=Piece(owner,t,t)
        p=replace(initial_state(c).position,board=tuple(board),side_to_move=0,
          hands=(Hands((('P',1),)),Hands((('P',16),('L',4),('N',4),('S',4),('G',4),('B',2),('R',1)))))
        r['resource_ledger']=resource_ledger(c,p,'shogi');engine=semantic_engine_for(c)
        r['owner_checked']=engine.in_check(p,0);r['previous_owner_safe']=not engine.in_check(p,1)
        s=synthetic_state(c,p);game=PublicGame(c);term=game.terminal(s)
        r['root_state']=asdict(s);r['ongoing']=not term.is_terminal
        if not (r['owner_checked'] and r['previous_owner_safe'] and r['ongoing']):raise ValueError('root premise fails')
        actions=list(game.actions(s,check));check()
        if len(actions)>128:raise ValueError('128 complete-root action cap')
        r['all_action_ids']=[str(a) for a in actions];r['enumerated']=len(actions)
        drops=[a for a in actions if getattr(a,'base_type_id',None)=='P' and hasattr(a,'to_square')]
        legal=sorted(a.to_square.rank*9+a.to_square.file for a in drops)
        coarse=[q for q in range(72) if board[q] is None and q%9!=0]
        r['masked_drops']=coarse;r['legal_drops']=legal;r['removed']=sorted(set(coarse)-set(legal))
        r['expected_sets_match']=len(coarse)==63 and legal==[9*i+4 for i in range(1,8)]
        r['complete']=r['expected_sets_match'] and len(actions)>len(drops)
    except Exception as e:r['error']=f'{type(e).__name__}: {e}'
    r['seconds']=monotonic()-start
    r['source_hashes_unchanged']=all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in r['source_sha256'].items())
    OUT.write_text(json.dumps(r,indent=2,default=str)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps({k:v for k,v in r.items() if k not in ('root_state','source_sha256','masked_drops','removed')},default=str))
