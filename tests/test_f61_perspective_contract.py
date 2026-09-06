"""Two-orientation witness for the compact successor-root-Q contract."""

import json
from pathlib import Path

import pytest

from generic_chess.ai.limits import SearchLimits
from generic_chess.learning.nonlinear import compact_residual_native_value
from generic_chess.native import native_available
from generic_chess.native.adapter import pack_semantic_search_position
from generic_chess.native.semantic import evaluate as native_evaluate
from generic_chess.native.semantic_engine import SemanticSearchEngine

from scripts import f59_action_spectrum_diagnosis as f59


ROOT = Path(__file__).resolve().parents[1]
MODELS = ROOT / "docs" / "architecture" / "GENERICCHESS_F61_MODEL_PARAMS.json"


def _controlled_model(perspective_marker=...):
    source = json.loads(MODELS.read_text(encoding="utf-8"))["candidates"][0]["model"]
    dimension = len(source["input_mean"])
    controlled = dict(source)
    controlled.update(
        input_mean=[0.0] * dimension,
        input_scale=[1.0] * dimension,
        hidden_weights=[[0.0] * dimension for _ in range(source["width"])],
        hidden_bias=[0.0] * source["width"],
        output_weights=[0.0] * source["width"],
        output_bias=1.0,
        target_scale=10.0,
    )
    if perspective_marker is ...:
        controlled.pop("perspective", None)
    else:
        controlled["perspective"] = perspective_marker
    return controlled


@pytest.mark.skipif(not native_available(), reason="native extension is not built")
def test_successor_root_q_is_negative_child_value_in_both_orientations():
    label = f59.LABELS[1]
    compiled, native, _profile = f59._ruleset(label)
    parent = f59._parent(label)
    controlled = _controlled_model("successor_root_q")
    child = parent.child_checkpoint(
        board_weights=parent.board_weights, hand_weights=parent.hand_weights,
        dynamic_weights=parent.dynamic_weights, compact_nonlinear=controlled,
        games_seen_delta=0, positions_seen_delta=0, training_updates_delta=1,
        training_config_hash="f61-perspective-witness", training_seed=1,
    )
    session = f59._session(compiled, {"action_history": []})
    deltas = []
    for _ in range(2):
        action = sorted(session.legal_actions(), key=lambda a: str(a))[0]
        session.submit(action)
        baseline = SemanticSearchEngine(compiled, native, checkpoint=parent, tt_megabytes=1)
        corrected = SemanticSearchEngine(compiled, native, checkpoint=child, tt_megabytes=1)
        limits = SearchLimits(max_depth=1, max_nodes=100, quiescence_max_depth=0)
        deltas.append(corrected.search(session, limits).score - baseline.search(session, limits).score)
    # The first position has current child side 1 and the second current child
    # side 0.  In both cases the corrected root result reflects the same
    # favorable residual; the old owner-0 mapping flips one orientation.
    assert deltas == [2560, 2560]
    assert all(delta != 0 for delta in deltas)
    assert -10.0 * 256 == -2560  # R_V_child = -R_Q_root, independently.


@pytest.mark.skipif(not native_available(), reason="native extension is not built")
def test_owner0_default_preserves_v4_behavior_in_both_orientations():
    compiled, native, _profile = f59._ruleset(f59.LABELS[1])
    session = f59._session(compiled, {"action_history": []})
    implicit = _controlled_model()
    explicit = _controlled_model("owner0")
    contributions = []
    for _ in range(2):
        packed = pack_semantic_search_position(compiled, native, session)
        baseline = native_evaluate(native, packed, evaluator_scale=256)
        implicit_score = native_evaluate(
            native, packed, compact_values=implicit, evaluator_scale=256
        )
        explicit_score = native_evaluate(
            native, packed, compact_values=explicit, evaluator_scale=256
        )
        assert implicit_score == explicit_score
        contributions.append(implicit_score - baseline)
        action = sorted(session.legal_actions(), key=str)[0]
        session.submit(action)
    assert contributions == [2560, -2560]


@pytest.mark.skipif(not native_available(), reason="native extension is not built")
def test_python_perspective_conversion_matches_native_contribution():
    compiled, native, _profile = f59._ruleset(f59.LABELS[1])
    session = f59._session(compiled, {"action_history": []})
    for _ in range(2):
        packed = pack_semantic_search_position(compiled, native, session)
        baseline = native_evaluate(native, packed, evaluator_scale=256)
        for perspective in ("owner0", "successor_root_q"):
            score = native_evaluate(
                native,
                packed,
                compact_values=_controlled_model(perspective),
                evaluator_scale=256,
            )
            expected = compact_residual_native_value(
                10.0,
                perspective=perspective,
                side_to_move=session.state.position.side_to_move,
            )
            assert score - baseline == round(expected * 256)
        action = sorted(session.legal_actions(), key=str)[0]
        session.submit(action)
