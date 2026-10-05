"""One complete guarded virtual source route, not an alternating GameState."""
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
from scripts.resource_mode_context import resource_ledger
OUT=ROOT/'docs/research/data/shogi_royal_source_route_20261005.json'
SOURCES=('scripts/audit_shogi_royal_source_route.py','docs/research/SHOGI_ROYAL_SOURCE_ROUTE_PROTOCOL.md',
 'docs/research/data/shogi_checked_drop_guard_20261005.json','scripts/resource_mode_context.py',
 'generic_chess/rules/standard_shogi.py','generic_chess/rules/compiler.py','generic_chess/core/semantic_executor.py')

if __name__=='__main__':
    if OUT.exists():raise FileExistsError('frozen full-route producer never rerun')
    start=monotonic();r=dict(complete=False,steps=[],virtual_materializations=0,enumerated_actions=0,
      public_transitions=0,goal_queries=0,source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES})
    def check():
        if monotonic()-start>=15:raise TimeoutError('15sec total route cap')
    try:
        c=compile_ruleset_for_execution(build_standard_shogi_ruleset());e=semantic_engine_for(c)
        board=[None]*81
        for sq,owner,t in ((4,0,'K'),(27,0,'P'),(76,1,'R'),(80,1,'K')):board[sq]=Piece(owner,t,t)
        p=replace(initial_state(c).position,board=tuple(board),side_to_move=0,
          hands=(Hands((('P',1),)),Hands((('P',16),('L',4),('N',4),('S',4),('G',4),('B',2),('R',1)))))
        r['initial_ledger']=resource_ledger(c,p,'shogi');r['initial_checked']=e.in_check(p,0)
        if not r['initial_checked'] or e.in_check(p,1):raise ValueError('initial royal premise')
        destinations=[13,22,31,40,49,58,67,76]
        source=None
        for i,target in enumerate(destinations):
            check();actions=e.legal_actions(p,checkpoint=check)
            r['enumerated_actions']+=2*len(actions)  # apply performs a second complete membership check.
            if len(actions)>128 or r['enumerated_actions']>5000:raise ValueError('action enumeration cap')
            promote='TP' if target==58 else None
            selected=[a for a in actions if a.source==source and a.target==target and a.promotion_target_id==promote and a.actor_type==('P' if i<=5 else 'TP')]
            if len(selected)!=1:raise ValueError('prescribed action not unique/eligible')
            row=dict(index=i,before=asdict(p),all_actions=[asdict(a) for a in actions],action=asdict(selected[0]))
            r['steps'].append(row)
            if r['virtual_materializations']>=128:raise ValueError('physical event cap')
            raw=e.apply(p,selected[0]);r['virtual_materializations']+=1;check()
            row['raw_after']=asdict(raw);row['owner_safe_after']=not e.in_check(raw,0)
            row['ledger']=resource_ledger(c,raw,'shogi')
            piece=raw.board[target]
            if not row['owner_safe_after'] or piece is None or piece.owner!=0 or piece.base_type_id!='P':raise ValueError('path guard/origin fails')
            if raw.side_to_move!=1:raise ValueError('actual event did not switch turn')
            p=replace(raw,side_to_move=0) if i<7 else raw
            row['next_virtual_position']=asdict(p);source=target
        r['target_removed_to_hand']=p.hands[0].count('R')==1 and p.board[76].current_type_id=='TP'
        r['complete']=len(r['steps'])==8 and r['target_removed_to_hand']
    except Exception as error:r['error']=f'{type(error).__name__}: {error}'
    r['seconds']=monotonic()-start
    r['source_hashes_unchanged']=all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in r['source_sha256'].items())
    OUT.write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps({k:v for k,v in r.items() if k not in ('steps','source_sha256')}))
