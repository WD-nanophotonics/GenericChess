"""Is the served hand term's first move divergence a quality improvement?

DEEPSEEK_AUX private probe, segment 78213c35-4252-44bb-8c11-acb79a5005e7.

The d2/d3 game files show the served (``hand_weight=0.9``) and hand-blind
(``0.0``) arms first pick different moves within ply 0-4 of a colour-swapped
pair.  Action divergence is not utility.  This probe therefore judges those
first-divergence positions with a *third* fixed judge that uses neither arm
config: a hand-blind ``hand_weight=0.0`` search at depth 4 / 20k nodes /
quiescence 4 (hard 8) / ordering on / TT off.  For each candidate move the
judge is run from the child position and the score is negated, so the value is
expressed for the mover at the shared position.
``delta = served_value - blind_value``.

Pre-written plan (before any result was observed):
``judged-divergence/plan.json``.  Guards: 400 searches / 900 s, no overwrite,
partial file with an ``interrupted`` flag on guard trip.  A pre-written
secondary re-judges *only exact depth-4 ties* at depth 6 / 40k nodes within
60 further searches and 600 s, so the depth-4 endpoint cannot be selected by
the tie-break.

Scope: descriptive quality check on already-observed positions; no hypothesis
test, no endpoint tuning, no strength/generality claim, no product change.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import time
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))

from generic_chess.generation.config import GeneratorConfig  # noqa: E402
from generic_chess.generation.generator import generate_game  # noqa: E402
from generic_chess.ai.alphabeta.search import run_root_search  # noqa: E402
from generic_chess.ai.alphabeta.statistics import SearchStatistics  # noqa: E402
from generic_chess.ai.alphabeta.transposition import TranspositionTable  # noqa: E402
from generic_chess.ai.evaluation.config import EvaluationConfig  # noqa: E402
from generic_chess.ai.evaluation.evaluator import Evaluator  # noqa: E402
from generic_chess.ai.evaluation.profile import build_ruleset_profile  # noqa: E402
from generic_chess.ai.limits import SearchLimits  # noqa: E402
from generic_chess.core.movegen import legal_actions  # noqa: E402
from generic_chess.core.transition import (  # noqa: E402
    apply_action,
    initial_state,
    legal_successors,
)

EVIDENCE = HERE.parent
START_PLY = 8
MIN_START_ACTIONS = 6
ARM_LIMITS_DEPTH = {2: 2, 3: 3}
ORACLE = dict(max_depth=4, max_nodes=20_000,
              quiescence_max_depth=4, quiescence_hard_max_depth=8)
TIE_BREAK = dict(max_depth=6, max_nodes=40_000,
                 quiescence_max_depth=4, quiescence_hard_max_depth=8)
MAX_SEARCHES = 400
MAX_SECONDS = 900.0
TIE_BREAK_MAX_SEARCHES = 60
TIE_BREAK_MAX_SECONDS = 600.0
NO_TIE_BREAK = [False]


class BudgetTripped(RuntimeError):
    pass


class Budget:
    def __init__(self, max_searches: int, max_seconds: float) -> None:
        self.max_searches = max_searches
        self.max_seconds = max_seconds
        self.searches = 0
        self.started = time.monotonic()

    def elapsed(self) -> float:
        return time.monotonic() - self.started

    def spend(self, label: str) -> None:
        if self.searches + 1 > self.max_searches:
            raise BudgetTripped(f"max_searches {self.max_searches} hit before {label}")
        if self.elapsed() >= self.max_seconds:
            raise BudgetTripped(f"max_seconds {self.max_seconds} hit before {label}")
        self.searches += 1


class TieBreakBudget:
    """Sub-cap for the pre-written depth-6 re-judge of exact depth-4 ties."""

    def __init__(self) -> None:
        self.searches = 0
        self.started: float | None = None

    def available(self) -> bool:
        if self.searches + 2 > TIE_BREAK_MAX_SEARCHES:
            return False
        if self.started is not None and time.monotonic() - self.started >= TIE_BREAK_MAX_SECONDS:
            return False
        return True

    def note_search(self) -> None:
        if self.started is None:
            self.started = time.monotonic()
        self.searches += 1


def generated_compiled(size: int, seed: int):
    game = generate_game(
        GeneratorConfig(seed=seed, board_size=size, setup_preset="classic_like")
    )
    return game.compiled_ruleset


def make_searcher(compiled, hand_weight: float) -> Evaluator:
    config = EvaluationConfig(hand_weight=hand_weight)
    profile = build_ruleset_profile(compiled, config)
    return Evaluator(compiled, profile, config)


def arm_limits(depth: int) -> dict:
    return dict(max_depth=ARM_LIMITS_DEPTH[depth], max_nodes=20_000,
                quiescence_max_depth=4, quiescence_hard_max_depth=8)


def run_search(state, compiled, evaluator, limits: dict, budget: Budget,
               label: str, tie_budget: TieBreakBudget | None = None) -> dict:
    budget.spend(label)
    if tie_budget is not None:
        tie_budget.note_search()
    stats = SearchStatistics()
    action, score, _pv, reason = run_root_search(
        state,
        compiled,
        evaluator,
        TranspositionTable(max_entries=20_000),
        SearchLimits(
            max_depth=limits["max_depth"],
            max_nodes=limits["max_nodes"],
            quiescence_max_depth=limits["quiescence_max_depth"],
            quiescence_hard_max_depth=limits["quiescence_hard_max_depth"],
        ),
        None,
        stats,
        use_tt=False,
        use_ordering=True,
    )
    return dict(
        action=action,
        action_text=repr(action) if action is not None else None,
        score=score,
        reason=reason,
        nodes=stats.nodes,
        qnodes=stats.qnodes,
        max_depth=limits["max_depth"],
        max_nodes=limits["max_nodes"],
        node_cap_hit=stats.nodes >= limits["max_nodes"],
    )


def sample_start(compiled, seed: int):
    """Deterministic start position, identical to the earlier game probes."""
    for offset in range(4):
        rng = random.Random(seed * 1009 + offset)
        state = initial_state(compiled)
        while state.ply_count < 60:
            if state.terminal_status.is_terminal:
                break
            if state.ply_count >= START_PLY:
                actions = legal_actions(state, compiled)
                children = legal_successors(state, compiled)
                if (len(actions) >= MIN_START_ACTIONS
                        and not any(c.terminal_status.is_terminal for _, c in children)):
                    return state
            children = legal_successors(state, compiled)
            if not children:
                break
            _, state = rng.choice(children)
    return None


def first_diff(a: list[str], b: list[str]) -> int | None:
    if a == b:
        return None
    for i in range(min(len(a), len(b))):
        if a[i] != b[i]:
            return i
    return min(len(a), len(b))


def arms_of(game: dict) -> dict[int, str]:
    return {int(key): value for key, value in game["side_arm"].items()}


def load_pairs(depth: int) -> dict[int, list[dict]]:
    pairs: dict[int, list[dict]] = {}
    pattern = f"results_hand_term_match_served-blind_d{depth}_*.json"
    for path in sorted(EVIDENCE.glob(pattern)):
        data = json.loads(path.read_text(encoding="utf-8"))
        for game in data["games"]:
            pairs.setdefault(game["seed"], []).append(game)
    return pairs


def judge_pair(compiled, seed: int, depth: int, both: list[dict],
               budget: Budget, tie_budget: TieBreakBudget,
               judge_hand_weight: float = 0.0) -> dict:
    """Reconstruct the shared prefix and judge the first-divergence moves."""
    games = sorted(both, key=lambda g: g["served_side"])
    g0, g1 = games
    index = first_diff(g0["moves"], g1["moves"])
    wins = sum(1 for g in games if g["outcome"] == "served_win")
    kind = "sweep" if wins == 2 else ("blind" if wins == 0 else "split")
    record = dict(seed=seed, depth=depth, pair_kind=kind, first_diff_ply=index,
                  served_sides=[g0["served_side"], g1["served_side"]],
                  outcomes=[g0["outcome"], g1["outcome"]])
    if index is None:
        record["status"] = "no_divergence"
        return record
    if index >= min(len(g0["moves"]), len(g1["moves"])):
        record["status"] = "truncated_list"
        return record
    start = sample_start(compiled, seed)
    if start is None or start.ply_count != g0["start_ply"]:
        record["status"] = "start_mismatch"
        return record
    searchers = {"served": make_searcher(compiled, 0.9),
                 "blind": make_searcher(compiled, 0.0),
                 "oracle": make_searcher(compiled, judge_hand_weight)}
    state = start
    for ply in range(index):
        arm = arms_of(g0)[state.position.side_to_move]
        step = run_search(state, compiled, searchers[arm], arm_limits(depth), budget,
                          f"prefix seed{seed} d{depth} ply{ply}")
        if step["action_text"] != g0["moves"][ply]:
            record["status"] = "prefix_mismatch"
            record["prefix_mismatch"] = dict(ply=ply, expected=g0["moves"][ply],
                                             got=step["action_text"])
            return record
        state = apply_action(state, step["action"], compiled)
    side = state.position.side_to_move
    candidates: dict[str, dict] = {}
    for arm in ("served", "blind"):
        candidates[arm] = run_search(state, compiled, searchers[arm],
                                     arm_limits(depth), budget,
                                     f"candidate seed{seed} d{depth} {arm}")
    record["divergence_side"] = side
    record["candidates"] = {
        arm: dict(move=step["action_text"], score=step["score"],
                  reason=step["reason"], nodes=step["nodes"],
                  qnodes=step["qnodes"], node_cap_hit=step["node_cap_hit"])
        for arm, step in candidates.items()
    }
    expectations = {arms_of(game)[side]: game["moves"][index]
                    for game in (g0, g1)}
    record["saved_moves_at_divergence"] = expectations
    mismatched = [arm for arm, text in expectations.items()
                  if candidates[arm]["action_text"] != text]
    if mismatched:
        record["status"] = "candidate_mismatch"
        record["candidate_mismatch"] = mismatched
        return record
    record["status"] = "judged"
    judged = {}
    for arm in ("served", "blind"):
        child = apply_action(state, candidates[arm]["action"], compiled)
        terminal = child.terminal_status
        if terminal.is_terminal:
            judged[arm] = dict(terminal=True, status=terminal.status.value,
                               winner=terminal.winner)
            continue
        step = run_search(child, compiled, searchers["oracle"], ORACLE, budget,
                          f"oracle4 seed{seed} d{depth} {arm}")
        judged[arm] = dict(terminal=False, score_for_mover=-step["score"],
                           reason=step["reason"], nodes=step["nodes"],
                           qnodes=step["qnodes"], node_cap_hit=step["node_cap_hit"])
    record["oracle"] = judged
    if judged["served"]["terminal"] or judged["blind"]["terminal"]:
        record["status"] = "terminal_child"
        return record
    delta = judged["served"]["score_for_mover"] - judged["blind"]["score_for_mover"]
    record["delta"] = delta
    record["verdict"] = ("served_better" if delta > 0
                         else "blind_better" if delta < 0 else "tie")
    if delta == 0 and not NO_TIE_BREAK[0]:
        record["tie_break"] = tie_break(state, compiled, searchers, candidates,
                                        budget, tie_budget, seed, depth)
    return record


def tie_break(state, compiled, searchers, candidates, budget: Budget,
              tie_budget: TieBreakBudget, seed: int, depth: int) -> dict:
    """Pre-written secondary judge for exact depth-4 ties only."""
    if not tie_budget.available():
        return dict(status="skipped_sub_cap", searches_used=tie_budget.searches)
    values = {}
    for arm in ("served", "blind"):
        child = apply_action(state, candidates[arm]["action"], compiled)
        if child.terminal_status.is_terminal:
            return dict(status="skipped_terminal_child")
        step = run_search(child, compiled, searchers["oracle"], TIE_BREAK, budget,
                          f"oracle6 seed{seed} d{depth} {arm}", tie_budget)
        values[arm] = dict(score_for_mover=-step["score"], reason=step["reason"],
                           nodes=step["nodes"], qnodes=step["qnodes"],
                           node_cap_hit=step["node_cap_hit"])
    delta6 = values["served"]["score_for_mover"] - values["blind"]["score_for_mover"]
    return dict(status="judged", scores=values, delta=delta6,
                verdict=("served_better" if delta6 > 0
                         else "blind_better" if delta6 < 0 else "tie"))


def aggregate_records(records: list[dict]) -> dict:
    out: dict = dict(total_records=len(records),
                     statuses=dict(Counter(r["status"] for r in records)))
    groups: dict[str, dict] = {}
    for record in records:
        group = ("config_decided" if record["pair_kind"] in ("sweep", "blind")
                 else "divergent_split")
        bucket = groups.setdefault(group, dict(positions=0, verdicts=Counter(),
                                               deltas=[], node_cap_hits=0,
                                               reasons=Counter(),
                                               tie_break=Counter(), by_depth={}))
        if record["status"] != "judged":
            continue
        bucket["positions"] += 1
        bucket["verdicts"][record["verdict"]] += 1
        bucket["deltas"].append(record["delta"])
        for arm in ("served", "blind"):
            if record["oracle"][arm]["node_cap_hit"]:
                bucket["node_cap_hits"] += 1
            bucket["reasons"][record["oracle"][arm]["reason"]] += 1
        if "tie_break" in record:
            bucket["tie_break"][record["tie_break"]["status"]] += 1
        depth_bucket = bucket["by_depth"].setdefault(
            str(record["depth"]), dict(positions=0, verdicts=Counter()))
        depth_bucket["positions"] += 1
        depth_bucket["verdicts"][record["verdict"]] += 1
    for bucket in groups.values():
        bucket["verdicts"] = dict(bucket["verdicts"])
        bucket["reasons"] = dict(bucket["reasons"])
        bucket["tie_break"] = dict(bucket["tie_break"])
        for depth_bucket in bucket["by_depth"].values():
            depth_bucket["verdicts"] = dict(depth_bucket["verdicts"])
        if bucket["deltas"]:
            bucket["delta_min"] = min(bucket["deltas"])
            bucket["delta_max"] = max(bucket["deltas"])
        del bucket["deltas"]
    out["groups"] = groups
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default=str(HERE / "results_judged_divergence.json"))
    parser.add_argument("--only-depth", type=int, default=None)
    parser.add_argument("--only-seeds", type=int, nargs="*", default=None)
    parser.add_argument("--judge-hand-weight", type=float, default=0.0,
                        help="hand_weight of the depth-4 judge; the pre-written "
                             "primary judge is 0.0 (hand-blind)")
    parser.add_argument("--no-tie-break", action="store_true",
                        help="skip the pre-written depth-6 tie-break "
                             "(used only by the judge-robustness variant)")
    parser.add_argument("--allow-overwrite", action="store_true")
    args = parser.parse_args()
    out = Path(args.out)
    if out.exists() and not args.allow_overwrite:
        print(f"refusing to overwrite existing result {out}", file=sys.stderr)
        return 2
    NO_TIE_BREAK[0] = args.no_tie_break
    started = time.time()
    budget = Budget(MAX_SEARCHES, MAX_SECONDS)
    tie_budget = TieBreakBudget()
    records: list[dict] = []
    problems: list[str] = []
    interrupted = None
    seeds = set(args.only_seeds) if args.only_seeds else None
    for depth in ([args.only_depth] if args.only_depth else [2, 3]):
        for seed, both in sorted(load_pairs(depth).items()):
            if seeds is not None and seed not in seeds:
                continue
            if len(both) != 2:
                problems.append(f"seed {seed} d{depth}: {len(both)} games")
                continue
            compiled = generated_compiled(4, seed)
            try:
                records.append(judge_pair(compiled, seed, depth, both,
                                          budget, tie_budget,
                                          args.judge_hand_weight))
            except BudgetTripped as exc:
                interrupted = str(exc)
                problems.append(str(exc))
                break
            except RuntimeError as exc:
                problems.append(f"seed {seed} d{depth}: {exc}")
        if interrupted:
            break
    payload = dict(
        role="DEEPSEEK_AUX",
        segment="78213c35-4252-44bb-8c11-acb79a5005e7",
        question=("At the first move-divergence position of each colour-swapped "
                  "pair, does a hand-blind deeper oracle prefer the served "
                  "move, and does that preference separate config-decided "
                  "pairs from divergent splits?"),
        plan="judged-divergence/plan.json (written before the run)",
        oracle=ORACLE,
        judge_hand_weight=args.judge_hand_weight,
        tie_break_limits=TIE_BREAK,
        guards=dict(max_searches=MAX_SEARCHES, max_seconds=MAX_SECONDS,
                    searches_used=budget.searches,
                    tie_break_searches=tie_budget.searches),
        elapsed_seconds=round(budget.elapsed(), 1),
        interrupted=interrupted,
        records=records,
        aggregate=aggregate_records(records),
        problems=problems,
        written_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(started)),
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(payload["aggregate"], indent=1))
    print("problems", problems)
    print("searches", budget.searches, "tie_break_searches", tie_budget.searches,
          "elapsed_s", round(budget.elapsed(), 1))
    print("wrote", out)
    return 0 if not problems and not interrupted else 1


if __name__ == "__main__":
    raise SystemExit(main())
