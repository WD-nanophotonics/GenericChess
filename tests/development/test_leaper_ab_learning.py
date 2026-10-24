"""Reject false targets and PV/update claims in the portable learner reader."""
from copy import deepcopy
import json,math
import pytest
from scripts import leaper_design as L
from scripts.leaper_ab_learner_exposure import source_documents,restore
from scripts.verify_leaper_ab_learning import verify_game,verify_uniform_game,td_sum
from generic_chess.learning.incremental import FixedScaleSessionEnv,Model,SessionChoice


@pytest.fixture
def literal_one_edge():
    world=json.loads(source_documents()['contact/inputs.json']);c=L.compile_rule(L.ruleset_from_dict(world['rule']));s=restore(c,world['roots'][0]['record']);sha=L.state_sha(s.state);a=s.legal_actions()[0]
    choice=L.record_value(SessionChoice('ACTION',action=a));s.submit(a);phi=list(FixedScaleSessionEnv(s,unit_type='A').features())
    receipt=dict(complete=True,action=choice,pv_choices=[choice],pv_phi=phi,pv_terminal=False,value=Model((1,1,0,0)).raw(phi),nodes=1)
    row=dict(slot=dict(phase='eval',root=0,role=0),before=[1,1,0,0],after=[1,1,0,0],queries=[dict(state_sha256=sha,actor=0,receipt=receipt)],final_record=L.record_value(s.to_record()),terminal=L.record_value(s.result),result=dict(outcome=None,update=None),utility=None)
    return world,row


def test_actual_literal_edge_is_accepted_but_unknown_is_never_draw(literal_one_edge):
    world,row=literal_one_edge
    assert verify_game(world,row)['PV_plies']==1
    bad=deepcopy(row);bad['result']['outcome']=0;bad['utility']=0
    with pytest.raises(ValueError,match='UNKNOWN/actual terminal'):verify_game(world,bad)


@pytest.mark.parametrize('field,value', [('value',999),('pv_phi',[999,0,0,0]),('pv_terminal',True)])
def test_literal_pv_corruptions_rejected(literal_one_edge,field,value):
    world,row=literal_one_edge;bad=deepcopy(row);bad['queries'][0]['receipt'][field]=value
    with pytest.raises(ValueError):verify_game(world,bad)


def test_complete_state_binding_rejected(literal_one_edge):
    world,row=literal_one_edge;row['queries'][0]['state_sha256']='0'*64
    with pytest.raises(ValueError,match='full-history'):verify_game(world,row)


def test_nonzero_error_does_not_create_a_fixed_feature_gradient():
    after,stats=td_sum([1,2,0,0],[dict(value=1,pv_phi=[1,0,0,0],pv_terminal=False)],0)
    assert after==[1,2,0,0]and not stats['changed']and stats['loss']>0
    active,stats=td_sum([1,2,0,0],[dict(value=2,pv_phi=[0,1,0,0],pv_terminal=False)],0)
    expected=2-.05*math.tanh(.2)*(1-math.tanh(.2)**2)/10
    assert active[1]==pytest.approx(expected)and stats['changed']and active[0]==1


def test_censor_preserves_interior_targets_without_inventing_final_credit():
    receipts=[dict(value=2,pv_phi=[0,1,0,0],pv_terminal=False),dict(value=0,pv_phi=[0,0,0,0],pv_terminal=False)]
    after,stats=td_sum([1,2,0,0],receipts,None)
    assert after[1]<2 and stats['samples']==1 and stats['censored']and stats['terminal_credit_l1']==0


def test_completed_but_uncommitted_query_is_not_a_move_or_td_observation(literal_one_edge):
    world,row=literal_one_edge;c=L.compile_rule(L.ruleset_from_dict(world['rule']));s=restore(c,world['roots'][0]['record'])
    row['slot'].update(seed=5);row['events']=[dict(row['queries'][0],kind='candidate')]
    row['final_record']=L.record_value(s.to_record());row['terminal']=L.record_value(s.result)
    row['result'].update(plies=0,queries=1,nodes=1)
    counts=verify_uniform_game(world,row)
    assert counts['uncommitted_tail_events']==1 and counts.get('committed_plies',0)==0
    row['result']['outcome']=0
    with pytest.raises(ValueError):verify_uniform_game(world,row)


def test_uniform_stream_is_replayed_from_actual_legal_actions():
    import random
    world=json.loads(source_documents()['contact/inputs.json']);c=L.compile_rule(L.ruleset_from_dict(world['rule']));s=restore(c,world['roots'][0]['record']);sha=L.state_sha(s.state)
    choices=sorted(FixedScaleSessionEnv(s,unit_type='A').actions(),key=lambda a:json.dumps(L.record_value(a),sort_keys=True));choice=choices[random.Random(7).randrange(len(choices))];s.submit(choice.action)
    row=dict(slot=dict(phase='eval',root=0,role=1,seed=7),before=[1,1,0,0],after=[1,1,0,0],events=[dict(kind='Uniform',actor=0,state_sha256=sha,choice=L.record_value(choice))],final_record=L.record_value(s.to_record()),terminal=L.record_value(s.result),result=dict(outcome=None,update=None,plies=1,queries=0,nodes=0),utility=None)
    assert verify_uniform_game(world,row)['Uniform_selections']==1
    bad=deepcopy(row);bad['events'][0]['choice']=L.record_value(next(a for a in choices if a!=choice))
    with pytest.raises(ValueError,match='Uniform RNG'):verify_uniform_game(world,bad)


def test_json_roundtrip_pair_keys_have_the_same_scientific_representation():
    from scripts.verify_leaper_ab_learning_packet import no_time
    value=dict(pairs=[dict(key=('contact',0,1),difference=0)],seconds=3)
    assert no_time(value)==no_time(json.loads(json.dumps(value)))


@pytest.fixture
def tiny_packet(tmp_path):
    import gzip,hashlib
    directory=tmp_path/'packet';directory.mkdir()
    body=dict(documents_utf8={'case.json':'{}'},source_capsules_utf8={'untrusted.py':"raise RuntimeError('capsules must never execute')\n"})
    decoded=json.dumps(body).encode();raw=gzip.compress(decoded,mtime=0)
    meta=lambda text:dict(bytes=len(text.encode()),sha256=hashlib.sha256(text.encode()).hexdigest())
    manifest=dict(packet_sha256=hashlib.sha256(raw).hexdigest(),decoded_sha256=hashlib.sha256(decoded).hexdigest(),external_files={},producer_bindings={},**{group:{k:meta(v)for k,v in docs.items()}for group,docs in body.items()})
    (directory/'evidence.json.gz').write_bytes(raw);(directory/'manifest.json').write_text(json.dumps(manifest))
    output=tmp_path/'read';output.mkdir();return directory,output


def test_capsules_are_data_only_and_not_materialized_as_code(tiny_packet):
    from scripts.verify_leaper_ab_learning_packet import read
    directory,output=tiny_packet;_,packet=read(directory,output)
    assert (output/'case.json').read_text()=='{}'and not(output/'untrusted.py').exists()
    assert 'raise RuntimeError'in packet['source_capsules_utf8']['untrusted.py']


def test_corrupt_packet_rejected_before_decoding(tiny_packet):
    from scripts.verify_leaper_ab_learning_packet import read
    directory,output=tiny_packet;p=directory/'evidence.json.gz';raw=p.read_bytes();p.write_bytes(raw[:-1]+bytes((raw[-1]^1,)))
    with pytest.raises(ValueError,match='packet hash'):read(directory,output)
