"""Corrected Pawn-aware structural guard; original frozen pilot remains intact."""
from collections import Counter
from dataclasses import replace

from generic_chess.core.identity import repetition_identity_key
from generic_chess.core.position import HistoryRecord
from generic_chess.core.semantic_executor import semantic_engine_for
from generic_chess.core.transition import initial_state


def ongoing_resource_root(compiled, position, game, checkpoint):
    files = Counter()
    for square, piece in enumerate(position.board):
        checkpoint()
        if piece is None:
            continue
        if game == 'chess' and piece.current_type_id == 'P':
            # Western Pawn atoms are intentionally empty: semantic patterns
            # own its forward/capture/double-step geometry.
            if square//8 in (0, 7):
                return None, 'pawn_terminal_rank'
        elif not compiled.support.empty_mobility[piece.current_type_id][piece.owner][square]:
            return None, 'dead_board_mode'
        if piece.current_type_id == 'P':
            files[piece.owner, square % compiled.board_size] += 1
    if game == 'shogi' and any(n > 1 for n in files.values()):
        return None, 'nifu'
    engine = semantic_engine_for(compiled)
    if any(engine.in_check(position, owner, checkpoint=checkpoint) for owner in (0, 1)):
        return None, 'anchor_check'
    key = repetition_identity_key(position, compiled)
    counts = ((key, 1),); history = (HistoryRecord(key, -1, '', False),)
    terminal = engine.terminal_result(position, 0, counts, history, checkpoint=checkpoint)
    if terminal.is_terminal:
        return None, 'terminal_root'
    return replace(initial_state(compiled), position=position, repetition_counts=counts,
                   history=history, terminal_status=terminal), None
