"""Command-line replay of a GameRecord (``python -m generic_chess.cli.replay``)."""

from __future__ import annotations

import argparse
import sys
from typing import TextIO

from ..rules.compiler import compile_ruleset
from ..rules.serialization import deserialize_ruleset
from ..session.serialization import deserialize_game_record
from ..session.session import GameSession, SessionRecordError
from .render import render_session


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="generic_chess.cli.replay",
        description="Replay a GameRecord against an explicit RuleSet file.",
    )
    parser.add_argument("--ruleset", required=True, help="path to the JSON RuleSet file")
    parser.add_argument("--record", required=True, help="path to the GameRecord JSON file")
    parser.add_argument("--final-only", action="store_true", help="print only the final position")
    return parser


def main(argv: list[str] | None = None, stdout: TextIO | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    stdout = stdout if stdout is not None else sys.stdout

    try:
        with open(args.ruleset, "r", encoding="utf-8") as fh:
            ruleset_text = fh.read()
        with open(args.record, "r", encoding="utf-8") as fh:
            record_text = fh.read()
    except OSError as exc:
        print(f"error: cannot read file: {exc}", file=sys.stderr)
        return 1

    try:
        compiled = compile_ruleset(deserialize_ruleset(ruleset_text))
        record = deserialize_game_record(record_text)
        session = GameSession.replay(compiled, record)
    except (ValueError, SessionRecordError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if not args.final_only:
        print(f"ruleset {compiled.ruleset_fingerprint[:8]}  "
              f"record fingerprint {record.ruleset_fingerprint[:8]}", file=stdout)
        for rec in session.history:
            print(f"{rec.ply:>3}. player {rec.player}: {rec.action}", file=stdout)
    print(render_session(session), file=stdout)
    print(f"final result: {session.result}", file=stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
