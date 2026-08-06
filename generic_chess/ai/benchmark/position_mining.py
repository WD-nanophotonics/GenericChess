"""Deterministic position mining across rule/state categories.

Positions are produced only through legal action sequences on public
Session/Core APIs; fixtures are (ruleset spec, action prefix) pairs that can
be replayed exactly.  Exploration uses a seeded RNG with weak preferences
(capture/promotion/drop/check) that only influence which positions are found,
never the rules themselves.
"""

from __future__ import annotations

import json
import random
from typing import Callable

from ...core.actions import Action, BoardMove, DropMove, action_to_dict
from ...core.attacks import anchor_square, is_in_check, is_square_attacked
from ...core.coordinates import Square, index_to_square, square_to_index
from ...rules.compiled import CompiledRuleSet
from ...session.session import GameSession
from .audit_schema import PositionFixtureSpec
from .audit_suite import RuleSetFixtureSpec, build_compiled

_TARGET_CATEGORIES: tuple[str, ...] = (
    "midgame",
    "endgame",
    "in_check",
    "multi_evasion",
    "low_anchor_escape",
    "immediate_capture",
    "immediate_promotion",
    "near_repetition",
    "high_branching",
    "low_branching",
    "drop_available",
    "checking_drop",
    "nonchecking_drop",
)
MIN_PLY_FOR_CATEGORIES = 4


def _canonical_key(action: Action) -> str:
    return json.dumps(action_to_dict(action), sort_keys=True)


def _is_capture(state, action: Action, n: int) -> bool:
    if isinstance(action, DropMove):
        return False
    occupant = state.position.board[square_to_index(action.to_square, n)]
    return occupant is not None and occupant.owner != state.position.side_to_move


def _gives_check(session: GameSession, action: Action, compiled) -> bool:
    from ...core.transition import apply_action

    child = apply_action(session.state, action, compiled)
    return is_in_check(child.position, 1 - session.state.position.side_to_move, compiled)


def _anchor_escape(state, side: int, compiled) -> int:
    n = compiled.board_size
    pos = state.position
    sq = anchor_square(pos, side, compiled)
    if sq is None:
        return 0
    count = 0
    for df in (-1, 0, 1):
        for dr in (-1, 0, 1):
            if df == 0 and dr == 0:
                continue
            target = Square(sq.file + df, sq.rank + dr)
            if not (0 <= target.file < n and 0 <= target.rank < n):
                continue
            idx = square_to_index(target, n)
            if pos.board[idx] is not None:
                continue
            if not is_square_attacked(pos, target, 1 - side, compiled):
                count += 1
    return count


def _in_promotion_zone(state, compiled) -> bool:
    n = compiled.board_size
    side = state.position.side_to_move
    for idx, piece in enumerate(state.position.board):
        if piece is None or piece.owner != side or piece.promoted:
            continue
        base = compiled.types_by_id[piece.base_type_id]
        if not base.is_promotable:
            continue
        square = index_to_square(idx, n)
        if any(square == f for f, _ in compiled.promotion_allowed[piece.base_type_id][side]):
            return True
    return False


def position_features(session: GameSession, compiled) -> dict:
    state = session.state
    n = compiled.board_size
    side = state.position.side_to_move
    actions = session.legal_actions()
    capture = promotion = drop = 0
    for action in actions:
        if isinstance(action, DropMove):
            drop += 1
        elif action.promotion_target_id is not None:
            promotion += 1
        elif _is_capture(state, action, n):
            capture += 1
    non_anchor = sum(
        1
        for piece in state.position.board
        if piece is not None and not compiled.types_by_id[piece.current_type_id].is_anchor
    )
    in_check = is_in_check(state.position, side, compiled)
    repetition_risk = any(count >= 2 for _, count in state.repetition_counts)
    return {
        "ply": state.ply_count,
        "root_legal_actions": len(actions),
        "capture_actions": capture,
        "promotion_actions": promotion,
        "drop_actions": drop,
        "non_anchor_pieces": non_anchor,
        "in_check": in_check,
        "evasions": len(actions) if in_check else 0,
        "anchor_escape": _anchor_escape(state, side, compiled),
        "promotion_zone": _in_promotion_zone(state, compiled),
        "repetition_risk": repetition_risk,
        "branching": len(actions),
    }


def category_matches(features: dict, compiled) -> set[str]:
    cats = set()
    n = compiled.board_size
    if features["ply"] == 0:
        cats.add("opening")
    if features["ply"] < MIN_PLY_FOR_CATEGORIES:
        return cats
    if features["ply"] >= 8 and features["non_anchor_pieces"] >= 4:
        cats.add("midgame")
    if features["non_anchor_pieces"] <= 4:
        cats.add("endgame")
    if features["in_check"]:
        cats.add("in_check")
    if features["evasions"] >= 3:
        cats.add("multi_evasion")
    if features["anchor_escape"] <= 1:
        cats.add("low_anchor_escape")
    if features["capture_actions"] >= 1:
        cats.add("immediate_capture")
    if features["promotion_actions"] >= 1:
        cats.add("immediate_promotion")
    if features["repetition_risk"]:
        cats.add("near_repetition")
    if features["branching"] >= max(12, 3 * n):
        cats.add("high_branching")
    if features["branching"] <= 3:
        cats.add("low_branching")
    if features["drop_actions"] >= 1:
        cats.add("drop_available")
    return cats


def _checking_drop_category(session: GameSession, actions, compiled) -> str | None:
    drops = [a for a in actions if isinstance(a, DropMove)]
    if not drops:
        return None
    checking = any(_gives_check(session, a, compiled) for a in drops)
    return "checking_drop" if checking else "nonchecking_drop"


def _choose_action(
    session: GameSession, actions, rng: random.Random, compiled
) -> Action:
    ordered = sorted(actions, key=_canonical_key)
    n = compiled.board_size
    roll = rng.random()
    if roll < 0.30:
        caps = [a for a in ordered if _is_capture(session.state, a, n)]
        if caps:
            return rng.choice(caps)
    if roll < 0.45:
        promos = [
            a for a in ordered
            if isinstance(a, BoardMove) and a.promotion_target_id is not None
        ]
        if promos:
            return rng.choice(promos)
    if roll < 0.60:
        drops = [a for a in ordered if isinstance(a, DropMove)]
        if drops:
            return rng.choice(drops)
    if roll < 0.75:
        checks = [a for a in ordered if _gives_check(session, a, compiled)]
        if checks:
            return rng.choice(checks)
    return rng.choice(ordered)


def mine_positions(
    spec: RuleSetFixtureSpec,
    *,
    playout_seed: int = 1,
    max_games: int = 4,
    max_plies: int = 80,
    max_positions: int = 3,
) -> tuple[CompiledRuleSet, list[PositionFixtureSpec]]:
    """Deterministically mine up to ``max_positions`` category fixtures."""
    compiled = build_compiled(spec)
    found: dict[str, PositionFixtureSpec] = {}
    found["opening"] = PositionFixtureSpec(
        fixture_id=f"{spec.fixture_id}:opening",
        ruleset_fixture_id=spec.fixture_id,
        action_prefix=(),
        expected_categories=("opening",),
        playout_seed=playout_seed,
    )
    desired = [c for c in _TARGET_CATEGORIES]
    for game_index in range(max_games):
        session = GameSession(compiled)
        rng = random.Random(f"{spec.ruleset_seed}:{playout_seed}:{game_index}")
        history: list[Action] = []
        for _ in range(max_plies):
            if session.result.status.value != "ongoing":
                break
            actions = session.legal_actions()
            if not actions:
                break
            features = position_features(session, compiled)
            cats = category_matches(features, compiled)
            if (
                features["ply"] >= MIN_PLY_FOR_CATEGORIES
                and features["drop_actions"] >= 1
            ):
                extra = _checking_drop_category(session, actions, compiled)
                if extra:
                    cats.add(extra)
            for cat in desired:
                if cat in cats and cat not in found:
                    found[cat] = PositionFixtureSpec(
                        fixture_id=f"{spec.fixture_id}:{cat}",
                        ruleset_fixture_id=spec.fixture_id,
                        action_prefix=tuple(action_to_dict(a) for a in history),
                        expected_categories=(cat,),
                        playout_seed=playout_seed,
                    )
            non_opening_found = sum(1 for c in found if c != "opening")
            if non_opening_found >= max_positions - 1:
                break
            action = _choose_action(session, actions, rng, compiled)
            session.submit(action)
            history.append(action)
        non_opening_found = sum(1 for c in found if c != "opening")
        if non_opening_found >= max_positions - 1:
            break
    preferred = [
        "midgame",
        "in_check",
        "high_branching",
        "immediate_capture",
        "drop_available",
        "immediate_promotion",
        "endgame",
    ]
    non_opening = [
        found[c]
        for c in preferred
        if c in found and c != "opening"
    ]
    # Prefer later positions so category fixtures are not all the opening ply.
    non_opening.sort(key=lambda p: len(p.action_prefix), reverse=True)
    kept = [found["opening"]] + non_opening[: max_positions - 1]
    return compiled, kept


def mine_suite(
    specs,
    *,
    playout_seed: int = 1,
    max_games: int = 4,
    max_plies: int = 80,
    max_positions: int = 3,
) -> list[PositionFixtureSpec]:
    positions: list[PositionFixtureSpec] = []
    for spec in specs:
        _, kept = mine_positions(
            spec,
            playout_seed=playout_seed,
            max_games=max_games,
            max_plies=max_plies,
            max_positions=max_positions,
        )
        positions.extend(kept)
    return positions
