"""Two actual alternating public events, explicit changed hand allocation."""
from dataclasses import asdict,replace
import hashlib,json,sys
from pathlib import Path
from time import monotonic
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from generic_chess.core.actions import action_source_square,action_target_square
from generic_chess.core.pieces import Piece
from generic_chess.core.position import Hands
from generic_chess.core.transition import initial_state
from generic_chess.core.semantic_executor import semantic_engine_for
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from scripts.audit_exchange_custody import synthetic_state
from scripts.public_goal_intervals import PublicGame
from scripts.resource_mode_context import resource_ledger
OUT=ROOT/'docs/research/data/shogi_active_rook_20261005.json'
SOURCES=('scripts/audit_shogi_active_rook.py','docs/research/SHOGI_ACTIVE_ROOK_PROTOCOL.md',
 'scripts/audit_exchange_custody.py','scripts/public_goal_intervals.py','scripts/resource_mode_context.py',
 'generic_chess/rules/standard_shogi.py','generic_chess/rules/compiler.py','generic_chess/core/transition.py')

if __name__=='__main__':
    if OUT.exists():raise FileExistsError('active-R event producer never rerun')
    start=monotonic();out=dict(complete=False,steps=[],public_transitions=0,enumerated=0,goal_queries=0,
      source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES})
    def check():
        if monotonic()-start>=15:raise TimeoutError('15sec total event cap')
    def square(q):return None if q is None else q.rank*9+q.file
    try:
        c=compile_ruleset_for_execution(build_standard_shogi_ruleset());game=PublicGame(c);e=semantic_engine_for(c)
        board=[None]*81
        for q,owner,t in ((4,0,'K'),(27,0,'P'),(76,1,'R'),(80,1,'K')):board[q]=Piece(owner,t,t)
        p=replace(initial_state(c).position,board=tuple(board),side_to_move=0,
          hands=(Hands((('P',1),('L',4),('N',4),('S',4),('G',4),('B',2),('R',1))),Hands((('P',16),))))
        s=synthetic_state(c,p);out['initial_ledger']=resource_ledger(c,p,'shogi')
        if game.terminal(s).is_terminal or not e.in_check(p,0) or e.in_check(p,1):raise ValueError('root premise fails')
        for index,(origin,target) in enumerate(((None,13),(76,13))):
            check();choices=list(game.actions(s,check));out['enumerated']+=len(choices)
            row=dict(before=asdict(s),all_actions=[str(a) for a in choices]);out['steps'].append(row)
            if len(choices)>128 or out['enumerated']>5000:raise ValueError('full action cap')
            selected=[a for a in choices if square(action_source_square(a))==origin and square(action_target_square(a))==target and getattr(a,'promotion_target_id',None) is None and (index or getattr(a,'base_type_id',None)=='P')]
            if len(selected)!=1:raise ValueError('named actual event not unique')
            row['action']=str(selected[0]);s=game.successor(s,selected[0]);out['public_transitions']+=1;check()
            row['after']=asdict(s);row['mover_safe']=not e.in_check(s.position,index)
            row['ledger']=resource_ledger(c,s.position,'shogi')
            if not row['mover_safe']:raise ValueError('mover unsafe after own action')
        out['source_removed']=s.position.board[13].current_type_id=='R' and s.position.hands[1].count('P')==17
        out['owner_checked_again']=e.in_check(s.position,0)
        out['complete']=out['source_removed'] and out['owner_checked_again'] and len(s.history)==3 and s.ply_count==2
    except Exception as error:out['error']=f'{type(error).__name__}: {error}'
    out['seconds']=monotonic()-start;out['source_hashes_unchanged']=all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in out['source_sha256'].items())
    OUT.write_text(json.dumps(out,indent=2,default=str)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps({k:v for k,v in out.items() if k not in ('steps','source_sha256')}))
