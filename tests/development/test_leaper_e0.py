from dataclasses import replace
import pytest
from scripts import leaper_design as L
from scripts.leaper_e0 import full_rule_code,brier_gain_bounds,interaction_bounds,freeze_predictions


def test_full_rule_stratum_does_not_drop_third_actor():
    r=L.definition(23,28)
    c=L.PieceType('C','C',tuple(L.LeapAtom(v) for v in L.offsets(31)))
    r=replace(r,piece_types=r.piece_types+(c,))
    w={'masks':[23,28],'code':[23,28,31],'rule':L.ruleset_to_dict(r,include_metadata=True)}
    assert full_rule_code(w)==(23,28,31)
    w['code']=[23,28,16]
    with pytest.raises(ValueError,match='metadata disagrees'):full_rule_code(w)


def test_missing_binary_label_retains_both_score_extremes():
    assert brier_gain_bounds(.7,.2)==pytest.approx([-.45,.55])
    assert brier_gain_bounds(.7,.2,1)==pytest.approx([.55,.55])
    with pytest.raises(ValueError):brier_gain_bounds(1.1,.2)


def test_missing_cell_is_not_a_draw():
    cells={'S3':[0,0],'U3':[1,1],'S4':[0,0],'U4':[-1,1]}
    assert interaction_bounds(cells)==[-2,0]
    cells['U4']=[-1,-1]
    assert interaction_bounds(cells)==[-2,-2]


def test_prediction_freeze_uses_registered_calibration_and_refuses_fitness(tmp_path):
    reg={'E0_prediction_rule':{'target':'finite policy interaction'},'calibrated_probability_by_feature':{'False':.1,'True':.4},'calibrated_constant_probability':.3}
    ws={'worlds':[{'world':0,'code_world':0,'placement_index':0,'prefix_index':0,'initial_terminal':{'status':'ongoing'}}]}
    rows=[{'world':0,'policy':p,'decision':{'action':a}} for p,a in [('S3','a'),('U3','b'),('S4','a'),('U4','a')]]
    L.write_record(tmp_path/'registration.json',reg);L.write_record(tmp_path/'inputs.json',ws);L.write_record(tmp_path/'preflight.json',{'status':'CLOSED','missing':[],'rows':rows})
    f=freeze_predictions(tmp_path)
    assert f['new_fitness_at_freeze']==0 and f['rows'][0]['positive_feature']
    assert f['rows'][0]['probability_any_role_nonzero_interaction']==.4
    assert f['rows'][0]['zero_information_baseline_probability']==.3
    with pytest.raises(AssertionError):freeze_predictions(tmp_path)
