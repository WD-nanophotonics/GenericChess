"""Explicit recorded public GameState decoder; no event application."""
def read_game_state(value):
    """Decode explicit public-state records; terminal freshness is caller-owned."""
    from generic_chess.core.pieces import Piece
    from generic_chess.core.position import Position,Hands,HistoryRecord,GameState
    from generic_chess.core.terminal import TerminalStatus,TerminalResult
    p=dict(value['position'])
    p['board']=tuple(None if x is None else Piece(**x) for x in p['board'])
    p['hands']=tuple(Hands(tuple(tuple(pair) for pair in h['counts'])) for h in p['hands'])
    p['aux_state']=tuple((tuple(k),tuple(v) if isinstance(v,list) else v) for k,v in p['aux_state'])
    status=value['terminal_status']
    return GameState(Position(**p),value['ply_count'],tuple(tuple(pair) for pair in value['repetition_counts']),
       TerminalResult(TerminalStatus(status['status']),status['winner']),tuple(HistoryRecord(**h) for h in value['history']))
