"""Prospective full-grammar own-source paths; no alternate history or values."""
from dataclasses import asdict, replace
import hashlib, json, sys
from pathlib import Path
from time import monotonic
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from generic_chess.core.pieces import Piece
from generic_chess.core.transition import initial_state
from generic_chess.core.semantic_executor import semantic_engine_for
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.western_chess import build_western_chess_ruleset
OUT=ROOT/'docs/research/data/chess_pawn_aux_route_20261005.json'
SOURCES=('scripts/audit_chess_pawn_aux_route.py','docs/research/CHESS_PAWN_AUX_REDUCTION_PROTOCOL.md',
 'generic_chess/rules/western_chess.py','generic_chess/core/semantic_executor.py','generic_chess/rules/compiler.py')

if __name__=='__main__':
    if OUT.exists():raise FileExistsError('frozen qualifier never rerun')
    start=monotonic();out=dict(complete=False,rows=[],enumerated=0,virtual_materializations=0,goal_queries=0,
      source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES})
    def check():
        if monotonic()-start>=15:raise TimeoutError('15sec total cap')
    try:
        c=compile_ruleset_for_execution(build_western_chess_ruleset());e=semantic_engine_for(c)
        out['pawn_patterns']=[asdict(x) for x in c.ir.patterns if 'P' in x.type_ids]
        out['aux_slots']=[asdict(x) for x in c.ir.aux_slots]
        ep=[x for x in c.ir.aux_slots if x.name=='ep_target'][0]
        for owner in (0,1):
            def mirror(s):return 56-8*(s//8)+s%8 if owner else s
            board=[None]*64
            for sq,side,t in ((0,0,'K'),(63,1,'K'),(11,0,'P'),(60,1,'N')):
                board[mirror(sq)]=Piece(side^owner,t,t)
            p=replace(initial_state(c).position,board=tuple(board),side_to_move=owner,
                      aux_state=tuple(((x.slot_id,-1),None if x.name=='ep_target' else 0) for x in c.ir.aux_slots))
            source=mirror(11)
            for i,t in enumerate((27,35,43,51,60)):
                check();actions=e.legal_actions(p,checkpoint=check);out['enumerated']+=2*len(actions)
                if len(actions)>128 or out['enumerated']>5000:raise ValueError('action cap')
                target=mirror(t);selected=[a for a in actions if a.source==source and a.target==target
                  and a.promotion_target_id==('Q' if i==4 else None)]
                ep_actions=[a for a in actions if a.source==source and 'en_passant' in str(a)]
                if len(selected)!=1 or ep_actions:raise ValueError('path/EP eligibility mismatch')
                row=dict(owner=owner,index=i,before=asdict(p),actions=[asdict(a) for a in actions],selected=asdict(selected[0]))
                out['rows'].append(row)
                if out['virtual_materializations']>=128:raise ValueError('event cap')
                raw=e.apply(p,selected[0]);out['virtual_materializations']+=1;check();row['after']=asdict(raw)
                token=dict(raw.aux_state)[(ep.slot_id,-1)]
                expected=(3,5 if owner else 2) if i==0 else None
                if token!=expected:raise ValueError('unexpected EP lifecycle')
                moved=raw.board[target]
                if moved.owner!=owner or moved.base_type_id!='P' or e.in_check(raw,owner):raise ValueError('origin/safety mismatch')
                p=replace(raw,side_to_move=owner);source=target
        out['complete']=len(out['rows'])==10
    except Exception as error:out['error']=f'{type(error).__name__}: {error}'
    out['seconds']=monotonic()-start
    out['source_hashes_unchanged']=all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in out['source_sha256'].items())
    OUT.write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps({k:v for k,v in out.items() if k not in ('rows','pawn_patterns','aux_slots','source_sha256')}))
