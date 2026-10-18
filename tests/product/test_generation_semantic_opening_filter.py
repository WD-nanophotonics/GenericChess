"""Semantic opening preferences keep distinct bindings at shared coordinates."""
import pytest

from generic_chess.core.coordinates import Square
from generic_chess.core.movement import LeapAtom, RayAtom
from generic_chess.core.pieces import Piece, PieceType
from generic_chess.generation.config import GeneratorConfig
from generic_chess.generation.filters import run_soft_filters
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.schema import (
    RuleSet, RuleSemanticAction, RuleGeometrySpec, RuleActionEffect,
    RuleSquareRef, RuleAuxState, RuleSlotGuard, RuleInvariant,
)
from generic_chess.session.session import GameSession


def composed_rule(mate, max_ply):
    king = PieceType("K", "K", tuple(
        LeapAtom((df, dr)) for df in (-1, 0, 1) for dr in (-1, 0, 1)
        if df or dr), is_anchor=True)
    rook = PieceType("R", "R", (
        LeapAtom((0, 1)), RayAtom((0, 1)), RayAtom((0, -1)),
        RayAtom((1, 0)), RayAtom((-1, 0))))
    rows = [[None] * 4 for _ in range(4)]
    kf, kr = (2, 1) if mate else (0, 0)
    rows[kr][kf] = Piece(0, "K", "K")
    rows[1][1] = Piece(0, "R", "R")
    rows[3][3] = Piece(1, "K", "K")
    marked = RuleSemanticAction(
        name="marked_advance", type_ids=("R",),
        geometry=RuleGeometrySpec(kind="leap", offset=(0, 1)),
        target_relation="empty", composition="augment",
        aux_state=(RuleAuxState("mark", "bool", "global", "persistent", 0),),
        slot_guards=(RuleSlotGuard("mark", value=0),),
        effects=(
            RuleActionEffect("move", from_ref=RuleSquareRef("source"),
                             to_ref=RuleSquareRef("target")),
            RuleActionEffect("set_bool", slot_name="mark", value=1),
        ), invariants=(RuleInvariant("own_anchor_safe"),))
    return RuleSet(
        board_size=4, piece_types=(king, rook),
        initial_position=tuple(map(tuple, rows)),
        drop_allowed={"R": ((False,) * 16,) * 2},
        semantic_actions=(marked,), max_ply=max_ply)


@pytest.mark.parametrize("mate", (False, True))
@pytest.mark.parametrize("max_ply", (64, 1))
def test_opening_preference_counts_and_executes_lossless_semantic_actions(mate, max_ply):
    compiled = compile_ruleset_for_execution(composed_rule(mate, max_ply))
    session = GameSession(compiled)
    actions = session.legal_actions()
    # Leap, ray and the auxiliary-effect binding share coordinates. Their
    # semantic identities must survive both counting and trial transitions.
    shared = [a for a in actions if
              a.from_square == Square(1, 1) and a.to_square == Square(1, 2)]
    assert len(shared) == 3
    assert len({a.pattern_id for a in shared}) == 3
    cfg = GeneratorConfig(
        seed=0, board_size=4, require_promotable_type=False,
        require_no_opening_win_in_one=True)
    result = {v.name: v for v in run_soft_filters(
        cfg, compiled, {t.type_id: t for t in compiled.piece_types})}
    assert result["opening_legal_moves_in_range"].detail.startswith(
        f"{len(actions)} legal moves ")
    # With the supporting king on c2, Rb2-b4 is mate; otherwise there is
    # no winning first action. Mate retains priority at the max-ply boundary.
    assert result["opening_has_no_win_in_one"].passed is (not mate)
    assert session.state.ply_count == 0 and not session.history


def test_disabled_semantic_preference_still_counts_distinct_bindings(monkeypatch):
    from generic_chess.generation import filters
    compiled = compile_ruleset_for_execution(composed_rule(False, 64))
    expected = len(GameSession(compiled).legal_actions())
    def forbidden(*args):
        raise AssertionError("disabled preference must not trial child actions")
    monkeypatch.setattr(filters, "apply_action", forbidden)
    cfg = GeneratorConfig(seed=0, board_size=4, require_promotable_type=False)
    result = {v.name: v for v in filters.run_soft_filters(
        cfg, compiled, {t.type_id: t for t in compiled.piece_types})}
    assert "opening_has_no_win_in_one" not in result
    assert result["opening_legal_moves_in_range"].detail.startswith(
        f"{expected} legal moves ")
