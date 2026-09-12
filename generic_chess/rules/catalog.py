"""Small catalog of production-built RuleSets."""

from __future__ import annotations

from .schema import RuleSet
from .western_chess import build_western_chess_ruleset
from .standard_shogi import build_standard_shogi_ruleset


_BUILTIN_BUILDERS = {
    "western_chess": build_western_chess_ruleset,
    "standard_shogi": build_standard_shogi_ruleset,
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


def resolve_builtin_ruleset_by_fingerprint(fingerprint: str) -> tuple[str, RuleSet] | None:
    """Resolve a production built-in by its canonical execution fingerprint.

    The resolver deliberately rebuilds each catalog entry through the
    production compiler; arbitrary or guessed fingerprints never resolve.
    """
    if not isinstance(fingerprint, str):
        return None
    from .compiler import compile_ruleset_for_execution

    for name in builtin_ruleset_names():
        ruleset = build_builtin_ruleset(name)
        compiled = compile_ruleset_for_execution(ruleset)
        if compiled.ruleset_fingerprint == fingerprint:
            return name, ruleset
    return None
