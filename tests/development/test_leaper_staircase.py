"""Censoring and full-input controls for finite forward-axis comparisons."""
from pathlib import Path
from dataclasses import replace
import hashlib
import pytest
from scripts import leaper_design as L
from scripts.leaper_forecast import staircase_analysis
from generic_chess.core.pieces import Piece,PieceType
from generic_chess.core.movement import LeapAtom


def batch(root, kind, utilities):
    root.mkdir();worlds=[]
    for code,mask in enumerate((1,2)):
        rule=L.definition(mask,8);board=[list(v) for v in rule.initial_position]
        board[0][2]=Piece(0,'C','C');board[3][1]=Piece(1,'C','C')
        rule=replace(rule,initial_position=tuple(tuple(v) for v in board),
            piece_types=rule.piece_types+(PieceType('C','C',tuple(LeapAtom(v) for v in L.offsets(8))),),
            drop_allowed={**rule.drop_allowed,'C':((False,)*16,)*2})
        c=L.compile_rule(rule);record=L.record_value(L.GameSession(c).to_record())
        worlds.append({'world':code,'code_world':code,'layout_index':0,'masks':[mask,8],
            'C_mask':8,'roster':'ABC','rule':L.ruleset_to_dict(rule,include_metadata=True),
            'fingerprint':L.compute_fingerprint(rule),'initial_record':record})
    L.write_record(root/'inputs.json',{'worlds':worlds})
    policies={'cheap':['AB','FLOOR'],'resource':['N2048','N512'],'material':['STATIC_ADAPTER','M0']}[kind]
    reg={'roles':[0,1],'pairs':{'P':policies},'repetitions':1,'nodes':512,
        'planned_games':4,'input_sha256':L.sha(root/'inputs.json'),'q':0,'forced_check_depth':8,
        'rule_max_ply':128,'caller_plies':128,'repetition_limit':4,'disk_cache':False,'TT':'fresh/game','source_sha256':'same'}
    if kind=='resource':reg['search_variants']={'N2048':{'base':'AB','nodes':2048},'N512':{'base':'AB','nodes':512}}
    L.write_record(root/'registration.json',reg);slots=[]
    for ix,(code,role) in enumerate((c,a) for c in (0,1) for a in (0,1)):
        u=utilities[code];s={'slot':ix,'world':code,'pair':'P','role':role,'repeat':0,'utility':u,
            'status':'finished' if u[0]==u[1] else 'not_started'}
        if s['status']=='finished':
            s['receipt']=f'game-{ix:03d}.json'
            # Synthetic outcomes exercise aggregation only; no WDL/replay claim.
            L.write_record(root/s['receipt'],{**s,'queries':[],'final_record':worlds[code]['initial_record']})
        slots.append(s)
    L.write_record(root/'results.json',{'status':'CLOSED','slots':slots});return root


@pytest.fixture
def arms(tmp_path):
    return [batch(tmp_path/k,k,[[1,1],[0,0]]) for k in ('cheap','resource','material')]


def change(path, name, f):
    value=L.load(path/name);f(value);L.write_record(path/name,value)


def test_finite_positive_candidate_and_strict_dominance(arms):
    r=staircase_analysis(*arms)
    assert r['positive_lower_bound_all3_codes']==[0]
    assert r['robust_dominance']==[{'dominating_code':0,'dominated_code':1}]
    assert r['possibly_nondominated_codes']==[0]
    assert r['per_code'][0]['axes']['cheap']['planned']==2


def test_unknown_cannot_be_an_optimistic_winner_or_midpoint_dominated(arms):
    change(arms[1],'results.json',lambda r:[s.update(status='not_started',utility=[-1,1]) for s in r['slots'] if s['world']==1])
    r=staircase_analysis(*arms)
    assert r['per_code'][1]['axes']['resource']['bounds']==['-1','1']
    # Code0 ties unknown's upper bound on resource, so still robustly dominates.
    assert r['possibly_nondominated_codes']==[0]
    change(arms[0],'results.json',lambda r:[s.update(utility=[0,0]) for s in r['slots'] if s['world']==0])
    for ix in (0,1):change(arms[0],f'game-{ix:03d}.json',lambda g:g.update(utility=[0,0]))
    change(arms[1],'results.json',lambda r:[s.update(utility=[0,0]) for s in r['slots'] if s['world']==0])
    for ix in (0,1):change(arms[1],f'game-{ix:03d}.json',lambda g:g.update(utility=[0,0]))
    r=staircase_analysis(*arms)
    assert r['possibly_nondominated_codes']==[0,1]
    assert r['positive_lower_bound_all3_codes']==[]


def test_unattempted_draw_imputation_is_refused(arms):
    change(arms[1],'results.json',lambda r:r['slots'][0].update(status='not_started',utility=[0,0]))
    with pytest.raises(ValueError,match='imputed'):staircase_analysis(*arms)


def test_duplicate_planned_cell_refused(arms):
    change(arms[0],'results.json',lambda r:r['slots'].__setitem__(1,dict(r['slots'][0])))
    with pytest.raises(ValueError,match='census'):staircase_analysis(*arms)


def test_changed_initial_history_refused_even_with_fresh_file_hash(arms):
    change(arms[2],'inputs.json',lambda r:r['worlds'][0]['initial_record'].update(initial_setup_key='changed'))
    change(arms[2],'registration.json',lambda r:r.update(input_sha256=L.sha(arms[2]/'inputs.json')))
    with pytest.raises(ValueError,match='initial histories'):staircase_analysis(*arms)


def test_changed_q_contract_is_not_called_a_budget_axis(arms):
    change(arms[1],'registration.json',lambda r:r.update(q=1))
    with pytest.raises(ValueError,match='controls differ'):staircase_analysis(*arms)


def test_changed_input_file_hash_refused(arms):
    with (arms[0]/'inputs.json').open('ab') as f:f.write(b' ')
    with pytest.raises(ValueError,match='hash mismatch'):staircase_analysis(*arms)


def test_incomplete_running_axis_refused(arms):
    change(arms[2],'results.json',lambda r:r.update(status='RUNNING'))
    with pytest.raises(ValueError,match='closed'):staircase_analysis(*arms)


def test_same_code_label_cannot_merge_different_movement_rules(arms):
    for d in arms:
        def disguise(v):
            v['worlds'][1].update(code_world=0,layout_index=1,masks=[1,8])
        change(d,'inputs.json',disguise)
        change(d,'registration.json',lambda r:r.update(input_sha256=L.sha(d/'inputs.json')))
    with pytest.raises(ValueError,match='code layouts'):staircase_analysis(*arms)
