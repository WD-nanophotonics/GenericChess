"""New checked Knight/Rook structural preflight, no public successors."""
from dataclasses import replace
import hashlib,json,sys
from pathlib import Path
from time import monotonic
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from generic_chess.core.pieces import Piece
from generic_chess.core.transition import initial_state
from generic_chess.core.semantic_executor import semantic_engine_for
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.western_chess import build_western_chess_ruleset
from scripts.audit_exchange_custody import synthetic_state
from scripts.native_chess_contact_intervals import EMPTY_AUX
from scripts.public_goal_intervals import PublicGame
from scripts.research_record import write_record,record_value
OUT=ROOT/'docs/research/data/contact_narrow_preflight_20261005.json'
SOURCES=('scripts/audit_contact_narrow_preflight.py','docs/research/CONTACT_NARROW_SEARCH_PROTOCOL.md','scripts/public_goal_intervals.py','scripts/audit_exchange_custody.py','generic_chess/rules/western_chess.py')
OLD=('chess_pinned_queen_mate_20261005.json','chess_knight_interposition_20261005.json','chess_double_check_20261005.selections.json')
def board_key(board):
    return tuple(None if p is None else (p.owner,p.base_type_id,p.current_type_id,p.promoted) for p in board)
def serialized_key(board):
    return tuple(None if p is None else (p['owner'],p['base_type_id'],p['current_type_id'],p['promoted']) for p in board)
if __name__=='__main__':
    if OUT.exists():raise FileExistsError('prospective preflight never rerun')
    start=monotonic();r=dict(complete=False,rows=[],accepted=[],enumerated=0,public_transitions=0,source_queries=0,source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES})
    def check():
        if monotonic()-start>=15:raise TimeoutError('15sec preflight')
    try:
        old=set()
        def collect(value):
            if isinstance(value,dict):
                if 'position' in value and 'board' in value['position']:old.add(serialized_key(value['position']['board']))
                for x in value.values():collect(x)
            elif isinstance(value,list):
                for x in value:collect(x)
        for name in OLD:
            p=ROOT/'docs/research/data'/name;r['source_sha256'][str(p.relative_to(ROOT)).replace('\\','/')]=hashlib.sha256(p.read_bytes()).hexdigest();collect(json.loads(p.read_text()))
        old|={tuple(None if p is None else (1-p[0],*p[1:]) for p in reversed(board)) for board in list(old)}
        c=compile_ruleset_for_execution(build_western_chess_ruleset());game=PublicGame(c);engine=semantic_engine_for(c)
        for king in (1,2,3):
            for rook in (57,58,59):
                for knight in (9,10,11):
                    check();board=[None]*64
                    for square,owner,kind in ((king,0,'K'),(63,1,'K'),(rook,1,'R'),(knight,0,'N')):board[square]=Piece(owner,kind,kind)
                    row=dict(king=king,rook=rook,knight=knight);r['rows'].append(row)
                    p=replace(initial_state(c).position,board=tuple(board),side_to_move=0,aux_state=EMPTY_AUX);state=synthetic_state(c,p)
                    if board_key(board) in old:row['reject']='exposed equality';continue
                    if engine.in_check(p,1):row['reject']='previous mover check';continue
                    if not engine.in_check(p,0):row['reject']='not checked';continue
                    if game.terminal(state).is_terminal:row['reject']='terminal';continue
                    acts=list(game.actions(state,check));r['enumerated']+=len(acts)
                    if len(acts)>128 or r['enumerated']>5000:raise ValueError('preflight action cap')
                    row['actions']=[str(a) for a in acts]
                    if not 2<=len(acts)<=4:row['reject']='outside narrow2..4';continue
                    row['root']=record_value(state);r['accepted'].append(row)
                    if len(r['accepted'])==2:break
                if len(r['accepted'])==2:break
            if len(r['accepted'])==2:break
        r['complete']=len(r['accepted'])==2
    except Exception as error:r['error']=f'{type(error).__name__}: {error}'
    r['seconds']=monotonic()-start;r['source_hashes_unchanged']=all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in r['source_sha256'].items())
    write_record(OUT,r);print(json.dumps({k:v for k,v in r.items() if k not in ('rows','accepted','source_sha256')}))
