"""Bounded terminal-only tactical probes for F86A quality measurement."""

from __future__ import annotations

from dataclasses import dataclass

from ..session.session import GameSession


@dataclass(frozen=True, slots=True)
class TacticalProbeResult:
    value: float | None
    nodes: int
    solved: bool
    forced_win: bool
    unique_best: bool | None


def minimax_node_value(
    values: list[float | None] | tuple[float | None, ...],
    *,
    maximizing: bool,
) -> float | None:
    """Combine child W/D/L values from the root player's perspective.

    A decisive partial proof is retained: MAX can prove a win from one known
    winning child, and MIN can prove a loss from one known losing child.
    Otherwise any unresolved child keeps the node unresolved.
    """
    known = [value for value in values if value is not None]
    if maximizing:
        if 1.0 in known:
            return 1.0
    elif 0.0 in known:
        return 0.0
    if len(known) != len(values) or not known:
        return None
    return (max if maximizing else min)(known)


def _terminal_value(session: GameSession, root_player: int) -> float:
    result = session.result
    if result.winner is None:
        return 0.5
    return 1.0 if result.winner == root_player else 0.0


def probe_terminal_only(
    session: GameSession,
    *,
    depth: int = 4,
    node_budget: int = 256,
) -> TacticalProbeResult:
    """Solve only terminal W/D/L outcomes; cutoff is unresolved, never draw."""
    if not 1 <= depth <= 4:
        raise ValueError("depth must be between 1 and 4")
    if not 1 <= node_budget <= 256:
        raise ValueError("node_budget must be between 1 and 256")
    root_player = session.state.position.side_to_move
    nodes = 0

    def search(current: GameSession, remaining: int) -> float | None:
        nonlocal nodes
        if current.result.status.value != "ongoing":
            return _terminal_value(current, root_player)
        if remaining == 0 or nodes >= node_budget:
            return None
        actions = current.legal_actions()
        if not actions:
            return _terminal_value(current, root_player)
        values: list[float] = []
        for action in actions:
            if nodes >= node_budget:
                return None
            nodes += 1
            child = GameSession.replay(current.compiled, current.to_record())
            child.submit(action)
            value = search(child, remaining - 1)
            if value is None:
                values.append(float("nan"))
            else:
                values.append(value)
        known = [value for value in values if value == value]
        actor_is_root = current.state.position.side_to_move == root_player
        return minimax_node_value(
            [None if value != value else value for value in values],
            maximizing=actor_is_root,
        )

    root_actions = session.legal_actions()
    if not root_actions:
        value = _terminal_value(session, root_player)
        return TacticalProbeResult(value, 0, True, value == 1.0, None)
    child_values: list[float | None] = []
    for action in root_actions:
        if nodes >= node_budget:
            child_values.append(None)
            continue
        nodes += 1
        child = GameSession.replay(session.compiled, session.to_record())
        child.submit(action)
        child_values.append(search(child, depth - 1))
    solved = all(value is not None for value in child_values)
    maximizing = session.state.position.side_to_move == root_player
    value = minimax_node_value(child_values, maximizing=maximizing)
    known = [item for item in child_values if item is not None]
    best_value = (max if maximizing else min)(known) if known else None
    unique_best = None
    if solved and best_value is not None:
        unique_best = sum(value == best_value for value in child_values) == 1
    return TacticalProbeResult(
        value=value if solved else (1.0 if value == 1.0 else 0.0 if value == 0.0 else None),
        nodes=nodes,
        solved=solved,
        forced_win=value == 1.0,
        unique_best=unique_best,
    )
