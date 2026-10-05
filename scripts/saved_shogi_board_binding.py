"""Decode only saved lossless9x9 board IDs, still validated by public apply."""
import re
from generic_chess.core.actions import SemanticBoardMove
from generic_chess.core.coordinates import Square

def saved_shogi_board_binding(state,key):
    if state.position.board_shape.width!=9 or state.position.board_shape.height!=9:
        raise ValueError('9x9 board required')
    m=re.fullmatch(r'([^:]+):([^:]+):([a-i])([1-9])-([a-i])([1-9])(?:=([A-Z]+))?',key)
    if not m:raise ValueError('saved Shogi board identity required')
    pattern,gid,sf,sr,tf,tr,prom=m.groups()
    source=Square(ord(sf)-ord('a'),int(sr)-1); target=Square(ord(tf)-ord('a'),int(tr)-1)
    piece=state.position.board[source.rank*9+source.file]
    if piece is None or piece.owner!=state.position.side_to_move:raise ValueError('invalid saved source')
    action=SemanticBoardMove(pattern,gid,piece.current_type_id,source,target,prom)
    if str(action)!=key:raise ValueError('lossy saved identity')
    return action
