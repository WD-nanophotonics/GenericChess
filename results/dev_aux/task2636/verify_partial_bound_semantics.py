from __future__ import annotations

import json
import hashlib
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from results.dev_aux.task2625.analyze import bounds as task2625_bounds

PLAN_PATH = ROOT / "results/dev_aux/task2636/one-init-study-plan.json"
OUT_PATH = ROOT / "results/dev_aux/task2636/partial-bound-semantics.json"


def reward_range(state: str, reward: int | None = None) -> tuple[int, int]:
    if state == "ACTUAL_TERMINAL":
        if type(reward) is not int or reward not in (-1, 0, 1):
            raise ValueError("actual terminal must have a W/L/D reward")
        return reward, reward
    if state == "UNKNOWN":
        if reward is not None:
            raise ValueError("completed UNKNOWN cannot carry a W/L/D label")
        return -1, 1
    if state == "MISSING":
        if reward is not None:
            raise ValueError("missing slot cannot carry an outcome")
        return -1, 1
    raise ValueError("unrecognized evaluation endpoint state")


def difference_bounds(td: tuple[str, int | None], initial: tuple[str, int | None]) -> tuple[int, int]:
    td_low, td_high = reward_range(*td)
    initial_low, initial_high = reward_range(*initial)
    return td_low - initial_high, td_high - initial_low


def main() -> None:
    plan = json.loads(PLAN_PATH.read_text(encoding="utf-8"))
    if plan["evaluation"]["paired_root_color_contrasts"] != 512:
        raise AssertionError("predeclared finite denominator changed")
    cases = {
        "known_win_vs_missing": difference_bounds(("ACTUAL_TERMINAL", 1), ("MISSING", None)),
        "known_draw_vs_completed_unknown": difference_bounds(("ACTUAL_TERMINAL", 0), ("UNKNOWN", None)),
        "both_missing": difference_bounds(("MISSING", None), ("MISSING", None)),
        "unknown_vs_known_loss": difference_bounds(("UNKNOWN", None), ("ACTUAL_TERMINAL", -1)),
        "unknown_vs_missing": difference_bounds(("UNKNOWN", None), ("MISSING", None)),
    }
    expected = {
        "known_win_vs_missing": (0, 2),
        "known_draw_vs_completed_unknown": (-1, 1),
        "both_missing": (-2, 2),
        "unknown_vs_known_loss": (0, 2),
        "unknown_vs_missing": (-2, 2),
    }
    if cases != expected:
        raise AssertionError(f"completion bound cases changed: {cases}")
    if task2625_bounds(None, None) != (-2, 2) or task2625_bounds(1, None) != (0, 2) or task2625_bounds(0, -1) != (1, 1):
        raise AssertionError("task2625 finite completion-bound arithmetic changed")
    try:
        reward_range("UNKNOWN", 0)
    except ValueError:
        pass
    else:
        raise AssertionError("UNKNOWN was accidentally accepted as a draw")
    try:
        reward_range("MISSING", 0)
    except ValueError:
        pass
    else:
        raise AssertionError("missing slot was accidentally accepted as a draw")

    pair_count = plan["evaluation"]["paired_root_color_contrasts"]
    all_missing_sum = (-2 * pair_count, 2 * pair_count)
    result = {
        "status": "PASS_UNKNOWN_MISSING_AND_FINITE_DENOMINATOR_SEMANTICS",
        "plan_sha256": hashlib.sha256(PLAN_PATH.read_bytes()).hexdigest(),
        "verifier_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "predeclared_pairs": pair_count,
        "predeclared_slots": plan["evaluation"]["slots"],
        "cases": {key: list(value) for key, value in cases.items()},
        "completed_unknown_is_distinct_from_missing": True,
        "neither_state_is_a_draw": True,
        "both_remain_bounded_over": [-1, 1],
        "all_missing_total_difference_bounds": list(all_missing_sum),
        "all_missing_mean_difference_bounds": [all_missing_sum[0] / pair_count, all_missing_sum[1] / pair_count],
        "denominator_drops_missing_pairs": False,
        "training_or_evaluation_started": False,
    }
    OUT_PATH.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
