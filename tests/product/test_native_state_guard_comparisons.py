"""Native state guards compare zero for unresolved subjects and honor exists operators."""
from dataclasses import replace
import operator
from scripts.research_record import record_value

import pytest

from generic_chess import native
from generic_chess.ai.alphabeta.native_legality import NativeSemanticLegalityProvider
from generic_chess.core.movement import LeapAtom
from generic_chess.core.pieces import Piece, PieceType
from generic_chess.core.position import Hands, Position
from generic_chess.core.semantic_executor import SemanticEngine, _semantic_public_action
from generic_chess.native import semantic as sem
from generic_chess.native.adapter import pack_semantic_search_position
from generic_chess.native.compiler import compile_native_semantic_rules, NativeUnsupportedRuleError
from generic_chess.native.mirror import expected_snapshot
from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.rules.schema import (
    RuleActionEffect, RuleAuxState, RuleGeometrySpec, RuleSemanticAction,
    RuleSet, RuleSlotGuard, RuleSpatialSelector, RuleSquareRef,
    RuleStateGuard, RuleTypeRef,
)
from generic_chess.session.session import GameSession

pytestmark = pytest.mark.skipif(not native.native_available(), reason="Native unavailable")
COMPARISONS = {"eq": operator.eq, "ne": operator.ne, "lt": operator.lt,
               "le": operator.le, "gt": operator.gt, "ge": operator.ge}


def guarded(subject="offboard", aggregation="count", comparison="eq", value=0,
            owner=0, occupied_target=False):
    n = 5
    king = PieceType("K", "K", (LeapAtom((1, 0)),), is_anchor=True)
    actor = PieceType("A", "A", (LeapAtom((2, 0)),))
    base = PieceType("B", "B", (LeapAtom((2, 0)),),
                     is_promotable=True, promotion_target_ids=("A",))
    board = [None] * (n*n)
    board[0], board[-1] = Piece(0, "K", "K"), Piece(1, "K", "K")
    board[6], board[11] = Piece(owner, "A", "A"), Piece(owner, "B", "A", True)
    if occupied_target:
        board[16] = Piece(1-owner, "B", "B")
    ref = (RuleSquareRef("source") if subject in ("source", "global") else
           RuleSquareRef("offset_from_source", offset=(20, 0) if subject == "offboard" else (1, 0)))
    guard = RuleStateGuard(
        aggregation=aggregation, owner="any", type_ref=RuleTypeRef("any"),
        compare_field="base", promoted="any", location="board",
        spatial=RuleSpatialSelector("same_file" if subject == "global" else "exact", refs=(ref,)),
        comparison=comparison, value=value,
        subject_ref=None if subject == "global" else ref,
    )
    action = RuleSemanticAction(
        name="guarded_capture", type_ids=("A",),
        geometry=RuleGeometrySpec(kind="ray", direction=(0, 1), min_steps=1, owner_relative=False),
        target_relation="enemy", state_guards=(guard,),
        slot_guards=(RuleSlotGuard("enabled", value=1),),
        aux_state=(RuleAuxState("enabled", "bool", "global", "persistent", initial=1),),
        effects=(RuleActionEffect("remove", square_ref=RuleSquareRef("target"), piece_owner="opponent"),
                 RuleActionEffect("move", from_ref=RuleSquareRef("source"), to_ref=RuleSquareRef("target"))),
    )
    rule = RuleSet(board_size=n, piece_types=(king, actor, base),
        initial_position=tuple(tuple(board[r*n:(r+1)*n]) for r in range(n)),
        drop_allowed={tid: ((False,) * 25,) * 2 for tid in ("A", "B")},
        promotion_allowed={"B": (frozenset(), frozenset())},
        promotion_forced={"B": (frozenset(), frozenset())}, semantic_actions=(action,))
    compiled = compile_semantic_ruleset(rule)
    slot, = compiled.ir.aux_slots
    position = Position(tuple(board), (Hands.empty(), Hands.empty()), owner,
                        compiled.ruleset_fingerprint, aux_state=(((slot.slot_id, -1), 1),))
    return rule, compiled, position


@pytest.mark.parametrize("owner", [0, 1])
@pytest.mark.parametrize("subject", ["offboard", "empty", "source", "global"])
@pytest.mark.parametrize("aggregation", ["count", "exists"])
@pytest.mark.parametrize("comparison", list(COMPARISONS))
@pytest.mark.parametrize("value", [0, 1])
def test_attack_guard_aggregation_and_comparison(owner, subject, aggregation, comparison, value):
    _, compiled, position = guarded(subject, aggregation, comparison, value, owner)
    oracle = SemanticEngine(compiled)
    count = 2 if subject == "global" else 1 if subject == "source" else 0
    expected = COMPARISONS[comparison](int(bool(count)) if aggregation == "exists" else count, value)
    assert oracle.is_square_attacked(position, 16, owner) == expected
    rules = compile_native_semantic_rules(compiled)
    packed = sem.pack_current_position(rules, position, ply_count=0)
    before = sem.snapshot(rules, packed)
    for by_owner in (0, 1):
        wanted = oracle.attacked_squares(position, by_owner)
        assert sem.attacked_squares(rules, packed, by_owner) == wanted
        assert frozenset(i for i in range(25) if sem.is_square_attacked(rules, packed, i, by_owner)) == wanted
    assert sem.snapshot(rules, packed) == before


@pytest.mark.parametrize("subject,aggregation,value", [
    ("offboard", "count", 0), ("source", "exists", 0),
    ("source", "count", 1), ("global", "exists", 1),
])
def test_guarded_frontier_and_full_history_children(subject, aggregation, value):
    _, compiled, _ = guarded(subject, aggregation, "eq", value, occupied_target=True)
    session = GameSession(compiled)
    engine = SemanticEngine(compiled)
    rules = compile_native_semantic_rules(compiled)
    packed = pack_semantic_search_position(compiled, rules, session)
    before = session.state, session.to_record(), session._search_witnesses
    expected = {_semantic_public_action(engine, a): a for a in engine.legal_actions(session.state.position)}
    actual = {sem.public_action(rules, a): a for a in sem.guarded_actions(rules, packed)}
    assert set(actual) == set(expected)
    for action, raw in actual.items():
        child = GameSession(compiled)
        child.submit(action)
        got = sem.snapshot(rules, sem.make_checked(rules, packed, raw))
        wanted = expected_snapshot(child.state.position, rules, compiled)
        for field in ("board", "hands", "aux_state", "side"):
            assert record_value(got[field]) == record_value(wanted[field])
        assert len(child.state.history) == 2
    assert before == (session.state, session.to_record(), session._search_witnesses)


@pytest.mark.parametrize("advertise", [None, False])
def test_old_kernel_refuses_affected_guards_and_preserves_safe_rules(monkeypatch, advertise):
    module = native._module()
    caps = module.native_capabilities().copy()
    assert caps.pop("semantic_state_guard_comparisons") is True
    if advertise is not None:
        caps["semantic_state_guard_comparisons"] = advertise
    class OldBackend:
        def native_capabilities(self):
            return caps
        def __getattr__(self, name):
            return getattr(module, name)
    for subject, aggregation in (("offboard", "count"), ("global", "exists")):
        _, affected, position = guarded(subject, aggregation, "eq", 0)
        with pytest.raises(NativeUnsupportedRuleError, match="rebuilt kernel"):
            compile_native_semantic_rules(affected, backend_module=OldBackend())
        monkeypatch.setattr(module, "native_capabilities", lambda: caps)
        assert NativeSemanticLegalityProvider.try_create(affected) is None
        assert SemanticEngine(affected).legal_actions(position)
    _, safe, _ = guarded("global", "count", "ge", 0)
    assert compile_native_semantic_rules(safe, backend_module=OldBackend()).native_executable
    _, safe_exists, _ = guarded("global", "exists", "eq", 1)
    assert compile_native_semantic_rules(safe_exists, backend_module=OldBackend()).native_executable


@pytest.mark.parametrize("n", [8, 16])
@pytest.mark.parametrize("subject_bound", [False, True])
@pytest.mark.parametrize("kind", ["source", "offset_from_source"])
def test_wide_drop_source_reference_is_explicitly_refused(n, subject_bound, kind):
    # 0xFF is the transport's drop-source sentinel, but square255 exists
    # on a16x16 board. Core's absent source must not become that piece.
    king = PieceType("K", "K", (LeapAtom((1, 0)),), is_anchor=True)
    hand = PieceType("H", "H", (LeapAtom((1, 0)),))
    board = [None] * (n*n)
    board[0], board[-1] = Piece(0, "K", "K"), Piece(1, "K", "K")
    ref = RuleSquareRef(kind, offset=(0, 0) if kind == "offset_from_source" else None)
    guard = RuleStateGuard("count", "any", RuleTypeRef("any"), "base", "any", "board",
        RuleSpatialSelector("exact", refs=(ref,)), "eq", 0,
        subject_ref=ref if subject_bound else None)
    action = RuleSemanticAction(name="source_guarded_drop", type_ids=("H",),
        geometry=RuleGeometrySpec(kind="drop"), target_relation="empty", state_guards=(guard,),
        aux_state=(RuleAuxState("mark", "bool", "global", "persistent", initial=0),),
        effects=(RuleActionEffect("remove_from_hand", piece_type_ref=RuleTypeRef("action_base")),
                 RuleActionEffect("place", to_ref=RuleSquareRef("target"), piece_type_ref=RuleTypeRef("action_base")),
                 RuleActionEffect("set_bool", slot_name="mark", value=1)))
    rule = RuleSet(board_size=n, piece_types=(king, hand),
        initial_position=tuple(tuple(board[r*n:(r+1)*n]) for r in range(n)),
        drop_allowed={"H": ((True,) * (n*n),) * 2}, semantic_actions=(action,))
    compiled = compile_semantic_ruleset(rule)
    engine = SemanticEngine(compiled)
    position = replace(engine._initial_position(), hands=(Hands((("H", 1),)), Hands.empty()))
    wanted = {_semantic_public_action(engine, a) for a in engine.legal_actions(position)}
    assert len(wanted) == 2 * (n*n - 2) + 1
    if n == 16:
        with pytest.raises(NativeUnsupportedRuleError, match="wide drop.*source"):
            compile_native_semantic_rules(compiled)
        assert NativeSemanticLegalityProvider.try_create(compiled) is None
    else:
        rules = compile_native_semantic_rules(compiled)
        packed = sem.pack_current_position(rules, position, ply_count=0)
        actual = {sem.public_action(rules, a) for a in sem.guarded_actions(rules, packed)}
        assert actual == wanted
