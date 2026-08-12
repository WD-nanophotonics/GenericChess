"""Authoritative state-identity boundaries for Core consumers.

F1 keeps the existing byte-stable SHA-256 encodings and centralizes the
dispatch between legacy and semantic rulesets.  Callers must use this module
instead of selecting :mod:`core.keys` helpers themselves.

The five concepts are deliberately separate:

* :class:`PositionIdentity` is the ruleset-aware position identity;
* :class:`RepetitionIdentity` is the key stored in repetition counts;
* :class:`SearchStateIdentity` adds the currently required path context;
* :class:`ExternalStableKey` is deterministic and serialization-safe;
* :class:`RuntimeHash` is only a future process-local performance boundary.

F1 does not implement a runtime hash, incremental hashing, or a history
representation redesign.  Existing semantic and legacy SHA encodings remain
the source of truth for external keys.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import NewType, TYPE_CHECKING

from .errors import ensure_ruleset_match
from .keys import position_key as legacy_position_key
from .keys import semantic_position_key
from .position import GameState, Position

if TYPE_CHECKING:
    from ..rules.compiled import CompiledRuleSet


ExternalStableKey = NewType("ExternalStableKey", str)
"""Deterministic SHA-256 key safe for records and cross-process artifacts."""

RuntimeHash = NewType("RuntimeHash", int)
"""Reserved process-local hash type; construction belongs to F2."""


@dataclass(frozen=True, slots=True)
class PositionIdentity:
    """Ruleset-aware identity of one immutable :class:`Position`."""

    key: ExternalStableKey
    ruleset_fingerprint: str
    semantic: bool


@dataclass(frozen=True, slots=True)
class RepetitionIdentity:
    """Identity used as the key in a state's repetition-count map."""

    key: ExternalStableKey


@dataclass(frozen=True, slots=True)
class SearchStateIdentity:
    """Hashable search identity including current path/adjudication context."""

    ruleset_fingerprint: str
    position: PositionIdentity
    ply_count: int
    repetition_counts: tuple[tuple[str, int], ...]
    adjudication_context: tuple


def _semantic_identity_inputs(compiled):
    """Return semantic support/slots, or ``None`` for a legacy ruleset.

    Dispatch is based on the compiled ruleset type, never on a caller's
    knowledge of which key implementation happens to be available.
    """
    from ..rules.ir import CompiledSemanticRuleset

    if not isinstance(compiled, CompiledSemanticRuleset):
        return None
    if compiled.support is None:
        raise ValueError("semantic ruleset has no canonical Core support payload")
    return compiled.support, compiled.ir.aux_slots


def position_identity(position: Position, compiled: "CompiledRuleSet") -> PositionIdentity:
    """Build the authoritative position identity without changing key bytes."""
    ensure_ruleset_match(position, compiled)
    semantic_inputs = _semantic_identity_inputs(compiled)
    if semantic_inputs is None:
        key = legacy_position_key(position, compiled)
        semantic = False
    else:
        support, aux_slots = semantic_inputs
        key = semantic_position_key(position, support, aux_slots)
        semantic = True
    return PositionIdentity(
        key=ExternalStableKey(key),
        ruleset_fingerprint=compiled.ruleset_fingerprint,
        semantic=semantic,
    )


def position_identity_key(position: Position, compiled: "CompiledRuleSet") -> ExternalStableKey:
    """Return the canonical external key for a position."""
    return position_identity(position, compiled).key


def repetition_identity(position: Position, compiled: "CompiledRuleSet") -> RepetitionIdentity:
    """Return the ruleset-defined repetition identity.

    Current certified behavior counts the same external position key used by
    Core state transitions.  Keeping this as a distinct API leaves room for a
    ruleset-defined equivalence without allowing callers to bypass authority.
    """
    return RepetitionIdentity(position_identity_key(position, compiled))


def repetition_identity_key(position: Position, compiled: "CompiledRuleSet") -> ExternalStableKey:
    """Return the key to store in ``GameState.repetition_counts``."""
    return repetition_identity(position, compiled).key


def _history_adjudication_context(state: GameState, compiled) -> tuple:
    if getattr(compiled, "repetition_policy", "draw") != "continuous_check_loss":
        return ()
    history = state.history
    if not history:
        return (None, 0, ())
    current_key = history[-1].position_key
    occurrences = [
        index for index, record in enumerate(history)
        if record.position_key == current_key
    ]
    limit = max(1, int(getattr(compiled, "repetition_limit", 4)))
    start = (
        occurrences[-min(limit, len(occurrences))]
        if occurrences
        else max(0, len(history) - 1)
    )
    cycle = history[start + 1 :]
    actor_summary = tuple(
        (
            actor,
            sum(record.actor == actor for record in cycle),
            sum(record.actor == actor and record.gave_check for record in cycle),
        )
        for actor in (0, 1)
    )
    return (current_key, len(occurrences), actor_summary)


def search_state_identity(
    state: GameState,
    compiled: "CompiledRuleSet",
    *,
    position_key_override: ExternalStableKey | str | None = None,
) -> SearchStateIdentity:
    """Build the safe current search identity.

    ``position_key_override`` is only for a Core-issued lazy-child key that
    was already produced by this authority.  Repetition counts and the
    continuous-check context remain explicit; F1 does not make path-dependent
    Standard-Shogi states TT-compatible.
    """
    if position_key_override is None:
        position = position_identity(state.position, compiled)
    else:
        ensure_ruleset_match(state.position, compiled)
        position = PositionIdentity(
            key=ExternalStableKey(str(position_key_override)),
            ruleset_fingerprint=compiled.ruleset_fingerprint,
            semantic=_semantic_identity_inputs(compiled) is not None,
        )
    return SearchStateIdentity(
        ruleset_fingerprint=compiled.ruleset_fingerprint,
        position=position,
        ply_count=state.ply_count,
        repetition_counts=state.repetition_counts,
        adjudication_context=_history_adjudication_context(state, compiled),
    )


def history_adjudication_context(state: GameState, compiled) -> tuple:
    """Public owned boundary for the existing path-dependent context."""
    return _history_adjudication_context(state, compiled)


__all__ = [
    "ExternalStableKey",
    "RuntimeHash",
    "PositionIdentity",
    "RepetitionIdentity",
    "SearchStateIdentity",
    "position_identity",
    "position_identity_key",
    "repetition_identity",
    "repetition_identity_key",
    "search_state_identity",
    "history_adjudication_context",
]
