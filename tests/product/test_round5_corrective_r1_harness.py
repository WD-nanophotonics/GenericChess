"""Focused pre-formal checks for Round 5 Corrective R1."""

from pathlib import Path

import pytest

from generic_chess.core.movegen import legal_actions
from generic_chess.learning.round5_corrective_r1 import (
    CERTIFIED_FINGERPRINT,
    _action_map,
    _assert_certified,
    _seed_session,
)


def test_r1_uses_exact_certified_semantic_ruleset():
    compiled = _assert_certified()
    assert compiled.ruleset_fingerprint == CERTIFIED_FINGERPRINT
    assert compiled.support is not None
    assert compiled.ir.ir_version == 2
    assert compiled.ir.patterns


def test_r1_maps_every_initial_legal_action_losslessly():
    compiled = _assert_certified()
    # Self-contained initial Shogi fixture; never access another checkout.
    session = _seed_session(compiled, "lnsgkgsnl/1r5b1/ppppppppp/9/9/9/PPPPPPPPP/1B5R1/LNSGKGSNL b - 1")
    actions = legal_actions(session.state, compiled)
    mapping = _action_map(compiled, session.state)
    assert actions
    assert all(len(matches) == 1 for matches in mapping.values())
    assert sum(len(matches) for matches in mapping.values()) == len(actions)
