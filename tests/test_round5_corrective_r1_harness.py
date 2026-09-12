"""Focused pre-formal checks for Round 5 Corrective R1."""

from pathlib import Path

import pytest

from generic_chess.core.movegen import legal_actions
from generic_chess.learning.round5_corrective_r1 import (
    CERTIFIED_FINGERPRINT,
    _action_map,
    _assert_certified,
    _load_suite,
    _seed_session,
)
from generic_chess.learning.alphasho_bridge import ALPHASHO_ROOT


def test_r1_uses_exact_certified_semantic_ruleset():
    compiled = _assert_certified()
    assert compiled.ruleset_fingerprint == CERTIFIED_FINGERPRINT
    assert compiled.support is not None
    assert compiled.ir.ir_version == 2
    assert compiled.ir.patterns


def test_r1_maps_every_initial_legal_action_losslessly():
    suite = ALPHASHO_ROOT / "configs" / "training" / "evaluation_positions.jsonl"
    if not suite.is_file():
        pytest.skip("optional AlphaSho evaluation suite is not available")
    compiled = _assert_certified()
    session = _seed_session(compiled, _load_suite()[0]["sfen"])
    actions = legal_actions(session.state, compiled)
    mapping = _action_map(compiled, session.state)
    assert actions
    assert all(len(matches) == 1 for matches in mapping.values())
    assert sum(len(matches) for matches in mapping.values()) == len(actions)
