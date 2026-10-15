"""Observed legal auxiliary-state witness for unordered bound-as-tie PVs.

The root scalar and even literal leaf score can match while an interior action
is suboptimal. This programmable semantic game tests that concrete mechanism;
it is not evidence about natural-game failure frequency.
"""
import pytest
from generic_chess.rules.schema import (RuleSet, RuleSemanticAction,
    RuleGeometrySpec, RuleSlotGuard, RuleAuxState, RuleActionEffect,
    RuleSquareRef, RuleTypeRef, RuleInvariant)
from generic_chess.core.pieces import Piece, PieceType
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.session.session import GameSession
from generic_chess.core.transition import apply_action
from generic_chess.core.movegen import legal_actions
from generic_chess.native.compiler import compile_native_semantic_rules
from generic_chess.native.adapter import pack_semantic_search_position
from generic_chess.native import semantic as sem
from generic_chess.native import native_available

pytestmark = pytest.mark.skipif(not native_available(), reason="Native unavailable")


def phase_graph():
    def fixed(x, y):
        return RuleSquareRef("fixed", square=(x, y), owner_relative=False)

    def phase(k):
        return fixed(k % 4, k // 4)

    slot = RuleAuxState("phase", "square_or_none", "global", "persistent",
                        initial=(0, 0))
    actors = {"W": (1, 0), "B": (1, 3)}
    # R->A; A->V,U; V has value6; U->Q,C; Q admits5 or3, C only5.
    # The enemy-target hint for C is intentional; its actual effects do not
    # capture. Checked semantic execution, rather than the hint, is authority.
    edges = [
        ("r", "W", 0, 1, (0, 1), None),
        ("aV", "B", 1, 2, (0, 1), None),
        ("aU", "B", 1, 3, (1, 1), None),
        ("v", "W", 2, 4, (0, 1), None),
        ("vleaf", "B", 4, 7, (0, 1), 6),
        ("q", "W", 3, 5, (0, 1), None),
        ("c", "W", 3, 6, (1, 3), None),
        ("q5", "B", 5, 7, (0, 1), 5),
        ("q3", "B", 5, 7, (1, 1), 3),
        ("c5", "B", 6, 7, (0, 1), 5),
        ("endW", "W", 7, 7, (0, 1), None),
        ("endB", "B", 7, 7, (0, 1), None),
    ]
    actions = []
    for name, actor, src, dst, target, value in edges:
        ox, oy = actors[actor]
        effects = [RuleActionEffect("set_token", slot_name="phase",
                                    square_ref=phase(dst))]
        if value is not None:
            effects.append(RuleActionEffect("set_current_type",
                square_ref=fixed(2, 2),
                type_ref=RuleTypeRef("explicit", type_id="S"+str(value))))
        actions.append(RuleSemanticAction(name=name, type_ids=(actor,),
            geometry=RuleGeometrySpec("leap",
                offset=(target[0]-ox, target[1]-oy), owner_relative=False),
            target_relation="enemy" if name == "c" else "empty",
            slot_guards=(RuleSlotGuard("phase", square_ref=phase(src)),),
            aux_state=(slot,), effects=tuple(effects),
            invariants=(RuleInvariant("own_anchor_safe"),)))
    board = [[None]*4 for _ in range(4)]
    for owner, tid, (x, y) in [
        (0, "K", (0, 0)), (1, "K", (3, 3)), (0, "W", (1, 0)),
        (1, "B", (1, 3)), (0, "S0", (2, 2)),
    ]:
        board[y][x] = Piece(owner, tid, tid)
    types = ["K", "W", "B", "S0", "S3", "S5", "S6"]
    return RuleSet(board_size=4,
        piece_types=tuple(PieceType(t, t, (), is_anchor=t == "K") for t in types),
        initial_position=tuple(tuple(row) for row in board),
        drop_allowed={t: ((False,)*16,)*2 for t in types if t != "K"},
        semantic_actions=tuple(actions))


@pytest.mark.parametrize("window", [False, True])
def test_completed_pv_prefixes_preserve_exact_core_choices(window):
    c = compile_ruleset_for_execution(phase_graph())
    s = GameSession(c)
    values = dict(K=0, W=0, B=0, S0=0, S3=3, S5=5, S6=6)

    def oracle(state, depth):
        if depth == 0:
            side = state.position.side_to_move
            return sum((1 if p.owner == side else -1)*values[p.current_type_id]
                       for p in state.position.board if p is not None)
        assert not state.terminal_status.is_terminal
        actions = legal_actions(state, c)
        assert actions
        return max(-oracle(apply_action(state, a, c), depth-1) for a in actions)

    nr = compile_native_semantic_rules(c)
    pos = pack_semantic_search_position(c, nr, s)
    before = sem.snapshot(nr, pos), s.to_record()
    result = sem.semantic_iterative_search(nr, pos, 4,
        board_values=values, hand_values=values, tt_megabytes=0,
        root_window_pruning=window)
    assert result["completed_depth"] == 4
    assert result["score"] == oracle(s.state, 4) == 5
    assert len(result["principal_variation"]) == 4
    state = s.state
    for ply, code in enumerate(result["principal_variation"]):
        action = sem.public_action(nr, code)
        assert action in legal_actions(state, c)
        child = apply_action(state, action, c)
        assert -oracle(child, 3-ply) == oracle(state, 4-ply)
        state = child
    assert before == (sem.snapshot(nr, pos), s.to_record())
