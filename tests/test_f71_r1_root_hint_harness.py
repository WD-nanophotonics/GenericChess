"""Regression coverage for the F71-R1 root-only hint channel."""

from dataclasses import replace
from pathlib import Path

import pytest

from generic_chess.ai.limits import SearchLimits
from generic_chess.core.coordinates import Square
from generic_chess.native import native_available
from generic_chess.native.mirror import pack_semantic_action
from generic_chess.native.semantic_engine import SemanticSearchEngine
from scripts import f59_action_spectrum_diagnosis as f59
from scripts import f71_causal_root_hint_probe as f71


ROOT = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.skipif(not native_available(), reason="native extension is not built")


def _limits():
    return SearchLimits(max_depth=2, max_nodes=128, quiescence_max_depth=0)


def _fresh(compiled, native, checkpoint):
    return SemanticSearchEngine(compiled, native, checkpoint=checkpoint, tt_megabytes=0)


def _illegal_packable_action(session, native):
    legal = set(f71._action_key(action) for action in session.legal_actions())
    for action in session.legal_actions():
        for rank in range(9):
            for file in range(9):
                candidate = replace(action, to_square=Square(file, rank))
                if f71._action_key(candidate) in legal:
                    continue
                pack_semantic_action(native, session.state.position, candidate)
                return candidate
    raise AssertionError("test position did not provide a packable illegal action")


def test_root_hint_reorders_root_only_and_illegal_hint_fails_closed():
    compiled, native, _profile = f59._ruleset(f71.LABEL)
    checkpoint = f71._load_gen1(compiled)
    record = f71._load_stable_roots(1)[0]["record"]
    session = f59._session(compiled, record)

    baseline = _fresh(compiled, native, checkpoint).search(session, _limits())
    default_first = baseline.root_iteration_first_actions[0]
    assert default_first is not None
    hint = next(
        action for action in session.legal_actions()
        if f71._action_key(action) != f71._action_key(default_first)
    )
    hinted = _fresh(compiled, native, checkpoint).search(
        session, _limits(), root_order_hint=hint
    )
    attempted = hinted.root_iterations_attempted
    assert hinted.root_hint_requested == hint
    assert hinted.root_hint_legal
    assert hinted.root_hint_apply_count == attempted
    assert all(
        action == hint
        for action in hinted.root_iteration_first_actions[:attempted]
    )
    assert hinted.root_iteration_first_actions[0] != default_first

    illegal = _illegal_packable_action(session, native)
    closed = _fresh(compiled, native, checkpoint).search(
        session, _limits(), root_order_hint=illegal
    )
    assert not closed.root_hint_legal
    assert closed.root_hint_apply_count == 0
    assert closed.root_iteration_first_actions[0] == default_first

    repeat = _fresh(compiled, native, checkpoint).search(session, _limits())
    assert (
        repeat.action,
        repeat.score,
        repeat.nodes,
        repeat.qnodes,
        repeat.completed_depth,
        repeat.root_iteration_first_actions,
    ) == (
        baseline.action,
        baseline.score,
        baseline.nodes,
        baseline.qnodes,
        baseline.completed_depth,
        baseline.root_iteration_first_actions,
    )


def test_root_hint_channel_is_root_only_and_not_a_tt_injection():
    source = (ROOT / "generic_chess" / "_native" / "native_module.c").read_text(
        encoding="utf-8"
    )
    assert "if (ply == 0 && ctx->root_order_hint_present)" in source
    assert "root_order_hint" in source
    harness = (ROOT / "scripts" / "f71_causal_root_hint_probe.py").read_text(
        encoding="utf-8"
    )
    assert "ctypes" not in harness
    assert "_inject_root_hint" not in harness
