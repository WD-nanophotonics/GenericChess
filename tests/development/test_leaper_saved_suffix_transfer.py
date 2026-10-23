from copy import deepcopy
import json
import pytest
from scripts.leaper_saved_suffix_transfer import try_witness,run,apply,verify
from scripts.leaper_explorer_truth import digest


def case():
    from scripts.leaper_microgames import conditional_C_liability
    from generic_chess.rules.schema import ruleset_from_dict
    from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution
    from generic_chess.session.session import GameSession
    from generic_chess.session.serialization import deserialize_game_record
    from scripts.leaper_design import state_sha
    p=conditional_C_liability();c=compile_legacy_ruleset_for_semantic_execution(ruleset_from_dict(p['rule']))
    s=GameSession.replay(c,deserialize_game_record(json.dumps(p['with_C_prefix_record'])))
    hid=state_sha(s.state);ply=s.state.ply_count
    root=dict(id=hid,fingerprint=c.ruleset_fingerprint,ply=ply,rule_remaining=c.max_ply-ply,
              record_id='r',cooperative_decisive=None,universal_draw=None)
    truth=dict(rules={c.ruleset_fingerprint:p['rule']},records={'r':p['with_C_record']},roots=[root])
    q=dict(id=hid,fingerprint=c.ruleset_fingerprint,source_record_id='r',source_id=hid,
           source_ply=ply,length=2)
    proposals=dict(input_digest=digest(truth),rows=[q],caps=dict(proof_seconds=10,proposals=1))
    return truth,proposals,s,p['with_C_record']['actions'][ply:]


def test_literal_positive_path_does_not_mutate_target_or_prove_forced_wdl():
    t,q,s,actions=case();before=s.state
    observed=try_witness(s,actions)
    assert observed['proved'] and observed['terminal_winner']==1 and observed['executed']==2
    assert s.state==before
    packet=run(t,q);out=apply(t,packet)
    assert out['roots'][0]['cooperative_decisive']is True
    assert 'wdl_bounds'not in out['roots'][0]
    assert t['roots'][0]['cooperative_decisive']is None
    assert verify(t,q,packet)['counts']==dict(positive_roots=1,literal_edges=2)


def test_incomplete_path_is_unknown_not_all_future_draw():
    _,_,s,actions=case();observation=try_witness(s,actions[:1])
    assert observation['proved']is False and observation['status']=='ongoing'


def test_chronological_loop_erasure_retains_only_recorded_nonloop_edges():
    from scripts.leaper_saved_suffix_transfer import erase_cycles
    actions=list('0123456')
    witness,indices=erase_cycles(list('abcbdefd'),actions)
    assert indices==[0,3]and witness==['0','3']
    with pytest.raises(ValueError):erase_cycles(['a','b'],[])


def test_shortened_actual_path_keeps_literal_proof_and_source_subsequence_binding():
    from scripts.leaper_saved_suffix_transfer import shorten_run
    t,q,_,actions=case()
    # The actual method's admission must reject this3x3toy. Direct literal
    # verification still checks a supplied subsequence without a scope claim.
    with pytest.raises(AssertionError):shorten_run(t,q)
    p=run(t,q);p['method']='chronological_loop_erasure'
    p['rows'][0].update(retained_source_indices=[0,1],witness=actions)
    assert verify(t,q,p)['counts']['positive_roots']==1
    p['rows'][0]['retained_source_indices']=[1,0]
    with pytest.raises(ValueError,match='indices'):verify(t,q,p)


@pytest.mark.parametrize('damage',['source','proposal','length','winner','target','duplicate'])
def test_positive_proof_bindings_and_observations_reject_corruption(damage):
    t,q,_,_=case();p=run(t,q)
    if damage=='source':p['input_digest']='bad'
    if damage=='proposal':p['proposal_digest']='bad'
    if damage=='length':
        q['rows'][0]['length']=1;p['rows'][0]['proposal']['length']=1;p['proposal_digest']=digest(q)
    if damage=='winner':p['rows'][0]['observation']['terminal_winner']=0
    if damage=='target':p['rows'][0]['id']='bad'
    if damage=='duplicate':p['rows']+=deepcopy(p['rows'])
    with pytest.raises((ValueError,KeyError)):verify(t,q,p)
