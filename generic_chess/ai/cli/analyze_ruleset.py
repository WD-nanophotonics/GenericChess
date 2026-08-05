"""Dump a RuleSet evaluation profile.

Usage::

    python -m generic_chess.ai.cli.analyze_ruleset --ruleset rules.json [--json-out profile.json]
    python -m generic_chess.ai.cli.analyze_ruleset --seed 42 [--board-size 8]
"""

from __future__ import annotations

import argparse
import json
import sys
import time

from ...generation.config import GeneratorConfig
from ...generation.generator import generate_game
from ...rules.serialization import deserialize_ruleset
from ...rules.compiler import compile_ruleset
from ..evaluation.cache import EvaluationProfileCache
from ..evaluation.config import EvaluationConfig
from ..evaluation.diagnostics import profile_report, report_text


def _load_compiled(args):
    if args.ruleset:
        with open(args.ruleset, "r", encoding="utf-8") as fh:
            ruleset = deserialize_ruleset(fh.read())
        return compile_ruleset(ruleset)
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
    parser = argparse.ArgumentParser(prog="generic_chess.ai.cli.analyze_ruleset")
    parser.add_argument("--ruleset", default=None)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--board-size", type=int, default=8)
    parser.add_argument("--preset", default="classic_like")
    parser.add_argument("--hybrid", action="store_true")
    parser.add_argument("--json-out", default=None)
    parser.add_argument("--no-disk", action="store_true")
    args = parser.parse_args(argv)
    try:
        compiled = _load_compiled(args)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    config = EvaluationConfig()
    cache = EvaluationProfileCache(use_disk=not args.no_disk)
    started = time.monotonic()
    profile, hit = cache.get_or_build(compiled, config)
    elapsed = time.monotonic() - started
    report = profile_report(profile, hit, elapsed)
    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as fh:
            json.dump(report, fh, sort_keys=True, indent=2)
        print(f"profile written to {args.json_out}")
    else:
        print(report_text(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
