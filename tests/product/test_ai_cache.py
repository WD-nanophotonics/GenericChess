"""Evaluation profile caches: memory, disk, invalidation, corruption."""

import json
import os
import shutil
import uuid
from dataclasses import replace
from pathlib import Path

import pytest

from generic_chess.ai.evaluation.cache import EvaluationProfileCache, MovementCapabilityCache
from generic_chess.ai.evaluation.config import EvaluationConfig, config_hash
from generic_chess.ai.evaluation.profile import build_ruleset_profile

from ai_fixtures import build_4x4_rooks, build_mate, king, rook


@pytest.fixture()
def ai_tmp_dir():
    base = Path(__file__).resolve().parents[2]
    tmp = base / f".gc_ai_tmp_{uuid.uuid4().hex}"
    os.makedirs(tmp, mode=0o777)
    yield tmp
    resolved = tmp.resolve()
    if tmp.exists() and resolved.is_relative_to(base.resolve()):
        shutil.rmtree(resolved)


def test_memory_cache_hit_after_miss():
    compiled = build_4x4_rooks()
    config = EvaluationConfig()
    cache = EvaluationProfileCache(use_disk=False)
    profile, hit = cache.get_or_build(compiled, config)
    assert not hit
    profile2, hit2 = cache.get_or_build(compiled, config)
    assert hit2
    assert profile2 == profile


def test_disk_cache_roundtrip(ai_tmp_dir):
    compiled = build_4x4_rooks()
    config = EvaluationConfig()
    cache1 = EvaluationProfileCache(disk_dir=ai_tmp_dir, use_disk=True)
    profile1, hit1 = cache1.get_or_build(compiled, config)
    assert not hit1
    cache2 = EvaluationProfileCache(disk_dir=ai_tmp_dir, use_disk=True)
    profile2, hit2 = cache2.get_or_build(compiled, config)
    assert hit2
    assert profile2 == profile1
    assert list(ai_tmp_dir.glob("profile-*.json"))


def test_disk_cache_invalidations(ai_tmp_dir):
    compiled = build_4x4_rooks()
    config = EvaluationConfig()
    EvaluationProfileCache(disk_dir=ai_tmp_dir).get_or_build(compiled, config)

    other_config = EvaluationConfig(density_weights=(0.5, 0.2, 0.1, 0.1, 0.1))
    miss_cache = EvaluationProfileCache(disk_dir=ai_tmp_dir)
    _, hit = miss_cache.get_or_build(compiled, other_config)
    assert not hit  # config changed -> miss

    versioned = EvaluationProfileCache(disk_dir=ai_tmp_dir)
    _, hit = versioned.get_or_build(
        compiled, EvaluationConfig(evaluator_version=config.evaluator_version + "-next")
    )
    assert not hit  # evaluator version changed -> miss

    other_ruleset = build_mate(2)
    _, hit = EvaluationProfileCache(disk_dir=ai_tmp_dir).get_or_build(other_ruleset, config)
    assert not hit  # fingerprint changed -> miss


def test_generic_v5_rebuilds_persisted_generic_v4_profile(ai_tmp_dir):
    compiled = build_4x4_rooks()
    old = EvaluationConfig(evaluator_version="generic-v4")
    old_cache = EvaluationProfileCache(disk_dir=ai_tmp_dir, use_disk=True)
    old_profile, old_hit = old_cache.get_or_build(compiled, old)
    assert not old_hit
    assert old_profile.evaluator_version == "generic-v4"
    assert list(ai_tmp_dir.glob("profile-*.json"))

    current = EvaluationConfig()
    new_cache = EvaluationProfileCache(disk_dir=ai_tmp_dir, use_disk=True)
    rebuilt, new_hit = new_cache.get_or_build(compiled, current)
    assert not new_hit
    assert rebuilt.evaluator_version == "generic-v5"


def test_profile_algorithm_version_ignores_pre_semantic_projection_disk_cache(ai_tmp_dir):
    from generic_chess.ai.evaluation.cache import _profile_to_dict
    from generic_chess.rules.compiler import compile_ruleset_for_execution
    from generic_chess.rules.western_chess import build_western_chess_ruleset

    compiled = compile_ruleset_for_execution(build_western_chess_ruleset())
    old_config = EvaluationConfig(evaluator_version="generic-v2")
    new_config = EvaluationConfig()
    current = build_ruleset_profile(compiled, new_config)
    assert current.board_value_by_type["P"] > 1

    stale = _profile_to_dict(current)
    stale["evaluator_version"] = old_config.evaluator_version
    stale["config_hash"] = config_hash(old_config)
    stale["board_value_by_type"]["P"] = 1
    stale["hand_value_by_base_type"]["P"] = 1
    legacy_path = ai_tmp_dir / (
        f"profile-{compiled.ruleset_fingerprint[:16]}-"
        f"{config_hash(old_config)[:12]}.json"
    )
    legacy_path.write_text(json.dumps(stale), encoding="utf-8")

    cache = EvaluationProfileCache(disk_dir=ai_tmp_dir, use_disk=True)
    rebuilt, hit = cache.get_or_build(compiled, new_config)
    assert not hit
    assert rebuilt.board_value_by_type["P"] == current.board_value_by_type["P"]
    assert rebuilt.hand_value_by_base_type["P"] == current.hand_value_by_base_type["P"]


def test_corrupt_disk_cache_rebuilds(ai_tmp_dir):
    compiled = build_4x4_rooks()
    config = EvaluationConfig()
    cache = EvaluationProfileCache(disk_dir=ai_tmp_dir)
    profile, _ = cache.get_or_build(compiled, config)
    for path in ai_tmp_dir.glob("profile-*.json"):
        path.write_text("{corrupt json", encoding="utf-8")
    cache2 = EvaluationProfileCache(disk_dir=ai_tmp_dir)
    profile2, hit = cache2.get_or_build(compiled, config)
    assert not hit
    assert profile2 == profile


def test_movement_capability_cache():
    from generic_chess.core.movement import LeapAtom

    config = EvaluationConfig()
    cache = MovementCapabilityCache()
    atoms = (LeapAtom((0, 1)),)
    p1, hit1 = cache.get_or_build(8, atoms, config)
    assert not hit1
    p2, hit2 = cache.get_or_build(8, atoms, config)
    assert hit2  # geometry reuse ignores ruleset fingerprint
    assert p1 == p2


def test_profile_reuses_capability_across_rulesets():
    from generic_chess.core.pieces import Piece
    from generic_chess.rules.compiler import compile_ruleset
    from generic_chess.rules.schema import RuleSet

    class CountingCache(MovementCapabilityCache):
        def __init__(self) -> None:
            super().__init__()
            self.builds = 0

        def get_or_build(self, n, atoms, config):
            profile, hit = super().get_or_build(n, atoms, config)
            if not hit:
                self.builds += 1
            return profile, hit

    config = EvaluationConfig()
    cache = CountingCache()
    p1 = build_ruleset_profile(build_4x4_rooks(), config, capability_cache=cache)
    builds_after_first = cache.builds
    assert builds_after_first == 2  # K and R geometries

    rows = [[None] * 4 for _ in range(4)]
    rows[0][0] = Piece(0, "K", "K", False)
    rows[3][3] = Piece(1, "K", "K", False)
    rows[1][2] = Piece(0, "R", "R", False)
    rows[2][1] = Piece(1, "R", "R", False)
    mask = (True,) * 16
    ruleset = RuleSet(
        board_size=4,
        piece_types=(king(), rook()),
        initial_position=tuple(tuple(r) for r in rows),
        drop_allowed={"R": (mask, mask)},
        promotion_allowed={},
        promotion_forced={},
    )
    compiled2 = compile_ruleset(ruleset)
    p2 = build_ruleset_profile(compiled2, config, capability_cache=cache)
    assert cache.builds == builds_after_first  # same geometry, no new builds
    assert (
        p1.piece_profiles["R"].movement_signature
        == p2.piece_profiles["R"].movement_signature
    )
    assert (
        p1.piece_profiles["R"].raw_capability_score
        == p2.piece_profiles["R"].raw_capability_score
    )


def _same_rule_different_profile_scopes():
    """Same fingerprint, deliberately different supported normalization scopes."""
    from generic_chess.core.pieces import Piece, PieceType
    from generic_chess.rules.compiler import (
        compile_ruleset, compile_legacy_ruleset_for_semantic_execution,
    )
    from generic_chess.rules.schema import RuleSet

    board = [[None] * 4 for _ in range(4)]
    board[0][0] = Piece(0, "K", "K")
    board[3][3] = Piece(1, "K", "K")
    board[1][0] = Piece(0, "R", "R")
    board[2][3] = Piece(1, "R", "R")
    unused = tuple(PieceType(f"U{i}", f"U{i}", ()) for i in range(5))
    rules = RuleSet(
        board_size=4,
        piece_types=(king(), rook(), *unused),
        initial_position=tuple(tuple(row) for row in board),
        drop_allowed={"R": ((True,) * 16,) * 2,
                      **{p.type_id: ((False,) * 16,) * 2 for p in unused}},
    )
    legacy = compile_ruleset(rules)
    semantic = compile_legacy_ruleset_for_semantic_execution(rules)
    assert legacy.ruleset_fingerprint == semantic.ruleset_fingerprint
    config = EvaluationConfig()
    expected = tuple(build_ruleset_profile(c, config) for c in (legacy, semantic))
    # Legacy closes initial types; semantic conservatively includes declarations.
    # The cache must preserve BOTH existing contracts, not change their values.
    assert expected[0].board_value_by_type["R"] == 1000
    assert expected[1].board_value_by_type["R"] == 1
    return (legacy, semantic), config, expected


@pytest.mark.parametrize("first", [0, 1])
def test_profile_cache_separates_execution_representations(first):
    compiled, config, expected = _same_rule_different_profile_scopes()
    cache = EvaluationProfileCache(use_disk=False)
    for index in (first, 1 - first):
        profile, hit = cache.get_or_build(compiled[index], config)
        assert not hit
        assert profile == expected[index]
    for index in (0, 1):
        profile, hit = cache.get_or_build(compiled[index], config)
        assert hit
        assert profile == expected[index]


@pytest.mark.parametrize("first", [0, 1])
def test_disk_profile_cache_separates_execution_representations(ai_tmp_dir, first):
    compiled, config, expected = _same_rule_different_profile_scopes()
    for index in (first, 1 - first):
        profile, hit = EvaluationProfileCache(disk_dir=ai_tmp_dir).get_or_build(
            compiled[index], config)
        assert not hit
        assert profile == expected[index]
    for index in (0, 1):
        profile, hit = EvaluationProfileCache(disk_dir=ai_tmp_dir).get_or_build(
            compiled[index], config)
        assert hit
        assert profile == expected[index]


@pytest.mark.parametrize("index", [0, 1])
def test_unqualified_old_disk_profile_is_not_adopted(ai_tmp_dir, index):
    from generic_chess.ai.evaluation.cache import _profile_to_dict

    compiled, config, expected = _same_rule_different_profile_scopes()
    ambiguous = ai_tmp_dir / (
        f"profile-{compiled[index].ruleset_fingerprint[:16]}-"
        f"{config_hash(config)[:12]}.json")
    ambiguous.write_text(json.dumps(_profile_to_dict(expected[1 - index])),
                         encoding="utf-8")
    profile, hit = EvaluationProfileCache(disk_dir=ai_tmp_dir).get_or_build(
        compiled[index], config)
    assert not hit
    assert profile == expected[index]
    assert ambiguous.exists()  # Old user cache is ignored, not destructively purged.


@pytest.mark.parametrize("index", [0, 1])
def test_scoped_disk_payload_from_other_representation_is_rebuilt(ai_tmp_dir, index):
    compiled, config, expected = _same_rule_different_profile_scopes()
    for item in compiled:
        EvaluationProfileCache(disk_dir=ai_tmp_dir).get_or_build(item, config)
    paths = list(ai_tmp_dir.glob("profile-*.json"))
    assert len(paths) == 2
    target = next(path for path in paths if json.loads(path.read_text(
        encoding="utf-8"))["board_value_by_type"]["R"]
        == expected[index].board_value_by_type["R"])
    other = next(path for path in paths if path != target)
    target.write_bytes(other.read_bytes())
    profile, hit = EvaluationProfileCache(disk_dir=ai_tmp_dir).get_or_build(
        compiled[index], config)
    assert not hit
    assert profile == expected[index]
