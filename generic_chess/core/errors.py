"""Public exceptions raised by the Core layer."""

from __future__ import annotations


class IllegalActionError(ValueError):
    """Raised when an action is not legal in the current state.

    Includes actions that are geometrically invalid, would expose the mover's
    anchor, forge a promotion, or are applied to a terminal state.
    """


class RuleSetMismatchError(ValueError):
    """Raised when a position/state is used with a mismatched compiled ruleset."""


def ensure_ruleset_match(position, compiled) -> None:
    """Raise :class:`RuleSetMismatchError` unless the position belongs to the ruleset."""
    if position.ruleset_fingerprint != compiled.ruleset_fingerprint:
        raise RuleSetMismatchError(
            f"position fingerprint {position.ruleset_fingerprint!r} does not match "
            f"compiled ruleset fingerprint {compiled.ruleset_fingerprint!r}"
        )
