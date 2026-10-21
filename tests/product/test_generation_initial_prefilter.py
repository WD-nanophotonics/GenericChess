"""Early generator rejection must preserve Core attacks and accepted RNG output."""
from pathlib import Path
import json
import random
import hashlib
import pytest
from generic_chess.core.attacks import is_in_check
from generic_chess.core.coordinates import Square
from generic_chess.core.movement import LeapAtom, RayAtom
from generic_chess.core.pieces import Piece, PieceType
from generic_chess.core.position import Position
from generic_chess.generation.generator import generate_game
from generic_chess.generation.config import GeneratorConfig
from generic_chess.generation.config import GenerationError
from generic_chess.generation.generator import _initial_anchors_attacked
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.serialization import serialize_ruleset
from rule_semantics_ir_fixtures import _semantic_ruleset, _king_type

BASELINES = json.loads((Path(__file__).parent / 'data/generation_prefilter_baseline_20261015.json').read_text(encoding='utf-8'))['rows']


@pytest.mark.parametrize('row', BASELINES, ids=lambda row: str(row['seed']))
def test_early_filter_preserves_prechange_generated_rule_bytes(row):
    config = GeneratorConfig(seed=row['seed'], board_size=row['n'],
        setup_preset='bilateral_random', allow_hybrid=True, max_generation_attempts=16)
    if not row['accepted']:
        with pytest.raises(GenerationError, match='no valid game generated after 16 attempts'):
            generate_game(config)
        return
    game = generate_game(config)
    assert game.generation_report.generation_attempts == row['attempts']
    assert hashlib.sha256(serialize_ruleset(game.ruleset).encode()).hexdigest() == row['ruleset_sha256']


@pytest.mark.parametrize('n', [4, 8, 18, 32])
def test_early_attack_predicate_matches_core_on_typed_occupancies(n):
    types = (_king_type(), PieceType('L', 'L', (LeapAtom((3, 1)), LeapAtom((-2, 0)))),
        PieceType('R', 'R', (RayAtom((1, 0)), RayAtom((0, 1)), RayAtom((-1, 1), 2))))
    board = [None] * (n * n)
    board[0], board[-1] = Piece(0, 'K', 'K'), Piece(1, 'K', 'K')
    compiled = compile_ruleset_for_execution(_semantic_ruleset(types, (), n=n,
        rows=tuple(tuple(board[i:i+n]) for i in range(0, n*n, n))))
    rng = random.Random(15000+n)
    observed = set()
    for _ in range(64):
        cells = list(range(n*n)); rng.shuffle(cells)
        board = [None] * (n*n)
        board[cells.pop()], board[cells.pop()] = Piece(0, 'K', 'K'), Piece(1, 'K', 'K')
        for _ in range(min(4*n, len(cells))):
            tid = rng.choice(('L', 'R')); board[cells.pop()] = Piece(rng.randrange(2), tid, tid)
        position = Position(tuple(board), ruleset_fingerprint=compiled.ruleset_fingerprint)
        expected = any(is_in_check(position, owner, compiled) for owner in (0, 1))
        rows = tuple(tuple(board[i:i+n]) for i in range(0, n*n, n))
        assert _initial_anchors_attacked(n, rows, compiled.types_by_id) == expected
        observed.add(expected)
    assert observed == {False, True}
