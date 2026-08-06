"""CLI entry point: ``python -m generic_chess.ai.benchmark``."""

from __future__ import annotations

import argparse
import json
import sys

from .profiles import ALL_PROFILES, all_profiles, profile_by_name
from .runner import RunConfig, run_benchmark
from .suite import DEFAULT_SUITE


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="generic_chess.ai.benchmark",
        description="Paired-control SearchTuning benchmark for GenericChess.",
    )
    parser.add_argument("--profile", choices=list(ALL_PROFILES), default="pvs")
    parser.add_argument("--all-profiles", action="store_true")
    parser.add_argument("--list-profiles", action="store_true")
    parser.add_argument("--seconds", type=float, default=1.0)
    parser.add_argument("--nodes", type=int, default=None)
    parser.add_argument("--max-plies", type=int, default=120)
    parser.add_argument("--out-dir", default="artifacts/bench")
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args(argv)

    if args.list_profiles:
        for profile in all_profiles():
            print(profile.name)
        return 0

    if args.all_profiles:
        profiles = all_profiles()
    else:
        profiles = [profile_by_name(args.profile)]

    try:
        for candidate in profiles:
            control = profile_by_name("baseline")
            out_dir = args.out_dir
            if args.all_profiles:
                out_dir = f"{args.out_dir}/{candidate.name}"
            summary = run_benchmark(
                RunConfig(
                    control=control,
                    candidate=candidate,
                    suite=DEFAULT_SUITE,
                    seconds=args.seconds,
                    nodes=args.nodes,
                    max_plies=args.max_plies,
                ),
                out_dir,
                resume=args.resume,
            )
            print(f"[{candidate.name}] {json.dumps(summary, sort_keys=True)}")
    except Exception as exc:  # human-readable failures, no traceback
        print(f"benchmark failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
