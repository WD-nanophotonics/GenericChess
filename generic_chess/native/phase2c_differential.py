"""Phase 2C differential CLI: TT on/off fixed depth and iterative equivalence.

Usage::

    python -m generic_chess.native.phase2c_differential
    python -m generic_chess.native.phase2c_differential --extended
"""

from __future__ import annotations

import argparse
import sys

from ..ai.evaluation.config import EvaluationConfig
from ..ai.evaluation.native_compat import NativeCompatibleEvaluator
from ..ai.evaluation.profile import build_ruleset_profile
from ..core.keys import position_key
from ..ai.limits import SearchLimits
from . import _module, native_available
from .compiler import compile_native_evaluation, compile_native_rules
from .engine import NativeSearchEngine
from .reference import canonical_pack, reference_fixed_depth_minimax


def _compare_fixture(compiled, session, label, extended: bool, problems: list):
    config = EvaluationConfig()
    profile = build_ruleset_profile(compiled, config)
    evaluator = NativeCompatibleEvaluator(compiled, profile, config)
    rules = compile_native_rules(compiled)
    eval_tables = compile_native_evaluation(rules, profile, config)
    engine = NativeSearchEngine(compiled, rules, eval_tables, 4)
    from ..native.adapter import pack_native_search_position, to_python_action

    pos = pack_native_search_position(compiled, rules, session)
    depths = (1, 2, 3) if extended else (1, 2)
    checked = 0
    for depth in depths:
        ref = reference_fixed_depth_minimax(session.state, compiled, evaluator, depth)
        off = _module().engine_fixed_depth_search(engine._capsule, pos, depth)
        _module().search_engine_clear_tt(engine._capsule)
        on = _module().engine_fixed_depth_search(engine._capsule, pos, depth)
        on_action = (
            to_python_action(rules, on["best_action"])
            if on["best_action"] is not None
            else None
        )
        checked += 2
        if off["score"] != ref[0]:
            problems.append(
                f"score mismatch fixture={label} key={position_key(session.state.position, compiled)} "
                f"history={len(session.history)} depth={depth} tt=off "
                f"python={ref[0]} native={off['score']}"
            )
        if on["score"] != ref[0]:
            problems.append(
                f"score mismatch fixture={label} key={position_key(session.state.position, compiled)} "
                f"history={len(session.history)} depth={depth} tt=on "
                f"python={ref[0]} native={on['score']}"
            )
        if off["best_action"] != on["best_action"]:
            problems.append(
                f"canonical-best mismatch fixture={label} depth={depth} "
                f"tt-off={off['best_action']} tt-on={on['best_action']}"
            )
        if ref[1] and on_action is not None:
            packed = canonical_pack(compiled, session.state, on_action)
            if packed != min(
                canonical_pack(compiled, session.state, a) for a in ref[1]
            ):
                problems.append(
                    f"returned-action-outside-reference-best-set fixture={label} "
                    f"depth={depth} action={on_action}"
                )
    # Iterative without budgets must equal the deepest fixed depth.
    deepest = max(depths)
    iterative = engine.search(
        session, SearchLimits(max_depth=deepest, quiescence_max_depth=0)
    )
    ref = reference_fixed_depth_minimax(session.state, compiled, evaluator, deepest)
    checked += 1
    if iterative.score != ref[0] or iterative.action != ref[2]:
        problems.append(
            f"iterative mismatch fixture={label} depth={deepest} "
            f"python=({ref[0]},{ref[2]}) native=({iterative.score},{iterative.action})"
        )
    return checked


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="generic_chess.native.phase2c_differential")
    parser.add_argument("--extended", action="store_true")
    args = parser.parse_args(argv)
    if not native_available():
        print("native extension is not built; run scripts/build_native_zig.py",
              file=sys.stderr)
        return 2
    from ..ai.benchmark.audit_suite import (
        build_session,
        smoke_ruleset_specs,
        standard_ruleset_specs,
    )
    from ..ai.benchmark.position_mining import mine_suite

    problems: list[str] = []
    checked = 0
    specs = standard_ruleset_specs()
    positions = mine_suite(
        specs,
        playout_seed=1,
        max_games=2,
        max_plies=12 if args.extended else 8,
        max_positions=3 if args.extended else 2,
    )
    specs_by_id = {s.fixture_id: s for s in specs}
    for pos in positions:
        compiled, session = build_session(
            specs_by_id[pos.ruleset_fixture_id], pos.action_prefix
        )
        if compiled.board_size > 6:
            continue  # keep the default CLI fast (small boards only)
        checked += _compare_fixture(
            compiled, session, pos.fixture_id, args.extended, problems
        )
    for line in problems:
        print(line)
    print(f"checked {checked} comparisons, {len(problems)} problem lines")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
