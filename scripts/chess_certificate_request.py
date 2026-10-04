"""Local pawn-free request association ONLY; never an external certificate."""
from collections import Counter
from dataclasses import asdict
from functools import lru_cache
import hashlib
import json

from generic_chess.core.identity import repetition_identity_key
from generic_chess.core.semantic_executor import semantic_engine_for
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.western_chess import build_western_chess_ruleset
from scripts.public_goal_intervals import PublicGame
from scripts.resource_mode_context import resource_ledger


@lru_cache(maxsize=1)
def _western_fingerprint():
    return compile_ruleset_for_execution(build_western_chess_ruleset()).ruleset_fingerprint


def chess_certificate_request(state, compiled):
    """Encode a qualified local ongoing state without claiming source proof.

    No tablebase/network/library use. Strict scope makes every dropped field
    explicit; full local provenance/history remains bound outside current FEN.
    """
    if compiled.ruleset_fingerprint != _western_fingerprint():
        raise ValueError('exact production Western fingerprint required')
    position = state.position
    resource_ledger(compiled, position, 'chess')
    if type(position.side_to_move) is not int or position.side_to_move not in (0, 1):
        raise ValueError('side0/1 required')
    pieces = [(i, p) for i, p in enumerate(position.board) if p]
    if len(pieces) > 5 or any(p.current_type_id not in ('K', 'N', 'B', 'R', 'Q') for _, p in pieces):
        raise ValueError('pawn-free at most five-piece scope required')
    # Slot IDs have no names; exact production compiler sorted declaration order
    # is b_ks,b_qs,ep_target,w_ks,w_qs. Require explicit values, not defaults1.
    expected_aux = {((0, -1), 0), ((1, -1), 0), ((2, -1), None),
                    ((3, -1), 0), ((4, -1), 0)}
    if (len(position.aux_state) != 5 or set(position.aux_state) != expected_aux
            or any(type(v) is not int for key, v in position.aux_state if key != (2, -1))):
        raise ValueError('explicit zero rights/None EP, no extra/duplicate aux required')
    kings = {p.owner: i for i, p in pieces if p.current_type_id == 'K'}
    if max(abs(kings[0]%8-kings[1]%8), abs(kings[0]//8-kings[1]//8)) <= 1:
        raise ValueError('nonadjacent Kings required')
    engine = semantic_engine_for(compiled)
    previous = 1-position.side_to_move
    if engine.in_check(position, previous):
        raise ValueError('previous mover cannot have left own King in check')
    if type(state.ply_count) is not int or not 0 <= state.ply_count < compiled.support.max_ply:
        raise ValueError('valid ongoing absolute ply required')
    terminal = PublicGame(compiled).terminal(state)
    if terminal.is_terminal:
        raise ValueError('authoritative terminal-first handling required')
    if len(state.history) != state.ply_count+1:
        raise ValueError('complete ply-associated history required')
    counts = dict(state.repetition_counts)
    if (len(counts) != len(state.repetition_counts)
            or any(not isinstance(k, str) or not k or type(v) is not int or v < 1 for k, v in state.repetition_counts)
            or counts != Counter(h.position_key for h in state.history)
            or state.history[-1].position_key != repetition_identity_key(position, compiled)):
        raise ValueError('consistent full history/current repetition identity required')
    rows = []
    for rank in reversed(range(8)):
        row = ''; empty = 0
        for file in range(8):
            piece = position.board[rank*8+file]
            if piece is None:
                empty += 1
            else:
                if empty:
                    row += str(empty); empty = 0
                row += piece.current_type_id if piece.owner == 0 else piece.current_type_id.lower()
        if empty:
            row += str(empty)
        rows.append(row)
    fen = '/'.join(rows)+(' w' if position.side_to_move == 0 else ' b')+f' - - 0 {state.ply_count//2+1}'
    payload = asdict(state)
    payload['terminal_status']['status'] = terminal.status.value
    raw = json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=True)
    digest = hashlib.sha256(raw.encode('utf-8')).hexdigest()
    return {'schema': 'local-pawn-free-chess-request-v1', 'fen': fen,
            'state_sha256': digest, 'local_state': payload,
            'ruleset_fingerprint': compiled.ruleset_fingerprint,
            'absolute_ply': state.ply_count, 'remaining_horizon': compiled.support.max_ply-state.ply_count,
            'max_repetition_count': max(counts.values()), 'source_verified': False,
            'scope': 'current-state encoding/association only; no historical reachability or external move/goal proof'}
