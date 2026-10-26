"""Reject unsupported/invalid batch TD settings before any data/search/update."""
import pytest
from generic_chess.learning.tdleaf import TDLeafConfig

@pytest.mark.parametrize('gamma',[0.,.5,.99,-1.,float('nan'),float('inf'),True])
def test_batch_discount_is_not_silently_ignored(gamma):
    with pytest.raises(ValueError,match='gamma=1'):
        TDLeafConfig(gamma=gamma)

@pytest.mark.parametrize('name,value',[
    ('lambd',-1.),('lambd',1.1),('lambd',float('nan')),
    ('alpha',0.),('alpha',-1.),('alpha',float('nan')),('alpha',float('inf')),('alpha',1e6),
    ('value_scale',0.),('value_scale',-1.),('value_scale',float('nan')),('value_scale',float('inf'))])
def test_invalid_settings_fail_before_diagnostic_fallback_or_arithmetic(name,value):
    with pytest.raises(ValueError,match=name):
        TDLeafConfig(**{name:value})

@pytest.mark.parametrize('lam',[0.,.7,1.])
def test_current_explicit_gamma_one_configs_keep_fields(lam):
    cfg=TDLeafConfig(gamma=1.,lambd=lam,alpha=.1,value_scale=10.)
    assert cfg.gamma==1. and cfg.lambd==lam and cfg.alpha==.1 and cfg.value_scale==10.


@pytest.mark.parametrize('reference_median', [0., 200.])
def test_diagnostic_default_alpha_matches_actual_trainer_fallback(reference_median):
    from generic_chess.learning.material import LearnableMaterialCheckpoint
    from generic_chess.learning.trajectory import TrainingPoint, TrainingTrajectory
    from generic_chess.learning.tdleaf import tdleaf_update
    from generic_chess.learning.diagnostics import td_signal_diagnostics
    cp = LearnableMaterialCheckpoint(board_weights={'P':100.,'Q':300.},
        hand_weights={'P':90.,'Q':270.}, value_scale=800.,
        reference_median=reference_median, w_max=10000.)
    point = TrainingPoint(ply=0, root_position_key='root', action=None,
        exploration=False, pv=(), leaf_position_key='leaf',
        leaf_feature_board=(1,0), leaf_feature_hand=(0,1),
        leaf_value=0., completed_depth=1)
    trajectory = TrainingTrajectory(ruleset_fingerprint='',generation=0,
        game_seed=1,initial_position_key='root',actions=(),search_nodes=1,
        search_max_depth=1,terminal='checkmate',winner=0,
        type_ids=('P','Q'),points=(point,))
    default = TDLeafConfig(value_scale=400.)
    # Actual trainer's documented default uses checkpoint scale, not override.
    explicit = TDLeafConfig(alpha=2., value_scale=400.)
    assert tdleaf_update([trajectory],cp,default)==tdleaf_update([trajectory],cp,explicit)
    assert td_signal_diagnostics([trajectory],cp,default)==td_signal_diagnostics([trajectory],cp,explicit)
