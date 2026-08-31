"""Pure, action-independent declaration/claim assessment."""

from __future__ import annotations

from dataclasses import dataclass

from .attacks import is_in_check
from .position import GameState, Position


class InvalidDeclarationError(ValueError):
    """The caller selected an unknown or incorrectly bound declaration."""


@dataclass(frozen=True, slots=True)
class DeclarationAssessment:
    declaration_id: str
    actor: int
    outcome: str
    weighted_score: int | None = None


def _declarations(compiled):
    return tuple(getattr(compiled, "declarations", ()))


def _state_parts(state):
    if isinstance(state, GameState):
        return state.position, state.ply_count
    if isinstance(state, Position):
        return state, 0
    raise TypeError("state must be a Position or GameState")


def _owner_matches(selector: str, piece_owner: int, actor: int) -> bool:
    if selector == "any":
        return True
    if selector == "self":
        return piece_owner == actor
    return piece_owner != actor


def _compare(op: str, left: int, right: int) -> bool:
    return {
        "eq": left == right,
        "ne": left != right,
        "lt": left < right,
        "le": left <= right,
        "gt": left > right,
        "ge": left >= right,
    }.get(op, False)


def _fixed_index(ref, board_size: int) -> int | None:
    if ref is None or ref.kind != "fixed" or ref.square is None:
        return None
    file, rank = ref.square
    if not (0 <= file < board_size and 0 <= rank < board_size):
        return None
    return rank * board_size + file


def _spatial_holds(spatial, index: int, declaration, board_size: int) -> bool:
    if spatial.kind == "zone":
        zone = declaration.zones.get(spatial.zone_id)
        return zone is not None and index in zone.squares
    if spatial.kind == "exact" and spatial.refs:
        return index == _fixed_index(spatial.refs[0], board_size)
    return False


def _guard_holds(guard, position: Position, declaration, actor: int) -> bool:
    board_size = int(len(position.board) ** 0.5)
    if guard.location != "board":
        return False
    if guard.subject_ref is not None:
        indices = (_fixed_index(guard.subject_ref, board_size),)
    else:
        indices = range(len(position.board))
    count = 0
    for index in indices:
        if index is None:
            continue
        piece = position.board[index]
        if piece is None or not _owner_matches(guard.owner, piece.owner, actor):
            continue
        if guard.type_ref.kind == "explicit":
            selected = (
                piece.base_type_id
                if guard.compare_field == "base"
                else piece.current_type_id
            )
            if selected != guard.type_ref.type_id:
                continue
        elif guard.type_ref.kind != "any":
            return False
        if guard.promoted != "any" and ((guard.promoted == "yes") != piece.promoted):
            continue
        if not _spatial_holds(guard.spatial, index, declaration, board_size):
            continue
        count += 1
    value = (1 if count else 0) if guard.aggregation == "exists" else count
    return _compare(guard.comparison, value, guard.value)


def _in_check(position: Position, actor: int, compiled) -> bool:
    from .semantic_executor import semantic_engine_for

    engine = semantic_engine_for(compiled)
    return engine.in_check(position, actor) if engine is not None else is_in_check(position, actor, compiled)


def _score(position: Position, declaration, actor: int) -> int:
    metric = declaration.weighted_metric
    if metric is None:
        return 0
    board_size = int(len(position.board) ** 0.5)
    weights = dict(metric.weights)
    score = 0
    for index, piece in enumerate(position.board):
        if piece is None or not _owner_matches(metric.owner, piece.owner, actor):
            continue
        if metric.spatial is not None and not _spatial_holds(
            metric.spatial, index, declaration, board_size
        ):
            continue
        type_id = piece.base_type_id if metric.compare_field == "base" else piece.current_type_id
        score += weights.get(type_id, 0)
    if metric.include_hands:
        for owner, hand in enumerate(position.hands):
            if not _owner_matches(metric.owner, owner, actor):
                continue
            for type_id, count in hand.items():
                score += weights.get(type_id, 0) * count
    return score


def assess_declaration(state, compiled, declaration_id: str) -> DeclarationAssessment:
    """Assess one explicitly selected declaration without changing state."""
    position, ply = _state_parts(state)
    matches = [d for d in _declarations(compiled) if d.declaration_id == declaration_id]
    if not matches:
        raise InvalidDeclarationError(f"unknown declaration ID {declaration_id!r}")
    declaration = matches[0]
    actor = position.side_to_move
    if declaration.owner != actor:
        raise InvalidDeclarationError(
            f"declaration {declaration_id!r} belongs to player {declaration.owner}, not player {actor}"
        )
    score = _score(position, declaration, actor) if declaration.weighted_metric else None
    valid = all(_guard_holds(g, position, declaration, actor) for g in declaration.state_guards)
    if declaration.require_not_in_check and _in_check(position, actor, compiled):
        valid = False
    if declaration.ply_limit is not None and ply >= declaration.ply_limit:
        valid = False
    if not valid:
        outcome = declaration.failure_outcome
    else:
        outcome = declaration.failure_outcome
        for band in declaration.outcome_bands:
            if score is not None and score >= band.threshold:
                outcome = band.outcome
                break
    return DeclarationAssessment(declaration.declaration_id, actor, outcome, score)


def available_declarations(state, compiled) -> tuple[DeclarationAssessment, ...]:
    """Return only non-losing declarations belonging to the side to move."""
    position, _ = _state_parts(state)
    out = []
    for declaration in _declarations(compiled):
        if declaration.owner != position.side_to_move:
            continue
        assessment = assess_declaration(state, compiled, declaration.declaration_id)
        if assessment.outcome != "LOSS":
            out.append(assessment)
    return tuple(out)


__all__ = [
    "DeclarationAssessment",
    "InvalidDeclarationError",
    "assess_declaration",
    "available_declarations",
]
