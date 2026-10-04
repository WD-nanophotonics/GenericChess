"""Declared synthetic full-resource proposals; no labels or value estimates."""
from dataclasses import replace
from fractions import Fraction

from generic_chess.core.pieces import Piece
from generic_chess.core.position import Hands
from generic_chess.core.transition import initial_state
from scripts.audit_f24f_western_chess_perft import position_from_fen
from scripts.resource_mode_context import owned_mode_mass, resource_ledger


def sample_resource_mode(compiled, game, mode, rng):
    """Return (position, tag, rejection); whole-proposal Pawn collisions stop.

    The mark is drawn uniformly from original own base tokens. Only that token
    changes current mode or moves to own hand. All other tokens remain initial.
    The law is not historical reachability, nor a general full-game population.
    """
    if (game, compiled.board_size) not in (('chess', 8), ('shogi', 9)):
        raise ValueError('declared standard Chess/Shogi scope required')
    if not isinstance(mode, tuple) or len(mode) not in (2, 3):
        raise ValueError('refined board/base/current or hand/base mode required')
    location, base = mode[:2]
    metadata = compiled.support.type_metadata
    initial = initial_state(compiled).position
    tokens = [p for p in initial.board if p]
    candidates = [i for i, p in enumerate(tokens) if p.owner == 0 and p.base_type_id == base]
    if not candidates or metadata[base].is_anchor:
        raise ValueError('ordinary initial base group required')
    if location == 'board' and len(mode) == 3:
        current = mode[2]
        if current != base and current not in metadata[base].promotion_target_ids:
            raise ValueError('allowed promotion origin required')
    elif location == 'hand' and len(mode) == 2 and game == 'shogi':
        current = base
    else:
        raise ValueError('declared board mode or Shogi held base required')
    marked = rng.choice(candidates)
    tokens[marked] = Piece(0, base, current, current != base)
    board_tokens = [(p, i == marked) for i, p in enumerate(tokens)
                    if not (i == marked and location == 'hand')]
    n = compiled.board_size
    board = [None]*(n*n)
    pawns = [(p, mark) for p, mark in board_tokens if p.current_type_id == 'P']
    tag_square = None
    if game == 'chess':
        squares = rng.sample([r*n+f for r in range(1, 7) for f in range(n)], len(pawns))
        for (piece, mark), square in zip(pawns, squares):
            board[square] = piece
            if mark:
                tag_square = square
        template = position_from_fen('8/8/8/8/8/8/8/8 w - - 0 1', compiled)
    else:
        for owner in (0, 1):
            group = [(p, mark) for p, mark in pawns if p.owner == owner]
            files = rng.sample(range(9), len(group))
            for (piece, mark), file in zip(group, files):
                rank = rng.randrange(8) + owner
                square = rank*n+file
                if board[square] is not None:
                    return None, None, 'pawn_collision'
                board[square] = piece
                if mark:
                    tag_square = square
        template = initial
    other = [(p, mark) for p, mark in board_tokens if p.current_type_id != 'P']
    squares = rng.sample([i for i, p in enumerate(board) if p is None], len(other))
    for (piece, mark), square in zip(other, squares):
        board[square] = piece
        if mark:
            tag_square = square
    hands = (Hands(((base, 1),)), Hands.empty()) if location == 'hand' else (Hands.empty(), Hands.empty())
    position = replace(template, board=tuple(board), hands=hands, side_to_move=0)
    tag = {'owner': 0, 'base': base, 'board': {} if tag_square is None else {tag_square: Fraction(1)},
           'held': Fraction(location == 'hand'), 'lost': Fraction(0)}
    resource_ledger(compiled, position, game, full_chess=True)
    if owned_mode_mass(position, tag, metadata) != {mode: Fraction(1)}:
        raise ValueError('proposal does not realize the declared owned mode')
    return position, tag, None
