"""Plain-text rendering for boards, hands, actions and session status."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..core.actions import Action
from ..core.attacks import is_in_check
from ..core.coordinates import Square, square_to_index
from ..core.position import Position

if TYPE_CHECKING:
    from ..session.session import GameSession


def _cell_text(piece) -> str:
    if piece is None:
        return "."
    return ("+" if piece.promoted else "") + piece.current_type_id


def render_board(position: Position, n: int) -> str:
    """Render the board with file/rank coordinates (rank n-1 on top)."""
    max_cell = max([1] + [len(_cell_text(p)) for p in position.board if p is not None])
    cell_w = max_cell + 1
    lines = []
    # File labels a..z.
    header = "   " + "".join((chr(ord("a") + f) if f < 26 else str(f)).ljust(cell_w) for f in range(n))
    lines.append(header)
    for rank in range(n - 1, -1, -1):
        cells = []
        for file in range(n):
            piece = position.board[square_to_index(Square(file, rank), n)]
            cells.append(_cell_text(piece).ljust(cell_w))
        lines.append(f"{rank + 1:>2} " + "".join(cells))
    return "\n".join(lines)


def _hand_text(position: Position, player: int) -> str:
    hand = position.hands[player]
    if not hand.counts:
        return "(empty)"
    return ", ".join(f"{tid}x{count}" for tid, count in hand.counts)


def render_hands(position: Position) -> str:
    return (
        f"player 0 hand: {_hand_text(position, 0)}\n"
        f"player 1 hand: {_hand_text(position, 1)}"
    )


def format_actions(actions: tuple[Action, ...] | list[Action]) -> list[str]:
    """Numbered, human-readable legal actions starting from 1."""
    return [f"{i}. {action}" for i, action in enumerate(actions, start=1)]


def render_status(session: "GameSession") -> str:
    pos = session.state.position
    side = pos.side_to_move
    n = pos.board_size()
    check = "yes" if is_in_check(pos, side, session.compiled) else "no"
    return (
        f"ruleset {session.compiled.ruleset_fingerprint[:8]}  "
        f"ply {session.state.ply_count}  side to move {side}  check {check}  "
        f"result {session.result}"
    )


def render_session(session: "GameSession") -> str:
    pos = session.state.position
    n = pos.board_size()
    return "\n".join(
        [
            render_status(session),
            render_board(pos, n),
            render_hands(pos),
        ]
    )


def render_history(session: "GameSession") -> str:
    if not session.history:
        return "(no moves yet)"
    lines = []
    for rec in session.history:
        lines.append(f"{rec.ply:>3}. player {rec.player}: {rec.action}")
    return "\n".join(lines)
