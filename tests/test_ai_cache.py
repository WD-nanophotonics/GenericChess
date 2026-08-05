"""Evaluation profile caches: memory, disk, invalidation, corruption."""

import json
import os
import shutil
import uuid
from pathlib import Path

import pytest

from generic_chess.ai.evaluation.cache import EvaluationProfileCache, MovementCapabilityCache
from generic_chess.ai.evaluation.config import EvaluationConfig
from generic_chess.ai.evaluation.profile import build_ruleset_profile

from ai_fixtures import build_4x4_rooks, build_mate, king, rook


@pytest.fixture()
def ai_tmp_dir():
    base = Path(__file__).resolve().parent.parent
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
        compiled, EvaluationConfig(evaluator_version="generic-v2")
    )
    assert not hit  # evaluator version changed -> miss

    other_ruleset = build_mate(2)
    _, hit = EvaluationProfileCache(disk_dir=ai_tmp_dir).get_or_build(other_ruleset, config)
    assert not hit  # fingerprint changed -> miss


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
