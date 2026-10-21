"""The collector and trainer must include frozen v3 spatial value contributions."""
import pytest
from native_test_helpers import requires_native
import math
from dataclasses import replace
from conftest import make_ruleset,king_type,T
from generic_chess.core.movement import RayAtom
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution
from generic_chess.native.compiler import compile_native_semantic_rules
from generic_chess.learning.material import LearnableMaterialCheckpoint
from generic_chess.learning.selfplay import collect_self_play,SelfPlayConfig
from generic_chess.learning.features import material_features,spatial_occupancy_features,localized_control_features,linear_value
from generic_chess.session.session import GameSession
from generic_chess.core.transition import apply_action
from generic_chess.native.semantic import evaluate
from generic_chess.native.adapter import pack_semantic_search_position

@requires_native
@pytest.mark.parametrize("with_control", [False, True])
@pytest.mark.parametrize("horizon", [1, 64])
def test_actual_v3_leaf_and_bootstrap_use_frozen_spatial_contribution(with_control, horizon):
    rule=replace(make_ruleset(4,[king_type(),T('R',RayAtom((0,1)),RayAtom((0,-1)))],lines=['...k','....','R...','K...']),max_ply=horizon);c=compile_legacy_ruleset_for_semantic_execution(rule);native=compile_native_semantic_rules(c)
    base=LearnableMaterialCheckpoint(ruleset_fingerprint=c.ruleset_fingerprint,board_weights={'R':1.},hand_weights={'R':1.},value_scale=10.,reference_median=1.)
    # Fixed unfitted zero-sum rows, all supported types, including anchors. Not a performance candidate.
    spatial={f'{owner}:{t}':tuple(([1.+owner]+[0.]*7+[-1.-owner])if t=='K'else[0.]*9)for owner in(0,1)for t in native.type_ids}
    cp=replace(base,spatial_occupancy_weights=spatial, localized_control_weights=(1.,0.,0.,0.,0.,0.,0.,0.,-1.) if with_control else ());cp.validate_ruleset(c)
    t,=collect_self_play(c,native,cp,SelfPlayConfig(games=1,nodes_per_move=1000,max_depth=1,max_plies=1,epsilon=0.))
    p=t.points[0];s=GameSession(c).state
    for a in p.pv:s=apply_action(s,a,c)
    f=material_features(s.position,('R',));occupancy=spatial_occupancy_features(s.position,tuple(native.type_ids));control=localized_control_features(s.position,c)
    value=linear_value(f,cp.board_weights,cp.hand_weights,spatial_occupancy=occupancy,spatial_occupancy_weights=cp.spatial_occupancy_weights,localized_control=control,localized_control_weights=cp.localized_control_weights)
    leafsession=GameSession(c)
    for a in p.pv:leafsession.submit(a)
    packed=pack_semantic_search_position(c,native,leafsession)
    raw_native=evaluate(native,packed,board_values=cp.semantic_quantized_board(native.type_ids),hand_values=cp.semantic_quantized_hand(native.type_ids),dynamic_values=cp.semantic_quantized_dynamic(),spatial_occupancy_values=cp.semantic_quantized_spatial(native.type_ids),localized_control_values=cp.semantic_quantized_localized_control(),evaluator_scale=cp.semantic_native_scale)
    raw_owner0=raw_native/cp.semantic_native_scale*(1 if leafsession.state.position.side_to_move==0 else -1)
    if horizon == 64:
        assert raw_owner0 == value
    # At rule MAX_PLY Native controls are gated; Position-only Core controls
    # are not an oracle there. Terminal constants take precedence regardless.
    predicted = 0. if horizon == 1 else math.tanh(raw_owner0/cp.value_scale)
    assert p.leaf_value == pytest.approx(predicted)
    if horizon == 1:
        assert p.leaf_terminal_z == 0. and t.bootstrap_value is None
    else:
        assert t.bootstrap_value == pytest.approx(predicted)
    restored = type(t).from_dict(t.to_dict())
    assert restored.to_dict() == t.to_dict()
    from generic_chess.learning.tdleaf import tdleaf_update, TDLeafConfig
    from generic_chess.learning.diagnostics import td_signal_diagnostics
    draw = replace(restored, terminal='draw', winner=None, truncated=False, bootstrap_value=None)
    expected=-predicted
    update = tdleaf_update([draw], cp, TDLeafConfig(alpha=.1))
    assert update.mean_td_error == pytest.approx(expected)
    # R is the sole trainable board coordinate. Existing median normalization
    # restores it to one; the untouched hand value exposes the true raw step.
    raw_step = .1 * expected * (1 - predicted * predicted) / cp.value_scale
    assert update.hand_weights["R"] == pytest.approx(1 / (1 + raw_step))
    records, _, _, _ = td_signal_diagnostics([draw], cp, TDLeafConfig(alpha=.1))
    assert records[0].delta == pytest.approx(expected)


@pytest.mark.parametrize("entry", ["collect", "train", "diagnose"])
def test_compact_model_is_explicitly_unsupported_before_partial_td(entry):
    from generic_chess.learning.tdleaf import tdleaf_update, TDLeafConfig
    from generic_chess.learning.diagnostics import td_signal_diagnostics
    checkpoint = LearnableMaterialCheckpoint(compact_nonlinear={"opaque": "unsupported"})
    with pytest.raises(NotImplementedError, match="compact nonlinear"):
        if entry == "collect":
            collect_self_play(None, None, checkpoint, SelfPlayConfig())
        elif entry == "train":
            tdleaf_update([], checkpoint, TDLeafConfig())
        else:
            td_signal_diagnostics([], checkpoint, TDLeafConfig())


def test_optional_rich_feature_roundtrip_preserves_legacy_payload():
    from generic_chess.learning.trajectory import TrainingPoint, TrainingTrajectory
    point = TrainingPoint(0, "r", None, False, (), "l", (1,), (0,), 0., 1)
    trajectory = TrainingTrajectory("fp", 0, 1, "i", (), 1, 1, (point,), "draw", None, ("R",))
    legacy = trajectory.to_dict()
    assert "leaf_feature_spatial" not in legacy["points"][0]
    assert "leaf_feature_control" not in legacy["points"][0]
    assert TrainingTrajectory.from_dict(legacy).to_dict() == legacy
    rich = replace(point, leaf_feature_spatial=(("0:K", (1,0,0,0,0,0,0,0,0)),),
                   leaf_feature_control=(8,-1,-1,-1,-1,-1,-1,-1,-1))
    changed = replace(trajectory, points=(rich,))
    assert TrainingTrajectory.from_dict(changed.to_dict()).to_dict() == changed.to_dict()
    assert changed.trajectory_id != trajectory.trajectory_id
    assert changed.feature_payload(rich) != trajectory.feature_payload(point)


@requires_native
@pytest.mark.parametrize("case", ["ep-history", "castling-right", "alternate-start"])
def test_spatial_pv_preserves_full_session_context_and_parent(case):
    from generic_chess.rules.compiler import compile_ruleset_for_execution
    from generic_chess.rules.western_chess import build_western_chess_ruleset
    from generic_chess.rules.schema import RuleInitialSetupOption
    from generic_chess.core.coordinates import Square
    from generic_chess.learning.selfplay import _spatial_snapshot
    from generic_chess.native.semantic import spatial_features
    from rule_semantics_ir_fixtures import castling_ruleset

    if case == "ep-history":
        compiled = compile_ruleset_for_execution(build_western_chess_ruleset())
        session = GameSession(compiled)
        double = next(a for a in session.legal_actions()
                      if a.from_square == Square(0, 1) and a.to_square == Square(0, 3))
        session.submit(double)
        assert any(v is not None for _, v in session.state.position.aux_state)
        pv = (session.legal_actions()[0],)
    elif case == "castling-right":
        compiled = compile_ruleset_for_execution(castling_ruleset())
        session = GameSession(compiled)
        pv = (next(a for a in session.legal_actions()
                   if a.from_square == Square(4, 0) and a.to_square == Square(6, 0)),)
    else:
        rook = T("R", RayAtom((0, 1)), RayAtom((0, -1)))
        rule = make_ruleset(5, [king_type(), rook],
                            lines=["....k", ".....", "R....", ".....", "K...."])
        other = make_ruleset(5, [king_type(), rook],
                             lines=["....k", ".....", ".R...", ".....", "K...."])
        compiled = compile_legacy_ruleset_for_semantic_execution(replace(
            rule, initial_setup_options=(RuleInitialSetupOption("other", other.initial_position),)))
        session = GameSession(compiled, "other")
        session.submit(session.legal_actions()[0])
        pv = (session.legal_actions()[0],)
    native = compile_native_semantic_rules(compiled)
    checkpoint = LearnableMaterialCheckpoint(
        localized_control_weights=(1.,0.,0.,0.,0.,0.,0.,0.,-1.))
    parent = session.state, session.to_record(), session.history, session._search_witnesses
    expected = GameSession.replay(compiled, session.to_record())
    for a in pv:
        expected.submit(a)
    packed = pack_semantic_search_position(compiled, native, expected)
    want = spatial_features(native, packed)["localized_control"]
    assert _spatial_snapshot(compiled, native, session, pv, checkpoint, expected.state) == ((), want)
    assert parent == (session.state, session.to_record(), session.history, session._search_witnesses)
    # A rejected continuation must leave the same live parent intact too.
    with pytest.raises(ValueError):
        _spatial_snapshot(compiled, native, session,
                          (replace(pv[0], pattern_id="invalid-pattern"),),
                          checkpoint, expected.state)
    assert parent == (session.state, session.to_record(), session.history, session._search_witnesses)
