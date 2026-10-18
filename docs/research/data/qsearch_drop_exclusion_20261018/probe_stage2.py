"""Independent confirmatory panel, seeds 113-160.

Plan: ``plan_stage2.json`` (written before this run).  Stage 1 found that the
only two blind threats attacked pieces worth less than the dropped base type.
Stage 2 asks the materially refined question on fresh seeds and additionally
records whether the dropped piece is left en prise.  No product code changes.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import statistics
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.resolve().parents[1]

spec = importlib.util.spec_from_file_location(
    "qdrop_stage1", HERE / "check_qsearch_drop_exclusion.py"
)
stage1 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(stage1)

from generic_chess.ai.evaluation.config import MATE_THRESHOLD  # noqa: E402
from generic_chess.core.attacks import is_square_attacked  # noqa: E402
from generic_chess.core.movegen import legal_actions  # noqa: E402
from generic_chess.core.transition import initial_state, legal_successors  # noqa: E402

SEEDS = tuple(range(113, 161))
OUT = HERE / "results_stage2_fresh_seeds.json"
ANALYSIS_OUT = HERE / "stage2-analysis.json"
LOG = HERE / "plan-log2.json"
SOURCE_FILES = stage1.SOURCE_FILES


def sample_start2(compiled, seed: int):
    import random

    for offset in range(12):
        rng = random.Random(seed * 1009 + offset)
        state = initial_state(compiled)
        while state.ply_count < 80:
            if state.terminal_status.is_terminal:
                break
            if state.ply_count >= 10:
                actions = legal_actions(state, compiled)
                children = legal_successors(state, compiled)
                if (
                    len(actions) >= 6
                    and not any(child.terminal_status.is_terminal for _, child in children)
                ):
                    return state, offset
            children = legal_successors(state, compiled)
            if not children:
                break
            _, state = rng.choice(children)
    return None, None


def drop_square_status(child, action, side: int, compiled) -> dict:
    target = action.to_square
    return {
        "attacked_by_enemy": is_square_attacked(child.position, target, 1 - side, compiled),
        "defended_by_mover": is_square_attacked(child.position, target, side, compiled),
    }


def analyze_position2(seed, compiled, profile, evaluator, state, offset) -> dict:
    categories = stage1.drop_categories(state, compiled)
    side = state.position.side_to_move
    parent_static = evaluator.evaluate(state)
    excluded_records = []
    for record in categories["excluded"]:
        action = next(
            a for a, _c in categories["successors"] if str(a) == record["action_key"]
        )
        child = next(
            c for a, c in categories["successors"] if str(a) == record["action_key"]
        )
        threats = stage1.blind_threats(child, state, side, compiled, profile)
        undefended = [t for t in threats if not t["defended"]]
        drop_value = int(profile.board_value_by_type.get(record["base_type"], 0))
        profitable = [t for t in undefended if t["target_value"] > drop_value]
        confirmation = None
        if undefended:
            child_search = stage1.search(child, compiled, evaluator, 1)
            mover_score = -child_search["score"]
            confirmation = {
                "child_score_side_to_move": child_search["score"],
                "child_score_mover_perspective": mover_score,
                "parent_static": parent_static,
                "exceeds_parent_static": mover_score > parent_static,
                "reason": child_search["reason"],
                "nodes": child_search["nodes"],
                "qnodes": child_search["qnodes"],
                "seconds": child_search["seconds"],
            }
        excluded_records.append(
            {
                **record,
                "drop_value": drop_value,
                "new_enemy_attacks": len(threats),
                "blind_threats": len(undefended),
                "profitable_blind_threats": len(profitable),
                "profitable_records": [
                    {
                        "action": record["action_key"],
                        "base_type": record["base_type"],
                        "drop_square": [
                            action.to_square.file,
                            action.to_square.rank,
                        ],
                        "drop_value": drop_value,
                        "target_square": t["square"],
                        "target_type": t["target_type"],
                        "target_value": t["target_value"],
                        "value_gap": t["target_value"] - drop_value,
                        "drop_square_status": drop_square_status(
                            child, action, side, compiled
                        ),
                        "confirmation": confirmation,
                    }
                    for t in profitable
                ],
                "threats": threats,
                "max_blind_threat_value_gap": max(
                    (t["target_value"] - drop_value for t in undefended), default=None
                ),
                "drop_square": drop_square_status(child, action, side, compiled),
                "confirmation": confirmation,
            }
        )
    searches = {d: stage1.search(state, compiled, evaluator, d) for d in (2, 3)}
    secondary = stage1.search(state, compiled, evaluator, 4)
    d2, d3 = searches[2], searches[3]
    return {
        "seed": seed,
        "offset": offset,
        "ply": state.ply_count,
        "side_to_move": side,
        "ruleset_fingerprint": compiled.ruleset_fingerprint,
        "legal_actions": len(legal_actions(state, compiled)),
        "drops_total": categories["drops_total"],
        "excluded_drops": len(excluded_records),
        "checking_drops": len(categories["checking"]),
        "terminal_drops": len(categories["terminal"]),
        "classify_nonchecking_drop_excluded": categories[
            "classify_nonchecking_drop_excluded"
        ],
        "blind_threat_drops": sum(1 for r in excluded_records if r["blind_threats"]),
        "profitable_blind_threat_drops": sum(
            1 for r in excluded_records if r["profitable_blind_threats"]
        ),
        "excluded_drop_records": excluded_records,
        "checking_drop_records": categories["checking"],
        "terminal_drop_records": categories["terminal"],
        "searches": {str(d): s for d, s in searches.items()},
        "depth4_secondary": secondary,
        "d2_score": d2["score"],
        "d3_score": d3["score"],
        "d4_score": secondary["score"],
        "d2_action": d2["action"],
        "d3_action": d3["action"],
        "action_equal_2_3": d2["action_key"] == d3["action_key"],
        "abs_score_delta_2_3": abs(d3["score"] - d2["score"]),
        "search_reason_d2": d2["reason"],
        "search_reason_d3": d3["reason"],
        "mate_bound": abs(d2["score"]) >= MATE_THRESHOLD
        or abs(d3["score"]) >= MATE_THRESHOLD,
    }


def wilson_upper_one_sided(
    k: int, n: int, z: float = 1.6448536269514722
) -> float | None:
    if n == 0:
        return None
    p = k / n
    denominator = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denominator
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denominator
    return min(1.0, centre + half)


def evaluate_endpoints(positions: list[dict], excluded_total: int, profitable_total: int):
    eligible = [p for p in positions if not p["mate_bound"]]
    group = [p for p in eligible if p["blind_threat_drops"] > 0]
    rest = [p for p in eligible if p["blind_threat_drops"] == 0]
    group_median = statistics.median([p["abs_score_delta_2_3"] for p in group]) if group else None
    rest_median = statistics.median([p["abs_score_delta_2_3"] for p in rest]) if rest else None
    group_flips = sum(1 for p in group if not p["action_equal_2_3"])
    rest_flips = sum(1 for p in rest if not p["action_equal_2_3"])
    group_rate = group_flips / len(group) if group else None
    rest_rate = rest_flips / len(rest) if rest else None
    delta_ok = (
        group_median is not None
        and rest_median is not None
        and rest_median > 0
        and group_median >= 2 * rest_median
    )
    flip_ok = (
        group_rate is not None
        and rest_rate is not None
        and group_flips >= 3
        and group_rate >= 2 * rest_rate
    )
    horizon_supported = len(group) >= 3 and (delta_ok or flip_ok)
    if profitable_total == 0 and len(positions) >= 30:
        profitable_statement = "no material-winning hidden drop observed in this panel"
    elif profitable_total == 0:
        profitable_statement = "no material-winning hidden drop observed, but fewer than 30 eligible positions"
    else:
        profitable_statement = "profitable blind threats observed; inspect the listed positions"
    return {
        "eligible_non_mate_positions": len(eligible),
        "mate_bound_positions": [p["seed"] for p in positions if p["mate_bound"]],
        "profitable_blind_threats": profitable_total,
        "excluded_drops": excluded_total,
        "profitable_rate_per_excluded_drop": (
            profitable_total / excluded_total if excluded_total else None
        ),
        "profitable_rate_wilson95_upper": wilson_upper_one_sided(
            profitable_total, excluded_total
        ),
        "profitable_statement": profitable_statement,
        "blind_group_positions": len(group),
        "rest_positions": len(rest),
        "blind_group_median_abs_delta": group_median,
        "rest_median_abs_delta": rest_median,
        "blind_group_flips": group_flips,
        "rest_flips": rest_flips,
        "blind_group_flip_rate": group_rate,
        "rest_flip_rate": rest_rate,
        "delta_criterion": bool(delta_ok),
        "flip_criterion": bool(flip_ok),
        "supported": bool(horizon_supported),
        "outcome": (
            "support"
            if horizon_supported
            else ("inconclusive" if len(group) < 3 else "no_support")
        ),
        "criterion_source": "plan_stage2.json decision_rule_written_before_run",
    }


def main() -> int:
    if OUT.exists() and "--allow-overwrite" not in sys.argv[1:]:
        print(f"refusing to overwrite {OUT.name}", file=sys.stderr)
        return 2
    started = time.monotonic()
    imported_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.strip()
    positions, problems = [], []
    for seed in SEEDS:
        try:
            compiled = stage1.generated_compiled(seed)
            state, offset = sample_start2(compiled, seed)
            if state is None:
                problems.append(f"seed {seed}: no eligible start position in 12 offsets")
                continue
            evaluator, profile = stage1.make_searcher(compiled)
            record = analyze_position2(seed, compiled, profile, evaluator, state, offset)
            positions.append(record)
            print(
                seed,
                "ply",
                record["ply"],
                "excluded",
                record["excluded_drops"],
                "blind",
                record["blind_threat_drops"],
                "profitable",
                record["profitable_blind_threat_drops"],
                "delta",
                record["abs_score_delta_2_3"],
                flush=True,
            )
        except Exception as exc:
            problems.append(f"seed {seed}: {type(exc).__name__}: {exc}")
            print(f"seed {seed} FAILED {type(exc).__name__}: {exc}", flush=True)
    excluded_total = sum(p["excluded_drops"] for p in positions)
    profitable_total = sum(p["profitable_blind_threat_drops"] for p in positions)
    endpoints = evaluate_endpoints(positions, excluded_total, profitable_total)
    sampled = [p["seed"] for p in positions]
    missing_seeds = [s for s in SEEDS if s not in sampled]
    profitable_records = [
        {"seed": p["seed"], "offset": p["offset"], **r}
        for p in positions
        for rec in p["excluded_drop_records"]
        for r in rec["profitable_records"]
    ]
    aggregate = {
        "positions": len(positions),
        "sampled_seeds": sampled,
        "missing_seeds": missing_seeds,
        "excluded_drops": excluded_total,
        "profitable_records": profitable_records,
        "new_enemy_attack_drops": sum(
            r["new_enemy_attacks"] > 0
            for p in positions
            for r in p["excluded_drop_records"]
        ),
        "blind_threat_drops": sum(p["blind_threat_drops"] for p in positions),
        "profitable_blind_threat_drops": profitable_total,
        "checking_drops": sum(p["checking_drops"] for p in positions),
        "terminal_drops": sum(p["terminal_drops"] for p in positions),
        "classification_crosscheck_mismatches": [
            p["seed"]
            for p in positions
            if p["classify_nonchecking_drop_excluded"] != p["excluded_drops"]
        ],
        "blind_drop_square_attacked_undefended": sum(
            1
            for p in positions
            for r in p["excluded_drop_records"]
            if r["blind_threats"]
            and r["drop_square"]["attacked_by_enemy"]
            and not r["drop_square"]["defended_by_mover"]
        ),
        "blind_confirmations_above_parent_static": sum(
            1
            for p in positions
            for r in p["excluded_drop_records"]
            if r["confirmation"] and r["confirmation"]["exceeds_parent_static"]
        ),
        "action_flips_2_3": sum(1 for p in positions if not p["action_equal_2_3"]),
        "search_seconds_total": round(
            sum(
                s["seconds"]
                for p in positions
                for s in list(p["searches"].values()) + [p["depth4_secondary"]]
            )
            + sum(
                r["confirmation"]["seconds"]
                for p in positions
                for r in p["excluded_drop_records"]
                if r["confirmation"]
            ),
            2,
        ),
        "problems": problems,
    }
    payload = {
        "role": "DEEPSEEK_AUX",
        "session_id": stage1.SESSION_ID,
        "generated_at": imported_at,
        "source_result": "stage 1 seeds 101-112 in results_qsearch_drop_exclusion.json",
        "design": {
            "seeds": list(SEEDS),
            "board_size": 4,
            "setup_preset": "classic_like",
            "hand_weight": 0.9,
            "depths": [2, 3],
            "secondary_depth": 4,
            "node_cap": 20000,
            "quiescence_max_depth": 4,
            "quiescence_hard_max_depth": 8,
            "use_tt": False,
            "use_ordering": True,
            "start_offsets": 12,
        },
        "positions": positions,
        "aggregate": aggregate,
        "endpoints": endpoints,
        "nonclaims": [
            "search-horizon measurement only; no games and no strength/utility claim",
            "pseudo-attack geometry ignores pins, so undefended is approximate",
            "one position per generated rule; not a population statement",
            "no product code, default, cap or frozen-panel change",
        ],
    }
    OUT.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    ANALYSIS_OUT.write_text(
        json.dumps(
            {
                "role": "DEEPSEEK_AUX",
                "source": OUT.name,
                "aggregate": aggregate,
                "endpoints": endpoints,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    LOG.write_text(
        json.dumps(
            {
                "role": "DEEPSEEK_AUX",
                "session_id": stage1.SESSION_ID,
                "generated_at": imported_at,
                "git_head": head,
                "elapsed_seconds": round(time.monotonic() - started, 2),
                "hashes": {
                    str(p): stage1.sha256_file(ROOT / p) for p in SOURCE_FILES
                }
                | {
                    "plan_stage2.json": stage1.sha256_file(HERE / "plan_stage2.json"),
                    "probe_stage2.py": stage1.sha256_file(Path(__file__)),
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
    print(json.dumps({"aggregate": aggregate, "endpoints": endpoints}, indent=1))
    return 0 if not problems else 1


if __name__ == "__main__":
    raise SystemExit(main())
