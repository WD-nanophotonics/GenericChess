"""Small catalog of production-built RuleSets."""

from __future__ import annotations

from .schema import RuleSet
from .western_chess import build_western_chess_ruleset


_BUILTIN_BUILDERS = {
    "western_chess": build_western_chess_ruleset,
}


def builtin_ruleset_names() -> tuple[str, ...]:
    """Return the exact names accepted by :func:`build_builtin_ruleset`."""
    return tuple(_BUILTIN_BUILDERS)


def build_builtin_ruleset(name: str) -> RuleSet:
    """Build a named production RuleSet; reject unknown names exactly."""
    if not isinstance(name, str):
        raise ValueError(f"unknown built-in ruleset {name!r}")
    try:
        builder = _BUILTIN_BUILDERS[name]
    except KeyError as exc:
        raise ValueError(
            f"unknown built-in ruleset {name!r}; expected one of {builtin_ruleset_names()}"
        ) from exc
    return builder()

