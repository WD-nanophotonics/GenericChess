from __future__ import annotations

import json
from pathlib import Path

import pytest

from generic_chess.ai.limits import SearchLimits
from generic_chess.core.actions import action_to_dict
from generic_chess.learning.compact_checkpoint import load_compact_checkpoint
from generic_chess.learning.material import LearnableMaterialCheckpoint
from generic_chess.native.semantic_engine import SemanticSearchEngine
from generic_chess.session.session import GameSession
from scripts import f50_generic_learnable_evaluator as f50
from scripts.f87_two_trajectory_native_search_distillation import COMPACT_CHECKPOINT, SEEDS, WORK_ORDER


def test_f87_contract_freezes_two_parent_native_trajectories():
    assert WORK_ORDER == "GENERICCHESS_F87_TWO_TRAJECTORY_NATIVE_SEARCH_DISTILLATION"
    assert SEEDS == (870401, 870402)


def test_compact_checkpoint_preserves_fixed_position_score_and_choice():
    if not COMPACT_CHECKPOINT.is_file():
        pytest.skip("published compact checkpoint evidence is unavailable")
    compact = load_compact_checkpoint(COMPACT_CHECKPOINT, "f86_parent")
    assert compact.checkpoint_id == "c45623c0b905780ed1fd896a8f9364fd369bed1e641519f45fb40a3faf014d71"
    # Round-trip the compact payload into the legacy checkpoint type so the
    # evaluator/search comparison remains independent of retired F82/F83
    # materialized model descriptors. These frozen outputs are the migration
    # witness captured before the retired descriptors were removed.
    legacy = LearnableMaterialCheckpoint.from_dict(compact.to_dict())
    compiled, native, _profile = f50._ruleset("B_CANONICAL_STANDARD_SHOGI")
    session = GameSession(compiled)
    limits = SearchLimits(max_depth=1, max_nodes=100, quiescence_max_depth=0)
    old_result = SemanticSearchEngine(compiled, native, checkpoint=legacy, tt_megabytes=0).search(session, limits)
    new_result = SemanticSearchEngine(compiled, native, checkpoint=compact, tt_megabytes=0).search(session, limits)
    assert old_result.score == -1473600
    assert action_to_dict(old_result.action) == {
        "kind": "semantic_board",
        "pattern_id": "legacy_028",
        "geometry_id": "g21",
        "actor_type_id": "P",
        "from": [6, 2],
        "to": [6, 3],
        "promotion_target_id": None,
    }
    assert new_result.score == old_result.score
    assert action_to_dict(new_result.action) == action_to_dict(old_result.action)


def test_f87_descriptor_references_bounded_compact_candidate_when_present():
    path = Path(__file__).resolve().parents[1] / "artifacts/f87_two_trajectory_native_search_distillation/successor_candidate_descriptor.json"
    if not path.is_file():
        pytest.skip("F87 Stage-A evidence is unavailable")
    descriptor = json.loads(path.read_text(encoding="utf-8"))
    assert "candidate_checkpoint" not in descriptor
    assert descriptor["candidate_checkpoint_ref"]["variant"] == "candidate"
