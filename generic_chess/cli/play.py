"""Two-player command-line game (``python -m generic_chess.cli.play``)."""

from __future__ import annotations

import argparse
import os
import sys
from typing import TextIO

from ..generation.config import GeneratorConfig
from ..generation.config import GenerationError
from ..generation.generator import generate_game
from ..core.actions import (
    Action,
    action_drop_base_type_id,
    action_promotion_target_id,
    action_source_square,
    action_target_square,
)
from ..core.coordinates import square_str
from ..rules.catalog import build_builtin_ruleset
from ..rules.compiler import compile_ruleset_for_execution
from ..rules.serialization import deserialize_ruleset, serialize_ruleset
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
    parser.add_argument(
        "--builtin-ruleset",
        type=str,
        default=None,
        help="use a named production RuleSet (currently western_chess)",
    )
    parser.add_argument("--record-out", type=str, default=None, help="save the GameRecord to PATH")
    parser.add_argument("--ruleset-out", type=str, default=None, help="save the actual RuleSet to PATH")
    return parser


def _load_ruleset(args) -> tuple:
    """Return ``(compiled, ruleset)``; raise _CliError on user-facing errors."""
    if args.builtin_ruleset is not None:
        explicit = [
            name for name in ("ruleset", "seed", "board_size", "preset")
            if getattr(args, name) is not None
        ]
        if args.hybrid:
            explicit.append("hybrid")
        if explicit:
            raise _CliError(
                f"--builtin-ruleset cannot be combined with --{', --'.join(explicit)}"
            )
        try:
            ruleset = build_builtin_ruleset(args.builtin_ruleset)
            return compile_ruleset_for_execution(ruleset), ruleset
        except (ValueError, TypeError) as exc:
            raise _CliError(f"cannot build built-in ruleset: {exc}") from exc
    if args.ruleset is not None:
        explicit = [
            name for name in ("builtin_ruleset", "seed", "board_size", "preset")
            if getattr(args, name) is not None
        ]
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
            compiled = compile_ruleset_for_execution(ruleset)
        except ValueError as exc:
            raise _CliError(f"invalid ruleset file: {exc}") from exc
        return compiled, ruleset
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
    return game.compiled_ruleset, game.ruleset


def _save_record(session: GameSession, path: str) -> None:
    text = serialize_game_record(session.to_record())
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text + "\n")


def _same_path(a: str, b: str) -> bool:
    """True when two paths refer to the same file (existing or not)."""
    try:
        if os.path.exists(a) and os.path.exists(b):
            return os.path.samefile(a, b)
    except OSError:
        pass
    return os.path.normcase(os.path.abspath(a)) == os.path.normcase(os.path.abspath(b))


HELP_TEXT = """commands:
  <n>          submit the n-th legal action (1-based)
  <action>     submit an action string exactly matching a legal action, e.g. e2-e4
  moves        list legal actions
  board        show the board, hands and status
  history      show the move history
  declarations list currently non-losing declarations
  declare <id> submit a declaration (a failed claim ends in LOSS)
  help         show this help
  resign       resign as the current player
  quit         quit without resigning
"""


def visible_action_alias(action: Action) -> str:
    """Return the generic coordinate alias accepted by the CLI."""
    source = action_source_square(action)
    if source is None:
        return f"{action_drop_base_type_id(action)}@{square_str(action_target_square(action))}"
    alias = f"{square_str(source)}-{square_str(action_target_square(action))}"
    promotion = action_promotion_target_id(action)
    return f"{alias}={promotion}" if promotion is not None else alias


def _resolve_action_input(command: str, actions: tuple[Action, ...]):
    """Resolve exact semantic strings before unambiguous visible aliases."""
    exact = [action for action in actions if str(action) == command]
    if exact:
        return exact[0], None
    aliases = [action for action in actions if visible_action_alias(action) == command]
    if len(aliases) == 1:
        return aliases[0], None
    if len(aliases) > 1:
        return None, f"ambiguous action alias: {command!r} (use a number or exact action string)"
    return None, None


def main(argv: list[str] | None = None, stdin: TextIO | None = None, stdout: TextIO | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    stdin = stdin if stdin is not None else sys.stdin
    stdout = stdout if stdout is not None else sys.stdout

    if (
        args.record_out is not None
        and args.ruleset is not None
        and _same_path(args.record_out, args.ruleset)
    ):
        print("error: --record-out must not overwrite the ruleset file", file=sys.stderr)
        return 2

    try:
        compiled, ruleset = _load_ruleset(args)
    except _CliError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.ruleset_out is not None:
        targets = [path for path in (args.record_out, args.ruleset) if path is not None]
        for other in targets:
            if _same_path(args.ruleset_out, other):
                print(
                    f"error: --ruleset-out must not point at the same file as {other}",
                    file=sys.stderr,
                )
                return 2
        try:
            _save_text(serialize_ruleset(ruleset), args.ruleset_out)
        except OSError as exc:
            print(f"error: cannot write ruleset file: {exc}", file=sys.stderr)
            return 1

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
        if command in ("moves", "board", "history", "declarations", "help", "resign", "quit"):
            if command == "moves":
                for line in format_actions(actions):
                    print_out(line)
            elif command == "board":
                print_out(render_session(session))
            elif command == "history":
                print_out(render_history(session))
            elif command == "declarations":
                declarations = session.available_declarations()
                if declarations:
                    for assessment in declarations:
                        print_out(
                            f"{assessment.declaration_id}: {assessment.outcome} "
                            f"(score={assessment.weighted_score})"
                        )
                else:
                    print_out("no non-losing declarations")
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

        if command.startswith("declare "):
            declaration_id = command[len("declare "):].strip()
            if not declaration_id:
                print_out("usage: declare <declaration_id>")
                continue
            try:
                result = session.declare(declaration_id)
            except ValueError as exc:
                print_out(f"cannot declare: {exc}")
                continue
            print_out(f"declared: {result}")
            break

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
            chosen, error = _resolve_action_input(command, actions)
            if error:
                print_out(error)
                continue
            if chosen is None:
                print_out(f"unknown input: {command!r} (try 'help')")
                continue
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


def _save_text(text: str, path: str) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text + "\n")


def input_line(stdin: TextIO) -> str:
    line = stdin.readline()
    if line == "":
        raise EOFError
    return line


if __name__ == "__main__":
    raise SystemExit(main())
