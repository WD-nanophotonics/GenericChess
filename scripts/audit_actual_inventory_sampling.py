"""Whole-board conditioned proposals with no marked type or fixed source."""
from collections import Counter
from dataclasses import replace
import hashlib
import json
from math import comb
from pathlib import Path
from random import Random
import sys
from time import monotonic

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from generic_chess.core.pieces import Piece
from generic_chess.core.position import Hands
from generic_chess.core.semantic_executor import semantic_engine_for
from generic_chess.core.transition import initial_state
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from scripts.audit_actual_actor_enumeration import inventory
from scripts.audit_exchange_custody import synthetic_state
from scripts.audit_f24f_western_chess_perft import standard_engine, position_from_fen
from scripts.audit_physical_placement_sampling import serialize_board
from scripts.audit_secured_exchange_common_context import Budget

PROTOCOL = ROOT / 'docs/research/ACTUAL_INVENTORY_SAMPLING_PROTOCOL.md'
PROTOCOL_SHA = '5fd77d53808dd7ff78b3caf3aeabaa2311ba41610a865b9ba04fd43fca51946f'
SEED = 20261004


def pawn_pairs():
    return tuple((own, enemy) for own in range(8) for enemy in range(1, 9) if own != enemy)


def sample_actual_frame(compiled, game, rng):
    initial = initial_state(compiled).position
    tokens = [p for p in initial.board if p is not None]
    if any(p.promoted or p.base_type_id != p.current_type_id for p in tokens):
        raise ValueError('unpromoted initial inventory required')
    n = compiled.board_size
    if (game, n) not in (('chess', 8), ('shogi', 9)):
        raise ValueError('declared Chess/Shogi structural scope required')
    pawn_counts = Counter(p.owner for p in tokens if p.current_type_id == 'P')
    expected = {0: 8, 1: 8} if game == 'chess' else {0: 9, 1: 9}
    if pawn_counts != expected:
        raise ValueError('actual initial Pawn counts required')
    board = [None] * (n * n)
    if game == 'chess':
        pool = [r * n + f for r in range(1, 7) for f in range(n)]
        own = rng.sample(pool, 8)
        enemy = rng.sample([square for square in pool if square not in own], 8)
        for owner, squares in ((0, own), (1, enemy)):
            for square in squares:
                board[square] = Piece(owner, 'P', 'P')
        template = position_from_fen('8/8/8/8/8/8/8/8 w - - 0 1', compiled)
    else:
        for file in range(9):
            own, enemy = rng.choice(pawn_pairs())
            board[own * n + file] = Piece(0, 'P', 'P')
            board[enemy * n + file] = Piece(1, 'P', 'P')
        template = initial
    others = [p for p in tokens if p.current_type_id != 'P']
    squares = rng.sample([i for i, p in enumerate(board) if p is None], len(others))
    for square, piece in zip(squares, others):
        board[square] = piece
    return replace(template, board=tuple(board), hands=(Hands.empty(), Hands.empty()), side_to_move=0)


def validate_structural(compiled, position, game):
    if inventory(position) != inventory(initial_state(compiled).position):
        raise ValueError('actual initial inventory changed')
    if position.hands != (Hands.empty(), Hands.empty()) or position.side_to_move != 0:
        raise ValueError('empty-hand owner-zero board scope required')
    n = compiled.board_size
    pawns = [(square, p) for square, p in enumerate(position.board) if p and p.current_type_id == 'P']
    if game == 'chess':
        if any(square // n in (0, 7) for square, _ in pawns):
            raise ValueError('Chess Pawn terminal rank')
    elif game == 'shogi':
        files = Counter((p.owner, square % n) for square, p in pawns)
        if files != Counter({(owner, file): 1 for owner in (0, 1) for file in range(9)}):
            raise ValueError('Shogi Pawn-file structure')
        if any(square // n == (8 if p.owner == 0 else 0) for square, p in pawns):
            raise ValueError('Shogi dead Pawn rank')
    else:
        raise ValueError('undeclared structural scope')


def rejection_reason(compiled, position, game, budget):
    validate_structural(compiled, position, game)
    if game == 'shogi':
        for square, p in enumerate(position.board):
            budget.checkpoint()
            if p and p.current_type_id != 'P' and not compiled.support.empty_mobility[p.current_type_id][p.owner][square]:
                return 'dead_nonpawn_placement'
    engine = semantic_engine_for(compiled)
    for owner in (0, 1):
        if engine.in_check(position, owner, checkpoint=budget.checkpoint):
            return 'actual_anchor_check'
    terminal = synthetic_state(compiled, position).terminal_status.is_terminal
    budget.checkpoint()
    return 'actual_terminal_root' if terminal else None


def audit(budget=None, proposal_limit=128):
    if hashlib.sha256(PROTOCOL.read_bytes()).hexdigest() != PROTOCOL_SHA:
        raise ValueError('frozen actual-inventory sampling protocol changed')
    if not 1 <= proposal_limit <= 128:
        raise ValueError('proposal gate must remain at most 128 per game')
    budget = budget or Budget(seconds=10)
    rng = Random(SEED)
    chess, _ = standard_engine()
    shogi = compile_ruleset_for_execution(build_standard_shogi_ruleset())
    games = {}
    for game, compiled in (('chess', chess), ('shogi', shogi)):
        rejected = Counter(); accepted = None
        for attempt in range(1, proposal_limit + 1):
            budget.checkpoint()
            candidate = sample_actual_frame(compiled, game, rng)
            reason = rejection_reason(compiled, candidate, game, budget)
            if reason is None:
                accepted = candidate
                break
            rejected[reason] += 1
        games[game] = {'proposals': attempt, 'rejected': dict(rejected), 'admitted': accepted is not None,
                       'physical_board': None if accepted is None else serialize_board(accepted)}
        if accepted is None:
            break
    budget.checkpoint()
    return {'protocol_sha256': PROTOCOL_SHA,
            'program_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'seed': SEED, 'complete': len(games) == 2 and all(g['admitted'] for g in games.values()),
            'scope': 'synthetic actual-inventory proposal feasibility; no task/value scores',
            'pawn_layout_counts': {'chess': str(comb(48, 8) * comb(40, 8)), 'shogi': str(57 ** 9)},
            'games': games, 'elapsed_seconds': monotonic() - budget.started}


if __name__ == '__main__':
    result = audit()
    if len(sys.argv) > 1:
        Path(sys.argv[1]).write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps({**{k: v for k, v in result.items() if k != 'games'},
                      'games': {g: {k: v for k, v in row.items() if k != 'physical_board'}
                                for g, row in result['games'].items()}}, indent=2))
