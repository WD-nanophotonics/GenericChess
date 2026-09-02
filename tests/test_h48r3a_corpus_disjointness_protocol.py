"""H48R3A protocol and blocker-integrity tests."""

from __future__ import annotations

import copy
import hashlib
import json
import subprocess
from pathlib import Path

from scripts.f48_protocol import recompute_aggregation


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "tests" / "fixtures" / "h48r3a_corpus_disjointness_protocol_manifest.json"
BLOCKER = ROOT / "tests" / "fixtures" / "f48_corpus_collision_blocker.json"


def _canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def test_h48r3a_manifest_is_signed_and_has_no_resolved_seeds():
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    unsigned = {key: value for key, value in data.items() if key != "manifest_sha256"}
    assert hashlib.sha256(_canonical(unsigned).encode()).hexdigest() == data["manifest_sha256"]
    assert data["parent_checkpoint_sha"] == "67a35e6c88798e54bce1dd95b35ed9ed82c5b4d1"
    assert data["original_seed_triple"] == {"training": 480700, "holdout": 480701, "arena": 480702}
    assert data["candidate_ranges"]["holdout"] == {"start": 480701, "end": 490700, "inclusive": True, "count": 10000}
    assert data["candidate_ranges"]["arena"] == {"start": 480702, "end": 490701, "inclusive": True, "count": 10000}
    assert data["resolved_seed_fields_present"] is False
    assert "selected_holdout_seed" not in data and "selected_arena_seed" not in data
    assert not any("selected" in str(value).lower() for value in data["seed_selection_inputs"])
    assert data["seed_selection_excludes"] == ["evaluation", "search", "teacher", "checkpoint", "material_values", "game_outcome", "performance_metric", "learner"]


def test_blocker_fixture_preserves_exact_witness():
    data = json.loads(BLOCKER.read_text(encoding="utf-8"))
    assert data["candidate_sha"] == "67a35e6c88798e54bce1dd95b35ed9ed82c5b4d1"
    assert data["learning_started"] is False
    assert data["later_partition_started"] is False
    assert data["blocker_reason"] == "FROZEN_CORPUS_IDENTITY_COLLISION"
    assert data["intersections"]["training_holdout"] == [
        "05791139d850e973eca4dd73460a7efdb4164f0d4519674844c6e1b51cbb8fc2",
        "37f09298bb9da90526702980c76aadee3f6d4064ac8363bdfce9b77d2f2b40c3",
        "e4b3335bd92a07f5b3c76daa5f7eab0a5e77bc36f9ee734ff84b1f7e651a2498",
    ]
    assert data["intersections"]["training_arena"] == [
        "05791139d850e973eca4dd73460a7efdb4164f0d4519674844c6e1b51cbb8fc2",
        "e4427b1473158a6f49ff120dd57c7b5081829158d4ebbf5a59eedbdcf15dcebf",
    ]
    assert data["intersections"]["holdout_arena"] == [
        "05791139d850e973eca4dd73460a7efdb4164f0d4519674844c6e1b51cbb8fc2",
        "8037eef1132c92eb08f491a6c10087fe8f9b0e972aaf23894d084a201d5c8ef5",
    ]
    assert data["witness_raw_sha256"] == "eec95ff59229c0d2fb46999cafb1593b57c540caa2f6962c9a4330258d3829f5"


def test_h48_authority_files_are_unchanged_from_parent():
    paths = [
        "tests/fixtures/h48a_learnable_material_recovery_manifest.json",
        "tests/fixtures/h48r1a_experimental_degrees_of_freedom_manifest.json",
        "tests/fixtures/h48r2a_executable_training_screening_manifest.json",
        "tests/fixtures/h48b_generated_benchmark_selection.json",
    ]
    for path in paths:
        parent = subprocess.run(["git", "show", f"67a35e6c88798e54bce1dd95b35ed9ed82c5b4d1:{path}"], cwd=ROOT, capture_output=True, check=True).stdout
        current = subprocess.run(["git", "show", f"HEAD:{path}"], cwd=ROOT, capture_output=True, check=True).stdout
        assert current == parent
    assert subprocess.run(["git", "diff", "--quiet", "67a35e6c88798e54bce1dd95b35ed9ed82c5b4d1..HEAD", "--", "generic_chess"], cwd=ROOT).returncode == 0


def test_beyond_prior_is_or_across_generations_and_records_first():
    from tests.test_f48_protocol import _ruleset

    row = _ruleset()
    generations = []
    for generation in (1, 2, 3):
        value = copy.deepcopy(row["learners"]["M48-0"]["by_prior"]["P48-0"]["generations"][0])
        value["generation"] = generation
        generations.append(value)
    generations[1]["holdout_teacher_agreement"]["agreement"] = 0.83
    generations[2]["arena_vs_p48_0"] = {"mean_pair_score": 0.4, "bootstrap_low": 0.4}
    row["learners"]["M48-0"]["by_prior"]["P48-0"]["generations"] = generations
    result = recompute_aggregation(row, "M48-0")
    assert result["beyond_prior_by_generation"] == {"1": False, "2": True, "3": False}
    assert result["beyond_prior"] is True
    assert result["first_beyond_prior_generation"] == 2

