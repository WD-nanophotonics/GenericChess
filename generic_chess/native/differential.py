"""Python Core <-> native kernel differential diagnostics.

Usage::

    python -m generic_chess.native.differential --perft-depth 3
    python -m generic_chess.native.differential --fixture gen_classic_like_4_101:opening --show-actions
    python -m generic_chess.native.differential --show-attack-map
"""

from __future__ import annotations

import argparse
import sys

from ..ai.benchmark.audit_suite import (
    build_session,
    smoke_ruleset_specs,
    standard_ruleset_specs,
)
from ..ai.benchmark.position_mining import mine_suite
from . import native_available
from .adapter import (
    native_legal_actions,
    pack_native_position,
    to_python_action,
)
from .compiler import compile_native_rules
from .reference import canonical_action_set, python_legal_actions


def _run(fixture, show_actions: bool, show_attack_map: bool, perft_depth: int) -> int:
    from generic_chess.native.adapter import native_perft
    from generic_chess.native.reference import python_perft

    compiled, session = build_session(fixture["ruleset"], fixture["prefix"])
    rules = compile_native_rules(compiled)
    pos = pack_native_position(compiled, rules, session.state)
    print(f"fixture: {fixture['id']} fingerprint: {compiled.ruleset_fingerprint}")
    py_actions = python_legal_actions(session.state, compiled)
    nat_actions = [to_python_action(rules, a) for a in native_legal_actions(rules, pos)]
    py_set = set(canonical_action_set(py_actions))
    nat_set = set(canonical_action_set(nat_actions))
    print(f"legal actions: python={len(py_actions)} native={len(nat_actions)} equal={py_set == nat_set}")
    if show_actions and py_set != nat_set:
        only_py = py_set - nat_set
        only_nat = nat_set - py_set
        print("only python:", sorted(only_py))
        print("only native:", sorted(only_nat))
    if show_attack_map:
        from ..core.attacks import pseudo_attacks
        from . import _module

        for owner in (0, 1):
            nat = set(_module().native_attack_map(rules.capsule, pos, owner))
            py = {
                s.file + s.rank * compiled.board_size
                for s in pseudo_attacks(session.state.position, owner, compiled)
            }
            print(
                f"attack owner {owner}: equal={nat == py} "
                f"only_nat={sorted(nat - py)} only_py={sorted(py - nat)}"
            )
    for d in range(1, perft_depth + 1):
        n = native_perft(rules, pos, d)["nodes"]
        p = python_perft(compiled, session.state, d)
        print(f"perft depth {d}: native={n} python={p} equal={n == p}")
    return 0 if py_set == nat_set else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="generic_chess.native.differential")
    parser.add_argument("--fixture", default=None, help="fixture id (or run a default set)")
    parser.add_argument("--show-actions", action="store_true")
    parser.add_argument("--show-attack-map", action="store_true")
    parser.add_argument("--perft-depth", type=int, default=2)
    args = parser.parse_args(argv)
    if not native_available():
        print("native extension is not built; run scripts/build_native_zig.py", file=sys.stderr)
        return 2

    specs = standard_ruleset_specs()
    specs_by_id = {s.fixture_id: s for s in specs}
    positions = mine_suite(
        specs, playout_seed=1, max_games=2, max_plies=30, max_positions=2
    )
    positions_by_id = {p.fixture_id: p for p in positions}
    selected = []
    if args.fixture:
        pos = positions_by_id.get(args.fixture)
        if pos is None:
            print(f"unknown fixture {args.fixture!r}", file=sys.stderr)
            return 2
        selected = [pos]
    else:
        selected = positions[:4]

    failed = 0
    for pos in selected:
        spec = specs_by_id[pos.ruleset_fixture_id]
        fixture = {
            "id": pos.fixture_id,
            "ruleset": spec,
            "prefix": pos.action_prefix,
        }
        failed += _run(
            fixture,
            show_actions=args.show_actions,
            show_attack_map=args.show_attack_map,
            perft_depth=args.perft_depth,
        )
        print()
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
