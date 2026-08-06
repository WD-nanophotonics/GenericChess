"""Python/native fixed-depth search differential CLI.

Usage::

    python -m generic_chess.native.search_differential
    python -m generic_chess.native.search_differential --extended

The normal mode runs the committed corpus plus targeted and fuzz positions at
depths 1-2; ``--extended`` widens the fuzz and depth range.  Mismatch output
includes the fixture id, fingerprint, position key, history length, depth,
Python/native scores, best actions and PV.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from ..ai.evaluation.config import EvaluationConfig
from ..ai.evaluation.native_compat import NativeCompatibleEvaluator
from ..ai.evaluation.profile import build_ruleset_profile
from ..core.keys import position_key
from . import native_available
from .compiler import compile_native_evaluation, compile_native_rules
from .reference import canonical_pack, reference_fixed_depth_minimax
from .search import native_fixed_depth_search


def _compare(compiled, session, depth, label) -> list[str]:
    config = EvaluationConfig()
    profile = build_ruleset_profile(compiled, config)
    evaluator = NativeCompatibleEvaluator(compiled, profile, config)
    rules = compile_native_rules(compiled)
    eval_tables = compile_native_evaluation(rules, profile, config)
    ref = reference_fixed_depth_minimax(session.state, compiled, evaluator, depth)
    native = native_fixed_depth_search(compiled, rules, eval_tables, session, depth)
    problems = []
    if native.score != ref[0]:
        problems.append(
            f"score mismatch: python={ref[0]} native={native.score}"
        )
    if native.action != ref[2]:
        problems.append(
            f"canonical-best mismatch: python={ref[2]} native={native.action}"
        )
    if native.action is not None and native.action not in ref[1]:
        problems.append("returned-action-outside-reference-best-set")
    if problems:
        return [
            f"fixture={label} fingerprint={compiled.ruleset_fingerprint} "
            f"key={position_key(session.state.position, compiled)} "
            f"history={len(session.history)} depth={depth}",
            *[f"  {p}" for p in problems],
            f"  python pv={[str(a) for a in ref[3]]} "
            f"native pv={[str(a) for a in native.principal_variation]}",
        ]
    return []


def _corpus_runs():
    from ..ai.benchmark.audit_suite import (
        build_session,
        standard_ruleset_specs,
    )

    path = (
        Path(__file__).resolve().parent.parent.parent
        / "tests"
        / "fixtures"
        / "native_search_corpus_v1.json"
    )
    fixtures = json.loads(path.read_text(encoding="utf-8"))["fixtures"]
    specs = {s.fixture_id: s for s in standard_ruleset_specs()}
    for fixture in fixtures:
        compiled, session = build_session(
            specs[fixture["ruleset_fixture_id"]],
            tuple(fixture["action_prefix"]),
        )
        yield compiled, session, fixture["fixture_id"]


def _targeted_runs():
    from ..ai.benchmark.targeted_fixtures import build_targeted_fixtures
    from ..core.actions import action_from_dict
    from ..session.session import GameSession

    for fixture in build_targeted_fixtures():
        session = GameSession(fixture.compiled)
        for action_dict in fixture.action_prefix:
            session.submit(action_from_dict(action_dict))
        yield fixture.compiled, session, fixture.fixture_id


def _fuzz_runs(extended: bool):
    from ..ai.benchmark.audit_suite import (
        build_session,
        smoke_ruleset_specs,
    )
    from ..ai.benchmark.position_mining import mine_suite

    specs = smoke_ruleset_specs()
    positions = mine_suite(
        specs,
        playout_seed=9,
        max_games=3 if extended else 2,
        max_plies=20 if extended else 16,
        max_positions=4 if extended else 3,
    )
    for pos in positions:
        spec = next(s for s in specs if s.fixture_id == pos.ruleset_fixture_id)
        compiled, session = build_session(spec, pos.action_prefix)
        yield compiled, session, pos.fixture_id


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="generic_chess.native.search_differential")
    parser.add_argument("--extended", action="store_true")
    args = parser.parse_args(argv)
    if not native_available():
        print("native extension is not built; run scripts/build_native_zig.py",
              file=sys.stderr)
        return 2
    problems: list[str] = []
    checked = 0
    for compiled, session, label in _corpus_runs():
        for depth in (1, 2):
            checked += 1
            problems.extend(_compare(compiled, session, depth, label))
    for compiled, session, label in _targeted_runs():
        for depth in (1, 2):
            checked += 1
            problems.extend(_compare(compiled, session, depth, label))
    for compiled, session, label in _fuzz_runs(args.extended):
        depths = (1, 2, 3) if args.extended else (1, 2)
        for depth in depths:
            checked += 1
            problems.extend(_compare(compiled, session, depth, label))
    for line in problems:
        print(line)
    print(f"checked {checked} (python, native) comparisons, "
          f"{len(problems)} mismatch lines")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
