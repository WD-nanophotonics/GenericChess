"""Relative price controls vary leaf material only, retaining common ordering."""
from dataclasses import fields,replace
import pytest
from scripts import leaper_design as L
from scripts.leaper_prices import relative_profiles


def setup():
    rule=L.definition(1,8);c=L.compile_rule(rule);base,zero=L.material_profiles(c)
    profiles,rates=relative_profiles(rule,base)
    world={'rule':L.ruleset_to_dict(rule),'material_profiles':{'Static':L.record_value(base),'M0':L.record_value(zero)},'price_profiles':{k:L.record_value(v) for k,v in profiles.items()}}
    return rule,c,base,profiles,rates,world


def test_prices_retain_all_nonmaterial_fields_and_anchor_zero():
    rule,c,base,profiles,rates,world=setup()
    assert profiles['UNIT'].board_value_by_type=={'K':0,'A':1000,'B':1000}
    assert profiles['UNIT'].hand_value_by_base_type=={'K':0,'A':900,'B':900}
    for profile in profiles.values():
        for field in fields(base):
            if field.name not in ('board_value_by_type','hand_value_by_base_type','piece_profiles'):
                assert getattr(profile,field.name)==getattr(base,field.name)
        for t,old in base.piece_profiles.items():
            for field in fields(old):
                if field.name not in ('normalized_board_value','normalized_hand_value'):
                    assert getattr(profile.piece_profiles[t],field.name)==getattr(old,field.name)
    assert rates['A']==L.graph(1)['mean_empty_board_degree']
    assert rates['B']==L.graph(8)['mean_empty_board_degree']


def test_equal_movement_has_equal_price_and_offboard_offsets_add_zero():
    rule=L.definition(1,1);base,_=L.material_profiles(L.compile_rule(rule))
    profiles,rates=relative_profiles(rule,base)
    assert rates['A']==rates['B'] and profiles['MOBILITY'].board_value_by_type['A']==1000
    from generic_chess.core.movement import LeapAtom
    types=tuple(replace(t,movement_atoms=t.movement_atoms+(LeapAtom((99,99)),)) if t.type_id=='A' else t for t in rule.piece_types)
    _,other=relative_profiles(replace(rule,piece_types=types),base)
    assert other==rates


def test_actual_leaf_difference_is_exact_material_component_with_static_ordering():
    rule,c,base,profiles,rates,world=setup();s=L.GameSession(c);ordering=L.Evaluator(c,base,L.EvaluationConfig())
    static=L.make_player(c,'STATIC_ADAPTER',world)
    for name,profile in profiles.items():
        player=L.make_player(c,name,world)
        for t in base.board_value_by_type:assert player._evaluator.type_value(t)==ordering.type_value(t)
        for st in [s.state]+[ch for _,ch in L.legal_successors(s.state,c)]:
            diff=sum((1 if p.owner==0 else -1)*(base.board_value_by_type[p.current_type_id]-profile.board_value_by_type[p.current_type_id]) for p in st.position.board if p)
            if st.position.side_to_move:diff=-diff
            assert static._evaluator.evaluate(st)-player._evaluator.evaluate(st)==diff
    with pytest.raises(ValueError):relative_profiles(replace(rule,capture_disposition='capture_to_hand'),base)
    world['price_profiles']['UNIT']['board_value_by_type']['A']=3
    with pytest.raises(AssertionError):L.make_player(c,'UNIT',world)



def price_run(tmp_path,unknown=False,diverge=False):
    import copy
    rule,c,base,profiles,rates,world=setup()
    # A no-op board-price fixture exposes incorrect path equivalence handling.
    world=copy.deepcopy(world);world['world']=0;world['code_world']=0;world['layout_index']=0
    world['price_profiles']['UNIT']['board_value_by_type']=dict(base.board_value_by_type)
    L.write_record(tmp_path/'inputs.json',{'worlds':[world]})
    L.write_record(tmp_path/'registration.json',{'pairs':{'STATIC_UNIT':['STATIC_ADAPTER','UNIT']},'roles':[0,1],'repetitions':1,'planned_games':2,'input_sha256':L.sha(tmp_path/'inputs.json')})
    slots=[]
    for role in (0,1):
        slot={'slot':role,'world':0,'pair':'STATIC_UNIT','role':role,'repeat':0,'status':'not_started' if unknown and role==1 else 'finished','utility':[-1,1] if unknown and role==1 else [1 if role==0 else -1]*2}
        if slot['status']=='finished':
            slot['receipt']=f'game-{role}.json'
            L.write_record(tmp_path/slot['receipt'],{**slot,'queries':[],'final_record':{'actions':['different' if diverge and role else 'same']},'terminal':{'winner':0}})
        slots.append(slot)
    L.write_record(tmp_path/'results.json',{'status':'CLOSED','slots':slots,'seconds':0})


def test_price_analysis_keeps_unattempted_as_unknown_and_rejects_duplicate_census(tmp_path):
    from scripts.leaper_price_analysis import analyze
    price_run(tmp_path,unknown=True);a=analyze(tmp_path)
    assert a['summary'][0]['bounds']==['0','1'] and a['UNKNOWN']==1
    result=L.load(tmp_path/'results.json');result['slots'].append(result['slots'][0]);L.write_record(tmp_path/'results.json',result)
    with pytest.raises(AssertionError,match='census'):analyze(tmp_path)


def test_noop_path_failure_preserves_measured_assessment_before_rejecting(tmp_path):
    from scripts.leaper_price_analysis import analyze
    price_run(tmp_path,diverge=True)
    with pytest.raises(AssertionError,match='no-op'):analyze(tmp_path)
    a=L.load(tmp_path/'price-assessment.json')
    assert a['role_swap_paths'][0]['same_board_prices']
    assert not a['role_swap_paths'][0]['same_full_action_history']
    assert not (tmp_path/'price-assessment-qualification.json').exists()
