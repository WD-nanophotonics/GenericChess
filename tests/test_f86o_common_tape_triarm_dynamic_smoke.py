"""F86O PREP/RESULT contract tests."""

import json
from pathlib import Path

from generic_chess.benchmark.policy_tape import PolicyTape


ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "artifacts" / "f86o_common_tape_triarm_dynamic_smoke"
MANIFEST = ARTIFACTS / "manifest.json"
RESULT = ARTIFACTS / "summary.json"


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_f86o_prep_freezes_six_rulesets_and_four_tape_payloads():
    manifest = _load(MANIFEST)
    assert manifest["status"] == "PRE_REGISTERED_F86O_COMMON_TAPE_TRIARM_DYNAMIC_SMOKE"
    assert manifest["arms"] == ["L", "F", "N"]
    assert len(manifest["rulesets"]) == 6
    assert {(row["arm"], row["sample_id"]) for row in manifest["rulesets"]} == {
        (arm, sample) for arm in ("L", "F", "N") for sample in ("V4-3", "V5-3")
    }
    assert manifest["dynamic_budget"] == {"games_per_arm_sample": 2, "max_ply": 32, "real_games": 12}
    assert manifest["replay_contract"]["seat_assignments"] == [["A", "B"], ["B", "A"]]
    assert all(len(data["uniforms"]) == 32 for sample in manifest["policy_tapes"].values() for data in sample.values())


def test_f86o_tapes_are_reproducible_and_frozen_ruleset_fingerprints_match_order():
    manifest = _load(MANIFEST)
    for sample_id, policies in manifest["policy_tapes"].items():
        for policy_id, data in policies.items():
            assert list(PolicyTape.from_seed(policy_id, data["seed"], 32).uniforms) == data["uniforms"]
    by_key = {(row["arm"], row["sample_id"]): row["ruleset_fingerprint"] for row in manifest["rulesets"]}
    assert by_key["F", "V4-3"] == "8ca58376a52e539c7c8519e902b8dd9e6991b002586d36d846a7a864fffea05d"
    assert by_key["F", "V5-3"] == "29390db6050d1ba482a393f7466608a6f19d0df9e6d4f7c3bd3a556f2d194fff"
    assert by_key["N", "V4-3"] == "856a810d3a21eec779f9ba8300ce602cd24d3e8850ba895e39579603fd4ff3e2"
    assert by_key["N", "V5-3"] == "e8528688a64bce3f39231d9e4f38d5d200ade57c6f517ae33ce9b71b9f75ebe5"


def test_f86o_result_contract_is_deferred_until_after_prep_publish():
    assert not RESULT.exists() or _load(RESULT)["status"] == "F86O_COMMON_TAPE_TRIARM_DYNAMIC_SMOKE_COMPLETE"


def test_f86o_result_accounts_for_exact_games_and_terminal_labels_per_arm_sample():
    result = _load(RESULT)
    assert result["real_games"] == 12
    assert result["max_ply"] == 32
    assert result["routing"]["dynamic"] == ["TRANSPORT_BACKBONE_DYNAMIC_NONTERMINATION_FAILURE"]
    assert result["by_arm"]["L"]["by_sample"]["V4-3"]["terminal_distribution"] == {
        "ongoing@32": 1,
        "stalemate": 1,
    }
    assert result["by_arm"]["L"]["by_sample"]["V5-3"]["terminal_distribution"] == {
        "ongoing@32": 1,
        "stalemate": 1,
    }
    assert result["by_arm"]["F"]["terminal_distribution"] == {"ongoing@32": 4}
    assert result["by_arm"]["N"]["terminal_distribution"] == {"ongoing@32": 4}


def test_f86o_result_preserves_compact_game_evidence_and_unresolved_pairs():
    result = _load(RESULT)
    assert len(result["games"]) == 12
    assert all(len(game["action_sequence_sha256"]) == 64 for game in result["games"])
    assert all(len(game["final_position_digest"]) == 64 for game in result["games"])
    assert all("actions" not in game for game in result["games"])
    assert all(
        result["by_arm"][arm]["paired_outcomes"][sample]["scoreable"] is False
        for arm in ("L", "F", "N")
        for sample in ("V4-3", "V5-3")
    )
    assert result["tactical_nodes"] == 0
    assert result["bfs_expansions"] == 0
    assert result["teacher_training_compute"] == 0
    assert result["f85_actual_compute"] == 0
    assert result["default_generator_changed"] is False


def test_f86o_dynamic_route_is_conservative_and_controls_are_recorded():
    result = _load(RESULT)
    comparisons = {row["sample_id"]: row for row in result["comparisons"]["by_sample"]}
    assert comparisons["V4-3"]["arm_n_vs_legacy"]["stalemate_count_delta"] == -1
    assert comparisons["V5-3"]["arm_n_vs_legacy"]["stalemate_count_delta"] == -1
    assert comparisons["V4-3"]["arm_n_vs_full_reverse"]["ongoing_or_repetition_count_delta"] == 0
    assert comparisons["V5-3"]["arm_n_vs_full_reverse"]["ongoing_or_repetition_count_delta"] == 0
    assert result["by_arm"]["L"]["quality"]["median_game_length"] == 30.0
    assert result["by_arm"]["F"]["quality"]["median_game_length"] == 32.0
    assert result["by_arm"]["N"]["quality"]["median_game_length"] == 32.0
