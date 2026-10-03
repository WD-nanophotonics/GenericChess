"""Exact conditioned proposals and one full-inventory common frame per game."""
from collections import Counter
from dataclasses import replace
from fractions import Fraction
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
from scripts.audit_exchange_custody import synthetic_state
from scripts.audit_f24f_western_chess_perft import standard_engine, position_from_fen
from scripts.audit_secured_exchange_common_context import Budget, root_score

PROTOCOL = ROOT / 'docs/research/PHYSICAL_PLACEMENT_SAMPLING_PROTOCOL.md'
PROTOCOL_SHA = '706468d36bcee07e9c32b5d5d0834664e9beb9dc3eb23615d17686f712f8bf7d'
SEED = 20261003


def support_masses():
    return {'chess': Fraction(comb(47, 7) * comb(40, 8), comb(63, 7) * comb(56, 8)),
            'shogi': Fraction(7 * 57 ** 8, comb(80, 8) * comb(72, 9))}


def paired_choices(n=9, focal=(3, 3)):
    """Cartesian factors of all valid unlabelled Shogi Pawn pairs, exactly once."""
    file, rank = focal
    return [tuple((None, enemy) for enemy in range(1, n) if enemy != rank) if f == file else
            tuple((own, enemy) for own in range(n - 1) for enemy in range(1, n) if own != enemy)
            for f in range(n)]


def sample_frame(compiled, game, rng):
    initial = initial_state(compiled).position
    tokens = [piece for piece in initial.board if piece is not None]
    removed = next(i for i, p in enumerate(tokens) if p.owner == 0 and p.current_type_id == 'P')
    tokens.pop(removed)
    n = compiled.board_size; focal = 3 * n + 3
    board = [None] * (n * n); board[focal] = Piece(0, 'P', 'P')
    pawn_counts = Counter(p.owner for p in tokens if p.current_type_id == 'P')
    assert pawn_counts == ({0: 7, 1: 8} if game == 'chess' else {0: 8, 1: 9})
    if game == 'chess':
        pool = [r * n + f for r in range(1, 7) for f in range(n) if r * n + f != focal]
        for index, square in enumerate(rng.sample(pool, 15)):
            board[square] = Piece(0 if index < 7 else 1, 'P', 'P')
        template = position_from_fen('8/8/8/8/8/8/8/8 w - - 0 1', compiled)
    else:
        for file, choices in enumerate(paired_choices()):
            own, enemy = rng.choice(choices)
            if own is not None:
                board[own * n + file] = Piece(0, 'P', 'P')
            board[enemy * n + file] = Piece(1, 'P', 'P')
        template = initial
    other = [p for p in tokens if p.current_type_id != 'P']
    squares = rng.sample([i for i, p in enumerate(board) if p is None], len(other))
    for square, piece in zip(squares, other):
        board[square] = piece
    return replace(template, board=tuple(board), hands=(Hands.empty(), Hands.empty()), side_to_move=0)


def substituted(position, tid, compiled):
    initial_types = {p.base_type_id for p in initial_state(compiled).position.board if p}
    base = tid
    if tid not in initial_types:
        parents = [key for key, item in compiled.support.type_metadata.items() if tid in item.promotion_target_ids]
        if len(parents) != 1:
            raise ValueError('ambiguous promoted-type provenance')
        base = parents[0]
    board = list(position.board); n = compiled.board_size
    board[3 * n + 3] = Piece(0, base, tid, promoted=base != tid)
    return replace(position, board=tuple(board))


def rejection_reason(position, game, compiled, budget):
    n = compiled.board_size
    if game == 'shogi':
        for square, piece in enumerate(position.board):
            budget.checkpoint()
            if piece and not compiled.support.empty_mobility[piece.current_type_id][piece.owner][square]:
                return 'dead_nonfocal_placement'
    engine = semantic_engine_for(compiled)
    family = sorted(tid for tid, item in compiled.support.type_metadata.items() if not item.is_anchor)
    for tid in family:
        budget.checkpoint(); query = substituted(position, tid, compiled)
        if engine.in_check(query, 0, checkpoint=budget.checkpoint):
            return 'own_anchor_check'
        if engine.in_check(query, 1, checkpoint=budget.checkpoint):
            return 'nonmoving_anchor_check'
        if synthetic_state(compiled, query).terminal_status.is_terminal:
            return 'terminal_common_root'
    return None


def serialize_board(position):
    return [None if p is None else [p.owner, p.base_type_id, p.current_type_id, p.promoted] for p in position.board]


def audit(budget=None, proposal_limit=128):
    if hashlib.sha256(PROTOCOL.read_bytes()).hexdigest() != PROTOCOL_SHA:
        raise ValueError('frozen placement protocol changed')
    budget = budget or Budget(); rng = Random(SEED)
    chess, _ = standard_engine()
    shogi = compile_ruleset_for_execution(build_standard_shogi_ruleset())
    result = {'protocol_sha256': PROTOCOL_SHA,
              'program_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'seed': SEED, 'complete': False, 'support_masses': {k: str(v) for k, v in support_masses().items()},
              'games': {}, 'roots': []}
    for game, compiled, types in [('chess', chess, ('P', 'N', 'B', 'R', 'Q')),
                                  ('shogi', shogi, ('P', 'L', 'N', 'S', 'G', 'B', 'R'))]:
        rejected = Counter(); position = None; attempts = 0
        for attempts in range(1, proposal_limit + 1):
            budget.checkpoint(); candidate = sample_frame(compiled, game, rng)
            reason = rejection_reason(candidate, game, compiled, budget)
            if reason is None:
                position = candidate; break
            rejected[reason] += 1
        info = {'proposals': attempts, 'rejected': dict(rejected), 'admitted': position is not None,
                'common_screen_family': sorted(tid for tid, item in compiled.support.type_metadata.items() if not item.is_anchor)}
        result['games'][game] = info
        if position is None:
            result['incomplete_reason'] = 'no common frame within frozen proposal limit'
            break
        info['physical_board'] = serialize_board(position)
        info['observed_task_scores'] = {}
        for tid in types:
            budget.checkpoint()
            row = root_score(compiled, substituted(position, tid, compiled), budget)
            result['roots'].append({'game': game, 'focal_type': tid, **row})
            info['observed_task_scores'][tid] = row['success']
    else:
        result['complete'] = True
    result.update(materialized_transitions=budget.transitions, elapsed_seconds=monotonic() - budget.started)
    return result


if __name__ == '__main__':
    result = audit()
    if len(sys.argv) > 1:
        Path(sys.argv[1]).write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({**{k: v for k, v in result.items() if k not in ('roots', 'games')},
                      'games': {g: {k: v for k, v in info.items() if k != 'physical_board'} for g, info in result['games'].items()}}, indent=2))
