"""Exact saved Western semantic action identity binding, never legality bypass."""
import re
from generic_chess.core.semantic_executor import SemanticAction,_semantic_public_action

def saved_board_action(engine,state,key):
    if state.position.board_shape.width!=8 or state.position.board_shape.height!=8:raise ValueError('Western8x8 required')
    match=re.fullmatch(r'([^:]+):([^:]+):([a-h])([1-8])-([a-h])([1-8])(?:=([A-Z]+))?',key)
    if not match:raise ValueError('unsupported saved board action')
    pattern,gid,sf,sr,tf,tr,promotion=match.groups()
    source=(int(sr)-1)*8+ord(sf)-ord('a');target=(int(tr)-1)*8+ord(tf)-ord('a')
    piece=state.position.board[source]
    if piece is None or piece.owner!=state.position.side_to_move:raise ValueError('invalid source binding')
    action=_semantic_public_action(engine,SemanticAction(pattern,source,target,promotion,piece.current_type_id,gid))
    if str(action)!=key:raise ValueError('lossy action identity')
    return action
