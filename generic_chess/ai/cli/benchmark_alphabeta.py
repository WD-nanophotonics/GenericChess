"""AlphaBeta search benchmark and vs-random smoke games.

Usage::

    python -m generic_chess.ai.cli.benchmark_alphabeta --ruleset rules.json --nodes 100000 --repeat 5
    python -m generic_chess.ai.cli.benchmark_alphabeta --seed 42 --nodes 10000 --vs-random 6
"""

from __future__ import annotations

import argparse
import random
import sys
import time

from ...core.movegen import legal_actions
from ...generation.config import GeneratorConfig
from ...generation.generator import generate_game
from ...rules.serialization import deserialize_ruleset
from ...rules.compiler import compile_ruleset_for_execution
from ...session.result import SessionResult, SessionStatus
from ...session.session import GameSession
from ..alphabeta.player import AlphaBetaPlayer
from ..limits import SearchLimits


def _int_at_least(value: str, minimum: int) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be an integer") from exc
    if parsed < minimum:
        raise argparse.ArgumentTypeError(f"must be >= {minimum}")
    return parsed


def _result_bucket(result: SessionResult, ai_color: int) -> str:
    if result.winner is not None:
        return "ab" if result.winner == ai_color else "random"
    if result.status in (
        SessionStatus.STALEMATE,
        SessionStatus.REPETITION,
        SessionStatus.MAX_PLY,
        SessionStatus.ACTION_CLASS_DRAW,
        SessionStatus.NO_PROGRESS_DRAW,
    ):
        return "draw"
    # No-contest declarations and external stopping/caps are not rule draws.
    return "unresolved"


def _decision_action_label(decision) -> str:
    if decision.choice_kind == "DECLARATION" and decision.declaration is not None:
        return (
            f"<declaration:{decision.declaration.declaration_id}:"
            f"{decision.declaration.outcome}>"
        )
    return str(decision.action) if decision.action is not None else "<none>"


def _load_compiled(args):
    if args.ruleset:
        with open(args.ruleset, "r", encoding="utf-8") as fh:
            ruleset = deserialize_ruleset(fh.read())
        return compile_ruleset_for_execution(ruleset)
    game = generate_game(
        GeneratorConfig(
            seed=args.seed,
            board_size=args.board_size,
            setup_preset=args.preset,
            allow_hybrid=args.hybrid,
        )
    )
    return game.compiled_ruleset


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="generic_chess.ai.cli.benchmark_alphabeta")
    parser.add_argument("--ruleset", default=None)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--board-size", type=int, default=8)
    parser.add_argument("--preset", default="classic_like")
    parser.add_argument("--hybrid", action="store_true")
    parser.add_argument(
        "--nodes", type=lambda value: _int_at_least(value, 0), default=100_000
    )
    parser.add_argument(
        "--max-depth", type=lambda value: _int_at_least(value, 0), default=None
    )
    parser.add_argument(
        "--repeat", type=lambda value: _int_at_least(value, 1), default=3
    )
    parser.add_argument("--fresh-tt", action="store_true", help="reset the TT before every run")
    parser.add_argument(
        "--vs-random", type=lambda value: _int_at_least(value, 0), default=0
    )
    parser.add_argument("--no-disk", action="store_true")
    args = parser.parse_args(argv)
    if args.ruleset is None:
        if args.board_size < 4:
            parser.error("--board-size must be >= 4 when generating a ruleset")
        if args.preset not in ("classic_like", "bilateral_random", "free_random"):
            parser.error(
                "--preset must be one of: classic_like, bilateral_random, free_random"
            )

    compiled = _load_compiled(args)
    limits = SearchLimits(max_nodes=args.nodes, max_depth=args.max_depth, quiescence_max_depth=4)

    print(f"ruleset fingerprint: {compiled.ruleset_fingerprint}")
    print(f"nodes: {args.nodes}  max_depth: {limits.max_depth}  repeat: {args.repeat}")

    player = AlphaBetaPlayer(compiled, use_disk_cache=not args.no_disk)
    print(f"profile cache hit: {player.evaluation_profile_cache_hit}")

    best = None
    for i in range(args.repeat):
        if args.fresh_tt:
            player.reset()
        session = GameSession(compiled)
        started = time.perf_counter()
        decision = player.choose_action(session, limits)
        elapsed = time.perf_counter() - started
        total_nodes = decision.nodes + decision.qnodes
        main_nps = decision.nodes / elapsed if elapsed > 0 else 0.0
        q_nps = decision.qnodes / elapsed if elapsed > 0 else 0.0
        total_nps = (
            total_nodes / elapsed if elapsed > 0 else 0.0
        )
        print(
            f"run {i + 1}: action={_decision_action_label(decision)} score={decision.score} "
            f"depth={decision.completed_depth} nodes={decision.nodes} qnodes={decision.qnodes} "
            f"total_nodes={total_nodes} elapsed={elapsed:.3f}s "
            f"main_nps={main_nps:,.0f} q_nps={q_nps:,.0f} total_nps={total_nps:,.0f} "
            f"tt={decision.tt_probes}/{decision.tt_hits}/{decision.tt_cutoffs} "
            f"cutoffs={decision.beta_cutoffs} result_source={decision.result_source} "
            f"reason={decision.termination_reason}"
        )
        print(f"  PV: {' '.join(str(a) for a in decision.principal_variation) or '-'}")
        if best is None or decision.nodes > best.nodes:
            best = decision

    if args.vs_random > 0:
        _vs_random(compiled, args.vs_random, args.nodes, args.seed + 10_000)
    return 0


def _vs_random(compiled, games: int, nodes: int, seed: int) -> None:
    rng = random.Random(seed)
    ab = AlphaBetaPlayer(compiled, use_disk_cache=False)
    wins = {"ab": 0, "random": 0, "draw": 0, "unresolved": 0}
    total_plies = 0
    print(f"\nAlphaBeta vs Random ({games} games, {nodes} nodes/move, seed {seed})")
    for game_idx in range(games):
        session = GameSession(compiled)
        ab_first = game_idx % 2 == 0
        while True:
            if session.result.status is not SessionStatus.ONGOING:
                break
            if session.state.ply_count >= 400:
                break
            if session.state.ply_count % 2 == (0 if ab_first else 1):
                decision = ab.choose_action(session, SearchLimits(max_nodes=nodes))
                if decision.choice_kind == "DECLARATION":
                    declaration = decision.declaration
                    if declaration is not None:
                        try:
                            session.declare(declaration.declaration_id)
                        except ValueError:
                            pass
                    break
                action = decision.action
            else:
                actions = legal_actions(session.state, compiled)
                if not actions:
                    break
                action = rng.choice(actions)
            if action is None:
                break
            session.submit(action)
            total_plies += 1
        result = session.result
        wins[_result_bucket(result, 0 if ab_first else 1)] += 1
    print(
        f"AB wins: {wins['ab']}  Random wins: {wins['random']}  draws: {wins['draw']}  "
        f"unresolved: {wins['unresolved']}  "
        f"avg plies: {total_plies / games:.1f}"
    )


if __name__ == "__main__":
    raise SystemExit(main())
