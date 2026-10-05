"""One frozen complete72-context root-law qualification; no successors."""
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
OUT=ROOT/'docs/research/data/shogi_royal_context_law_20261005.json'
SOURCES=('scripts/audit_shogi_royal_context_law.py','docs/research/SHOGI_ROYAL_CONTEXT_LAW_PROTOCOL.md',
 'scripts/resource_mode_context.py','generic_chess/rules/standard_shogi.py',
 'generic_chess/rules/compiler.py','generic_chess/core/semantic_executor.py')

if __name__=='__main__':
    if OUT.exists():raise FileExistsError('complete context law never rerun')
    start=monotonic();out=dict(complete=False,rows=[],enumerated_actions=0,
      public_transitions=0,virtual_materializations=0,goal_queries=0,
      source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES})
    def check():
        if monotonic()-start>=15:raise TimeoutError('15sec total context cap')
    try:
        c=compile_ruleset_for_execution(build_standard_shogi_ruleset());e=semantic_engine_for(c)
        initial=initial_state(c).position
        for f in range(9):
            for rank in range(8):
                check();board=[None]*81;bp=(f+5)%9
                for sq,owner,t in ((9*rank+f,0,'K'),(27+bp,0,'P'),(72+f,1,'R'),(80 if f<=4 else 72,1,'K')):
                    if board[sq] is not None:raise ValueError('overlap')
                    board[sq]=Piece(owner,t,t)
                p=replace(initial,board=tuple(board),side_to_move=0,
                  hands=(Hands((('P',1),)),Hands((('P',16),('L',4),('N',4),('S',4),('G',4),('B',2),('R',1)))))
                row=dict(file=f,rank=rank,position=asdict(p),ledger=resource_ledger(c,p,'shogi'),
                  owner_checked=e.in_check(p,0),previous_owner_safe=not e.in_check(p,1))
                out['rows'].append(row)
                if not row['owner_checked'] or not row['previous_owner_safe']:raise ValueError('royal premise fails')
                actions=e.legal_actions(p,checkpoint=check);out['enumerated_actions']+=len(actions)
                row['all_actions']=[asdict(a) for a in actions]
                if len(actions)>128 or out['enumerated_actions']>5000:raise ValueError('complete action cap')
                row['coarse_drops']=[q for q in range(72) if board[q] is None and q%9!=bp]
                row['legal_drops']=sorted(a.target for a in actions if a.source is None and a.actor_type=='P')
                expected=[9*j+f for j in range(rank+1,8)]
                kings=(2 if f in (0,8) else 4) if rank==0 else (3 if f in (0,8) else (5 if rank==7 else 6))
                row['expected_match']=(len(row['coarse_drops'])==63 and row['legal_drops']==expected and len(actions)==kings+7-rank)
                if not row['expected_match']:raise ValueError('predeclared sets/counts disagree')
        out['complete']=len(out['rows'])==72 and out['enumerated_actions']==613
    except Exception as error:out['error']=f'{type(error).__name__}: {error}'
    out['seconds']=monotonic()-start
    out['source_hashes_unchanged']=all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in out['source_sha256'].items())
    OUT.write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps({k:v for k,v in out.items() if k not in ('rows','source_sha256')}))
