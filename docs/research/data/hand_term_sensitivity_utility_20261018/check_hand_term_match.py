"""Does the hand term's root-action sensitivity change game outcomes?

DEEPSEEK_AUX private probe (2026-10-18), segment
``d16d7db6-d36f-4a8c-9437-ef210b31df0c``.  Earlier items measured *ordering*
sensitivity: served ``hand_weight=0.9`` versus a hand-blind control picks a
different root action on 7/34 depth-4 rows (item 9) and 29/130 depth-1-3 rows
(item 5).  Action flips are not utility.  This probe plays complete games with
the shipped ``AlphaBetaPlayer`` and asks whether the same coefficient change
also changes who wins, under a fixed depth/node budget and color-swapped pairs.

Decision this informs: whether further hand-policy work has any expected
utility signal at all at this search budget, or whether the earlier flips are
behaviourally real but outcome-neutral on generated 4x4 rulesets.  It is a
scoped utility comparison, not a strength claim: 2-ply search, deterministic
play, one opening position per ruleset.
"""

from __future__ import annotations

import json
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import random  # noqa: E402

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

HERE = Path(__file__).resolve().parent
FIRST_SEED = int(sys.argv[1]) if len(sys.argv) > 1 else 59
LAST_SEED = int(sys.argv[2]) if len(sys.argv) > 2 else 70
DEPTH = int(sys.argv[3]) if len(sys.argv) > 3 else 2
NODE_CAP = int(sys.argv[4]) if len(sys.argv) > 4 else 20_000
PAIR_TAG = sys.argv[5] if len(sys.argv) > 5 else "served-blind"
WATCHDOG_PLIES = 160
PAIRS = {
    "served-blind": (("served", 0.9), ("blind", 0.0)),
    # Same arms, but the payload also records search-termination reasons per
    # side, so truncation asymmetry can be separated from evaluation effect.
    "served-blind-reasons": (("served", 0.9), ("blind", 0.0)),
    # Same-config control: both sides use identical configs, so any remaining
    # win/loss pattern measures start position and side-to-move asymmetry.
    "served-served": (("served", 0.9), ("served2", 0.9)),
}
ARMS = PAIRS[PAIR_TAG]
START_PLY = 8
MIN_START_ACTIONS = 6


def generated_compiled(size: int = 4, seed: int = 59):
    """Same construction the item-5..9 probes used (classic_like setup)."""
    game = generate_game(
        GeneratorConfig(seed=seed, board_size=size, setup_preset="classic_like")
    )
    return game.compiled_ruleset


def make_searcher(compiled, hand_weight: float):
    config = EvaluationConfig(hand_weight=hand_weight)
    profile = build_ruleset_profile(compiled, config)
    return Evaluator(compiled, profile, config)


def search(state, compiled, evaluator):
    stats = SearchStatistics()
    action, score, _pv, reason = run_root_search(
        state,
        compiled,
        evaluator,
        TranspositionTable(max_entries=20_000),
        SearchLimits(
            max_depth=DEPTH,
            max_nodes=NODE_CAP,
            quiescence_max_depth=4,
            quiescence_hard_max_depth=8,
        ),
        None,
        stats,
        use_tt=False,
        use_ordering=True,
    )
    return action, score, reason, stats.nodes, stats.qnodes


def sample_start(compiled, seed: int):
    """Walk a deterministic game and return a non-terminal mid-game state.

    Positions whose side to move has a terminal child are skipped so a game
    does not end on the first move. Starts are neutral with respect to the
    hand term: no capture-to-hand filter.
    """
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


def play_game(compiled, seed: int, start_state, side_arm: dict[int, str], searchers) -> dict:
    state = start_state
    moves: list[str] = []
    reasons: Counter[str] = Counter()
    reasons_by_arm: dict[str, Counter[str]] = {name: Counter() for name, _ in ARMS}
    nodes = {name: 0 for name, _ in ARMS}
    qnodes = {name: 0 for name, _ in ARMS}
    plies = 0
    while not state.terminal_status.is_terminal:
        if plies >= WATCHDOG_PLIES:
            break
        side = state.position.side_to_move
        arm = side_arm[side]
        action, _score, reason, n, qn = search(state, compiled, searchers[arm])
        nodes[arm] += n
        qnodes[arm] += qn
        reasons[reason] += 1
        reasons_by_arm[arm][reason] += 1
        if action is None:
            break
        state = apply_action(state, action, compiled)
        moves.append(repr(action))
        plies += 1
    served_side = next(side for side, name in side_arm.items() if name == "served")
    terminal = state.terminal_status
    status = terminal.status.value if terminal.is_terminal else "watchdog"
    winner = terminal.winner if terminal.is_terminal else None
    if status == "watchdog":
        outcome = "watchdog"
    elif winner is None:
        outcome = "draw"
    elif winner == served_side:
        outcome = "served_win"
    else:
        outcome = "served_loss"
    return dict(
        seed=seed,
        served_side=served_side,
        status=status,
        winner=winner,
        outcome=outcome,
        plies=plies,
        moves=moves,
        termination_reasons=dict(sorted(reasons.items())),
        termination_reasons_by_arm={
            name: dict(sorted(counter.items())) for name, counter in reasons_by_arm.items()
        },
        nodes=nodes,
        qnodes=qnodes,
    )


def main() -> int:
    started = time.monotonic()
    # Guard the output destination BEFORE running anything: an earlier run
    # silently overwrote a frozen 24-game result because the name lacked the
    # seed range. Refuse to reuse an existing file unless explicitly allowed.
    out = HERE / (
        f"results_hand_term_match_{PAIR_TAG}_d{DEPTH}_n{NODE_CAP}"
        f"_s{FIRST_SEED}-{LAST_SEED}.json"
    )
    if out.exists() and "--allow-overwrite" not in sys.argv[6:]:
        print(
            f"refusing to overwrite existing result {out.name}; "
            "pass --allow-overwrite to replace it",
            file=sys.stderr,
        )
        return 2
    games: list[dict] = []
    problems: list[str] = []
    for seed in range(FIRST_SEED, LAST_SEED + 1):
        compiled = generated_compiled(size=4, seed=seed)
        start_state = sample_start(compiled, seed)
        if start_state is None:
            problems.append(f"no eligible start position at seed {seed}")
            continue
        searchers = {
            name: make_searcher(compiled, weight) for name, weight in ARMS
        }
        first, second = (name for name, _ in ARMS)
        for game_index, assignment in enumerate(
            ({0: first, 1: second}, {0: second, 1: first})
        ):
            game = play_game(compiled, seed, start_state, assignment, searchers)
            game["game_index"] = game_index
            game["side_arm"] = {str(k): v for k, v in assignment.items()}
            game["start_ply"] = start_state.ply_count
            games.append(game)
        # In-process determinism guard: replay the first game with fresh searchers.
        reference_game = games[-2]
        replay_searchers = {
            name: make_searcher(compiled, weight) for name, weight in ARMS
        }
        replay = play_game(
            compiled, seed, start_state, {0: first, 1: second}, replay_searchers
        )
        if (replay["moves"] != reference_game["moves"]
                or replay["outcome"] != reference_game["outcome"]):
            problems.append(f"non-deterministic replay at seed {seed}")
    summary = Counter(g["outcome"] for g in games)
    statuses = Counter(g["status"] for g in games)
    node_totals = {name: sum(g["nodes"][name] for g in games) for name, _ in ARMS}
    qnode_totals = {name: sum(g["qnodes"][name] for g in games) for name, _ in ARMS}
    score = summary["served_win"] + 0.5 * summary["draw"]
    payload = dict(
        role="DEEPSEEK_AUX",
        segment="d16d7db6-d36f-4a8c-9437-ef210b31df0c",
        question=(
            "Does replacing the served hand term (0.9) with a hand-blind "
            "control (0.0) change head-to-head game outcomes on generated "
            "4x4 rulesets at a fixed search budget?"
        ),
        design=dict(
            seeds=[FIRST_SEED, LAST_SEED],
            ruleset_size=4,
            games_per_seed=2,
            color_swapped=True,
            search=dict(max_depth=DEPTH, max_nodes=NODE_CAP,
                        quiescence_max_depth=4, quiescence_hard_max_depth=8,
                        # Probe-local metadata defect fixed after the first four
                        # result files: those files say use_tt=True, but the
                        # actual ``search`` call above always passes use_tt=False.
                        use_tt=False, use_ordering=True),
            watchdog_plies=WATCHDOG_PLIES,
            arms=dict(ARMS),
        ),
        games=games,
        summary=dict(
            games=len(games),
            outcomes=dict(summary),
            served_score=score,
            served_score_fraction=(score / len(games)) if games else None,
            statuses=dict(statuses),
            node_totals=node_totals,
            qnode_totals=qnode_totals,
            mean_plies=sum(g["plies"] for g in games) / len(games) if games else None,
        ),
        problems=problems,
    )
    per_seed = {}
    for game in games:
        per_seed.setdefault(game["seed"], {})[game["game_index"]] = dict(
            outcome=game["outcome"],
            served_side=game["served_side"],
            winner=game["winner"],
            plies=game["plies"],
        )
    pair_patterns = Counter()
    side_wins = Counter()
    for seed, pair in per_seed.items():
        if len(pair) != 2:
            continue
        pair_patterns["/".join(sorted(pair[i]["outcome"] for i in (0, 1)))] += 1
        for game in pair.values():
            if game["winner"] is not None:
                side_wins[str(game["winner"])] += 1
    payload["pair_patterns"] = dict(sorted(pair_patterns.items()))
    payload["side_wins"] = dict(sorted(side_wins.items()))
    payload["pair_tag"] = PAIR_TAG
    out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(payload["summary"], indent=1))
    print("problems", problems)
    print("wrote", out.name, "elapsed_s", round(time.monotonic() - started, 1))
    return 0 if not problems else 1


if __name__ == "__main__":
    raise SystemExit(main())
