"""An actual saved full-history counterexample for optional sampling coupling."""
from pathlib import Path
from scripts import leaper_design as L

class RankRng:
    def __init__(self,index):self.index=index
    def randrange(self,n):
        assert 0<=self.index<n
        return self.index

def fixture():
    raw=L.load(Path(__file__).parent/'fixtures/leaper_floor_type_cycle.json')
    sessions=[L.GameSession.replay(L.compile_rule(L.ruleset_from_dict(x['rule'])),
              L.deserialize_game_record(__import__('json').dumps(x['record']))) for x in raw['parts']]
    return raw,sessions

def signature(action,mapping):
    return (mapping[action.actor_type_id],action.from_square.file,action.from_square.rank,
            action.to_square.file,action.to_square.rank)

def test_observed_default_index_mismatch_is_preserved():
    raw,sessions=fixture()
    actions=[L.floor(s,RankRng(raw['index']))[0] for s in sessions]
    assert [L.record_value(a) for a in actions]==raw['expected_default_actions']
    assert signature(actions[0],raw['type_maps'][0])!=signature(actions[1],raw['type_maps'][1])

def test_optin_coupling_matches_every_physical_rank_and_preserves_uniform_support():
    raw,sessions=fixture();n=len(sessions[0].legal_actions());observed=[]
    for i in range(n):
        actions=[L.floor(s,RankRng(i),physical_type_map=m)[0] for s,m in zip(sessions,raw['type_maps'])]
        keys=[signature(a,m) for a,m in zip(actions,raw['type_maps'])]
        assert keys[0]==keys[1]
        observed.append(keys[0])
    assert len(set(observed))==n
    assert set(observed)=={signature(a,raw['type_maps'][0]) for a in sessions[0].legal_actions()}


import pytest
from dataclasses import replace

def test_registered_mapping_rejects_partial_nonbijective_and_anchor_changes():
    raw,_=fixture();world={'rule':raw['parts'][0]['rule']}
    reg={'floor_coupling':L.FLOOR_COUPLING}
    valid=raw['type_maps'][0]
    assert L.floor_type_map(reg,{**world,'floor_type_map':valid})==valid
    for bad in ({'K':'K'},dict(valid,A='B'),dict(valid,K='A',A='K')):
        with pytest.raises(ValueError,match='bijection'):
            L.floor_type_map(reg,{**world,'floor_type_map':bad})
    with pytest.raises(ValueError,match='explicit'):
        L.floor_type_map({}, {**world,'floor_type_map':valid})
    with pytest.raises(ValueError,match='unknown'):
        L.floor_type_map({'floor_coupling':'typo'}, {**world,'floor_type_map':valid})

@pytest.mark.parametrize('alteration',[
    {'pass_enabled':True}, {'semantic_actions':('placeholder',)},
    {'capture_disposition':'capture_to_hand'},
    {'drop_allowed':{'A':((True,)*16,)*2}},
])
def test_full_rule_scope_is_not_silently_truncated(alteration):
    raw,_=fixture();rule=L.ruleset_from_dict(raw['parts'][0]['rule'])
    # The semantic-action placeholder cannot serialize; use a real schema option
    # below for the full additional-semantics rejection instead.
    if 'semantic_actions' in alteration:
        alteration={'initial_setup_options':(__import__('generic_chess.rules.schema',fromlist=['RuleInitialSetupOption']).RuleInitialSetupOption('alternate',rule.initial_position),)}
    with pytest.raises(ValueError):
        L.floor_type_map({'floor_coupling':L.FLOOR_COUPLING},
            {'rule':L.ruleset_to_dict(replace(rule,**alteration)), 'floor_type_map':raw['type_maps'][0]})


def test_reader_replays_optin_and_binds_registered_map(tmp_path,monkeypatch):
    import gzip,json
    from scripts.leaper_portrait import verify_packet
    raw,sessions=fixture();s=sessions[0];world={'world':0,'rule':raw['parts'][0]['rule'],'floor_type_map':raw['type_maps'][0]}
    import random
    rng=random.Random(19);initial=L.record_value(s.to_record());state=L.state_sha(s.state)
    action,detail=L.floor(s,rng,physical_type_map=world['floor_type_map'])
    q={'actor':s.state.position.side_to_move,'policy':'FLOOR','state_sha256':state,'legal_count':len(s.legal_actions()),'action':L.record_value(action),'floor':detail}
    s.submit(action)
    game={'world':0,'role':0,'initial_record':initial,'rng_seeds':{0:19,1:19},'queries':[q],
        'final_record':L.record_value(s.to_record()),'final_state':L.record_value(s.state),
        'terminal':L.record_value(s.result),'censor':'caller_test_cap','utility':[-1,1],
        'floor_coupling':L.FLOOR_COUPLING,'floor_type_map':world['floor_type_map']}
    packet={'games':[{'run':'coupled','rule':world['rule'],'game':game}],
        'runs':{'coupled':{'files':{'registration.json':{'floor_coupling':L.FLOOR_COUPLING},'inputs.json':{'worlds':[world]}}}}}
    dest=tmp_path/'packet.json.gz'
    def save():dest.write_bytes(gzip.compress(json.dumps(packet).encode()))
    save();assert verify_packet(dest)['FLOOR_policy_checks']==1
    game['floor_type_map']=dict(game['floor_type_map'],A='B',B='A');save()
    with pytest.raises(AssertionError,match='binding'):verify_packet(dest)
    game.pop('floor_coupling');game.pop('floor_type_map');save()
    with pytest.raises(AssertionError,match='binding'):verify_packet(dest)


def test_explicit_depth_limits_preserve_default_and_validate_requested_rung():
    reg={'nodes':512,'search_variants':{'D3':{'base':'AB','nodes':8192,'depth':3}}}
    assert L.policy_limits(reg,'AB')==L.limits(512)
    lim=L.policy_limits(reg,'D3');assert lim.max_depth==3 and lim.max_nodes==8192
    assert lim.max_time_seconds is None and lim.quiescence_max_depth==0 and lim.quiescence_hard_max_depth==8
    for bad in (True,0,65,2.5):
        reg['search_variants']['D3']['depth']=bad
        with pytest.raises(ValueError,match='requested search depth'):L.policy_limits(reg,'D3')


def test_actual_player_receives_requested_depth_instead_of_node_label(tmp_path,monkeypatch):
    monkeypatch.setattr(L,'PAIRS',((1,2),));d=tmp_path/'depth';L.prepare(d)
    reg=L.load(d/'registration.json');reg.update(pairs={'D2_D1':['D2','D1']},planned_games=2,caller_plies=2,
        search_variants={f'D{i}':{'base':'AB','nodes':128,'depth':i} for i in (1,2)})
    L.write_record(d/'registration.json',reg)
    L.write_record(d/'preflight.json',{'status':'CLOSED','missing':[],'seconds':0,'rows':[{'seconds':.001}],'cost_gate_passed':True})
    observed=[];make=L.make_player
    class Wrapped:
        def __init__(self,player):self.player=player
        def choose_action(self,s,lim):
            observed.append(lim.max_depth);return self.player.choose_action(s,lim)
    monkeypatch.setattr(L,'make_player',lambda c,p,w:Wrapped(make(c,p,w)))
    L.run(d);assert sorted(observed)==[1,1,2,2]
    for sl in L.load(d/'results.json')['slots']:
        for q in L.load(d/sl['receipt'])['queries']:
            assert q['requested_depth']==int(q['policy'][1:])
            assert q['decision']['completed_depth']<=q['requested_depth']
