"""CLI for the native-readiness performance audit.

Examples::

    python -m generic_chess.ai.cli.audit_native_readiness --suite smoke --nodes 1000 --repeats 1
    python -m generic_chess.ai.cli.audit_native_readiness --suite standard --nodes 10000 100000 --repeats 3
    python -m generic_chess.ai.cli.audit_native_readiness --suite representative --instrument
    python -m generic_chess.ai.cli.audit_native_readiness --generate-correctness-corpus
"""

from __future__ import annotations

import argparse
import dataclasses
import shutil
import sys
from pathlib import Path

import json

from ..alphabeta.tuning import SearchTuning
from ..benchmark.audit_report import merge_summaries, write_csv_detail, write_reports
from ..benchmark.correctness_corpus import write_corpus
from ..benchmark.native_readiness import (
    AuditConfig,
    environment_info,
    run_audit,
    write_full_suite_manifest,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="generic_chess.ai.cli.audit_native_readiness",
        description="Multi-RuleSet native-readiness performance audit.",
    )
    parser.add_argument(
        "--suite",
        choices=("smoke", "standard", "representative"),
        default="smoke",
        help="which deterministic suite to run",
    )
    parser.add_argument(
        "--nodes",
        nargs="+",
        type=int,
        default=None,
        help="node budgets (default: 1000 for smoke, 10000 100000 otherwise)",
    )
    parser.add_argument("--repeats", type=int, default=3, help="measured repeats after warm-up")
    parser.add_argument("--instrument", action="store_true", help="run instrumented audit subset")
    parser.add_argument(
        "--lazy-successors",
        action="store_true",
        help="experimental: use lazy successor handles (A/B via SearchTuning)",
    )
    parser.add_argument("--out", default="artifacts/native_readiness/latest")
    parser.add_argument("--positions-limit", type=int, default=None)
    parser.add_argument(
        "--span-positions",
        type=int,
        default=None,
        help="stride-select this many positions across the whole suite (all budgets)",
    )
    parser.add_argument("--max-boardsize", type=int, default=None)
    parser.add_argument(
        "--large-budget-cap",
        type=int,
        default=None,
        help="cap positions for budgets > 50000 nodes",
    )
    parser.add_argument("--no-core-profiling", action="store_true")
    parser.add_argument("--profiler", action="store_true", help="run cProfile/tracemalloc subset")
    parser.add_argument("--profile-fixtures", type=int, default=2)
    parser.add_argument(
        "--no-docs-copy",
        action="store_true",
        help="do not copy latest md/json into docs/performance",
    )
    parser.add_argument(
        "--generate-correctness-corpus",
        nargs="?",
        const="tests/fixtures/native_correctness_corpus_v1.json",
        default=None,
        metavar="PATH",
        help="write the correctness corpus JSON and exit",
    )
    parser.add_argument(
        "--generate-suite-manifest",
        nargs="?",
        const="tests/fixtures/native_readiness_suite_v1.json",
        default=None,
        metavar="PATH",
        help="mine the full standard suite and write the versioned manifest JSON, then exit",
    )
    parser.add_argument("--csv", default=None, help="optional CSV detail path")
    parser.add_argument(
        "--merge",
        default=None,
        help="merge node_budget/instrumented/profiler blocks from another audit_summary.json",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.generate_correctness_corpus is not None:
            path = write_corpus(args.generate_correctness_corpus, commit=environment_info()["commit"])
            print(f"correctness corpus written to {path}")
            return 0
        if args.generate_suite_manifest is not None:
            data = write_full_suite_manifest(args.generate_suite_manifest)
            print(
                f"suite manifest written to {args.generate_suite_manifest} "
                f"({len(data['rulesets'])} rulesets, {len(data['positions'])} positions)"
            )
            return 0
        if args.repeats < 1:
            print("--repeats must be >= 1", file=sys.stderr)
            return 2
        nodes = args.nodes
        if nodes is None:
            nodes = (1000,) if args.suite == "smoke" else (10000, 100000)
        if any(n < 1 for n in nodes):
            print("node budgets must be positive", file=sys.stderr)
            return 2
        config = AuditConfig(
            suite_name=args.suite,
            node_budgets=tuple(nodes),
            repeats=args.repeats,
            instrument=args.instrument,
            positions_limit=args.positions_limit,
            span_positions=args.span_positions,
            max_board_size=args.max_boardsize,
            large_budget_cap=args.large_budget_cap,
            out_dir=args.out,
            run_core_profiling=not args.no_core_profiling,
            run_profiler=args.profiler,
            profile_fixture_count=args.profile_fixtures,
        )
        if args.lazy_successors:
            config = dataclasses.replace(
                config,
                tuning=SearchTuning(use_lazy_successors=True),
            )
        summary = run_audit(config)
        if args.merge:
            with open(args.merge, encoding="utf-8") as fh:
                extra = json.load(fh)
            summary = merge_summaries(summary, extra)
        write_reports(summary, args.out)
        if args.csv:
            write_csv_detail(summary, args.csv)
        if not args.no_docs_copy:
            docs = Path("docs/performance")
            docs.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(
                Path(args.out) / "native_readiness_latest.json",
                docs / "native_readiness_latest.json",
            )
            shutil.copyfile(
                Path(args.out) / "native_readiness_latest.md",
                docs / "native_readiness_latest.md",
            )
        suite = summary.get("suite", {})
        print(
            f"audit ok: suite={args.suite} "
            f"rulesets={suite.get('ruleset_count')} positions={suite.get('position_count')} "
            f"budgets={nodes} -> {args.out}"
        )
        return 0
    except Exception as exc:  # human-readable failures, no traceback
        print(f"audit failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
