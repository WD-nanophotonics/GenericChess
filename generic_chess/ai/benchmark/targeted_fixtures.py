"""Targeted fixtures for the previously-uncovered position categories.

Each fixture is built through the public RuleSet/Position APIs and its
category predicate is verified against the real state.  Positions that cannot
be constructed legitimately are reported as uncovered rather than faked.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from ...core.actions import Action, DropMove, action_to_dict
from ...core.attacks import is_in_check
from ...core.movegen import legal_actions
from ...core.keys import position_key
from ...core.movement import LeapAtom, RayAtom
from ...core.pieces import Piece, PieceType
from ...core.position import GameState, Hands, Position
from ...core.terminal import TerminalResult, TerminalStatus
from ...core.transition import apply_action
from ...rules.compiled import CompiledRuleSet
from ...rules.schema import RuleSet
from .position_mining import _anchor_escape

KING_ATOMS = tuple(
    LeapAtom((df, dr)) for df in (-1, 0, 1) for dr in (-1, 0, 1) if (df, dr) != (0, 0)
)
ORTHO = (RayAtom((0, 1)), RayAtom((0, -1)), RayAtom((1, 0)), RayAtom((-1, 0)))
DIAG = (RayAtom((1, 1)), RayAtom((1, -1)), RayAtom((-1, 1)), RayAtom((-1, -1)))


@dataclass(frozen=True, slots=True)
class TargetedFixture:
    fixture_id: str
    compiled: CompiledRuleSet
    state: GameState
    expected_categories: tuple[str, ...]
    action_prefix: tuple[dict, ...] = ()

    def verify(self) -> bool:
        return all(self._check(c) for c in self.expected_categories)

    def _check(self, category: str) -> bool:
        compiled = self.compiled
        state = self.state
        side = state.position.side_to_move
        actions = list(legal_actions(state, compiled))
        if category == "multi_evasion":
            return is_in_check(state.position, side, compiled) and len(actions) >= 3
        if category == "near_repetition":
            return any(count >= 2 for _, count in state.repetition_counts)
        if category == "checking_drop":
            return any(
                isinstance(a, DropMove)
                and is_in_check(
                    apply_action(state, a, compiled).position,
                    1 - side,
                    compiled,
                )
                for a in actions
            )
        if category == "nonchecking_drop":
            drops = [a for a in actions if isinstance(a, DropMove)]
            return bool(drops) and not any(
                is_in_check(apply_action(state, a, compiled).position, 1 - side, compiled)
                for a in drops
            )
        if category == "low_anchor_escape":
            return _anchor_escape(state, side, compiled) <= 1
        if category == "low_branching":
            return len(actions) <= 3
        return False


def _pt(tid: str, atoms, *, anchor: bool = False) -> PieceType:
    return PieceType(tid, tid, tuple(atoms), is_anchor=anchor)


def _board(lines: list[str]) -> tuple[tuple[Piece | None, ...], ...]:
    rows = []
    for line in reversed(lines):
        row = []
        for ch in line:
            if ch == ".":
                row.append(None)
            else:
                owner = 0 if ch.isupper() else 1
                row.append(Piece(owner, ch.upper(), ch.upper(), False))
        rows.append(tuple(row))
    return tuple(rows)


def _state(
    compiled: CompiledRuleSet,
    lines: list[str],
    *,
    side_to_move: int,
    hands: tuple[tuple[tuple[str, int], ...], ...] = ((), ()),
) -> GameState:
    board = tuple(cell for row in _board(lines) for cell in row)
    hands_obj = (
        Hands(tuple(sorted(hands[0]))),
        Hands(tuple(sorted(hands[1]))),
    )
    position = Position(
        board=board,
        hands=hands_obj,
        side_to_move=side_to_move,
        ruleset_fingerprint=compiled.ruleset_fingerprint,
    )
    key = position_key(position, compiled)
    return GameState(
        position=position,
        ply_count=0,
        repetition_counts=((key, 1),),
        terminal_status=TerminalResult(TerminalStatus.ONGOING),
    )


def _compile(
    n: int,
    types: list[PieceType],
    initial_lines: list[str],
    *,
    drop_types: tuple[str, ...] = (),
) -> CompiledRuleSet:
    drop: dict[str, tuple[tuple[bool, ...], ...]] = {}
    for t in types:
        if t.is_anchor:
            continue
        if t.type_id in drop_types:
            mask = (True,) * (n * n)
        else:
            mask = (False,) * (n * n)
        drop[t.type_id] = (mask, mask)
    ruleset = RuleSet(
        schema_version=1,
        board_size=n,
        piece_types=tuple(types),
        initial_position=_board(initial_lines),
        drop_allowed=drop,
        promotion_allowed={},
        promotion_forced={},
        repetition_limit=4,
        max_ply=512,
        stalemate_result="draw",
    )
    from ...rules.compiler import compile_ruleset

    return compile_ruleset(ruleset)


def _k_r(n: int = 4, drop: bool = True) -> CompiledRuleSet:
    assert n == 4
    rows = ["....", ".R..", "..r.", "K..k"]
    return _compile(
        n,
        [_pt("K", KING_ATOMS, anchor=True), _pt("R", ORTHO)],
        rows,
        drop_types=("R",) if drop else (),
    )


def _k_r_b() -> CompiledRuleSet:
    return _compile(
        4,
        [_pt("K", KING_ATOMS, anchor=True), _pt("R", ORTHO), _pt("B", DIAG)],
        ["....", "....", "....", "K..k"],
        drop_types=(),
    )


def _fixture(
    fixture_id: str,
    compiled: CompiledRuleSet,
    state: GameState,
    categories: tuple[str, ...],
    prefix: tuple[Action, ...] = (),
) -> TargetedFixture:
    return TargetedFixture(
        fixture_id=fixture_id,
        compiled=compiled,
        state=state,
        expected_categories=categories,
        action_prefix=tuple(action_to_dict(a) for a in prefix),
    )


def _multi_evasion() -> TargetedFixture:
    compiled = _k_r()
    state = _state(
        compiled,
        ["Rr..", "....", ".r..", "k..K"],
        side_to_move=1,
    )
    return _fixture("targeted_multi_evasion", compiled, state, ("multi_evasion",))


def _near_repetition() -> TargetedFixture:
    from ...session.session import GameSession
    from ...core.actions import BoardMove
    from ...core.coordinates import Square

    compiled = _k_r()
    session = GameSession(compiled)
    prefix = [
        BoardMove(Square(1, 2), Square(1, 1)),  # white rook out
        BoardMove(Square(2, 1), Square(2, 2)),  # black rook out
        BoardMove(Square(1, 1), Square(1, 2)),  # white rook back
        BoardMove(Square(2, 2), Square(2, 1)),  # black rook back
    ]
    for action in prefix:
        session.submit(action)
    return _fixture(
        "targeted_near_repetition",
        compiled,
        session.state,
        ("near_repetition",),
        prefix=tuple(prefix),
    )


def _checking_drop() -> TargetedFixture:
    compiled = _k_r()
    state = _state(
        compiled,
        ["...k", "....", "....", "K..."],
        side_to_move=0,
        hands=((("R", 1),), ()),
    )
    return _fixture("targeted_checking_drop", compiled, state, ("checking_drop",))


def _nonchecking_drop() -> TargetedFixture:
    compiled = _k_r()
    state = _state(
        compiled,
        ["...K", "....", "r...", "kr.."],
        side_to_move=0,
        hands=((("R", 2),), ()),
    )
    return _fixture("targeted_nonchecking_drop", compiled, state, ("nonchecking_drop",))


def _low_anchor_escape() -> TargetedFixture:
    compiled = _k_r_b()
    state = _state(
        compiled,
        ["....", "..B.", "R...", "k.R."],
        side_to_move=1,
    )
    return _fixture("targeted_low_anchor_escape", compiled, state, ("low_anchor_escape",))


def _low_branching() -> TargetedFixture:
    compiled = _k_r()
    state = _state(
        compiled,
        ["....", "....", "..K.", "kR.."],
        side_to_move=1,
    )
    return _fixture("targeted_low_branching", compiled, state, ("low_branching",))


_BUILDERS: tuple[Callable[[], TargetedFixture], ...] = (
    _multi_evasion,
    _near_repetition,
    _checking_drop,
    _nonchecking_drop,
    _low_anchor_escape,
    _low_branching,
)


def build_targeted_fixtures() -> tuple[TargetedFixture, ...]:
    """Build and verify targeted fixtures; skip+report any that fail verification."""
    built = []
    for builder in _BUILDERS:
        fixture = builder()
        if fixture.verify():
            built.append(fixture)
    return tuple(built)


def uncovered_targeted_categories() -> tuple[str, ...]:
    covered = {c for f in build_targeted_fixtures() for c in f.expected_categories}
    wanted = (
        "multi_evasion",
        "near_repetition",
        "checking_drop",
        "nonchecking_drop",
        "low_anchor_escape",
        "low_branching",
    )
    return tuple(c for c in wanted if c not in covered)
