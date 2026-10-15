"""Fresh-history KRK fixtures for independent proof tests, never solver hints."""
from dataclasses import replace
from generic_chess.core.identity import repetition_identity_key
from generic_chess.core.movement import LeapAtom, RayAtom
from generic_chess.core.pieces import Piece, PieceType
from generic_chess.core.position import GameState, HistoryRecord
from generic_chess.core.terminal import TerminalResult, TerminalStatus, terminal_result
from generic_chess.core.transition import initial_state
from generic_chess.rules.schema import RuleSet
from generic_chess.rules.compiler import compile_ruleset


def krk_ruleset(width):
    king = PieceType('K','Anchor',tuple(LeapAtom((x,y)) for x in (-1,0,1)
                                     for y in (-1,0,1) if x or y),is_anchor=True)
    rook = PieceType('R','Ray',tuple(RayAtom(d) for d in ((1,0),(-1,0),(0,1),(0,-1))))
    board=[None]*(width*width)
    board[0],board[1],board[-1]=Piece(0,'K','K'),Piece(0,'R','R'),Piece(1,'K','K')
    return RuleSet(board_size=width,piece_types=(king,rook),
                   initial_position=tuple(tuple(board[y*width:y*width+width]) for y in range(width)),
                   drop_allowed={'R': ((False,)*(width*width),)*2},
                   capture_disposition='remove_from_game',max_ply=64,repetition_limit=3)


def compile_krk(width=4):
    return compile_ruleset(krk_ruleset(width))


def krk_state(compiled,k,b,r,turn,owner=0):
    board=[None]*(compiled.board_size**2)
    board[k],board[b],board[r]=Piece(owner,'K','K'),Piece(1-owner,'K','K'),Piece(owner,'R','R')
    pos=replace(initial_state(compiled).position,board=tuple(board),side_to_move=turn)
    key=repetition_identity_key(pos,compiled)
    state=GameState(pos,0,((key,1),),TerminalResult(TerminalStatus.ONGOING),
                    (HistoryRecord(key,-1,'',False),))
    return replace(state,terminal_status=terminal_result(state,compiled))
