from dataclasses import replace
import json
from math import comb
from pathlib import Path
from random import Random

import pytest

from generic_chess.core.pieces import Piece
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from scripts.audit_actual_inventory_sampling import audit, pawn_pairs, rejection_reason, sample_actual_frame, validate_structural
from scripts.audit_f24f_western_chess_perft import standard_engine
from scripts.audit_secured_exchange_common_context import Budget


@pytest.fixture(scope='module')
def compiled_games():
    return {'chess': standard_engine()[0], 'shogi': compile_ruleset_for_execution(build_standard_shogi_ruleset())}


def test_full_file_pair_factor_has_exact_complete_rule_valid_support(compiled_games):
    compiled = compiled_games['shogi']
    pairs = pawn_pairs()
    assert len(pairs) == len(set(pairs)) == 8 * 8 - 7 == 57
    expected = {(a, b) for a in range(9) for b in range(9)
                if a != b and compiled.support.empty_mobility['P'][0][a * 9]
                and compiled.support.empty_mobility['P'][1][b * 9]}
    assert set(pairs) == expected


def test_proposals_preserve_actual_inventory_and_have_no_fixed_pawn_source(compiled_games):
    for game, compiled in compiled_games.items():
        rng = Random(20261004)
        rows = [sample_actual_frame(compiled, game, rng) for _ in range(8)]
        for position in rows:
            validate_structural(compiled, position, game)
        n = compiled.board_size
        assert any(p.board[3 * n + 3] is None or p.board[3 * n + 3].current_type_id != 'P'
                   or p.board[3 * n + 3].owner != 0 for p in rows)


def test_malformed_inventory_and_pawn_structure_are_rejected(compiled_games):
    for game, compiled in compiled_games.items():
        position = sample_actual_frame(compiled, game, Random(1)); n = compiled.board_size
        source = next(i for i, p in enumerate(position.board) if p and p.owner == 0 and p.current_type_id == 'P')
        board = list(position.board); board[source] = Piece(0, 'Q', 'Q')
        with pytest.raises(ValueError, match='inventory changed'):
            validate_structural(compiled, replace(position, board=tuple(board)), game)
        board = list(position.board); target = (n - 1) * n + source % n
        board[source], board[target] = board[target], board[source]
        with pytest.raises(ValueError, match='Pawn.*rank'):
            validate_structural(compiled, replace(position, board=tuple(board)), game)
    compiled = compiled_games['shogi']; position = sample_actual_frame(compiled, 'shogi', Random(1))
    board = list(position.board)
    source = next(i for i, p in enumerate(board) if p and p.owner == 0 and p.current_type_id == 'P' and i % 9 == 0)
    target = next(r * 9 + 1 for r in range(8) if board[r * 9 + 1] is None)
    board[source], board[target] = board[target], board[source]
    with pytest.raises(ValueError, match='Pawn-file'):
        validate_structural(compiled, replace(position, board=tuple(board)), 'shogi')


def test_frozen_first_admission_evidence_reproduces(compiled_games):
    result = audit()
    root = Path(__file__).resolve().parents[1]
    recorded = json.loads((root / 'docs/research/data/actual_inventory_sampling_20261004.json').read_text())
    for key in ('protocol_sha256', 'program_sha256', 'seed', 'complete', 'scope', 'pawn_layout_counts', 'games'):
        assert recorded[key] == result[key]
    assert result['pawn_layout_counts'] == {'chess': str(comb(48, 8) * comb(40, 8)), 'shogi': str(57 ** 9)}
    assert result['complete']
    assert {game: row['proposals'] for game, row in result['games'].items()} == {'chess': 3, 'shogi': 14}
    for game, row in result['games'].items():
        compiled = compiled_games[game]
        template = sample_actual_frame(compiled, game, Random(0))
        position = replace(template, board=tuple(None if p is None else Piece(*p) for p in row['physical_board']))
        assert rejection_reason(compiled, position, game, Budget()) is None
        assert row['proposals'] == sum(row['rejected'].values()) + 1


def test_bound_failure_never_becomes_zero_population_or_score():
    result = audit(proposal_limit=1)
    assert not result['complete'] and not result['games']['chess']['admitted']
    assert result['games']['chess']['physical_board'] is None
    assert 'shogi' not in result['games']
    with pytest.raises(ValueError, match='at most 128'):
        audit(proposal_limit=129)
    with pytest.raises(TimeoutError):
        audit(Budget(seconds=-1))
