"""Actual counterfactual controller risks, not an experiment-output mirror."""
from dataclasses import asdict
import json
from pathlib import Path
from scripts import leaper_design as L
from scripts.leaper_prior_td_pilot import restore
from scripts.aux_mixed_experience_20261105 import copied,consumed_indices
from generic_chess.learning.incremental import Model,TDLeafEpisode,FixedScaleSessionEnv,play_episode,BudgetEnd

def test_callback_complete_query_can_be_unconsumed_after_post_query_stop():
    cfg=json.loads((Path(__file__).resolve().parents[2]/'docs/research/data/aux_capture_material_20261105/plan.json').read_bytes())
    w=cfg['worlds']['0']['train'];env=FixedScaleSessionEnv(restore(L.compile_rule(L.ruleset_from_dict(w['RuleSet'])),w['record']),unit_type='A',feature_mode='count_pairs')
    model=Model([1.,1.,1.,0.,0.,0.]+[0.]*21);before=env.record();events=[];stop=[False]
    def callback(ply,actor,r):
        events.append(dict(kind='candidate',receipt=L.record_value(asdict(r))));stop[0]=True
    def cancel():
        if stop[0]:raise BudgetEnd('POST_QUERY_TEST_STOP')
    ep=play_episode(env,model,opponent=copied(model),learner=TDLeafEpisode(),depth=1,query_nodes=2048,seconds=10,cancel=cancel,on_query=callback,search_backend='mainline')
    assert len(events)==1 and events[0]['receipt']['complete']
    assert ep.ending=='POST_QUERY_TEST_STOP' and ep.outcome is None and ep.plies==0
    assert ep.update['observed_searches']==0 and not ep.update['changed']
    assert consumed_indices(events,ep)==[] and env.record()==before

def test_fork_copies_full_model_without_cross_branch_mutation():
    common=Model([1.,.9,.8],fixed=1,scale=7.)
    single,mixed=copied(common),copied(common)
    assert single.fixed==mixed.fixed==common.fixed==1 and single.scale==mixed.scale==common.scale==7.
    saved=list(common.weights);single.apply([.1,.2,.3])
    assert common.weights==mixed.weights==saved and single.weights!=saved
    assert single.weights[1]==1.
