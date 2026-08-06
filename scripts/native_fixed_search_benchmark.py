"""Fixed-depth search microbenchmark: Python reference minimax vs a plain
Python fixed-depth alpha-beta vs the native fixed-depth search.

All three use the same material-only native-compatible evaluator and the same
numeric tie-break, so the wall-time comparison isolates search throughput.
Compile/pack/replay costs are reported separately from the search wall time.

Usage::

    python scripts/native_fixed_search_benchmark.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from generic_chess.ai.evaluation.config import EvaluationConfig
from generic_chess.ai.evaluation.native_compat import NativeCompatibleEvaluator
from generic_chess.ai.evaluation.profile import build_ruleset_profile
from generic_chess.native.compiler import compile_native_evaluation, compile_native_rules
from generic_chess.native.reference import (
    canonical_pack,
    reference_fixed_depth_minimax,
)
from generic_chess.native.search import native_fixed_depth_search


def _python_fixed_alpha_beta(state, compiled, evaluator, depth, ply=0):
    """Plain fixed-depth negamax/alpha-beta (no TT/qsearch/ordering)."""
    terminal = state.terminal_status
    if terminal.is_terminal:
        from generic_chess.native.reference import reference_terminal_score

        return reference_terminal_score(
            terminal, state.position.side_to_move, ply
        ), None
    if depth <= 0:
        return evaluator.evaluate(state), None
    best = -10**12
    best_action = None
    from generic_chess.core.transition import legal_successors

    for action, child in sorted(
        legal_successors(state, compiled), key=lambda pair: str(pair[0])
    ):
        score, _ = _python_fixed_alpha_beta(
            child, compiled, evaluator, depth - 1, ply + 1
        )
        score = -score
        if score > best:
            best = score
            best_action = action
    return best, best_action


def _fixtures():
    from generic_chess.ai.benchmark.audit_suite import (
        build_session,
        standard_ruleset_specs,
    )
    from generic_chess.core.movement import LeapAtom, RayAtom
    from generic_chess.core.pieces import Piece, PieceType
    from generic_chess.session.session import GameSession

    from tests.native_test_helpers import simple_ruleset

    specs = {s.fixture_id: s for s in standard_ruleset_specs()}
    out = []
    for fid in (
        "gen_classic_like_4_101",
        "gen_free_random_6_202",
        "gen_bilateral_random_4_102",
    ):
        compiled, session = build_session(specs[fid], ())
        out.append((fid, compiled, session))

    n = 8
    king = PieceType("K", "K", (), is_anchor=True)
    rook = PieceType(
        "R", "R", (RayAtom((0, 1)), RayAtom((0, -1)), RayAtom((1, 0)), RayAtom((-1, 0)))
    )
    leaper = PieceType("L", "L", (LeapAtom((2, 1)), LeapAtom((-2, 1)), LeapAtom((2, -1)), LeapAtom((-2, -1))))
    rows = [[None] * n for _ in range(n)]
    rows[0][0] = Piece(0, "K", "K", False)
    rows[n - 1][n - 1] = Piece(1, "K", "K", False)
    rows[1][0] = Piece(0, "R", "R", False)
    rows[1][1] = Piece(0, "L", "L", False)
    rows[n - 2][n - 1] = Piece(1, "R", "R", False)
    rows[n - 2][n - 2] = Piece(1, "L", "L", False)
    compiled = simple_ruleset(
        (king, rook, leaper), rows, drop_types=("R", "L"), board_size=n
    )
    out.append(("custom_ray_leap_8", compiled, GameSession(compiled)))
    return out


def main() -> int:
    config = EvaluationConfig()
    print(
        "fixture | depth | py_minimax(s,nodes) | py_ab(s,nodes) | "
        "native(s,nodes) | native wall | py_ab wall | speedup | compile | replay"
    )
    for label, compiled, session in _fixtures():
        profile = build_ruleset_profile(compiled, config)
        evaluator = NativeCompatibleEvaluator(compiled, profile, config)
        t0 = time.perf_counter()
        rules = compile_native_rules(compiled)
        eval_tables = compile_native_evaluation(rules, profile, config)
        compile_s = time.perf_counter() - t0
        t0 = time.perf_counter()
        native_fixed_depth_search(compiled, rules, eval_tables, session, 1)
        replay_s = time.perf_counter() - t0

        depth = 3 if compiled.board_size <= 4 else 2
        t0 = time.perf_counter()
        ref = reference_fixed_depth_minimax(session.state, compiled, evaluator, depth)
        py_mm_s = time.perf_counter() - t0
        t0 = time.perf_counter()
        py_score, py_action = _python_fixed_alpha_beta(
            session.state, compiled, evaluator, depth
        )
        py_ab_s = time.perf_counter() - t0
        t0 = time.perf_counter()
        native = native_fixed_depth_search(
            compiled, rules, eval_tables, session, depth
        )
        native_s = time.perf_counter() - t0
        speedup = py_ab_s / native_s if native_s > 0 else float("inf")
        assert py_score == ref[0] == native.score
        assert (py_action is None) == (native.action is None)
        print(
            f"{label} | {depth} | {ref[0]},{ref[4]} | {py_score},- | "
            f"{native.score},{native.nodes} | {native_s:.4f}s | {py_ab_s:.4f}s | "
            f"{speedup:.1f}x | {compile_s:.3f}s | {replay_s:.3f}s"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
