"""Scoped no-Pawn RNB rule bridge for the mature-engine proof assay."""
from dataclasses import replace
from generic_chess.core.actions import BoardMove
from generic_chess.core.movement import LeapAtom,RayAtom
from generic_chess.core.pieces import Piece,PieceType
from generic_chess.core.position import GameState,HistoryRecord
from generic_chess.core.terminal import TerminalResult,TerminalStatus,terminal_result
from generic_chess.core.identity import repetition_identity_key
from generic_chess.core.transition import initial_state
from generic_chess.rules.compiler import compile_ruleset
from scripts.generic_proof_fixtures import krk_ruleset


def compile_rnb(width=4):
    rs=krk_ruleset(width)
    n=PieceType('N','Leaper',tuple(LeapAtom((x,y)) for x,y in
       ((1,2),(2,1),(-1,2),(-2,1),(1,-2),(2,-1),(-1,-2),(-2,-1))))
    b=PieceType('B','Diagonal',tuple(RayAtom(d) for d in ((1,1),(1,-1),(-1,1),(-1,-1))))
    mask=(False,)*(width*width)
    return compile_ruleset(replace(rs,piece_types=rs.piece_types+(n,b),
                                  drop_allowed={'R':(mask,mask),'N':(mask,mask),'B':(mask,mask)},
                                  max_ply=96,repetition_limit=3))


def from_actor(c,raw):
    board=tuple(None if x=='.' else Piece(int(x.islower()),x.upper(),x.upper()) for x in raw[:-1])
    pos=replace(initial_state(c).position,board=board,side_to_move=raw[-1]);key=repetition_identity_key(pos,c)
    s=GameState(pos,0,((key,1),),TerminalResult(TerminalStatus.ONGOING),(HistoryRecord(key,-1,'',False),))
    return replace(s,terminal_status=terminal_result(s,c))


def actor_state(state):
    return tuple('.' if p is None else (p.current_type_id.lower() if p.owner else p.current_type_id)
                 for p in state.position.board)+(state.position.side_to_move,)


def uci(a):
    if not isinstance(a,BoardMove):raise ValueError('RNB bridge only has board actions')
    return chr(97+a.from_square.file)+str(a.from_square.rank+1)+chr(97+a.to_square.file)+str(a.to_square.rank+1)


def orbit(raw):
    w=int(len(raw[:-1])**.5);out=set()
    for reflect in (False,True):
        for rotations in range(4):
            board=['.']*(w*w)
            for i,p in enumerate(raw[:-1]):
                x,y=i%w,i//w
                if reflect:x=w-1-x
                for _ in range(rotations):x,y=w-1-y,x
                board[x+w*y]=p
            for color in (False,True):
                out.add(tuple(x.swapcase() if color else x for x in board)+(raw[-1]^color,))
    return out
