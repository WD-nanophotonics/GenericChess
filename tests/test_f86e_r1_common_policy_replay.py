"""F86E-R1 common-random policy tape contracts."""

import json
from pathlib import Path

from generic_chess.benchmark.policy_tape import PolicyTape


ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "artifacts" / "f86e_r1_common_policy_replay"


def _load(name):
    return json.loads((ARTIFACTS / name).read_text(encoding="utf-8"))


def test_common_tape_reuses_raw_uniforms_when_legal_counts_differ():
    tape = PolicyTape("A", 1234, (0.01, 0.24, 0.51, 0.99))
    legal_counts_left = [2, 7, 3, 10]
    legal_counts_right = [5, 2, 9, 4]
    assert [tape.uniform(index) for index in range(4)] == [
        tape.uniform(index) for index in range(4)
    ]
    assert [tape.choose_index(index, count) for index, count in enumerate(legal_counts_left)] == [
        0, 1, 1, 9
    ]
    assert [tape.choose_index(index, count) for index, count in enumerate(legal_counts_right)] == [
        0, 0, 4, 3
    ]


def test_f86e_r1_artifacts_account_for_controlled_replay():
    tapes = _load("policy_tapes.json")
    assert tapes["algorithm"] == "python_random_mt19937_random_floor_index_v1"
    assert tapes["length"] == 32
    assert set(tapes["samples"]) == {"V4-3", "V5-3"}
    assert all(set(sample) == {"A", "B"} for sample in tapes["samples"].values())
    assert all(len(policy["uniforms"]) == 32 for sample in tapes["samples"].values() for policy in sample.values())
    assert {sample: {policy: data["seed"] for policy, data in values.items()} for sample, values in tapes["samples"].items()} == {
        "V4-3": {"A": 8624301, "B": 8624302},
        "V5-3": {"A": 8625301, "B": 8625302},
    }

    results = _load("results.json")
    assert results["played_game_count"] == 16
    assert results["new_tactical_probe_compute"] == 0
    assert len(results["quality_games"]) == 16
    assert all(sum(row["cell"] == cell for row in results["quality_games"]) == 4 for cell in results["cell_names"])
    assert all(row["policy_tape_algorithm"] == tapes["algorithm"] for row in results["quality_games"])
    assert results["default_generator_changed"] is False
    assert results["no_ruleset_replacement"] is True
    assert results["no_seed_replacement"] is True
    assert results["f85_actual_compute"] == 0
