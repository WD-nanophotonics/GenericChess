"""Two-player command-line game (``python -m generic_chess.cli.play``)."""

from __future__ import annotations

import argparse
import os
import sys
from typing import TextIO

from ..generation.config import GeneratorConfig
from ..generation.config import GenerationError
from ..generation.generator import generate_game
from ..rules.compiler import compile_ruleset
from ..rules.serialization import deserialize_ruleset
from ..session.serialization import serialize_game_record
from ..session.session import GameSession, SessionFinishedError
from .render import format_actions, render_history, render_session, render_status


class _CliError(Exception):
    """User-facing CLI error with an already-readable message."""


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="generic_chess.cli.play",
        description="Two-player generic chess session (no UI).",
    )
    parser.add_argument("--seed", type=int, default=None, help="generator seed (default 42)")
    parser.add_argument("--board-size", type=int, default=None, help="board size (default 8)")
    parser.add_argument(
        "--preset",
        choices=("classic_like", "bilateral_random", "free_random"),
        default=None,
        help="setup preset (default classic_like)",
    )
    parser.add_argument("--hybrid", action="store_true", help="allow hybrid leap/ray pieces")
    parser.add_argument("--ruleset", type=str, default=None, help="path to a JSON RuleSet file")
    parser.add_argument("--record-out", type=str, default=None, help="save the GameRecord to PATH")
    return parser


def _load_ruleset(args) -> tuple:
    """Return the compiled ruleset; raise _CliError on user-facing errors."""
    if args.ruleset is not None:
        explicit = [name for name in ("seed", "board_size", "preset") if getattr(args, name) is not None]
        if args.hybrid:
            explicit.append("hybrid")
        if explicit:
            raise _CliError(
                f"--ruleset cannot be combined with --{', --'.join(explicit)}"
            )
        try:
            with open(args.ruleset, "r", encoding="utf-8") as fh:
                text = fh.read()
        except OSError as exc:
            raise _CliError(f"cannot read ruleset file: {exc}") from exc
        try:
            ruleset = deserialize_ruleset(text)
            compiled = compile_ruleset(ruleset)
        except ValueError as exc:
            raise _CliError(f"invalid ruleset file: {exc}") from exc
        return compiled
    seed = args.seed if args.seed is not None else 42
    board_size = args.board_size if args.board_size is not None else 8
    preset = args.preset if args.preset is not None else "classic_like"
    try:
        game = generate_game(
            GeneratorConfig(
                seed=seed,
                board_size=board_size,
                setup_preset=preset,
                allow_hybrid=args.hybrid,
            )
        )
    except (ValueError, GenerationError) as exc:
        raise _CliError(f"cannot generate game: {exc}") from exc
    return game.compiled_ruleset


def _save_record(session: GameSession, path: str) -> None:
    text = serialize_game_record(session.to_record())
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text + "\n")


HELP_TEXT = """commands:
  <n>          submit the n-th legal action (1-based)
  <action>     submit an action string exactly matching a legal action, e.g. e2-e4
  moves        list legal actions
  board        show the board, hands and status
  history      show the move history
  help         show this help
  resign       resign as the current player
  quit         quit without resigning
"""


def main(argv: list[str] | None = None, stdin: TextIO | None = None, stdout: TextIO | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    stdin = stdin if stdin is not None else sys.stdin
    stdout = stdout if stdout is not None else sys.stdout

    if args.record_out is not None and args.ruleset is not None:
        try:
            if os.path.exists(args.record_out) and os.path.exists(args.ruleset):
                if os.path.samefile(args.record_out, args.ruleset):
                    print("error: --record-out must not overwrite the ruleset file", file=sys.stderr)
                    return 2
        except OSError:
            pass

    try:
        compiled = _load_ruleset(args)
    except _CliError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    session = GameSession(compiled)
    record_path = args.record_out
    save_on_exit = record_path is not None

    def print_out(*parts: object) -> None:
        print(*parts, file=stdout)

    print_out(render_session(session))
    while True:
        if session.result.status.name != "ONGOING":
            break
        actions = session.legal_actions()
        if not actions:
            break  # Core already marks the terminal state
        print_out("legal actions:")
        for line in format_actions(actions):
            print_out(line)
        try:
            raw = input_line(stdin)
        except EOFError:
            break
        command = raw.strip()
        if not command:
            continue
        if command in ("moves", "board", "history", "help", "resign", "quit"):
            if command == "moves":
                for line in format_actions(actions):
                    print_out(line)
            elif command == "board":
                print_out(render_session(session))
            elif command == "history":
                print_out(render_history(session))
            elif command == "help":
                print_out(HELP_TEXT)
            elif command == "resign":
                try:
                    result = session.resign()
                except SessionFinishedError as exc:
                    print_out(f"cannot resign: {exc}")
                    continue
                print_out(f"resigned: {result}")
                break
            else:  # quit
                break
            continue

        # Numbered action or exact action string.
        chosen = None
        if command.isdigit():
            index = int(command)
            if 1 <= index <= len(actions):
                chosen = actions[index - 1]
            else:
                print_out(f"invalid action number: {command}")
                continue
        else:
            matches = [a for a in actions if str(a) == command]
            if not matches:
                print_out(f"unknown input: {command!r} (try 'help')")
                continue
            chosen = matches[0]
        try:
            session.submit(chosen)
        except ValueError as exc:
            print_out(f"cannot submit: {exc}")
            continue
        print_out(render_status(session))

    print_out(f"final result: {session.result}")

    if save_on_exit:
        try:
            _save_record(session, record_path)
        except OSError as exc:
            print(f"error: cannot write record file: {exc}", file=sys.stderr)
            return 1
        print_out(f"record saved to {record_path}")
    return 0


def input_line(stdin: TextIO) -> str:
    line = stdin.readline()
    if line == "":
        raise EOFError
    return line


if __name__ == "__main__":
    raise SystemExit(main())
