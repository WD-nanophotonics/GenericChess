"""Cheap H48C resolver-contract tests; no corpus resolution is run here."""

from __future__ import annotations

import json
from pathlib import Path

from generic_chess.learning.serialization import stable_sha256
from scripts.audit_f48_h48c_corpus_disjointness_resolution import _direct_first


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "audit_f48_h48c_corpus_disjointness_resolution.py"
FIXTURE = ROOT / "tests" / "fixtures" / "h48c_corpus_disjointness_resolution.json"
AUXILIARY = ROOT / "tests" / "fixtures" / "h48c_corpus_disjointness_collision_keys.json"
RULESETS = {
    "A_CANONICAL_WESTERN_CHESS": "7bc6cf3179f4eaea30b205576b9032dca47a16803e9cc8b3e29405cb1e820b35",
    "B_CANONICAL_STANDARD_SHOGI": "ac987c3ffe75d8fa885ba787c1aa7cf60e92205465bf056b12b2989674007635",
    "C_H48B_SELECTED_GENERATED": "9f7e7201a19f8f0ee6c0eacc766c2ac3a6c313e06bbc960d5d6dfb89137db923",
}


def test_h48c_selects_first_passing_candidate_and_preserves_failed_prefix():
    rows = [{"seed": 480701, "pass": False}, {"seed": 480702, "pass": True}, {"seed": 480703, "pass": True}]
    assert _direct_first(rows) == 480702
    assert [row["seed"] for row in rows[:2]] == [480701, 480702]


def test_h48c_source_has_no_measurement_or_learning_path():
    source = SCRIPT.read_text(encoding="utf-8")
    forbidden_imports = ("EvaluationConfig", "NativeSearchEngine", "AlphaBetaPlayer", "collect_self_play", "tdleaf_update", "run_arena")
    assert not any(f"import {name}" in source or f"from generic_chess.{name}" in source for name in forbidden_imports)
    assert "generic_chess.core.identity.position_identity_key" in source
    assert '"evaluator_invoked": False' in source


def test_h48c_selection_contract_is_cross_ruleset_and_identity_only():
    source = SCRIPT.read_text(encoding="utf-8")
    assert "for ruleset_id, compiled in rulesets" in source
    assert "training" in source and "holdout" in source and "arena" in source
    assert "HOLDOUT_START, HOLDOUT_END = 480701, 490700" in source
    assert "ARENA_START, ARENA_END = 480702, 490701" in source
    assert "if seed == selected_holdout" in source
    assert "_direct_first(holdout_attempts)" in source
    assert "_direct_first(arena_attempts)" in source


def test_h48c_fixture_binds_authority_seeds_and_no_learning():
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert fixture["status"] == "PASS"
    assert fixture["kind"] == "H48C_CORPUS_DISJOINTNESS_RESOLUTION"
    assert fixture["parent_h48r3a_sha"] == "d829f14e4c7c939bb1c2e06bc8b7d2b6f4b9e510"
    assert fixture["ruleset_fingerprints"] == RULESETS
    assert fixture["identity_authority"] == "generic_chess.core.identity.position_identity_key"
    assert fixture["original_failed_seed_triple"] == {"training": 480700, "holdout": 480701, "arena": 480702}
    assert fixture["resolved_seed_triple"] == {"training": 480700, "holdout": 480703, "arena": 480708}
    assert fixture["selected_holdout_seed"] == 480703
    assert fixture["selected_arena_seed"] == 480708
    assert all(fixture[name] is False for name in ("evaluator_invoked", "search_invoked", "learner_invoked", "selfplay_invoked", "arena_games_invoked"))


def test_h48c_fixture_records_failed_prefix_and_first_passing_candidates():
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    holdout = fixture["holdout_attempts"]
    arena = fixture["arena_attempts"]
    assert [row["seed"] for row in holdout] == [480701, 480702, 480703]
    assert [row["seed"] for row in arena] == [480702, 480704, 480705, 480706, 480707, 480708]
    assert all(row["pass"] is False for row in holdout[:-1])
    assert all(row["pass"] is False for row in arena[:-1])
    assert holdout[-1]["pass"] is True
    assert arena[-1]["pass"] is True
    for attempts in (holdout, arena):
        for row in attempts:
            assert set(item["ruleset_id"] for item in row["rulesets"]) == set(RULESETS)
            for item in row["rulesets"]:
                assert item["identity_set_count"] > 0
                assert len(item["identity_set_hash"]) == 64
                assert set(item["intersection_counts"]) == set(item["intersection_key_hashes"])
                assert isinstance(item["pass"], bool)


def test_h48c_fixture_reconstruction_runtime_guard_and_collision_binding():
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    auxiliary = json.loads(AUXILIARY.read_text(encoding="utf-8"))
    assert fixture["reconstruction_repeat_equal"] is True
    assert fixture["minimality"]["lexicographically_minimal"] is True
    assert fixture["minimality"]["direct_holdout"] == fixture["selected_holdout_seed"]
    assert fixture["minimality"]["direct_arena"] == fixture["selected_arena_seed"]
    assert fixture["runtime_guard"]["pairwise_disjoint"] is True
    for row in fixture["final_corpora"].values():
        assert row["pairwise_intersections"] == {"training_holdout": [], "training_arena": [], "holdout_arena": []}
        for corpus in (row["training"], row["holdout"], row["arena"]):
            assert corpus["identity_set_count"] > 0
            assert len(corpus["identity_set_hash"]) == 64
    assert stable_sha256(auxiliary) == fixture["collision_auxiliary_sha256"]
    assert [row["seed"] for row in auxiliary["holdout"]] == [480701, 480702]
    assert [row["seed"] for row in auxiliary["arena"]] == [480702, 480704, 480705, 480706, 480707]
