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
