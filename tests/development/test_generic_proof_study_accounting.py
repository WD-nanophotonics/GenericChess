"""Concrete censoring/missing-slot counterexamples; no engine or mock win."""
from scripts.generic_proof_study_audit import planned_bounds


def row(pay,plies=16,tail=None):return dict(payoff=pay,trajectory=[{}]*plies,tail_admission=tail)


def test_unstarted_D_slot_keeps_fixed_denominator():
    plan={'H':16}
    B=planned_bounds([row(1)],2,plan)
    D=planned_bounds([],2,plan)
    assert B['planned_finite_event_bounds']==[0.,1.]
    assert D['planned_finite_event_bounds']==[-1.,1.]
    assert D['missing_games']==2
    assert [D['planned_finite_event_bounds'][0]-B['planned_finite_event_bounds'][1],D['planned_finite_event_bounds'][1]-B['planned_finite_event_bounds'][0]]==[-2.,1.]


def test_uncertified_horizon_unknown_is_zero_event_but_incomplete_tail_is_not():
    plan={'H':16}
    out=planned_bounds([row(None),row(None,18,{'owner':0,'rank':5}),row(None,3)],3,plan)
    assert out['early_incomplete']==2 and out['missing_games']==0
    assert out['planned_finite_event_bounds']==[-2/3,2/3]
    assert out['planned_infinite_outcome_bounds']==[-1.,1.]
