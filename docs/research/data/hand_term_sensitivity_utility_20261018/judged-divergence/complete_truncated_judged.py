"""Complete the 31 previously truncated judged-divergence evaluations.

DEEPSEEK_AUX private probe, segment 78213c35-4252-44bb-8c11-acb79a5005e7.
Plan written before this run: ``plan-complete-truncated-judged.json``.

The recorded hand-blind depth-4 judge (20k nodes, q 4/hard 8) reported a
truncation reason for at least one candidate in 31 of its 45 judged cells, so
the served-vs-blind direction rests on 14 completed cells.  This script reruns
*only* those 31 cells:

  primary    the same judge definition, with the node cap escalated
             20k -> 40k -> 80k -> 160k per candidate until ``completed_depth``
             is reported.  The 20k rung must reproduce the saved score, reason,
             nodes and qnodes; a mismatch flags the cell as instrument_unstable.
  secondary  a clearly different instrument (q hard depth 16, node cap 80k)
             applied only to candidates still truncated after the ladder.  It
             tests whether the remaining truncation is the fixed 8-ply hard
             check cutoff.  Its verdicts are never pooled with the primary ones.

Guards: no overwrite, fixed search/time budgets, no p-values, no product code.
"""

from __future__ import annotations

import hashlib
import json
import sys
import time
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import check_judged_divergence as cgd  # noqa: E402

PRIMARY_RESULTS = HERE / "results_judged_divergence.json"
STRATA_RESULTS = HERE / "results_judged_divergence_strata.json"
DISTINCT_RESULTS = HERE / "results_judged_divergence_distinct_strata.json"
OUT = HERE / "results_complete_truncated_judged.json"

WEIGHT = 0.0
LADDER = [20_000, 40_000, 80_000, 160_000]
ORACLE_BASE = dict(max_depth=4, quiescence_max_depth=4,
                   quiescence_hard_max_depth=8)
SECONDARY = dict(max_depth=4, max_nodes=80_000, quiescence_max_depth=4,
                 quiescence_hard_max_depth=16)
PRIMARY_MAX_SEARCHES = 400
PRIMARY_MAX_SECONDS = 900.0
SECONDARY_MAX_SEARCHES = 100
SECONDARY_MAX_SECONDS = 600.0
EXPECTED_PATTERN = {
    ("one_truncated", 2): 8,
    ("one_truncated", 3): 9,
    ("both_truncated", 2): 8,
    ("both_truncated", 3): 6,
}


def sha_prefix(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:8].upper()


def stratum(record: dict) -> str:
    reasons = (record["oracle"]["blind"]["reason"],
               record["oracle"]["served"]["reason"])
    done = [reason == "completed_depth" for reason in reasons]
    if all(done):
        return "both_completed"
    if not any(done):
        return "both_truncated"
    return "one_truncated"


def majority(counter: Counter) -> str:
    served = counter.get("served_better", 0)
    blind = counter.get("blind_better", 0)
    if served > blind:
        return "served_better"
    if blind > served:
        return "blind_better"
    return "mixed"


def verdict_of(delta: int) -> str:
    return ("served_better" if delta > 0
            else "blind_better" if delta < 0 else "tie")


def ladder_search(state, compiled, evaluator, arm: str, seed: int, depth: int,
                  budget) -> tuple[dict, list[dict]]:
    """Run the same judge definition at increasing node caps until complete."""
    limits = dict(ORACLE_BASE)
    rungs: list[dict] = []
    final: dict | None = None
    for cap in LADDER:
        limits["max_nodes"] = cap
        step = cgd.run_search(state, compiled, evaluator, limits, budget,
                              f"ladder seed{seed} d{depth} {arm} n{cap}")
        final = dict(max_nodes=cap, score=step["score"],
                     reason=step["reason"], nodes=step["nodes"],
                     qnodes=step["qnodes"],
                     node_cap_hit=step["node_cap_hit"])
        rungs.append(final)
        if step["reason"] == "completed_depth":
            break
    return final, rungs


def rebuild_divergence(compiled, seed: int, depth: int, both: list[dict],
                       budget) -> dict:
    """Replay the saved shared prefix with the recorded arm configs."""
    games = sorted(both, key=lambda g: g["served_side"])
    g0 = games[0]
    start = cgd.sample_start(compiled, seed)
    if start is None or start.ply_count != g0["start_ply"]:
        return dict(ok=False, why="start_mismatch")
    searchers = {"served": cgd.make_searcher(compiled, 0.9),
                 "blind": cgd.make_searcher(compiled, 0.0)}
    state = start
    index = cgd.first_diff(g0["moves"], games[1]["moves"])
    if index is None:
        return dict(ok=False, why="no_divergence")
    for ply in range(index):
        arm = cgd.arms_of(g0)[state.position.side_to_move]
        step = cgd.run_search(state, compiled, searchers[arm],
                              cgd.arm_limits(depth), budget,
                              f"prefix seed{seed} d{depth} ply{ply}")
        if step["action_text"] != g0["moves"][ply]:
            return dict(ok=False, why="prefix_mismatch", ply=ply,
                        expected=g0["moves"][ply], got=step["action_text"])
        state = cgd.apply_action(state, step["action"], compiled)
    side = state.position.side_to_move
    candidates = {}
    for arm in ("served", "blind"):
        candidates[arm] = cgd.run_search(
            state, compiled, searchers[arm], cgd.arm_limits(depth), budget,
            f"candidate seed{seed} d{depth} {arm}")
    expectations = {cgd.arms_of(game)[side]: game["moves"][index]
                    for game in games}
    for arm, text in expectations.items():
        if candidates[arm]["action_text"] != text:
            return dict(ok=False, why="candidate_mismatch", arm=arm,
                        expected=text, got=candidates[arm]["action_text"])
    return dict(ok=True, state=state, candidates=candidates, index=index)


def cell_completion(compiled, record: dict, both: list[dict], budget) -> dict:
    seed, depth = record["seed"], record["depth"]
    out = dict(seed=seed, depth=depth, pair_kind=record["pair_kind"],
               first_diff_ply=record["first_diff_ply"],
               recorded_verdict=record["verdict"],
               recorded_stratum=stratum(record),
               recorded_tie_break=bool(record.get("tie_break")),
               recorded_oracle={arm: {k: record["oracle"][arm][k]
                                     for k in ("reason", "score_for_mover",
                                               "nodes", "qnodes")}
                                for arm in ("served", "blind")})
    rebuilt = rebuild_divergence(compiled, seed, depth, both, budget)
    if not rebuilt.get("ok"):
        out["status"] = "rebuild_failed"
        out["failure"] = {k: v for k, v in rebuilt.items() if k != "state"}
        return out
    state = rebuilt["state"]
    out["divergence_side"] = state.position.side_to_move
    out["saved_moves_at_divergence"] = {
        arm: rebuilt["candidates"][arm]["action_text"]
        for arm in ("served", "blind")}
    oracle = cgd.make_searcher(compiled, WEIGHT)
    arms: dict[str, dict] = {}
    unstable = False
    for arm in ("served", "blind"):
        child = cgd.apply_action(state, rebuilt["candidates"][arm]["action"],
                                 compiled)
        if child.terminal_status.is_terminal:
            arms[arm] = dict(terminal=True,
                             status=child.terminal_status.status.value,
                             winner=child.terminal_status.winner)
            continue
        final, rungs = ladder_search(child, compiled, oracle, arm, seed, depth,
                                     budget)
        saved = record["oracle"][arm]
        reproduced = (rungs[0]["score"] == -saved["score_for_mover"]
                      and rungs[0]["reason"] == saved["reason"]
                      and rungs[0]["nodes"] == saved["nodes"]
                      and rungs[0]["qnodes"] == saved["qnodes"])
        if not reproduced:
            unstable = True
        arms[arm] = dict(
            terminal=False, rungs=rungs,
            completed_rung=next((i + 1 for i, rung in enumerate(rungs)
                                 if rung["reason"] == "completed_depth"), None),
            final_reason=final["reason"],
            final_score_for_mover=-final["score"],
            reproduced_20k=reproduced,
            reproduction_expected=dict(
                score_for_mover=saved["score_for_mover"],
                reason=saved["reason"], nodes=saved["nodes"],
                qnodes=saved["qnodes"]))
    out["arms"] = arms
    out["instrument_unstable"] = unstable
    non_terminal = all(arms[arm].get("terminal") is False
                       for arm in ("served", "blind"))
    both_done = non_terminal and all(
        arms[arm]["final_reason"] == "completed_depth"
        for arm in ("served", "blind"))
    if both_done:
        delta = (arms["served"]["final_score_for_mover"]
                 - arms["blind"]["final_score_for_mover"])
        out["status"] = "newly_completed"
        out["delta"] = delta
        out["verdict"] = verdict_of(delta)
        out["recorded_sign_agrees"] = verdict_of(delta) == record["verdict"]
    elif non_terminal:
        out["status"] = "still_truncated"
    else:
        out["status"] = "terminal_child"
    out["_state"] = (state, rebuilt["candidates"])
    return out


def secondary_phase(cell: dict, budget) -> None:
    """Different instrument for candidates still truncated after the ladder."""
    state, candidates = cell["_state"]
    compiled = cell["_compiled"]
    for arm in ("served", "blind"):
        block = cell["arms"].get(arm)
        if not block or block.get("terminal") is not False:
            continue
        if block["final_reason"] == "completed_depth":
            continue
        child = cgd.apply_action(state, candidates[arm]["action"], compiled)
        if child.terminal_status.is_terminal:
            continue
        oracle = cgd.make_searcher(compiled, WEIGHT)
        step = cgd.run_search(child, compiled, oracle, SECONDARY, budget,
                              f"secondary seed{cell['seed']} "
                              f"d{cell['depth']} {arm}")
        block["secondary"] = dict(
            score_for_mover=-step["score"], reason=step["reason"],
            nodes=step["nodes"], qnodes=step["qnodes"],
            node_cap_hit=step["node_cap_hit"])


def main() -> int:
    if OUT.exists():
        print(f"refusing to overwrite existing result {OUT}", file=sys.stderr)
        return 2

    primary = json.loads(PRIMARY_RESULTS.read_text(encoding="utf-8"))
    inputs = {"results_judged_divergence.json": sha_prefix(PRIMARY_RESULTS),
              "results_judged_divergence_strata.json": sha_prefix(STRATA_RESULTS),
              "results_judged_divergence_distinct_strata.json":
                  sha_prefix(DISTINCT_RESULTS)}
    judged = [r for r in primary["records"] if r["status"] == "judged"]
    if len(judged) != 45:
        raise SystemExit(f"expected 45 judged cells, found {len(judged)}")
    truncated = [r for r in judged if stratum(r) != "both_completed"]
    pattern = Counter((stratum(r), r["depth"]) for r in truncated)
    if dict(pattern) != EXPECTED_PATTERN:
        raise SystemExit(f"expected pattern {EXPECTED_PATTERN}, "
                         f"found {dict(pattern)}")

    started = time.time()
    primary_budget = cgd.Budget(PRIMARY_MAX_SEARCHES, PRIMARY_MAX_SECONDS)
    secondary_budget = cgd.Budget(SECONDARY_MAX_SEARCHES, SECONDARY_MAX_SECONDS)
    pairs = {2: cgd.load_pairs(2), 3: cgd.load_pairs(3)}
    ordered = sorted(truncated, key=lambda r: (r["depth"], r["seed"]))
    cells: list[dict] = []
    problems: list[str] = []
    interrupted = None
    for record in ordered:
        both = pairs[record["depth"]].get(record["seed"], [])
        compiled = cgd.generated_compiled(4, record["seed"])
        try:
            cell = cell_completion(compiled, record, both, primary_budget)
        except cgd.BudgetTripped as exc:
            interrupted = str(exc)
            problems.append(str(exc))
            break
        cell["_compiled"] = compiled
        cells.append(cell)
        print(f"cell seed{record['seed']} d{record['depth']} "
              f"{cell['status']} unstable={cell.get('instrument_unstable')}",
              flush=True)

    if not interrupted:
        for cell in cells:
            if cell["status"] != "still_truncated":
                continue
            try:
                secondary_phase(cell, secondary_budget)
            except cgd.BudgetTripped as exc:
                interrupted = str(exc)
                problems.append(str(exc))
                break

    stable = [c for c in cells if not c.get("instrument_unstable")]
    newly = [c for c in stable if c["status"] == "newly_completed"]
    still = [c for c in cells if c["status"] == "still_truncated"]
    unstable = [c for c in cells if c.get("instrument_unstable")]
    rebuild_failed = [c for c in cells if c["status"] == "rebuild_failed"]

    c1 = []
    for cell in cells:
        c1.append(dict(
            seed=cell["seed"], depth=cell["depth"],
            recorded_stratum=cell["recorded_stratum"], status=cell["status"],
            completed_rung={arm: (cell["arms"][arm].get("completed_rung")
                                 if "arms" in cell else None)
                            for arm in ("served", "blind")},
            final_reason={arm: (cell["arms"][arm].get("final_reason")
                                if "arms" in cell else None)
                          for arm in ("served", "blind")},
            reproduced_20k={arm: (cell["arms"][arm].get("reproduced_20k")
                                  if "arms" in cell else None)
                            for arm in ("served", "blind")}))
    c2 = [dict(seed=cell["seed"], depth=cell["depth"],
               pair_kind=cell["pair_kind"], delta=cell["delta"],
               verdict=cell["verdict"],
               recorded_verdict=cell["recorded_verdict"],
               recorded_tie_break=cell["recorded_tie_break"],
               recorded_sign_agrees=cell["recorded_sign_agrees"])
          for cell in newly]

    original_completed = [r for r in judged if stratum(r) == "both_completed"]
    merged_verdicts = Counter(r["verdict"] for r in original_completed)
    merged_verdicts.update(c["verdict"] for c in newly)
    seed_cells: dict[int, list[str]] = {}
    for r in original_completed:
        seed_cells.setdefault(r["seed"], []).append(r["verdict"])
    for c in newly:
        seed_cells.setdefault(c["seed"], []).append(c["verdict"])
    seed_majority = Counter(majority(Counter(v)) for v in seed_cells.values())
    merged_positions: dict[tuple, str] = {}
    for r in original_completed:
        moves = r["saved_moves_at_divergence"]
        merged_positions.setdefault(
            (r["seed"], r["first_diff_ply"], r["divergence_side"],
             moves["served"], moves["blind"]), r["verdict"])
    for c in newly:
        moves = c["saved_moves_at_divergence"]
        merged_positions.setdefault(
            (c["seed"], c["first_diff_ply"], c["divergence_side"],
             moves["served"], moves["blind"]), c["verdict"])
    new_seed_majority = Counter(
        majority(Counter([c["verdict"] for c in newly if c["seed"] == seed]))
        for seed in {c["seed"] for c in newly})

    c4 = []
    secondary_pair_verdicts = Counter()
    for cell in still:
        reasons = {arm: cell["arms"][arm]["final_reason"]
                   for arm in ("served", "blind")}
        secondary = {arm: (cell["arms"][arm].get("secondary") or {}).get("reason")
                     for arm in ("served", "blind")}
        both_secondary_done = all(
            (cell["arms"][arm].get("secondary") or {}).get("reason")
            == "completed_depth" for arm in ("served", "blind"))
        pair_verdict = None
        if both_secondary_done:
            delta = (cell["arms"]["served"]["secondary"]["score_for_mover"]
                     - cell["arms"]["blind"]["secondary"]["score_for_mover"])
            pair_verdict = verdict_of(delta)
            secondary_pair_verdicts[pair_verdict] += 1
        c4.append(dict(seed=cell["seed"], depth=cell["depth"],
                       pair_kind=cell["pair_kind"],
                       remaining_reason=reasons, secondary_reason=secondary,
                       secondary_pair_verdict=pair_verdict))

    if len(newly) >= 10:
        decision = ("blind_direction_survives_completion"
                    if new_seed_majority.get("blind_better", 0)
                    > new_seed_majority.get("served_better", 0)
                    else "no_blind_majority_after_completion")
    elif newly:
        decision = "insufficient_expansion_lt_10"
    else:
        decision = "truncation_structural_at_bounded_caps"

    total_nodes = sum(
        rung["nodes"] + rung["qnodes"]
        for cell in cells if "arms" in cell
        for arm in ("served", "blind")
        for rung in cell["arms"][arm].get("rungs", []))

    payload = dict(
        written_at_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(started)),
        role="DEEPSEEK_AUX",
        segment="78213c35-4252-44bb-8c11-acb79a5005e7",
        plan=("judged-divergence/plan-complete-truncated-judged.json "
              "(written before this run)"),
        inputs=inputs,
        question=("When the recorded hand-blind depth-4 judge is re-run on the "
                  "31 truncated cells with an escalated node cap, how many "
                  "cells reach completed_depth for both candidates, and does "
                  "the served-vs-blind verdict of the newly completed cells "
                  "agree with the recorded truncated verdict?"),
        weight=WEIGHT, ladder=LADDER,
        secondary_instrument=SECONDARY,
        guards=dict(
            primary_max_searches=PRIMARY_MAX_SEARCHES,
            primary_max_seconds=PRIMARY_MAX_SECONDS,
            primary_searches_used=primary_budget.searches,
            primary_elapsed_seconds=round(primary_budget.elapsed(), 1),
            secondary_max_searches=SECONDARY_MAX_SEARCHES,
            secondary_max_seconds=SECONDARY_MAX_SECONDS,
            secondary_searches_used=secondary_budget.searches,
            secondary_elapsed_seconds=round(secondary_budget.elapsed(), 1),
            total_nodes_and_qnodes=total_nodes),
        interrupted=interrupted, problems=problems,
        counts=dict(truncated_cells=len(truncated),
                    newly_completed=len(newly),
                    still_truncated=len(still),
                    instrument_unstable=len(unstable),
                    rebuild_failed=len(rebuild_failed)),
        C1_per_cell_completion=c1,
        C2_newly_completed_verdicts=dict(
            cells=c2,
            counts=dict(Counter(c["verdict"] for c in newly)),
            recorded_sign_agrees=sum(1 for c in newly
                                     if c["recorded_sign_agrees"]),
            seed_majority=dict(new_seed_majority)),
        C3_merged_completed_set=dict(
            originally_completed_cells=len(original_completed),
            newly_completed_cells=len(newly),
            verdicts=dict(merged_verdicts),
            distinct_positions=len(merged_positions),
            position_verdicts=dict(Counter(merged_positions.values())),
            seed_majority=dict(seed_majority)),
        C4_still_truncated=dict(
            cells=c4,
            remaining_reason_counts=dict(Counter(
                cell["arms"][arm]["final_reason"]
                for cell in still for arm in ("served", "blind"))),
            secondary_completed=sum(
                1 for cell in still for arm in ("served", "blind")
                if (cell["arms"][arm].get("secondary") or {}).get("reason")
                == "completed_depth"),
            secondary_pair_verdicts=dict(secondary_pair_verdicts)),
        decision=decision,
        decision_basis=("prewritten rule in plan-complete-truncated-judged.json; "
                        "seed-level majority inside the newly completed cells"),
    )
    OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: payload[k] for k in (
        "counts", "C2_newly_completed_verdicts", "C3_merged_completed_set",
        "C4_still_truncated", "decision", "guards")}, indent=1))
    print("wrote", OUT, sha_prefix(OUT))
    return 0 if not problems and not interrupted else 1


if __name__ == "__main__":
    raise SystemExit(main())
