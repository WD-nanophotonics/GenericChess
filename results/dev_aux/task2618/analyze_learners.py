"""Exact finite-panel paired reward bounds; no population inference."""
from __future__ import annotations

from collections import defaultdict
import hashlib
import json
from pathlib import Path

from results.dev_aux.task2618.evaluate_learners import ENDPOINTS, finite_reward_bounds


ROOT = Path(__file__).resolve().parents[3]
RUN = ROOT / "results/dev_aux/task2618/learner-comparison-v1"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _key(slot: list) -> tuple[int, int, int]:
    seed_index, seed, family, color, _endpoint = slot
    return seed_index, family, color


def finite_panel_analysis(plan: dict, evaluation_rows: list[dict]) -> dict:
    slots = plan["evaluation"]["ordered_slots"]
    expected_slots = plan["evaluation"]["expected_slots"]
    if len(slots) != expected_slots or len(set(tuple(slot) for slot in slots)) != len(slots):
        raise ValueError("frozen evaluation slot list is incomplete or duplicated")
    slot_to_index = {tuple(slot): index for index, slot in enumerate(slots)}
    expected = set(slot_to_index)
    observed: dict[tuple, dict] = {}
    for row in evaluation_rows:
        index = row.get("slot_index")
        if not isinstance(index, int) or not 0 <= index < len(slots):
            raise ValueError("evaluation row has invalid slot index")
        slot = tuple(row.get("slot", ()))
        if slot != tuple(slots[index]) or slot in observed:
            raise ValueError("evaluation row does not match one unique frozen slot")
        seed_index, seed, family, color, endpoint = slot
        if endpoint not in ENDPOINTS or row.get("endpoint") != endpoint:
            raise ValueError("evaluation row endpoint differs from its frozen slot")
        if (row.get("seed_index"), row.get("seed"), row.get("family"),
                row.get("learner_color")) != (seed_index, seed, family, color):
            raise ValueError("evaluation row identity fields disagree with frozen slot")
        outcome = row.get("outcome_white_relative")
        bounds = finite_reward_bounds(outcome, color)
        if row.get("reward_bounds") != list(bounds):
            raise ValueError("evaluation reward bounds do not follow actual Chess/UNKNOWN policy")
        observed[slot] = {"bounds": bounds, "slot_index": index}

    if not set(observed).issubset(expected):
        raise ValueError("evaluation contains an unregistered slot")
    contrasts = []
    endpoint_pairs = [("initial", endpoint) for endpoint in ENDPOINTS[1:]]
    endpoint_pairs.extend((left, right) for i, left in enumerate(ENDPOINTS[1:])
                          for right in ENDPOINTS[i + 2:])
    grouping: dict[tuple, dict[str, tuple[int, int]]] = defaultdict(dict)
    for seed_index, seed, family, color, endpoint in slots:
        grouping[(seed_index, seed, family, color)][endpoint] = observed.get(
            (seed_index, seed, family, color, endpoint), {"bounds": (-1, 1)}
        )["bounds"]

    for left, right in endpoint_pairs:
        values = []
        by_seed: dict[int, list[tuple[int, int]]] = defaultdict(list)
        by_family: dict[int, list[tuple[int, int]]] = defaultdict(list)
        for (seed_index, _seed, family, _color), endpoints in grouping.items():
            left_bounds = endpoints[left]
            right_bounds = endpoints[right]
            difference = (left_bounds[0] - right_bounds[1],
                          left_bounds[1] - right_bounds[0])
            values.append(difference)
            by_seed[seed_index].append(difference)
            by_family[family].append(difference)
        if len(values) != expected_slots // len(ENDPOINTS):
            raise ValueError("paired contrast does not cover the complete planned slot denominator")

        def mean_bounds(items: list[tuple[int, int]]) -> list[float]:
            if not items:
                raise ValueError("empty finite-panel group")
            return [sum(pair[index] for pair in items) / len(items) for index in (0, 1)]

        family_bounds = [mean_bounds(items) for items in by_family.values()]
        seed_summary = {
            str(seed_index): {"matched_slots": len(items), "difference_bounds": mean_bounds(items)}
            for seed_index, items in sorted(by_seed.items())
        }
        contrasts.append({
            "left_minus_right": f"{left} - {right}",
            "matched_slots_planned": len(values),
            "observed_pair_slots": sum(
                (seed_index, seed, family, color, left) in observed
                and (seed_index, seed, family, color, right) in observed
                for seed_index, seed, family, color, _endpoint in slots
                if _endpoint == left
            ),
            "difference_bounds": mean_bounds(values),
            "per_seed_finite_panel": seed_summary,
            "per_family_cluster_bounds_minmax": {
                "lower": [min(item[0] for item in family_bounds), max(item[0] for item in family_bounds)],
                "upper": [min(item[1] for item in family_bounds), max(item[1] for item in family_bounds)],
            },
            "interpretation": "Exact bounds for this frozen finite panel only; UNKNOWN/missing outcomes remain [-1,+1]; no CI or population claim.",
        })
    return {
        "status": "FINITE_PANEL_BOUNDS_ONLY",
        "expected_slots": expected_slots,
        "observed_slots": len(observed),
        "missing_slots": expected_slots - len(observed),
        "unknown_is_draw": False,
        "population_inference": False,
        "contrasts": contrasts,
    }


def validate_evaluation_accounting(plan: dict, result: dict, rows: list[dict]) -> None:
    slots = plan["evaluation"]["ordered_slots"]
    seen = [row.get("slot_index") for row in rows]
    if result.get("expected_slots") != len(slots) or result.get("actual_slots") != len(rows):
        raise ValueError("evaluation result slot totals disagree with the frozen plan or rows")
    if len(set(seen)) != len(seen):
        raise ValueError("duplicate evaluation row slot index")
    missing = sorted(set(range(len(slots))) - set(seen))
    if result.get("missing_slots") != missing:
        raise ValueError("evaluation result missing-slot accounting disagrees with rows")
    status = result.get("status")
    if status not in {"COMPLETE", "PARTIAL_GLOBAL_CAP"}:
        raise ValueError("unexpected evaluation status")
    if status == "COMPLETE" and missing:
        raise ValueError("evaluation is marked complete with missing slots")
    if result.get("actual_terminal") != sum(row.get("outcome_white_relative") is not None for row in rows):
        raise ValueError("evaluation terminal count disagrees with outcome rows")
    if result.get("unknown") != sum(row.get("outcome_white_relative") is None for row in rows):
        raise ValueError("evaluation UNKNOWN count disagrees with outcome rows")
    if result.get("nodes") != sum(row.get("nodes", 0) for row in rows):
        raise ValueError("evaluation node total disagrees with game rows")
    if result.get("queries") != sum(row.get("searches", 0) for row in rows):
        raise ValueError("evaluation query total disagrees with game rows")


def analyze() -> dict:
    for name in ("plan.json", "training-result.json", "evaluation-result.json", "evaluation-games.jsonl"):
        if not (RUN / name).is_file():
            raise FileNotFoundError(f"evaluation artifact missing: {name}")
    output = RUN / "analysis.json"
    if output.exists():
        raise FileExistsError("analysis is write-once; refusing replacement")
    plan_raw = (RUN / "plan.json").read_bytes()
    plan = json.loads(plan_raw)
    result_raw = (RUN / "evaluation-result.json").read_bytes()
    evaluation_result = json.loads(result_raw)
    if evaluation_result.get("plan_sha256") != sha(plan_raw):
        raise ValueError("evaluation result is bound to another plan")
    rows = []
    for line in (RUN / "evaluation-games.jsonl").read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    validate_evaluation_accounting(plan, evaluation_result, rows)
    training_hash = sha((RUN / "training-result.json").read_bytes())
    if evaluation_result.get("training_result_sha256") != training_hash:
        raise ValueError("evaluation result is bound to another training artifact")
    result = finite_panel_analysis(plan, rows)
    if result["observed_slots"] != evaluation_result.get("actual_slots"):
        raise ValueError("evaluation result and game-row count differ")
    result.update({
        "plan_sha256": sha(plan_raw),
        "evaluation_result_sha256": sha(result_raw),
        "evaluation_games_sha256": sha((RUN / "evaluation-games.jsonl").read_bytes()),
    })
    with output.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n")
    return result


if __name__ == "__main__":
    print(json.dumps(analyze(), indent=2, sort_keys=True, allow_nan=False))
