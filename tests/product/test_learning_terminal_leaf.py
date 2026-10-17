"""Terminal PV leaves are constants, not material-evaluator training samples."""
from dataclasses import replace
import math

import pytest
from conftest import make_ruleset, king_type, T
from generic_chess.core.movement import RayAtom
from generic_chess.learning.material import LearnableMaterialCheckpoint
from generic_chess.learning.diagnostics import td_signal_diagnostics
from generic_chess.learning.selfplay import SelfPlayConfig, collect_self_play
from generic_chess.learning.tdleaf import TDLeafConfig, tdleaf_update
from generic_chess.learning.trajectory import TrainingPoint, TrainingTrajectory
from generic_chess.rules.compiler import compile_ruleset, compile_legacy_ruleset_for_semantic_execution
from generic_chess.native.compiler import compile_native_rules
from generic_chess.native.compiler import compile_native_semantic_rules
from native_test_helpers import requires_native


def checkpoint(fp="fp"):
    return LearnableMaterialCheckpoint(
        ruleset_fingerprint=fp, board_weights={"P": 100., "Q": 300.},
        hand_weights={"P": 90., "Q": 270.}, value_scale=800.,
        reference_median=200., w_max=10000.,
    )


def point(ply, board):
    return TrainingPoint(
        ply=ply, root_position_key="root", action=None, exploration=False,
        pv=(), leaf_position_key="leaf", leaf_feature_board=board,
        leaf_feature_hand=(0, 0), leaf_value=0., completed_depth=1,
    )


def trajectory(points, winner=0):
    return TrainingTrajectory(
        ruleset_fingerprint="fp", generation=0, game_seed=1,
        initial_position_key="root", actions=(), search_nodes=1,
        search_max_depth=1, points=tuple(points), terminal="checkmate",
        winner=winner, type_ids=("P", "Q"),
    )


@pytest.mark.parametrize("leaf_z,actual_winner", [(1., 1), (-1., 0), (0., None)])
def test_recorded_terminal_leaf_has_no_material_derivative(leaf_z, actual_winner):
    original = trajectory([point(0, (1, 2))], actual_winner)
    payload = original.to_dict()
    payload["points"][0]["leaf_terminal_z"] = leaf_z
    t = TrainingTrajectory.from_dict(payload)
    result = tdleaf_update([t], checkpoint(), TDLeafConfig(alpha=.1))
    actual = 0. if actual_winner is None else 1. if actual_winner == 0 else -1.
    assert result.mean_td_error == actual - leaf_z
    records, _, bd, hd = td_signal_diagnostics([t], checkpoint(), TDLeafConfig(alpha=.1))
    assert records[0].value_before == leaf_z
    assert records[0].delta == actual - leaf_z
    assert not any(bd.values()) and not any(hd.values())
    assert result.board_weights == checkpoint().board_weights
    assert result.hand_weights == checkpoint().hand_weights
    assert t.to_dict()["points"][0]["leaf_terminal_z"] == leaf_z
    assert TrainingTrajectory.from_dict(t.to_dict()).trajectory_id == t.trajectory_id


@pytest.mark.parametrize("lam", [0., .7, 1.])
def test_terminal_leaf_decays_prior_eligibility_without_erasing_it(lam):
    payload = trajectory([point(0, (1, 0)), point(1, (0, 5))], None).to_dict()
    payload["points"][1]["leaf_terminal_z"] = 1.
    t = TrainingTrajectory.from_dict(payload)
    cp = checkpoint()
    got = tdleaf_update([t], cp, TDLeafConfig(alpha=.1, lambd=lam))
    u = math.tanh(100. / 800.)
    d = .1 * ((1. - u) - lam) * (1. - u*u) / 800.
    factor = 400. / (400. + d)
    assert got.board_weights["P"] == pytest.approx((100.+d)*factor, abs=1e-12)
    assert got.board_weights["Q"] == pytest.approx(300.*factor, abs=1e-12)
    assert got.hand_weights["P"] == pytest.approx(90.*factor, abs=1e-12)
    assert got.mean_td_error == pytest.approx(-u/2)
    _, _, bd, hd = td_signal_diagnostics([t], cp, TDLeafConfig(alpha=.1, lambd=lam))
    assert bd["P"] == pytest.approx(d, abs=1e-15)
    assert bd["Q"] == 0. and not any(hd.values())


def test_legacy_point_payload_and_id_are_not_rewritten():
    old = trajectory([point(0, (1, 0))]).to_dict()
    assert "leaf_terminal_z" not in old["points"][0]
    t = TrainingTrajectory.from_dict(old)
    assert t.to_dict() == old
    assert TrainingTrajectory.from_dict(t.to_dict()).trajectory_id == t.trajectory_id


@requires_native
@pytest.mark.parametrize("semantic", [False, True])
def test_actual_native_rule_draw_pv_is_collected_as_constant(semantic):
    rule = replace(make_ruleset(
        4, [king_type(), T("R", RayAtom((0, 1)), RayAtom((0, -1)))],
        lines=["...k", "....", "R...", "K..."],
    ), max_ply=1)
    compiled = (compile_legacy_ruleset_for_semantic_execution if semantic else compile_ruleset)(rule)
    native = (compile_native_semantic_rules if semantic else compile_native_rules)(compiled)
    cp = LearnableMaterialCheckpoint(
        ruleset_fingerprint=compiled.ruleset_fingerprint,
        board_weights={"R": 1.}, hand_weights={"R": 1.},
        value_scale=10., reference_median=1.,
    )
    t, = collect_self_play(compiled, native, cp, SelfPlayConfig(
        games=1, nodes_per_move=1000, max_depth=1, epsilon=0.,
    ))
    assert t.terminal == "max_ply" and t.points
    assert all(p.leaf_feature_board == (1,) for p in t.points)
    assert all(p.leaf_value == 0. for p in t.points)
    assert all(p.leaf_terminal_z == 0. for p in t.points)
    assert tdleaf_update([t], cp, TDLeafConfig(alpha=.1)).mean_td_error == 0.


@pytest.mark.parametrize("value", [2., float("nan"), float("inf"), -float("inf")])
def test_invalid_terminal_leaf_target_is_rejected(value):
    payload = trajectory([point(0, (1, 0))]).to_dict()
    payload["points"][0]["leaf_terminal_z"] = value
    t = TrainingTrajectory.from_dict(payload)
    with pytest.raises(ValueError, match="terminal PV"):
        tdleaf_update([t], checkpoint(), TDLeafConfig(alpha=.1))
    with pytest.raises(ValueError, match="terminal PV"):
        td_signal_diagnostics([t], checkpoint(), TDLeafConfig(alpha=.1))


@requires_native
def test_actual_non_scoring_pv_is_not_a_draw_training_target():
    from generic_chess.rules.schema import RuleAutomaticAdjudication

    rule = replace(make_ruleset(
        4, [king_type(), T("R", RayAtom((0, 1)), RayAtom((0, -1)))],
        lines=["...k", "....", "R...", "K..."],
    ), max_ply=1, automatic_adjudications=(RuleAutomaticAdjudication("audit", 1),))
    compiled = compile_legacy_ruleset_for_semantic_execution(rule)
    native = compile_native_semantic_rules(compiled)
    cp = LearnableMaterialCheckpoint(
        ruleset_fingerprint=compiled.ruleset_fingerprint,
        board_weights={"R": 1.}, hand_weights={"R": 1.},
        value_scale=10., reference_median=1.,
    )
    with pytest.raises(ValueError, match="non-scoring PV leaf"):
        collect_self_play(compiled, native, cp, SelfPlayConfig(
            games=1, nodes_per_move=1000, max_depth=1, epsilon=0.,
        ))


@pytest.mark.parametrize("terminal", ["no_contest", "declaration"])
def test_diagnostics_reject_empty_non_scoring_episode(terminal):
    t = replace(trajectory([], None), terminal=terminal)
    with pytest.raises(ValueError, match="non-scoring"):
        td_signal_diagnostics([t], checkpoint(), TDLeafConfig(alpha=.1))


@requires_native
@pytest.mark.parametrize("outcome", ["WIN", "NO_CONTEST", "RESTART"])
def test_declaration_pv_is_not_silently_collected_as_ordinary_material(outcome):
    from generic_chess.session.session import GameSession
    from generic_chess.rules.schema import (RuleDeclaration, RuleWeightedMaterialMetric,
                                           RuleDeclarationOutcomeBand)
    from generic_chess.native.semantic_engine import SemanticSearchEngine
    from generic_chess.ai.limits import SearchLimits
    from generic_chess.core.declarations import available_declarations
    rule = make_ruleset(4, [king_type(), T("R", RayAtom((0,1)), RayAtom((0,-1)),
        RayAtom((1,0)), RayAtom((-1,0)))], lines=["k...", "....", "....", "..RK"])
    claim = RuleDeclaration("leaf_claim", 1, require_not_in_check=False,
        weighted_metric=RuleWeightedMaterialMetric(weights={"K":1}),
        outcome_bands=(RuleDeclarationOutcomeBand(1, outcome),))
    compiled = compile_legacy_ruleset_for_semantic_execution(replace(rule, declarations=(claim,)))
    native = compile_native_semantic_rules(compiled)
    checkpoint = LearnableMaterialCheckpoint(ruleset_fingerprint=compiled.ruleset_fingerprint,
        board_weights={"R":1.}, hand_weights={"R":1.}, value_scale=10., reference_median=1.)
    session = GameSession(compiled)
    result = SemanticSearchEngine(compiled, native, checkpoint=checkpoint, tt_megabytes=0).search(
        session, SearchLimits(max_depth=1, max_nodes=1000, quiescence_max_depth=0))
    assert result.completed_depth == 1 and result.principal_variation
    leaf = GameSession(compiled)
    for action in result.principal_variation:
        leaf.submit(action)
    if outcome == "WIN":
        assert result.decision_line[-1] == "leaf_claim"
        leaf.declare("leaf_claim")
        assert leaf.result.winner == 1
    else:
        # Native neutral floors may not carry the declaration in decision_line.
        # Available non-scoring claims are therefore an explicit unsupported
        # TD boundary, never inferred to be a real draw from a numeric score.
        assert any(x.outcome == outcome for x in available_declarations(leaf.state, compiled))
    with pytest.raises(NotImplementedError, match="declaration"):
        collect_self_play(compiled, native, checkpoint, SelfPlayConfig(games=1,
            max_depth=1, nodes_per_move=1000, max_plies=1, epsilon=0., tt_megabytes=0))


@requires_native
def test_actual_scoring_root_declaration_remains_collectible():
    from generic_chess.rules.schema import (RuleDeclaration, RuleWeightedMaterialMetric,
                                           RuleDeclarationOutcomeBand)
    rule = make_ruleset(4, [king_type()], lines=["...k", "....", "....", "K..."])
    claim = RuleDeclaration("root_win", 0, require_not_in_check=False,
        weighted_metric=RuleWeightedMaterialMetric(weights={"K":1}),
        outcome_bands=(RuleDeclarationOutcomeBand(1,"WIN"),))
    compiled = compile_legacy_ruleset_for_semantic_execution(replace(rule, declarations=(claim,)))
    native = compile_native_semantic_rules(compiled)
    checkpoint = LearnableMaterialCheckpoint(ruleset_fingerprint=compiled.ruleset_fingerprint,
        value_scale=10., reference_median=1.)
    trajectory, = collect_self_play(compiled, native, checkpoint,
        SelfPlayConfig(games=1, max_depth=1, nodes_per_move=1000, max_plies=1))
    assert trajectory.terminal_z == 1. and trajectory.winner == 0
    assert not trajectory.points and not trajectory.truncated
