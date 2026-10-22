"""Scientific probe contracts exposed by actual preparation/aggregation failures."""
import pytest
from generic_chess.session.result import SessionResult,SessionStatus
from generic_chess.session.session import GameSession
from generic_chess.rules.schema import ruleset_to_dict,ruleset_from_dict,compute_fingerprint
from scripts.leaper_design import offsets,graph,definition,compile_rule,outcome_value,match_action,record_value

@pytest.mark.parametrize('bad',[0,32,-1,True,1.5,'1'])
def test_orbit_mask_rejects_non_domain_inputs(bad):
    with pytest.raises(ValueError):offsets(bad)

def test_orbits_are_distinct_complete_d4_closed_sets():
    sets=[set(offsets(i)) for i in range(1,32)]
    assert len({tuple(sorted(s)) for s in sets})==31
    assert [len(offsets(1<<i)) for i in range(5)]==[4,4,4,8,4]
    for s in sets:
        assert (0,0) not in s
        assert {(-x,y) for x,y in s}==s
        assert {(y,x) for x,y in s}==s

@pytest.mark.parametrize('mask,components',[(1,[16]),(2,[8,8]),(4,[4,4,4,4]),(8,[16]),(16,[2]*8)])
def test_empty_board_graph_has_analytically_known_components(mask,components):
    assert graph(mask)['components']==components

@pytest.mark.parametrize('a,b',[(1,2),(1,3),(1,4),(1,8),(1,16),(2,4),(2,8),(4,8),(8,16),(3,8)])
def test_canonical_rules_roundtrip_and_compile(a,b):
    rules=definition(a,b);raw=ruleset_to_dict(rules,include_metadata=True)
    restored=ruleset_from_dict(raw)
    assert compute_fingerprint(restored)==compute_fingerprint(rules)
    s=GameSession(compile_rule(restored))
    assert s.to_record().ruleset_fingerprint==compute_fingerprint(rules)
    assert not s.state.terminal_status.is_terminal
    assert len(s.legal_actions())>0
    assert rules.capture_disposition=='remove_from_game'
    assert len([p for row in rules.initial_position for p in row if p])==6

@pytest.mark.parametrize('status',[SessionStatus.ONGOING,SessionStatus.NO_CONTEST])
def test_unknown_or_restart_is_never_draw(status):
    assert outcome_value(SessionResult(status,None),0) is None

@pytest.mark.parametrize('status',[SessionStatus.MAX_PLY,SessionStatus.REPETITION,SessionStatus.STALEMATE])
def test_true_rule_draw_uses_session_result_contract(status):
    # SessionResult has no is_terminal property: this is the actual observed API.
    r=SessionResult(status,None)
    assert outcome_value(r,0)==0
    assert outcome_value(r,1)==0
    assert outcome_value(r,0,'whole_cap') is None

def test_terminal_winner_has_opposite_role_values():
    r=SessionResult(SessionStatus.CHECKMATE,1)
    assert outcome_value(r,0)==-1
    assert outcome_value(r,1)==1

def test_diagnostic_action_must_match_a_real_legal_action():
    s=GameSession(compile_rule(definition(1,8)));action=s.legal_actions()[0]
    assert match_action(s,record_value(action))==action
    with pytest.raises(ValueError):match_action(s,{'not':'a move'})

def test_explicit_search_variant_keeps_evaluator_and_distinguishes_budget():
    from scripts.leaper_design import search_spec
    reg={'nodes':512,'search_variants':{'AB8192':{'base':'AB','nodes':8192}}}
    assert search_spec(reg,'AB')==('AB',512)
    assert search_spec(reg,'AB8192')==('AB',8192)
    for invalid in (True,0,-1,1.5):
        reg['search_variants']['AB8192']['nodes']=invalid
        with pytest.raises(ValueError,match='positive integer'):search_spec(reg,'AB8192')
    with pytest.raises(ValueError,match='unknown search base'):search_spec({'nodes':512},'TYPO')

@pytest.mark.parametrize('pair,plies,expected',[
    (['AB','RNG'],128,64),(['AB8192','AB'],128,128),
    (['STATIC_ADAPTER','M0'],3,3),(['AB','FLOOR'],3,2),(['RNG','FLOOR'],128,0),
])
def test_call_forecast_counts_both_actual_search_actors(pair,plies,expected):
    from scripts.leaper_design import forecast_search_turns
    assert forecast_search_turns({'pairs':{'actual':pair},'caller_plies':plies})==expected

def test_code_indexed_seed_bank_survives_representation_world_number():
    from scripts.leaper_design import actor_seeds
    reg={'seed':100};slot={'repeat':2,'role':1}
    expected={0:70310,1:70311}
    assert actor_seeds(reg,{'world':7},slot)==expected
    assert actor_seeds(reg,{'world':95,'seed_world':7},slot)==expected
    assert actor_seeds(reg,{'world':95},slot)!=expected
    for value in (True,-1,'7'):
        with pytest.raises(ValueError,match='seed_world'):actor_seeds(reg,{'world':95,'seed_world':value},slot)

def test_run_delivers_registered_budget_to_each_actual_actor(tmp_path,monkeypatch):
    import scripts.leaper_design as L
    monkeypatch.setattr(L,'PAIRS',((1,2),))
    d=tmp_path/'budgets';L.prepare(d)
    reg=L.load(d/'registration.json');reg.update(pairs={'HI_LO':['HI','AB']},planned_games=2,caller_plies=2,
        nodes=8,search_variants={'HI':{'base':'AB','nodes':16}})
    L.write_record(d/'registration.json',reg)
    L.write_record(d/'preflight.json',{'status':'CLOSED','missing':[],'seconds':0,'rows':[{'seconds':.001}],'cost_gate_passed':True})
    actual=[];original=L.make_player
    class Wrapped:
        def __init__(self,player):self.player=player
        def choose_action(self,s,lim):
            actual.append(lim.max_nodes)
            return self.player.choose_action(s,lim)
    monkeypatch.setattr(L,'make_player',lambda c,p,w:Wrapped(original(c,p,w)))
    L.run(d);r=L.load(d/'results.json')
    assert sorted(actual)==[8,8,16,16]
    for slot in r['slots']:
        row=L.load(d/slot['receipt']);assert row['utility']==[-1,1]
        for q in row['queries']:assert q['node_budget']==(16 if q['actor']==slot['role'] else 8)

def test_material_zero_preserves_other_fields_and_exact_component():
    from scripts.leaper_design import material_profiles,Evaluator,EvaluationConfig,legal_successors
    c=compile_rule(definition(8,16));s=GameSession(c);base,zero=material_profiles(c)
    assert zero.median_non_anchor_value==base.median_non_anchor_value
    assert zero.promotion_gain_by_type==base.promotion_gain_by_type
    assert all(v==0 for v in zero.board_value_by_type.values())
    assert all(v==0 for v in zero.hand_value_by_base_type.values())
    es=Evaluator(c,base,EvaluationConfig());ez=Evaluator(c,zero,EvaluationConfig());nonzero=False
    for st in [s.state]+[ch for _,ch in legal_successors(s.state,c)]:
        material=sum((1 if p.owner==0 else -1)*base.board_value_by_type[p.current_type_id] for p in st.position.board if p)
        if st.position.side_to_move==1:material=-material
        assert es.evaluate(st)-ez.evaluate(st)==material
        nonzero|=material!=0
    assert nonzero,'fixture includes an actual material-changing capture'

def test_same_adapter_keeps_static_ordering_in_both_leaf_modes():
    from scripts.leaper_design import material_profiles,Evaluator,EvaluationConfig,LeafOrderAdapter
    c=compile_rule(definition(1,8));base,zero=material_profiles(c);order=Evaluator(c,base,EvaluationConfig())
    for profile in (base,zero):
        adapter=LeafOrderAdapter(Evaluator(c,profile,EvaluationConfig()),order)
        for t in base.board_value_by_type:assert adapter.type_value(t)==order.type_value(t)

def test_material_preflight_requires_frozen_full_history_inputs(tmp_path):
    from scripts.leaper_design import prepare,preflight
    d=tmp_path/'material';prepare(d,material_ablation=True)
    with pytest.raises(ValueError,match='complete-history'):
        preflight(d)
    assert not(d/'preflight.json').exists(),'failure must precede any cost query or misleading successful receipt'

@pytest.mark.parametrize('material,expected',[(False,12),(True,8)])
def test_prepared_plan_counts_actual_codes_not_fixed_ten(tmp_path,monkeypatch,material,expected):
    import scripts.leaper_design as L
    monkeypatch.setattr(L,'PAIRS',((1,2),(1,3)))
    d=tmp_path/'two_codes';L.prepare(d,material_ablation=material)
    assert L.load(d/'registration.json')['planned_games']==expected

def test_run_uses_frozen_input_count_not_process_default_pairs(tmp_path,monkeypatch):
    import scripts.leaper_design as L
    original=L.PAIRS
    monkeypatch.setattr(L,'PAIRS',((1,2),(1,3)))
    d=tmp_path/'two_codes';L.prepare(d)
    inp=L.load(d/'inputs.json')
    for w in inp['worlds']:w['status']='setup_failed'
    L.write_record(d/'inputs.json',inp)
    reg=L.load(d/'registration.json');reg['input_sha256']=L.sha(d/'inputs.json');L.write_record(d/'registration.json',reg)
    L.write_record(d/'preflight.json',{'status':'CLOSED','missing':[],'seconds':0,'rows':[{'seconds':.001}],'cost_gate_passed':True})
    monkeypatch.setattr(L,'PAIRS',original)
    L.run(d)
    result=L.load(d/'results.json')
    assert len(result['slots'])==12
    assert all(s['status']=='setup_failed' for s in result['slots'])
    assert result['queries']==0


def test_run_preserves_frozen_nonempty_opening_history(tmp_path,monkeypatch):
    import scripts.leaper_design as L
    monkeypatch.setattr(L,'PAIRS',((1,2),))
    d=tmp_path/'prefix';L.prepare(d)
    inp=L.load(d/'inputs.json');w=inp['worlds'][0]
    session=L.GameSession(L.compile_rule(L.ruleset_from_dict(w['rule'])))
    for _ in range(2):session.submit(session.legal_actions()[0])
    assert not session.state.terminal_status.is_terminal
    w['initial_record']=L.record_value(session.to_record());w['initial_state']=L.record_value(session.state)
    L.write_record(d/'inputs.json',inp)
    reg=L.load(d/'registration.json');reg.update(pairs={'RNG_RNG':['RNG','RNG']},planned_games=2,caller_plies=3,input_sha256=L.sha(d/'inputs.json'))
    L.write_record(d/'registration.json',reg)
    L.write_record(d/'preflight.json',{'status':'CLOSED','missing':[],'seconds':0,'rows':[{'seconds':.001}],'cost_gate_passed':True})
    L.run(d)
    for slot in L.load(d/'results.json')['slots']:
        row=L.load(d/slot['receipt'])
        assert row['initial_record']==w['initial_record'], 'caller discarded frozen prefix'
        assert row['queries'][0]['root_ply']==2
        assert row['final_record']['actions'][:2]==w['initial_record']['actions']
        assert len(row['queries'])==1
    L.qualify(d)
    assert L.load(d/'qualification.json')['history_plies']==2
    from scripts.leaper_portrait import analyze
    analyze(d)
    assert all(r['plies']==3 and r['queries']==1 for r in L.load(d/'portrait.json')['rows'])
