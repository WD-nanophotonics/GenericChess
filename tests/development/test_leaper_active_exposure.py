import copy
from scripts.leaper_active_exposure import active_projection,any_truth
from scripts.leaper_endpoint_prepare import families
from scripts.leaper_structural_layout import layout

def minimal():
    return {'piece_types':[{'type_id':'K','is_anchor':True,'movement_atoms':[{'kind':'leap','offset':[1,0]}]},{'type_id':'Z','is_anchor':False,'movement_atoms':[{'kind':'leap','offset':[97,99]}]}],'initial_position':[[{'current_type_id':'K'}]],'capture_disposition':'remove_from_game','drop_allowed':{'Z':[[False]]}}

def test_remove_only_projection_excludes_never_created_type_but_not_actual_type():
    r=minimal();p,why=active_projection(r);assert [x['type_id'] for x in p['piece_types']]==['K'];assert len(r['piece_types'])==2
    r['initial_position'][0].append({'current_type_id':'Z'});assert len(active_projection(r)[0]['piece_types'])==2

def test_possible_creation_and_unknown_semantics_keep_all_declared_types():
    for patch in [{'drop_allowed':{'Z':[[True]]}},{'capture_disposition':'return_to_hand'},{'promotion_allowed':{'K':[[True]]}},{'initial_setup_options':[{}]},{'effects':[] }]:
        r=minimal();r.update(patch);p,why=active_projection(r);assert len(p['piece_types'])==2 and why.startswith('all-declared')
    r=minimal();r['piece_types'][0]['transform']='Z';assert active_projection(r)[1].startswith('all-declared')

def test_missing_complete_initialization_remains_unknown():
    r=minimal();r.pop('initial_position');assert active_projection(r)[0] is None
    r=minimal();r['initial_position']=[[{'current_type_id':'missing'}]];assert active_projection(r)[0] is None

def test_predeclared_family_formula_and_layouts_are_deterministic_and_use_all_types():
    fs=list(families());assert [b for b,_ in fs]==list(range(8))
    for _,types in fs:
        row=layout(types);col=layout(types,scan='column');assert row==layout(types) and row['placements']!=col['placements']
        assert {p['type'] for p in row['placements']}=={'K','A','B','C'};assert len(row['placements'])==14
        assert all(len({tuple(a['offset']) for a in p['movement_atoms']})==len(p['movement_atoms']) for p in types)
