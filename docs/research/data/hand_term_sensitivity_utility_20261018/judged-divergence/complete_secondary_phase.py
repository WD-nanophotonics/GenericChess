"""Finish the secondary-instrument coverage left by a clock-scope defect.

DEEPSEEK_AUX private probe, segment 78213c35-4252-44bb-8c11-acb79a5005e7.
Plan written before this run: ``plan-secondary-completion.json`` (A4616098).

``results_complete_truncated_judged.json`` (618EEED9) created the secondary
Budget together with the primary Budget, so its 600 s clock already included
the whole primary phase and tripped after 14 secondary searches.  The primary
endpoint C1-C3 is complete; only the diagnostic secondary coverage is partial.

This script:

  * reads 618EEED9 and 444CDA26 read-only and asserts their hashes;
  * selects the 21 cells recorded as ``still_truncated``;
  * replays each saved prefix/candidate with the recorded arm configs so the
    divergence state and the two candidate moves can be verified;
  * runs the pre-written secondary instrument (depth 4, 80k nodes, quiescence
    4/hard 16, hand-blind, ordering on, TT off) only for the candidate
    evaluations that still have no secondary record (19 expected);
  * reuses the recorded secondary reasons and pair verdicts for candidates
    that already completed, because the frozen payload preserved reasons and
    verdicts but not secondary scores;
  * creates the phase Budget immediately before the phase, so the clock no
    longer includes any earlier work.

Guards: refuse overwrite, 100 searches / 600 s for the whole phase, no
p-values, diagnostic only, never pooled with the primary verdicts.
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

FROZEN = HERE / "results_complete_truncated_judged.json"
PRIMARY = HERE / "results_judged_divergence.json"
OUT = HERE / "results_secondary_completion_judged.json"

FROZEN_SHA = "618EEED9"
PRIMARY_SHA = "444CDA26"
WEIGHT = 0.0
SECONDARY = dict(max_depth=4, max_nodes=80_000, quiescence_max_depth=4,
                 quiescence_hard_max_depth=16)
PHASE_MAX_SEARCHES = 100
PHASE_MAX_SECONDS = 600.0
EXPECTED_CELLS = 21
EXPECTED_MISSING = 19


def sha_prefix(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:8].upper()


def verdict_of(delta: int) -> str:
    return ("served_better" if delta > 0
            else "blind_better" if delta < 0 else "tie")


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


def main() -> int:
    if OUT.exists():
        print(f"refusing to overwrite existing result {OUT}", file=sys.stderr)
        return 2
    frozen_sha = sha_prefix(FROZEN)
    primary_sha = sha_prefix(PRIMARY)
    if frozen_sha != FROZEN_SHA:
        raise SystemExit(f"frozen input changed: expected {FROZEN_SHA}, "
                         f"found {frozen_sha}")
    if primary_sha != PRIMARY_SHA:
        raise SystemExit(f"primary input changed: expected {PRIMARY_SHA}, "
                         f"found {primary_sha}")

    frozen = json.loads(FROZEN.read_text(encoding="utf-8"))
    primary = json.loads(PRIMARY.read_text(encoding="utf-8"))
    records = {(r["seed"], r["depth"]): r for r in primary["records"]
               if r["status"] == "judged"}
    still = frozen["C4_still_truncated"]["cells"]
    if len(still) != EXPECTED_CELLS:
        raise SystemExit(f"expected {EXPECTED_CELLS} still-truncated cells, "
                         f"found {len(still)}")
    missing = [(c["seed"], c["depth"], arm) for c in still
               for arm in ("served", "blind")
               if c["remaining_reason"][arm] != "completed_depth"
               and c["secondary_reason"][arm] is None]
    if len(missing) != EXPECTED_MISSING:
        raise SystemExit(f"expected {EXPECTED_MISSING} missing secondary "
                         f"evaluations, found {len(missing)}: {missing}")

    pairs = {2: cgd.load_pairs(2), 3: cgd.load_pairs(3)}
    phase_started = time.time()
    # The fix: this clock starts at the phase boundary, not at process start.
    budget = cgd.Budget(PHASE_MAX_SEARCHES, PHASE_MAX_SECONDS)
    cells_out: list[dict] = []
    problems: list[str] = []
    interrupted = None

    for cell in still:
        seed, depth = cell["seed"], cell["depth"]
        record = records[(seed, depth)]
        entry = dict(
            seed=seed, depth=depth, pair_kind=cell["pair_kind"],
            first_diff_ply=record["first_diff_ply"],
            recorded_verdict=record["verdict"],
            saved_moves_at_divergence=record["saved_moves_at_divergence"],
            primary_final_reason=dict(cell["remaining_reason"]),
            recorded_secondary_reason=dict(cell["secondary_reason"]),
            recorded_secondary_pair_verdict=cell["secondary_pair_verdict"],
            arms={})
        compiled = cgd.generated_compiled(4, seed)
        try:
            rebuilt = rebuild_divergence(
                compiled, seed, depth, pairs[depth].get(seed, []), budget)
        except cgd.BudgetTripped as exc:
            interrupted = str(exc)
            problems.append(str(exc))
            break
        if not rebuilt.get("ok"):
            entry["status"] = "rebuild_failed"
            entry["failure"] = {k: v for k, v in rebuilt.items()
                                if k != "state"}
            cells_out.append(entry)
            print(f"cell seed{seed} d{depth} rebuild_failed "
                  f"{entry['failure']}", flush=True)
            continue
        state = rebuilt["state"]
        entry["divergence_side"] = state.position.side_to_move
        entry["saved_moves_verified"] = True
        for arm in ("served", "blind"):
            block = dict(
                primary_final_reason=cell["remaining_reason"][arm],
                recorded_secondary_reason=cell["secondary_reason"][arm])
            if cell["remaining_reason"][arm] == "completed_depth":
                block["skipped"] = "primary_completed"
                entry["arms"][arm] = block
                continue
            child = cgd.apply_action(state, rebuilt["candidates"][arm]["action"],
                                     compiled)
            if child.terminal_status.is_terminal:
                block["skipped"] = "terminal_child"
                block["terminal_status"] = child.terminal_status.status.value
                entry["arms"][arm] = block
                continue
            if cell["secondary_reason"][arm] is not None:
                # Recorded reason reused; the frozen payload kept no score.
                block["reused"] = True
                entry["arms"][arm] = block
                continue
            try:
                step = cgd.run_search(
                    child, compiled, cgd.make_searcher(compiled, WEIGHT),
                    SECONDARY, budget,
                    f"secondary seed{seed} d{depth} {arm}")
            except cgd.BudgetTripped as exc:
                interrupted = str(exc)
                problems.append(str(exc))
                break
            block.update(
                reused=False,
                secondary=dict(
                    score_for_mover=-step["score"], reason=step["reason"],
                    nodes=step["nodes"], qnodes=step["qnodes"],
                    node_cap_hit=step["node_cap_hit"]))
            entry["arms"][arm] = block
            print(f"secondary seed{seed} d{depth} {arm} "
                  f"{step['reason']} score={-step['score']}", flush=True)
        cells_out.append(entry)
        if interrupted:
            break

    # Build per-cell secondary pair verdicts.
    for entry in cells_out:
        if entry.get("status") == "rebuild_failed":
            continue
        arms = entry["arms"]
        complete = {}
        for arm in ("served", "blind"):
            block = arms.get(arm, {})
            if block.get("reused"):
                complete[arm] = block["recorded_secondary_reason"] == \
                    "completed_depth"
            else:
                complete[arm] = (block.get("secondary", {}).get("reason")
                                 == "completed_depth")
        primary_completed = [arm for arm in ("served", "blind")
                             if arms[arm]["primary_final_reason"]
                             == "completed_depth"]
        if primary_completed:
            entry["secondary_pair_status"] = "mixed_instrument"
            entry["secondary_pair_verdict"] = None
            entry["reused_pair_verdict"] = False
            continue
        if all(complete.values()):
            scores = {}
            for arm in ("served", "blind"):
                block = arms[arm]
                if block.get("reused"):
                    scores = None
                    break
                scores[arm] = block["secondary"]["score_for_mover"]
            if scores is not None:
                delta = scores["served"] - scores["blind"]
                entry["secondary_pair_status"] = "computed"
                entry["secondary_pair_delta"] = delta
                entry["secondary_pair_verdict"] = verdict_of(delta)
                entry["reused_pair_verdict"] = False
            else:
                # Both secondary evaluations were recorded earlier; only the
                # pair verdict, not the two scores, survived in the payload.
                entry["secondary_pair_status"] = "reused_verdict"
                entry["secondary_pair_verdict"] = \
                    entry["recorded_secondary_pair_verdict"]
                entry["reused_pair_verdict"] = True
        else:
            entry["secondary_pair_status"] = "incomplete"
            entry["secondary_pair_verdict"] = None
            entry["reused_pair_verdict"] = False

    new_secondary = [
        (entry["seed"], entry["depth"], arm)
        for entry in cells_out
        for arm in ("served", "blind")
        if entry["arms"].get(arm, {}).get("secondary")]
    secondary_reasons = Counter()
    for entry in cells_out:
        for arm in ("served", "blind"):
            block = entry["arms"].get(arm, {})
            reason = (block.get("secondary") or {}).get("reason") \
                if not block.get("reused") else block.get("recorded_secondary_reason")
            if reason:
                secondary_reasons[reason] += 1
    pair_verdicts = Counter(
        entry["secondary_pair_verdict"] for entry in cells_out
        if entry.get("secondary_pair_verdict"))
    disagree = [
        dict(seed=entry["seed"], depth=entry["depth"],
             recorded_verdict=entry["recorded_verdict"],
             secondary_pair_verdict=entry["secondary_pair_verdict"])
        for entry in cells_out
        if entry.get("secondary_pair_verdict")
        and entry["secondary_pair_verdict"] != entry["recorded_verdict"]]
    status_counts = Counter(entry.get("secondary_pair_status", "rebuild_failed")
                             for entry in cells_out)

    total_nodes = sum(
        ((block.get("secondary") or {}).get("nodes", 0)
         + (block.get("secondary") or {}).get("qnodes", 0))
        for entry in cells_out for block in entry["arms"].values())

    payload = dict(
        written_at_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                     time.gmtime(phase_started)),
        role="DEEPSEEK_AUX",
        segment="78213c35-4252-44bb-8c11-acb79a5005e7",
        plan=("judged-divergence/plan-secondary-completion.json A4616098 "
              "(written before this run)"),
        inputs={FROZEN.name: frozen_sha, PRIMARY.name: primary_sha},
        question=("Under the pre-written secondary instrument (depth 4, 80k "
                  "nodes, quiescence hard 16), do the candidate evaluations "
                  "still truncated after the primary ladder complete, and "
                  "what are their separate per-cell verdicts?"),
        instrument=SECONDARY,
        weight=WEIGHT,
        guards=dict(phase_max_searches=PHASE_MAX_SEARCHES,
                    phase_max_seconds=PHASE_MAX_SECONDS,
                    phase_searches_used=budget.searches,
                    phase_elapsed_seconds=round(budget.elapsed(), 1),
                    secondary_nodes_and_qnodes=total_nodes,
                    clock_scope="starts at the phase boundary"),
        interrupted=interrupted,
        problems=problems,
        counts=dict(still_truncated_cells=len(cells_out),
                    missing_secondary_evaluations=len(missing),
                    new_secondary_evaluations=len(new_secondary),
                    reused_secondary_reasons=sum(
                        1 for entry in cells_out
                        for block in entry["arms"].values()
                        if block.get("reused")),
                    secondary_reason_counts=dict(secondary_reasons),
                    pair_status_counts=dict(status_counts)),
        S1_per_candidate=dict(
            newly_run=[
                dict(seed=entry["seed"], depth=entry["depth"], arm=arm,
                     secondary=block["secondary"])
                for entry in cells_out for arm, block in entry["arms"].items()
                if block.get("secondary")],
            reused_reason_only=[
                dict(seed=entry["seed"], depth=entry["depth"], arm=arm,
                     reason=block["recorded_secondary_reason"])
                for entry in cells_out for arm, block in entry["arms"].items()
                if block.get("reused")],
            note=("frozen 618EEED9 preserved secondary reasons but not their "
                  "scores/nodes; those 11 reasons are reused read-only")),
        S2_per_cell=[
            dict(seed=entry["seed"], depth=entry["depth"],
                 pair_kind=entry["pair_kind"],
                 primary_final_reason=entry["primary_final_reason"],
                 recorded_secondary_reason=entry["recorded_secondary_reason"],
                 secondary_pair_status=entry.get("secondary_pair_status"),
                 secondary_pair_verdict=entry.get("secondary_pair_verdict"),
                 reused_pair_verdict=entry.get("reused_pair_verdict"))
            for entry in cells_out],
        S3=dict(reason_counts=dict(secondary_reasons),
                pair_verdicts=dict(pair_verdicts),
                pair_verdict_differs_from_recorded=disagree),
        S4=dict(phase_searches=budget.searches,
                phase_elapsed_seconds=round(budget.elapsed(), 1),
                secondary_nodes_and_qnodes=total_nodes),
        decision="diagnostic_only",
        decision_basis=("prewritten rule in plan-secondary-completion.json: "
                        "no primary endpoint, direction or decision changes; "
                        "the result records instrument sensitivity only"),
    )
    OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: payload[k] for k in (
        "counts", "S3", "guards", "interrupted", "problems")}, indent=1))
    print("wrote", OUT, sha_prefix(OUT))
    return 0 if not problems else 1


if __name__ == "__main__":
    raise SystemExit(main())
