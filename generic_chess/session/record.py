"""Immutable action and game records used for history and replay."""

from __future__ import annotations

from dataclasses import dataclass

from ..core.actions import Action


@dataclass(frozen=True, slots=True)
class ActionRecord:
    """One executed ply.

    ``ply`` starts at 1; ``player`` is the side that moved; the keys are the
    stable position keys immediately before and after the action.
    """

    ply: int
    player: int
    action: Action
    before_key: str
    after_key: str


@dataclass(frozen=True, slots=True)
class GameRecord:
    """Minimal, deterministic, serializable record of one game.

    Stores only what is needed to replay: the ruleset fingerprint, the ordered
    actions, and an optional resignation marker.  Everything else (winner,
    terminal status, positions) is re-derived by replaying.
    """

    schema_version: int
    ruleset_fingerprint: str
    actions: tuple[Action, ...]
    resigned_by: int | None
