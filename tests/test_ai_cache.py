"""Evaluation profile caches: memory, disk, invalidation, corruption."""

import json
import os
import shutil
import uuid
from pathlib import Path

import pytest

from generic_chess.ai.evaluation.cache import EvaluationProfileCache, MovementCapabilityCache
from generic_chess.ai.evaluation.config import EvaluationConfig

from ai_fixtures import build_4x4_rooks, build_mate


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
    p1, hit1 = cache.get_or_build(8, atoms, config, fingerprint="fp")
    assert not hit1
    p2, hit2 = cache.get_or_build(8, atoms, config, fingerprint="other-fp")
    assert hit2  # geometry reuse ignores ruleset fingerprint
    assert p1 == p2
