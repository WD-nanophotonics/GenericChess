from __future__ import annotations

import numpy as np

from generic_chess.core.pieces import Piece
from generic_chess.core.semantic_executor import semantic_engine_for
from generic_chess.core.transition import initial_state
from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from tests.test_f24c_mixed_mechanic_certification import A0, A1, H0, _mixed_ruleset, _position

from scripts.f133_shogi_resource_transition_action_semantics import (
    _microtests,
    _rename_ruleset,
    _resource_classes,
    _resource_transition,
)


def test_resource_classes_are_structural_and_type_rename_invariant():
    original = compile_semantic_ruleset(build_standard_shogi_ruleset())
    renamed = compile_semantic_ruleset(_rename_ruleset(build_standard_shogi_ruleset()))
    left = _resource_classes(original)
    right = _resource_classes(renamed)
    assert len(left["classes"]) == 7
    assert [item["signature_sha256"] for item in left["classes"]] == [item["signature_sha256"] for item in right["classes"]]


def test_mixed_capture_drop_and_promoted_capture_use_authoritative_hand_delta():
    compiled = compile_semantic_ruleset(_mixed_ruleset())
    classes = _resource_classes(compiled)
    engine = semantic_engine_for(compiled)
    anchors = [(0, 0, Piece(0, H0, H0)), (6, 6, Piece(1, H0, H0))]
    root = _position(compiled, [(1, 1, Piece(0, A0, A0)), (2, 1, Piece(1, A0, A0)), *anchors], hands=([(A0, 1)], ()))
    actions = engine.legal_actions(root)
    capture = next(action for action in actions if "capture_A0_A0" in action.pattern_id)
    drop = next(action for action in actions if action.source is None and action.actor_type == A0)
    capture_delta = _resource_transition(root, engine.apply(root, capture), classes)
    drop_delta = _resource_transition(root, engine.apply(root, drop), classes)
    assert np.max(capture_delta) == 1.0
    assert np.min(drop_delta) == -1.0

    promoted_root = _position(compiled, [(1, 1, Piece(0, A0, A0)), (2, 1, Piece(1, A0, A1, promoted=True)), *anchors], hands=([(A0, 1)], ()))
    promoted_capture = next(action for action in engine.legal_actions(promoted_root) if "capture_A0_A0" in action.pattern_id)
    assert np.max(_resource_transition(promoted_root, engine.apply(promoted_root, promoted_capture), classes)) == 1.0


def test_western_rules_have_no_reusable_resource_transition_classes():
    from generic_chess.rules.western_chess import build_western_chess_ruleset
    compiled = compile_semantic_ruleset(build_western_chess_ruleset())
    classes = _resource_classes(compiled)
    assert classes["classes"] == []
    position = initial_state(compiled).position
    assert _resource_transition(position, position, classes).shape == (0,)


def test_genericity_microtests_pass():
    report = _microtests()
    assert report["pass"] is True
