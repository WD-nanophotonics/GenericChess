"""Shared helpers for native Phase 2 tests (skippable without the extension)."""

from __future__ import annotations

import pytest

from generic_chess.core.keys import position_key
from generic_chess.core.position import GameState
from generic_chess.core.terminal import _terminal_from_parts
from generic_chess.generation.config import GeneratorConfig
from generic_chess.generation.generator import generate_game
from generic_chess.native import native_available

requires_native = pytest.mark.skipif(
    not native_available(), reason="native extension not built"
)


def generated_compiled(size: int = 4, seed: int = 7):
    game = generate_game(
        GeneratorConfig(seed=seed, board_size=size, setup_preset="classic_like")
    )
    return game.compiled_ruleset


def make_state(compiled, position) -> GameState:
    """Build a GameState for an arbitrary position (test-only helper)."""
    key = position_key(position, compiled)
    counts = ((key, 1),)
    status = _terminal_from_parts(position, 0, counts, compiled)
    return GameState(
        position=position,
        ply_count=0,
        repetition_counts=counts,
        terminal_status=status,
    )


def simple_ruleset(
    piece_types,
    rows,
    *,
    drop_types=(),
    drop_mask_all=False,
    promotion_allowed=None,
    promotion_forced=None,
    repetition_limit=4,
    max_ply=512,
    board_size=4,
):
    """Compile a RuleSet from plain types/rows (test-only helper)."""
    from generic_chess.core.pieces import Piece
    from generic_chess.rules.compiler import compile_ruleset
    from generic_chess.rules.schema import RuleSet

    n = board_size
    mask = (True,) * (n * n) if drop_mask_all else (False,) * (n * n)
    drop_allowed = {tid: (mask, mask) for tid in drop_types}
    return compile_ruleset(
        RuleSet(
            schema_version=1,
            board_size=n,
            piece_types=tuple(piece_types),
            initial_position=tuple(tuple(r) for r in rows),
            drop_allowed=drop_allowed,
            promotion_allowed=promotion_allowed or {},
            promotion_forced=promotion_forced or {},
            repetition_limit=repetition_limit,
            max_ply=max_ply,
            stalemate_result="draw",
        )
    )
