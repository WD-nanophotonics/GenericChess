"""Exact enumerated reference for shared-label loss bounds and coverage."""
from copy import deepcopy
from itertools import product
import pytest

from scripts.leaper_explorer_compare import compare, improvement_bounds


def inputs(labels=(True,False,None)):
    truth=dict(roots=[dict(id=str(i), fingerprint='A', mu_id='muA',
         split='exposed', wdl_fork=y, cooperative_decisive=None, universal_draw=None)
         for i,y in enumerate(labels)])
    def packet(name, probabilities):
        return dict(format='leaper-explorer-predictions-v1',freeze=dict(
             forecast_id=name,information_set='synthetic unit-test fixture only',
             frozen_at='fixture',truth_access='synthetic known truth, NOT actual E0'),
             predictions=[dict(id=str(i),fingerprint='A',mu_id='muA',
                 property='wdl_fork',probability=p,source_sha='a'*40,cost=dict(nodes=1))
                 for i,p in enumerate(probabilities) if p is not None])
    return truth,packet('model',[.9,.7,.9]),packet('baseline',[.8,.8,.8])


def row(output):
    return next(r for r in output['rows'] if r['property']=='wdl_fork')


def test_shared_unknown_labels_can_cancel_loss_exactly():
    assert improvement_bounds(.9,.9,None)==[0,0]
    assert improvement_bounds(.9,.8,None)==pytest.approx([-.17,.03])


def test_paired_bounds_match_every_binary_completion():
    # This separately enumerates all actual label completions. Individual
    # Brier endpoint subtraction would be much wider even at equal forecasts.
    for ps,qs in product(((0.,1.,.5),(.9,.8,.7),(.2,.9,.6)),repeat=2):
        truth,model,base=inputs((None,)*3)
        for i in range(3):
            model['predictions'][i]['probability']=ps[i]
            base['predictions'][i]['probability']=qs[i]
        actual=[sum((q-y)**2-(p-y)**2 for p,q,y in zip(ps,qs,ys))/3
                for ys in product((0,1),repeat=3)]
        got=row(compare(truth,model,base))
        assert got['paired_support_improvement_bounds']==pytest.approx([min(actual),max(actual)])
        assert got['whole_denominator_improvement_bounds']==pytest.approx([min(actual),max(actual)])


def test_unknown_is_not_false_and_shared_known_skill_uses_same_denominator():
    t,m,b=inputs();r=row(compare(t,m,b))
    assert (r['paired'],r['paired_known'],r['paired_unknown'])==(3,2,1)
    assert r['known_paired_model_brier']==pytest.approx((.01+.49)/2)
    assert r['known_paired_baseline_brier']==pytest.approx((.04+.64)/2)
    assert r['known_paired_brier_skill']==pytest.approx(1-.5/.68)


def test_missing_baseline_is_unpaired_and_cannot_be_imputed_as_half():
    t,m,b=inputs();b['predictions'].pop()
    r=row(compare(t,m,b));assert r['unpaired']==1
    assert r['paired_unknown']==0
    assert r['whole_denominator_improvement_bounds']==pytest.approx([(.18-1)/3,(.18+1)/3])


def test_empty_predictions_keep_full_missing_bounds_without_fake_perfect_skill():
    t,m,b=inputs();m['predictions']=[];b['predictions']=[]
    r=row(compare(t,m,b))
    assert r['paired_support_improvement_bounds'] is None
    assert r['whole_denominator_improvement_bounds']==[-1,1]
    assert r['known_paired_brier_skill'] is None
    assert r['skill_undefined_reason']=='no paired known labels'


def test_zero_baseline_loss_does_not_divide_by_zero_or_claim_skill_zero():
    t,m,b=inputs();t['roots']=t['roots'][:1];m['predictions']=m['predictions'][:1];b['predictions']=b['predictions'][:1]
    b['predictions'][0]['probability']=1
    r=row(compare(t,m,b))
    assert r['known_paired_brier_skill'] is None
    assert r['skill_undefined_reason']=='baseline has zero paired known loss'


def test_macro_retains_equal_rule_weight_under_missing_pairing():
    t,m,b=inputs();t['roots'][2].update(fingerprint='B',mu_id='muB')
    for packet in (m,b):packet['predictions'][2].update(fingerprint='B',mu_id='muB')
    r=row(compare(t,m,b))
    assert r['equal_rule_whole_improvement_bounds']==pytest.approx([(.18/2-.17)/2,(.18/2+.03)/2])
    assert r['equal_rule_whole_improvement_bounds']!=r['whole_denominator_improvement_bounds']


@pytest.mark.parametrize('field,value',[('mu_id','wrong'),('fingerprint','wrong'),('probability',True),('source_sha','a'),('cost',{})])
def test_baseline_is_subject_to_same_exact_join_and_provenance_checks(field,value):
    t,m,b=inputs();b['predictions'][0][field]=value
    with pytest.raises(ValueError):compare(t,m,b)


def test_freeze_and_duplicate_rejection():
    t,m,b=inputs();b['predictions'].append(deepcopy(b['predictions'][0]))
    with pytest.raises(ValueError):compare(t,m,b)
    t,m,b=inputs();b.pop('freeze')
    with pytest.raises(ValueError):compare(t,m,b)
    t,m,b=inputs();b['freeze']['forecast_id']='model'
    with pytest.raises(ValueError):compare(t,m,b)


def test_case_output_preserves_actual_known_errors_without_labelling_unknown():
    t,m,b=inputs();out=compare(t,m,b)
    assert [r['model_error'] for r in out['cases']]==[None,'FP',None]
    assert out['cases'][2]['truth'] is None
