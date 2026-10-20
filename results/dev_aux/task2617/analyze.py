"""Audit and bound the finite task2617 family-randomized cap comparison."""
from __future__ import annotations

from collections import Counter, defaultdict
import argparse
import hashlib
import json
from pathlib import Path

from results.dev_aux.task2617.evaluate import terminal_reward, validate_slots


TASK = Path(__file__).resolve().parent
ROOT = Path.cwd()


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    with path.open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, 1):
            if not line.strip():
                raise ValueError(f"blank JSONL row: {path}:{line_number}")
            rows.append(json.loads(line))
    return rows


def reward_interval(outcome: int | None, color: int) -> tuple[int, int, bool]:
    reward = terminal_reward(outcome, color)
    return (-1, 1, True) if reward is None else (reward, reward, False)


def file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def mean_bounds(intervals: list[tuple[int, int, bool]]) -> dict:
    if not intervals:
        raise ValueError("mean requires a nonempty registered set")
    low = sum(item[0] for item in intervals) / len(intervals)
    high = sum(item[1] for item in intervals) / len(intervals)
    return {
        "n": len(intervals),
        "lower": low,
        "upper": high,
        "censored": sum(item[2] for item in intervals),
        "censored_fraction": sum(item[2] for item in intervals) / len(intervals),
    }


def difference_bounds(a: dict, b: dict) -> dict:
    return {
        "n": min(a["n"], b["n"]),
        "lower": a["lower"] - b["upper"],
        "upper": a["upper"] - b["lower"],
    }


def analyze_data(plan: dict, eval_plan: dict, games: list[dict], queries: list[dict], eval_summary: dict | None = None) -> dict:
    slots = eval_plan["slots"]
    validate_slots(slots, plan, eval_plan)
    slot_by_key = {tuple(slot): slot for slot in slots}
    family_caps = plan["caps_by_family"]
    game_by_key = {}
    game_order = []
    for row in games:
        key = tuple(row["slot"])
        if key not in slot_by_key:
            raise ValueError(f"game row has unregistered slot: {key}")
        if key in game_by_key:
            raise ValueError(f"duplicate game row: {key}")
        family = row["slot"][2]
        if row["family_cap_nodes_both_sides"] != int(family_caps[str(family)]):
            raise ValueError(f"game row cap differs from registered family assignment: {key}")
        outcome = row["outcome"]
        if outcome not in (None, -1, 0, 1):
            raise ValueError(f"invalid actual W/D/L value for {key}: {outcome}")
        if row["reward"] != terminal_reward(outcome, row["slot"][3]):
            raise ValueError(f"game reward does not match actual terminal result: {key}")
        if (outcome is not None) != (row["ending"] == "ACTUAL_TERMINAL"):
            raise ValueError(f"game terminal flag disagrees with its recorded ending: {key}")
        game_by_key[key] = row
        game_order.append(key)

    # A stopped/capped runner can only have emitted a prefix of its frozen order.
    expected_order = [tuple(slot) for slot in slots]
    if game_order != expected_order[: len(game_order)]:
        raise ValueError("game rows are not an ordered prefix of the registered execution slots")

    query_nodes: Counter = Counter()
    query_counts: Counter = Counter()
    for row in queries:
        key = tuple(row["slot"])
        if key not in slot_by_key:
            raise ValueError(f"query row has unregistered slot: {key}")
        family = row["slot"][2]
        cap = int(family_caps[str(family)])
        if row["family_cap_nodes_both_sides"] != cap:
            raise ValueError(f"query row cap differs from registered family assignment: {key}")
        paid = row["nodes"]
        if type(paid) is not int or paid < 0 or paid > row["effective_nodes"]:
            raise ValueError(f"invalid paid-node receipt for {key}")
        if row["effective_nodes"] < 1 or row["effective_nodes"] > 8192:
            raise ValueError(f"query exceeded its registered per-query node budget: {key}")
        query_nodes[key] += paid
        query_counts[key] += 1
        if query_nodes[key] > cap:
            raise ValueError(f"combined actor nodes exceed registered family cap: {key}")
    for key, row in game_by_key.items():
        if row["nodes"] != query_nodes[key] or row["queries"] != query_counts[key]:
            raise ValueError(f"game summary does not match paid query receipts: {key}")
    if eval_summary is not None:
        missing = [slot for slot in slots if tuple(slot) not in game_by_key]
        actual_terminal = sum(row["outcome"] is not None for row in games)
        unknown = len(games) - actual_terminal
        if (
            eval_summary.get("expected") != len(slots)
            or eval_summary.get("actual") != len(games)
            or eval_summary.get("missing") != len(missing)
            or eval_summary.get("missing_slots") != missing
            or eval_summary.get("actual_terminal") != actual_terminal
            or eval_summary.get("unknown") != unknown
            or eval_summary.get("nodes") != sum(query_nodes.values())
            or eval_summary.get("queries") != len(queries)
        ):
            raise ValueError("run summary disagrees with game/query evidence")
        if eval_summary.get("status") == "COMPLETE" and missing:
            raise ValueError("COMPLETE evaluation summary has missing game slots")
        if set(query_nodes).difference(game_by_key):
            raise ValueError("query receipts exist without a game summary despite a run summary")

    actual_rows = {key: game_by_key.get(key) for key in slot_by_key}
    outcome_counts = defaultdict(Counter)
    endpoint_intervals: dict[tuple[int, str], list[tuple[int, int, bool]]] = defaultdict(list)
    pair_intervals: dict[tuple[int, str], list[tuple[int, int, bool]]] = defaultdict(list)
    paired_censored = Counter()

    for slot in slots:
        rule, seed, family, color, endpoint, _foe = slot
        cap = int(family_caps[str(family)])
        row = actual_rows[tuple(slot)]
        outcome = None if row is None else row["outcome"]
        interval = reward_interval(outcome, color)
        endpoint_intervals[(cap, endpoint)].append(interval)
        outcome_counts[(cap, endpoint)]["unknown" if outcome is None else str(outcome)] += 1

    # Matched endpoint-vs-initial contrasts within each family/seed/color cell.
    for slot in slots:
        rule, seed, family, color, endpoint, _foe = slot
        if endpoint == "initial":
            continue
        cap = int(family_caps[str(family)])
        initial_key = (rule, seed, family, color, "initial", _foe)
        endpoint_key = tuple(slot)
        initial_row = actual_rows[initial_key]
        endpoint_row = actual_rows[endpoint_key]
        initial_interval = reward_interval(None if initial_row is None else initial_row["outcome"], color)
        endpoint_interval = reward_interval(None if endpoint_row is None else endpoint_row["outcome"], color)
        diff = (
            endpoint_interval[0] - initial_interval[1],
            endpoint_interval[1] - initial_interval[0],
            endpoint_interval[2] or initial_interval[2],
        )
        pair_intervals[(cap, endpoint)].append(diff)
        paired_censored[(cap, endpoint)] += diff[2]

    by_cap = {}
    for cap in (20000, 40000):
        endpoint_results = {}
        for endpoint in eval_plan["endpoints"]:
            result = mean_bounds(endpoint_intervals[(cap, endpoint)])
            result["actual_wdl"] = {
                "loss": outcome_counts[(cap, endpoint)]["-1"],
                "draw": outcome_counts[(cap, endpoint)]["0"],
                "win": outcome_counts[(cap, endpoint)]["1"],
                "censored_unknown_or_missing": outcome_counts[(cap, endpoint)]["unknown"],
            }
            endpoint_results[endpoint] = result
        contrasts = {
            endpoint: mean_bounds(pair_intervals[(cap, endpoint)])
            for endpoint in eval_plan["endpoints"] if endpoint != "initial"
        }
        for endpoint, result in contrasts.items():
            result["censored_pairs"] = paired_censored[(cap, endpoint)]
        by_cap[str(cap)] = {"endpoints": endpoint_results, "endpoint_minus_initial": contrasts}

    cap_effects = {}
    for endpoint in eval_plan["endpoints"]:
        high = by_cap["40000"]["endpoints"][endpoint]
        low = by_cap["20000"]["endpoints"][endpoint]
        cap_effects[endpoint] = difference_bounds(high, low)
    contrast_cap_effects = {}
    for endpoint in eval_plan["endpoints"]:
        if endpoint == "initial":
            continue
        high = by_cap["40000"]["endpoint_minus_initial"][endpoint]
        low = by_cap["20000"]["endpoint_minus_initial"][endpoint]
        contrast_cap_effects[endpoint] = difference_bounds(high, low)

    return {
        "task": "DEV_AUX2617",
        "status": "FINITE_PANEL_BOUNDS",
        "registered_slots": len(slots),
        "observed_game_rows": len(games),
        "missing_game_rows": len(slots) - len(games),
        "observed_query_rows": len(queries),
        "paid_nodes_from_query_receipts": sum(query_nodes.values()),
        "all_observed_slots_respect_family_both_actor_caps": True,
        "run_summary_present": eval_summary is not None,
        "run_summary": eval_summary,
        "by_cap": by_cap,
        "cap_40000_minus_20000_endpoint_reward_bounds": cap_effects,
        "cap_effect_on_endpoint_minus_initial_bounds": contrast_cap_effects,
        "scope": "finite randomized 32-family panel; bounds vary only actual UNKNOWN/missing outcomes over [-1,+1]; no confidence interval or population claim",
        "unknown_is_draw": False,
    }


def render_markdown(report: dict) -> str:
    lines = [
        "# DEV_AUX task2617 finite-panel cap analysis",
        "",
        "This report is descriptive for the frozen randomized 32-family panel. It is not a confidence interval or a population claim. UNKNOWN and missing slots remain censored; only actual terminal W/D/L is scored.",
        "",
        f"Observed game rows: {report['observed_game_rows']}/{report['registered_slots']}; missing: {report['missing_game_rows']}; paid nodes from query receipts: {report['paid_nodes_from_query_receipts']:,}.",
        "",
        "## Endpoint reward bounds by assigned cap",
        "",
        "| Cap | Endpoint | Lower | Upper | Censored | Actual L/D/W |",
        "|---:|---|---:|---:|---:|---|",
    ]
    for cap, section in report["by_cap"].items():
        for endpoint, values in section["endpoints"].items():
            wdl = values["actual_wdl"]
            lines.append(
                f"| {cap} | {endpoint} | {values['lower']:.6f} | {values['upper']:.6f} | {values['censored']}/{values['n']} | {wdl['loss']}/{wdl['draw']}/{wdl['win']} |"
            )
    lines.extend(["", "## Endpoint-minus-initial paired bounds", "", "| Cap | Endpoint | Lower | Upper | Censored pairs |", "|---:|---|---:|---:|---:|"])
    for cap, section in report["by_cap"].items():
        for endpoint, values in section["endpoint_minus_initial"].items():
            lines.append(f"| {cap} | {endpoint} | {values['lower']:.6f} | {values['upper']:.6f} | {values['censored_pairs']}/{values['n']} |")
    lines.extend(["", "## 40k minus 20k finite-panel bounds", "", "No interval below is a statistical confidence interval.", "", "| Quantity | Lower | Upper |", "|---|---:|---:|"])
    for endpoint, values in report["cap_40000_minus_20000_endpoint_reward_bounds"].items():
        lines.append(f"| {endpoint} mean reward | {values['lower']:.6f} | {values['upper']:.6f} |")
    for endpoint, values in report["cap_effect_on_endpoint_minus_initial_bounds"].items():
        lines.append(f"| {endpoint} minus initial contrast | {values['lower']:.6f} | {values['upper']:.6f} |")
    lines.append("")
    return "\n".join(lines)


def analyze(directory: str | Path | None = None) -> dict:
    d = TASK / "run-002" if directory is None else Path(directory)
    if not d.is_absolute():
        d = ROOT / d
    if not (d / "eval-started.json").exists():
        raise FileNotFoundError("task2617 has no started evaluation; refusing to analyze")
    required = (
        d / "plan.json", d / "eval-plan.json", d / "registration.json",
        d / "runner-registration.json", d / "model-binding.json", d / "root-manifest.json",
        d / "eval-binding.json",
    )
    if not all(path.exists() for path in required):
        raise FileNotFoundError("task2617 started run is missing a registered binding")
    reg = json.loads((d / "registration.json").read_text(encoding="utf-8"))
    runreg = json.loads((d / "runner-registration.json").read_text(encoding="utf-8"))
    model_binding = json.loads((d / "model-binding.json").read_text(encoding="utf-8"))
    bindings = json.loads((d / "eval-binding.json").read_text(encoding="utf-8"))
    started = json.loads((d / "eval-started.json").read_text(encoding="utf-8"))
    if reg.get("attempt_id") != d.name:
        raise RuntimeError("attempt identifier does not match the selected immutable run directory")
    if started != bindings:
        raise RuntimeError("evaluation-start and binding receipts differ")
    for name, field in (
        ("plan.json", "plan_sha256"),
        ("eval-plan.json", "eval_plan_sha256"),
        ("root-manifest.json", "root_manifest_sha256"),
        ("runner-registration.json", "runner_registration_sha256"),
        ("model-binding.json", "model_binding_sha256"),
    ):
        if file_sha(d / name) != reg[field]:
            raise RuntimeError(f"registered artifact changed: {name}")
    if bindings.get("plan_sha256") != reg["eval_plan_sha256"]:
        raise RuntimeError("started run is bound to a different evaluation plan")
    if bindings.get("registration_sha256") != file_sha(d / "registration.json"):
        raise RuntimeError("started run registration receipt changed")
    if bindings.get("root_manifest_sha256") != reg["root_manifest_sha256"]:
        raise RuntimeError("started run root manifest differs from preregistration")
    if bindings.get("runtime_pins") != runreg["runtime_pins"]:
        raise RuntimeError("started run source pins differ from preregistration")
    if bindings.get("model_binding_sha256") != reg["model_binding_sha256"]:
        raise RuntimeError("started run model binding differs from preregistration")
    if model_binding["task2616_result_sha256"] != file_sha(ROOT / "results/dev_aux/task2616/result.json"):
        raise RuntimeError("task2616 endpoint model source changed before analysis")
    if model_binding["tree_training_result_sha256"] != file_sha(ROOT / "results/dev_aux/task2616/tree-training-result.json"):
        raise RuntimeError("task2616 TreeStrap source changed before analysis")
    for name, expected in runreg["runtime_pins"].items():
        if file_sha(ROOT / name) != expected:
            raise RuntimeError(f"runtime source changed before analysis: {name}")
    plan = json.loads((d / "plan.json").read_text(encoding="utf-8"))
    eval_plan = json.loads((d / "eval-plan.json").read_text(encoding="utf-8"))
    games = read_jsonl(d / "eval-games.jsonl")
    queries = read_jsonl(d / "eval-queries.jsonl")
    summary_path = d / "eval-result.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8")) if summary_path.exists() else None
    report = analyze_data(plan, eval_plan, games, queries, summary)
    json_path = d / "analysis.json"
    md_path = d / "analysis.md"
    with json_path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(report, indent=2, sort_keys=True) + "\n")
    with md_path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(render_markdown(report))
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, default=TASK / "run-002")
    args = parser.parse_args()
    print(json.dumps(analyze(args.directory), indent=2, sort_keys=True))
