"""DEEPSEEK_AUX bounded addendum: value every excluded drop against the served root.

Pre-registered in plan_addendum.json. Exploratory; no utility claim.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import time
from pathlib import Path

from generic_chess.ai.limits import SearchLimits

HERE = Path(__file__).resolve().parent
ROOT = HERE.resolve().parents[1]
RESULTS = HERE / "results_stage2_fresh_seeds.json"
OUT = HERE / "results_addendum.json"
LOG = HERE / "plan-log-addendum.json"
MAX_SECONDS = 600.0
MATE_THRESHOLD = 900_000_000

spec = importlib.util.spec_from_file_location("probe_stage2", HERE / "probe_stage2.py")
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)
stage1 = probe.stage1


def main() -> int:
    started = time.monotonic()
    stored = json.loads(RESULTS.read_text(encoding="utf-8"))["positions"]
    rows, interrupted = [], False
    completed_seeds = []
    for position in stored:
        if time.monotonic() - started > MAX_SECONDS:
            interrupted = True
            break
        seed = position["seed"]
        compiled = stage1.generated_compiled(seed)
        state, offset = probe.sample_start2(compiled, seed)
        if state is None or offset != position["offset"]:
            raise RuntimeError(f"state reconstruction mismatch for seed {seed}")
        evaluator, profile = stage1.make_searcher(compiled)
        categories = stage1.drop_categories(state, compiled)
        child_by_key = {str(a): c for a, c in categories["successors"]}
        parent_static = evaluator.evaluate(state)
        parent_mate = (
            abs(position["d2_score"]) >= MATE_THRESHOLD
            or abs(position["d3_score"]) >= MATE_THRESHOLD
        )
        drop_rows = []
        for record in position["excluded_drop_records"]:
            key = record["action_key"]
            child = child_by_key[key]
            child_static_mover = -evaluator.evaluate(child)
            child_search = stage1.search(child, compiled, evaluator, 2)
            mover_value = -child_search["score"]
            drop_rows.append(
                {
                    "action_key": key,
                    "base_type": record["base_type"],
                    "blind_threats": record["blind_threats"],
                    "profitable_blind_threats": record["profitable_blind_threats"],
                    "static_mover_after_drop": child_static_mover,
                    "static_delta_vs_parent": child_static_mover - parent_static,
                    "child_d2_mover_value": mover_value,
                    "vs_parent_d2": mover_value - position["d2_score"],
                    "vs_parent_d3": mover_value - position["d3_score"],
                    "search_reason": child_search["reason"],
                    "nodes": child_search["nodes"],
                    "qnodes": child_search["qnodes"],
                    "seconds": child_search["seconds"],
                }
            )
        rows.append(
            {
                "seed": seed,
                "offset": offset,
                "parent_d2_score": position["d2_score"],
                "parent_d3_score": position["d3_score"],
                "parent_static": parent_static,
                "parent_mate_bound": parent_mate,
                "excluded_drops": len(drop_rows),
                "drops": drop_rows,
            }
        )
        completed_seeds.append(seed)
        print(
            seed,
            "drops",
            len(drop_rows),
            "best_vs_d3",
            max((d["vs_parent_d3"] for d in drop_rows), default=None),
            "best_vs_d2",
            max((d["vs_parent_d2"] for d in drop_rows), default=None),
            "elapsed",
            round(time.monotonic() - started, 1),
            flush=True,
        )

    all_drops = [
        {"seed": row["seed"], **drop}
        for row in rows
        for drop in row["drops"]
    ]
    non_mate = [d for d in all_drops if not _parent_mate(rows, d["seed"])]
    candidates = sorted(
        (d for d in non_mate if d["vs_parent_d3"] > 0),
        key=lambda d: d["vs_parent_d3"],
        reverse=True,
    )
    confirmations = []
    for candidate in candidates[:10]:
        if time.monotonic() - started > MAX_SECONDS:
            interrupted = True
            break
        seed = candidate["seed"]
        position = next(p for p in stored if p["seed"] == seed)
        compiled = stage1.generated_compiled(seed)
        state, _offset = probe.sample_start2(compiled, seed)
        evaluator, _profile = stage1.make_searcher(compiled)
        child = {
            str(a): c for a, c in stage1.drop_categories(state, compiled)["successors"]
        }[candidate["action_key"]]
        confirm_started = time.monotonic()
        confirm_stats = stage1.SearchStatistics()
        action, score, _pv, reason = stage1.run_root_search(
            child,
            compiled,
            evaluator,
            stage1.TranspositionTable(max_entries=200_000),
            SearchLimits(
                max_depth=3,
                max_nodes=200_000,
                quiescence_max_depth=4,
                quiescence_hard_max_depth=8,
            ),
            None,
            confirm_stats,
            use_tt=False,
            use_ordering=True,
        )
        confirmations.append(
            {
                "seed": seed,
                "action_key": candidate["action_key"],
                "child_d3_mover_value": -score,
                "vs_parent_d3": -score - position["d3_score"],
                "best_reply_action": None if action is None else str(action),
                "reason": reason,
                "seconds": round(time.monotonic() - confirm_started, 4),
                "nodes": confirm_stats.nodes,
                "qnodes": confirm_stats.qnodes,
            }
        )

    summary = {
        "positions_completed": len(rows),
        "positions_total": len(stored),
        "interrupted": interrupted,
        "completed_seeds": completed_seeds,
        "excluded_drops": len(all_drops),
        "non_mate_parents": sum(1 for r in rows if not r["parent_mate_bound"]),
        "mate_bound_parents": [r["seed"] for r in rows if r["parent_mate_bound"]],
        "depth_matched_above_parent_d3": len(candidates),
        "depth_matched_ties_parent_d3": sum(
            1 for d in non_mate if d["vs_parent_d3"] == 0
        ),
        "shallower_reference_above_parent_d2": sum(
            1 for d in non_mate if d["vs_parent_d2"] > 0
        ),
        "static_above_parent": sum(
            1 for d in non_mate if d["static_delta_vs_parent"] > 0
        ),
        "candidates_top": candidates[:10],
        "confirmations": confirmations,
        "search_seconds_total": round(
            sum(d["seconds"] for d in all_drops)
            + sum(c.get("seconds", 0) for c in confirmations),
            2,
        ),
    }
    payload = {
        "role": "DEEPSEEK_AUX",
        "session_id": stage1.SESSION_ID,
        "plan": "plan_addendum.json",
        "source_result": str(RESULTS),
        "summary": summary,
        "positions": rows,
        "nonclaims": [
            "exploratory addendum, not a confirmation of the stage-2 endpoint",
            "child values are search sensitivity, not utility or strength",
            "score differences may reflect ties, truncation or search noise",
            "one position per generated rule; not a population statement",
        ],
    }
    OUT.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    LOG.write_text(
        json.dumps(
            {
                "role": "DEEPSEEK_AUX",
                "session_id": stage1.SESSION_ID,
                "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "elapsed_seconds": round(time.monotonic() - started, 2),
                "git_head": subprocess.run(
                    ["git", "rev-parse", "HEAD"],
                    cwd=ROOT,
                    capture_output=True,
                    text=True,
                    check=True,
                ).stdout.strip(),
                "hashes": {
                    "plan_addendum.json": stage1.sha256_file(
                        HERE / "plan_addendum.json"
                    ),
                    "probe_addendum.py": stage1.sha256_file(Path(__file__)),
                    "results_stage2_fresh_seeds.json": stage1.sha256_file(RESULTS),
                    "check_qsearch_drop_exclusion.py": stage1.sha256_file(
                        HERE / "check_qsearch_drop_exclusion.py"
                    ),
                },
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2))
    return 0


def _parent_mate(rows: list[dict], seed: int) -> bool:
    return next(r for r in rows if r["seed"] == seed)["parent_mate_bound"]


if __name__ == "__main__":
    raise SystemExit(main())
