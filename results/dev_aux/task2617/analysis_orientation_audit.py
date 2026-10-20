"""Post-run audit of task2617's displayed W/D/L perspective.

The registered analyzer's reward bounds already use learner perspective.
Its `actual_wdl` count table groups the unflipped outcome field, however,
which is the player-0 (White) result for this Chess task. This supplemental
audit preserves those artifacts and reports both orientations explicitly.
"""
from __future__ import annotations

from collections import Counter, defaultdict
import argparse
import hashlib
import json
from pathlib import Path


def summarize(games: list[dict], caps_by_family: dict[str, int]) -> dict:
    def empty_cell() -> dict:
        return {"player0_wdl": Counter(), "learner_wdl": Counter(), "unknown": 0}

    counts: dict[tuple[int, str], dict] = defaultdict(empty_cell)
    totals: Counter = Counter()
    for row in games:
        slot = row["slot"]
        if len(slot) != 6 or slot[0] != 0:
            raise ValueError(f"unexpected task2617 slot shape: {slot!r}")
        cap = int(caps_by_family[str(slot[2])])
        endpoint = slot[4]
        outcome = row["outcome"]
        color = slot[3]
        if color not in (0, 1) or outcome not in (None, -1, 0, 1):
            raise ValueError(f"invalid result/color: {outcome!r}/{color!r}")
        key = (cap, endpoint)
        if outcome is None:
            counts[key]["unknown"] += 1
            totals["unknown"] += 1
            continue
        counts[key]["player0_wdl"][outcome] += 1
        learner_result = outcome if color == 0 else -outcome
        counts[key]["learner_wdl"][learner_result] += 1
        totals["terminal"] += 1
    expected = {(20000, e) for e in ("initial", "TD", "WDL", "TreeStrap")} | {
        (40000, e) for e in ("initial", "TD", "WDL", "TreeStrap")
    }
    if set(counts) != expected:
        raise ValueError("observed cap/endpoint cells differ from the frozen design")
    if any(sum(counts[cell]["learner_wdl"].values()) + counts[cell]["unknown"] != 128 for cell in expected):
        raise ValueError("each cap/endpoint cell must contain exactly 128 registered slots")
    return {
        "task": "DEV_AUX2617",
        "status": "POST_RUN_ORIENTATION_AUDIT",
        "source_run": "run-002",
        "perspectives": {
            "player0_wdl": "Unflipped outcome; for this Chess task player 0 is White.",
            "learner_wdl": "Outcome flipped for color=1 (Black learner); matches the registered reward field.",
        },
        "registered_slots": len(games),
        "actual_terminal": totals["terminal"],
        "unknown_censored": totals["unknown"],
        "by_cap_endpoint": {
            f"{cap}/{endpoint}": {
                "n": 128,
                "player0_L_D_W": [counts[(cap, endpoint)]["player0_wdl"][-1], counts[(cap, endpoint)]["player0_wdl"][0], counts[(cap, endpoint)]["player0_wdl"][1]],
                "learner_L_D_W": [counts[(cap, endpoint)]["learner_wdl"][-1], counts[(cap, endpoint)]["learner_wdl"][0], counts[(cap, endpoint)]["learner_wdl"][1]],
                "unknown_censored": counts[(cap, endpoint)]["unknown"],
            }
            for cap, endpoint in sorted(expected)
        },
        "interpretation": (
            "The registered analyzer's reward bounds and endpoint-minus-initial bounds are already learner-perspective and unchanged. "
            "Its displayed Actual L/D/W counts are counts of the raw player-0 outcome, not learner-perspective counts; this supplement supplies both labels."
        ),
        "scope": "descriptive counts for the frozen randomized 32-family finite panel; no confidence interval or population claim",
    }


def render(report: dict) -> str:
    lines = [
        "# DEV_AUX task2617 outcome-orientation audit",
        "",
        "This post-run supplement does not alter the preregistration, frozen analyzer, original analysis, or evaluation outputs.",
        "The reward bounds were already calculated from learner-perspective rewards. Only the displayed `Actual L/D/W` counts in the original table used the unflipped outcome field.",
        "",
        "For this Chess adapter, player 0 is White and the terminal outcome is +1 for a White win, 0 for a draw, and -1 for a Black win. The slot color is the learner's color (0=White, 1=Black).",
        "",
        f"Observed rows: {report['registered_slots']}; actual terminals: {report['actual_terminal']}; censored UNKNOWN: {report['unknown_censored']}.",
        "",
        "| Cap | Endpoint | Player-0 L/D/W (original count perspective) | Learner L/D/W | UNKNOWN censored |",
        "|---:|---|---:|---:|---:|",
    ]
    for key, cell in report["by_cap_endpoint"].items():
        cap, endpoint = key.split("/", 1)
        p0 = "/".join(map(str, cell["player0_L_D_W"]))
        learner = "/".join(map(str, cell["learner_L_D_W"]))
        lines.append(f"| {cap} | {endpoint} | {p0} | {learner} | {cell['unknown_censored']}/128 |")
    lines.extend([
        "",
        "UNKNOWN slots are not counted as draws or learner outcomes. All rows remain in the fixed 128-slot denominator used by the finite-panel bounds.",
        "This is a descriptive finite-panel correction, not a confidence interval or population estimate.",
        "",
    ])
    return "\n".join(lines)


def file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def audit(directory: Path) -> dict:
    plan = json.loads((directory / "plan.json").read_text(encoding="utf-8"))
    rows = [json.loads(line) for line in (directory / "eval-games.jsonl").read_text(encoding="utf-8").splitlines() if line]
    summary = json.loads((directory / "eval-result.json").read_text(encoding="utf-8"))
    original = json.loads((directory / "analysis.json").read_text(encoding="utf-8"))
    if summary.get("status") != "COMPLETE" or len(rows) != summary.get("expected"):
        raise ValueError("run is not a complete frozen evaluation")
    for row in rows:
        outcome = row["outcome"]
        color = row["slot"][3]
        expected_reward = None if outcome is None else outcome * (1 if color == 0 else -1)
        if row["reward"] != expected_reward:
            raise ValueError("saved reward does not match learner-perspective outcome")
    report = summarize(rows, plan["caps_by_family"])
    if report["actual_terminal"] != summary["actual_terminal"] or report["unknown_censored"] != summary["unknown"]:
        raise ValueError("orientation aggregation disagrees with the immutable evaluator summary")
    for key, cell in report["by_cap_endpoint"].items():
        cap, endpoint = key.split("/", 1)
        frozen_counts = original["by_cap"][cap]["endpoints"][endpoint]["actual_wdl"]
        if cell["player0_L_D_W"] != [frozen_counts["loss"], frozen_counts["draw"], frozen_counts["win"]]:
            raise ValueError(f"raw count reproduction disagrees with original report: {key}")
    report["source_sha256"] = {
        name: file_sha(directory / name)
        for name in ("plan.json", "eval-result.json", "eval-games.jsonl", "analysis.json")
    }
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", type=Path, default=Path(__file__).parent / "run-002")
    args = parser.parse_args()
    report = audit(args.directory)
    (args.directory / "analysis-orientation-audit.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (args.directory / "analysis-orientation-audit.md").write_text(render(report), encoding="utf-8")
    print(json.dumps({"status": report["status"], "rows": report["registered_slots"], "terminal": report["actual_terminal"], "unknown": report["unknown_censored"]}, sort_keys=True))


if __name__ == "__main__":
    main()
