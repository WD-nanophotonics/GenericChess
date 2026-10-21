"""Scalar pseudo-attack must retain actor binding, guard continuation and target semantics."""
import pytest

from generic_chess.core.movement import LeapAtom
from generic_chess.core.pieces import Piece, PieceType
from generic_chess.core.position import Hands, Position
from generic_chess.core.semantic_executor import SemanticEngine
from generic_chess.native import native_available
from generic_chess.native.compiler import compile_native_semantic_rules
from generic_chess.native.semantic import (
    attacked_squares, is_square_attacked, pack_current_position, snapshot,
)
from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.rules.schema import (
    RuleActionEffect, RuleAuxState, RuleGeometrySpec, RuleSemanticAction,
    RuleSet, RuleSlotGuard, RuleSpatialSelector, RuleSquareRef,
    RuleStateGuard, RuleTypeRef,
)

pytestmark = pytest.mark.skipif(not native_available(), reason="native unavailable")


@pytest.mark.parametrize("owner", [0, 1])
@pytest.mark.parametrize("occupancy", ["empty", "own", "enemy"])
@pytest.mark.parametrize("enabled", [0, 1])
def test_scalar_attack_keeps_later_guarded_actor_and_pseudo_target(owner, occupancy, enabled):
    n = 5
    king = PieceType("K", "K", (LeapAtom((1, 0)),), is_anchor=True)
    actor = PieceType("A", "A", (LeapAtom((2, 0)),))
    base = PieceType("B", "B", (LeapAtom((2, 0)),),
                     is_promotable=True, promotion_target_ids=("A",))
    board = [None] * (n*n)
    board[0] = Piece(0, "K", "K")
    board[-1] = Piece(1, "K", "K")
    # Both A actors geometrically reach target. The earlier source fails the
    # base-type guard; the later transformed actor must still be considered.
    board[6] = Piece(owner, "A", "A")
    board[11] = Piece(owner, "B", "A", True)
    target = 16
    if occupancy != "empty":
        board[target] = Piece(owner if occupancy == "own" else 1-owner, "B", "B")
    action = RuleSemanticAction(
        name="capture_relation_with_actor_and_slot_guards", type_ids=("A",),
        geometry=RuleGeometrySpec(kind="ray", direction=(0, 1),
                                  min_steps=1, owner_relative=False),
        target_relation="enemy",
        state_guards=(RuleStateGuard(
            aggregation="count", owner="self", type_ref=RuleTypeRef("explicit", "B"),
            compare_field="base", promoted="any", location="board",
            spatial=RuleSpatialSelector("exact", refs=(RuleSquareRef("source"),)),
            comparison="eq", value=1, subject_ref=RuleSquareRef("source"),
        ),),
        slot_guards=(RuleSlotGuard("enabled", value=1),),
        aux_state=(RuleAuxState("enabled", "bool", "global", "persistent", initial=1),),
        effects=(RuleActionEffect("move", from_ref=RuleSquareRef("source"),
                                  to_ref=RuleSquareRef("target")),),
    )
    rules = RuleSet(board_size=n, piece_types=(king, actor, base),
                    initial_position=tuple(tuple(board[r*n:(r+1)*n]) for r in range(n)),
                    drop_allowed={tid: ((False,) * 25,) * 2 for tid in ("A", "B")},
                    promotion_allowed={"B": (frozenset(), frozenset())},
                    promotion_forced={"B": (frozenset(), frozenset())},
                    semantic_actions=(action,))
    compiled = compile_semantic_ruleset(rules)
    slot, = compiled.ir.aux_slots
    position = Position(tuple(board), (Hands.empty(), Hands.empty()), owner,
                        compiled.support.ruleset_fingerprint,
                        aux_state=(((slot.slot_id, -1), enabled),))
    oracle = SemanticEngine(compiled)
    assert oracle.is_square_attacked(position, target, owner) == bool(enabled)
    without_later = list(board)
    without_later[11] = None
    earlier_only = Position(tuple(without_later), position.hands, owner,
                            position.ruleset_fingerprint, aux_state=position.aux_state)
    assert not oracle.is_square_attacked(earlier_only, target, owner)
    native_rules = compile_native_semantic_rules(compiled)
    native_position = pack_current_position(native_rules, position, ply_count=0)
    before = snapshot(native_rules, native_position)
    for by_owner in (0, 1):
        expected = frozenset(sq for sq in range(n*n)
                             if oracle.is_square_attacked(position, sq, by_owner))
        assert attacked_squares(native_rules, native_position, by_owner) == expected
        assert frozenset(sq for sq in range(n*n)
                         if is_square_attacked(native_rules, native_position, sq, by_owner)) == expected
    assert snapshot(native_rules, native_position) == before
