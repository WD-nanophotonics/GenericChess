"""Independent rational finite-panel arithmetic and resource diagnostics.

All preregistered pairs, all roots, both cap strata and all seeds are retained.
No significance test, confidence interval, missing-outcome imputation or winner
selection is introduced. Requires the closed-run action/accounting audit first.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from fractions import Fraction
from itertools import combinations
import hashlib
import json
from pathlib import Path

from results.dev_aux.task2565.train import restore

ROOT = Path(__file__).resolve().parents[3]
RUN = ROOT / "results/dev_aux/task2620/run-002"
ENDPOINTS = ("initial", "TreeStrap", "TDLeaf", "WDL")


def bounds(row, color):
    if row is None or row["outcome_white_relative"] is None:
        return -1, 1
    outcome = row["outcome_white_relative"]
    if type(outcome) is not int or outcome not in (-1, 0, 1):
        raise ValueError("invalid rule outcome")
    reward = outcome if color == 0 else -outcome
    return reward, reward


def fraction_bounds(intervals):
    if not intervals:
        raise ValueError("empty finite panel")
    sums = [sum(row[i] for row in intervals) for i in (0, 1)]
    exact = [Fraction(value, len(intervals)) for value in sums]
    return dict(denominator=len(intervals), lower_sum=sums[0], upper_sum=sums[1],
                exact_bounds=[str(value) for value in exact],
                difference_bounds=[float(value) for value in exact])


def contrasts(plan, games):
    observed = {tuple(row["slot"]): row for row in games}
    if len(observed) != len(games):
        raise ValueError("duplicate game rows")
    blocks = sorted({tuple(slot[:4]) for slot in plan["evaluation"]["ordered_slots"]})
    result = []
    for left, right in combinations(ENDPOINTS, 2):
        intervals = []
        strata = defaultdict(list)
        masks = Counter()
        for block in blocks:
            _index, seed, family, color = block
            lr, rr = observed.get(block + (left,)), observed.get(block + (right,))
            lo, hi = bounds(lr, color), bounds(rr, color)
            difference = lo[0] - hi[1], lo[1] - hi[0]
            intervals.append(difference)
            strata[("seed", seed)].append(difference)
            strata[("cap", plan["evaluation"]["caps_by_family"][str(family)])].append(difference)
            strata[("root", family)].append(difference)
            lstatus = "missing" if lr is None else "unknown" if lr["outcome_white_relative"] is None else "terminal"
            rstatus = "missing" if rr is None else "unknown" if rr["outcome_white_relative"] is None else "terminal"
            masks[f"{lstatus}/{rstatus}"] += 1
        result.append(dict(left_minus_right=f"{left} - {right}",
                           **fraction_bounds(intervals), pair_status_counts=dict(masks),
                           per_seed={str(key): fraction_bounds(value) for (kind, key), value in strata.items() if kind == "seed"},
                           per_cap={str(key): fraction_bounds(value) for (kind, key), value in strata.items() if kind == "cap"},
                           per_root={str(key): fraction_bounds(value) for (kind, key), value in strata.items() if kind == "root"}))
    return result


def describe():
    output = RUN / "panel-description.json"
    if output.exists():
        raise FileExistsError("panel description is write-once")
    audited = json.loads((RUN / "independent-audit.json").read_text())
    plan_raw = (RUN / "plan.json").read_bytes()
    game_raw = (RUN / "evaluation-games.jsonl").read_bytes()
    if (audited["status"] != "PASS" or hashlib.sha256(plan_raw).hexdigest() != audited["plan_sha256"]
            or hashlib.sha256(game_raw).hexdigest() != audited["evaluation_games_sha256"]):
        raise ValueError("closed audit is not bound to this panel")
    plan = json.loads(plan_raw)
    games = [json.loads(line) for line in game_raw.splitlines() if line.strip()]
    calculated = contrasts(plan, games)
    shared = {row["left_minus_right"]: row for row in audited["finite_panel_contrasts"]}
    for row in calculated:
        other = shared[row["left_minus_right"]]
        if (row["difference_bounds"] != other["difference_bounds"]
                or row["denominator"] != other["matched_slots_planned"]):
            raise ValueError("independent rational arithmetic disagrees with pinned analysis")
    endings = defaultdict(Counter)
    totals = {endpoint: Counter() for endpoint in ENDPOINTS}
    last_queries = {}
    with (RUN / "evaluation-queries.jsonl").open(encoding="utf-8") as stream:
        for line in stream:
            q = json.loads(line)
            last_queries[q["slot_index"]] = q
    terminations = Counter()
    unknown_causes = defaultdict(Counter)
    for game in games:
        endpoint, cap = game["endpoint"], game["family_cap_nodes_both_sides"]
        totals[endpoint]["observed"] += 1
        totals[endpoint]["nodes_both_sides"] += game["nodes"]
        totals[endpoint]["queries"] += game["searches"]
        endings[(endpoint, cap)][game["ending"]] += 1
        if game["outcome_white_relative"] is None:
            totals[endpoint]["UNKNOWN"] += 1
            q = last_queries.get(game["slot_index"])
            if game["ending"] == "SEARCH_RESOURCE_UNKNOWN" and q:
                if q["nodes"] == q["effective_nodes"]:
                    reason = ("remaining_slot_nodes_exhausted" if q["effective_nodes"] < plan["evaluation"]["nodes_per_search"]
                              else "per_query_node_limit_reached")
                else:
                    reason = "resource_stop_before_node_limit"
            else:
                reason = game["ending"]
            unknown_causes[(endpoint, cap)][reason] += 1
        else:
            reward = game["learner_reward"]
            totals[endpoint]["win" if reward == 1 else "loss" if reward == -1 else "draw"] += 1
            env = restore(0, None, game["final_record"])
            terminations[env.board.outcome(claim_draw=True).termination.name] += 1
    for endpoint in ENDPOINTS:
        totals[endpoint]["missing"] = plan["evaluation"]["expected_slots"] // 4 - totals[endpoint]["observed"]
    result = dict(status="RATIONAL_ARITHMETIC_MATCH", plan_sha256=hashlib.sha256(plan_raw).hexdigest(),
                  game_sha256=hashlib.sha256(game_raw).hexdigest(), contrasts=calculated,
                  absolute_learner_relative_outcomes_and_costs={key: dict(value) for key, value in totals.items()},
                  terminal_authority_counts=dict(terminations),
                  ending_counts_by_endpoint_cap={f"{key[0]}:{key[1]}": dict(value) for key, value in endings.items()},
                  unknown_resource_diagnostics_by_endpoint_cap={f"{key[0]}:{key[1]}": dict(value) for key, value in unknown_causes.items()},
                  limits=["All counts and bounds describe the complete fixed finite panel, not a population confidence interval.",
                          "Budget strata use distinct preregistered roots, so their difference is not a within-root causal effect of extra nodes.",
                          "All games use the predeclared available-draw-claim policy, including legal intended-move claims.",
                          "No censored outcome is converted to a point reward; all missing slots remain in the denominator."])
    with output.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return result


if __name__ == "__main__":
    result = describe()
    print(json.dumps({key: value for key, value in result.items() if key != "contrasts"}, indent=2))
