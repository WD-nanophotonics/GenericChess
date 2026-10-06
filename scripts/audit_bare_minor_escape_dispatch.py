"""Sixteen explicit native/Pawn-origin controls for the geometric rule bridge."""
from pathlib import Path
from dataclasses import replace
from time import monotonic
import hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from generic_chess.core.pieces import Piece
from generic_chess.core.transition import initial_state,legal_successors
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.western_chess import build_western_chess_ruleset
from scripts.audit_exchange_custody import synthetic_state
from scripts.audit_lichess_complete_children import uci
from scripts.audit_bare_minor_mate_geometry import neighbors
from scripts.public_goal_intervals import PublicGame
from scripts.research_record import record_value,write_record
OUT=ROOT/'docs/research/data/bare_minor_escape_dispatch_20261006.json'
SOURCES=('scripts/audit_bare_minor_escape_dispatch.py','scripts/audit_bare_minor_mate_geometry.py',
 'docs/research/BARE_MINOR_MATE_GEOMETRY_PROTOCOL.md','docs/research/data/bare_minor_mate_geometry_20261006.json',
 'scripts/audit_exchange_custody.py','scripts/audit_lichess_complete_children.py','scripts/research_record.py',
 'scripts/public_goal_intervals.py','generic_chess/core/semantic_executor.py','generic_chess/rules/western_chess.py')


def audit(r):
    start=monotonic();rules=build_western_chess_ruleset();compiled=compile_ruleset_for_execution(rules);game=PublicGame(compiled)
    types={t.type_id:t for t in rules.piece_types}
    king_offsets=tuple((dx,dy) for dx in (-1,0,1) for dy in (-1,0,1) if dx or dy)
    n_offsets=((1,2),(2,1),(-1,2),(-2,1),(1,-2),(2,-1),(-1,-2),(-2,-1))
    assert {a.offset for a in types['K'].movement_atoms}==set(king_offsets)
    assert {a.offset for a in types['N'].movement_atoms}==set(n_offsets)
    assert {a.direction for a in types['B'].movement_atoms}=={(1,1),(-1,1),(1,-1),(-1,-1)}
    assert all(a.max_steps is None for a in types['B'].movement_atoms)
    assert all(not types[m].is_promotable for m in 'KNB')
    def attack(mode,minor,wk):
        if mode=='N':return set(neighbors(minor,n_offsets))
        out=set()
        for dx,dy in ((1,1),(-1,1),(1,-1),(-1,-1)):
            x,y=minor%8+dx,minor//8+dy
            while 0<=x<8 and 0<=y<8:
                s=y*8+x;out.add(s)
                if s==wk:break
                x+=dx;y+=dy
        return out
    for mode in 'NB':
        for bk in (0,7,27,63):
            wk=next(k for k in range(64) if k!=bk and k not in neighbors(bk,king_offsets))
            minor=next(m for m in range(64) if m not in (bk,wk) and bk in attack(mode,m,wk))
            protected=set(neighbors(wk,king_offsets))|{wk};a=attack(mode,minor,wk)
            expected=sorted(s for s in neighbors(bk,king_offsets) if s not in protected and (s==minor or s not in a))
            for origin in (mode,'P'):
                board=[None]*64
                board[wk]=Piece(0,'K','K',False);board[bk]=Piece(1,'K','K',False);board[minor]=Piece(0,origin,mode,origin!=mode)
                p=replace(initial_state(compiled).position,board=tuple(board),side_to_move=1,
                    aux_state=(((0,-1),0),((1,-1),0),((2,-1),None),((3,-1),0),((4,-1),0)))
                state=synthetic_state(compiled,p)
                if game.terminal(state).is_terminal:raise ValueError('geometric escape must be locally ongoing')
                pairs=list(legal_successors(state,compiled));r['public_transitions']+=len(pairs)
                observed=sorted(x.to_square.rank*8+x.to_square.file for x,c in pairs)
                if observed!=expected:raise ValueError('complete geometric/local King-escape mismatch')
                r['rows'].append(dict(mode=mode,origin=origin,bk=bk,wk=wk,minor=minor,complete_actions=sorted(uci(x) for x,c in pairs),escape_squares=observed,state=record_value(state)))
                if monotonic()-start>15:raise TimeoutError('dispatch control safety fuse')
    r.update(complete=True,inspected_piece_geometry_matches=True,seconds=monotonic()-start,
             scope='16 explicit complete legal-list controls; not executor census of447888 worlds')


if __name__=='__main__':
    if OUT.exists():raise FileExistsError('preserve explicit controls')
    r=dict(complete=False,rows=[],public_transitions=0,source_calls=0,source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES})
    start=monotonic()
    try:audit(r)
    except Exception as e:r['error']=f'{type(e).__name__}: {e}'
    r['seconds']=monotonic()-start;r['source_hashes_unchanged']=all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==pin for p,pin in r['source_sha256'].items())
    write_record(OUT,r);print(json.dumps({k:v for k,v in r.items() if k not in ('rows','source_sha256')}))
