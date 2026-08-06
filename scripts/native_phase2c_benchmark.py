"""Native Phase 2C benchmark: TT states, iterative, budgets, one-time costs.

Usage::

    python scripts/native_phase2c_benchmark.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from generic_chess.ai.evaluation.config import EvaluationConfig
from generic_chess.ai.evaluation.profile import build_ruleset_profile
from generic_chess.ai.limits import SearchLimits
from generic_chess.native import _module
from generic_chess.native.compiler import compile_native_evaluation, compile_native_rules
from generic_chess.native.engine import NativeSearchEngine
from generic_chess.session.session import GameSession


def _fixtures():
    from generic_chess.core.movement import LeapAtom, RayAtom
    from generic_chess.core.pieces import Piece, PieceType

    from tests.native_test_helpers import generated_compiled, simple_ruleset

    out = []
    for size, seed in ((4, 7), (6, 11), (8, 3)):
        compiled = generated_compiled(size=size, seed=seed)
        out.append((f"generated_{size}x{size}", compiled, GameSession(compiled)))
    # Promotion-heavy ruleset.
    n = 6
    king = PieceType("K", "K", (), is_anchor=True)
    pawn = PieceType(
        "P", "P", (LeapAtom((0, 1)), LeapAtom((0, -1))),
        is_promotable=True, promotion_target_ids=("Q",),
    )
    queen = PieceType(
        "Q", "Q", tuple(
            RayAtom((df, dr)) for df in (-1, 0, 1) for dr in (-1, 0, 1)
            if (df, dr) != (0, 0)
        ),
    )
    rows = [[None] * n for _ in range(n)]
    rows[0][0] = Piece(0, "K", "K", False)
    rows[n - 1][n - 1] = Piece(1, "K", "K", False)
    rows[1][0] = Piece(0, "P", "P", False)
    rows[1][1] = Piece(1, "P", "P", False)
    compiled = simple_ruleset(
        (king, pawn, queen), rows, drop_types=("P", "Q"),
        promotion_allowed={"P": ((), ())}, promotion_forced={"P": ((), ())},
        board_size=n,
    )
    out.append(("promotion_heavy", compiled, GameSession(compiled)))
    # Transposition-rich cycle (one move per ply).
    from test_native_history import _cycle_ruleset, _session_at_ply

    compiled = _cycle_ruleset()
    out.append(("transposition_cycle", compiled, _session_at_ply(compiled, 3)))
    return out


def main() -> int:
    config = EvaluationConfig()
    print("== fixed depth: TT off cold / TT on cold / TT on warm ==")
    print("fixture | depth | state | score | nodes | wall_ms | NPS | tt_hits")
    for label, compiled, session in _fixtures():
        profile = build_ruleset_profile(compiled, config)
        rules = compile_native_rules(compiled)
        eval_tables = compile_native_evaluation(rules, profile, config)
        engine = NativeSearchEngine(compiled, rules, eval_tables, 8)
        from generic_chess.native.adapter import pack_native_search_position

        pos = pack_native_search_position(compiled, rules, session)
        depth = 3 if compiled.board_size <= 4 else 2
        rows = []
        # TT off cold.
        t0 = time.perf_counter()
        off = _module().native_fixed_depth_search(
            rules.capsule, eval_tables.capsule, pos, depth
        )
        dt_off = (time.perf_counter() - t0) * 1000
        rows.append(
            f"{label} | {depth} | tt-off | {off['score']} | {off['nodes']} | "
            f"{dt_off:.2f} | {off['nodes']/(dt_off/1000):.0f} | 0"
        )
        # TT on cold.
        engine.clear_tt()
        t0 = time.perf_counter()
        on = _module().engine_fixed_depth_search(engine._capsule, pos, depth)
        dt_on_cold = (time.perf_counter() - t0) * 1000
        rows.append(
            f"{label} | {depth} | tt-on-cold | {on['score']} | {on['nodes']} | "
            f"{dt_on_cold:.2f} | {on['nodes']/(dt_on_cold/1000):.0f} | {on['tt_hits']}"
        )
        # TT on warm.
        t0 = time.perf_counter()
        warm = _module().engine_fixed_depth_search(engine._capsule, pos, depth)
        dt_warm = (time.perf_counter() - t0) * 1000
        rows.append(
            f"{label} | {depth} | tt-on-warm | {warm['score']} | {warm['nodes']} | "
            f"{dt_warm:.2f} | {warm['nodes']/(dt_warm/1000):.0f} | {warm['tt_hits']}"
        )
        for row in rows:
            print(row)

    print("\n== fixed node budget (16x16 generated, TT on) ==")
    from tests.native_test_helpers import generated_compiled

    compiled = generated_compiled(size=16, seed=5)
    profile = build_ruleset_profile(compiled, config)
    rules = compile_native_rules(compiled)
    eval_tables = compile_native_evaluation(rules, profile, config)
    engine = NativeSearchEngine(compiled, rules, eval_tables, 8)
    session = GameSession(compiled)
    for budget in (100, 1000, 10000):
        result = engine.search(
            session,
            SearchLimits(max_depth=12, max_nodes=budget, quiescence_max_depth=0),
        )
        print(
            f"budget {budget}: depth={result.completed_depth} nodes={result.nodes} "
            f"score={result.score} wall={result.elapsed_seconds*1000:.1f}ms "
            f"reason={result.termination_reason}"
        )

    print("\n== one-time costs ==")
    t0 = time.perf_counter()
    compiled = generated_compiled(size=6, seed=11)
    t_rules = time.perf_counter() - t0
    t0 = time.perf_counter()
    profile = build_ruleset_profile(compiled, config)
    t_profile = time.perf_counter() - t0
    t0 = time.perf_counter()
    rules = compile_native_rules(compiled)
    t_compile = time.perf_counter() - t0
    t0 = time.perf_counter()
    eval_tables = compile_native_evaluation(rules, profile, config)
    t_eval = time.perf_counter() - t0
    t0 = time.perf_counter()
    engine = NativeSearchEngine(compiled, rules, eval_tables, 8)
    t_engine = time.perf_counter() - t0
    session = GameSession(compiled)
    from generic_chess.native.adapter import pack_native_search_position

    t0 = time.perf_counter()
    pos = pack_native_search_position(compiled, rules, session)
    t_replay = time.perf_counter() - t0
    t0 = time.perf_counter()
    _module().native_iterative_search(engine._capsule, pos, 3, None, None, None)
    t_search = time.perf_counter() - t0
    print(f"rules compile: {t_rules*1000:.1f}ms | profile: {t_profile*1000:.1f}ms")
    print(f"native rules: {t_compile*1000:.1f}ms | eval tables: {t_eval*1000:.1f}ms")
    print(f"engine alloc: {t_engine*1000:.1f}ms | history replay: {t_replay*1000:.1f}ms")
    print(f"search (depth 3): {t_search*1000:.1f}ms")
    return 0


if __name__ == "__main__":
    sys.exit(main())
