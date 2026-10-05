import hashlib,json
from pathlib import Path
from dataclasses import replace
from fractions import Fraction as F
import pytest
from scripts.shogi_static_inventory import StaticInventory,SCALE
from scripts.shogi_shared_hand_inventory import SharedHandInventory
from scripts.material_leaf_choice import inventory_features
from scripts.research_state_replay import read_game_state
from scripts.audit_shogi_promotion_use import selections
ROOT=Path(__file__).resolve().parents[1];DATA=ROOT/'docs/research/data'

def test_shared_vector_and_actual_base_hand_sign():
    weights={'P':F(7711,SCALE),'TP':F(30057,SCALE),'R':F(96770,SCALE)}
    for bad in ({'P':-1,'R':0},{'P':0,'R':SCALE+1},{'TP':0,'R':0},{'P':True,'R':0}):
        with pytest.raises(ValueError):SharedHandInventory(weights,bad)
    tree=json.loads((DATA/'shogi_promotion_use_20261005.json').read_text())
    branch=tree['branches']['legacy_029:g21:a7-a8=TP']
    state=read_game_state(next(iter(branch['leaves'].values()))['state'])
    a=StaticInventory(weights);b=SharedHandInventory(weights)
    assert a.evaluate(state)-b.evaluate(state)==SCALE
    flipped=replace(state,position=replace(state.position,side_to_move=1))
    assert a.evaluate(flipped)-b.evaluate(flipped)==-SCALE

def test_full_box_certificate_and_one_new_point_accounting():
    r=json.loads((DATA/'shogi_shared_hand_search_20261006.json').read_text())
    tree=json.loads((DATA/'shogi_promotion_use_20261005.json').read_text())
    features={key:{reply:inventory_features(read_game_state(leaf['state']).position,{'K'}) for reply,leaf in branch['leaves'].items()} for key,branch in tree['branches'].items()}
    row=r['searches'][0];certificate=selections(features,{t:F(w,SCALE) for t,w in row['integer_weights'].items()})
    assert json.loads(json.dumps(certificate,default=str))==r['shared_hand_box_certificate']
    assert certificate['margins']['legacy_029:g21:a7-a8']==(F(11173,50000),)*2
    assert r['complete'] and len(r['searches'])==1 and row['score']==30057
    assert row['ties']==certificate['tie_set'] and row['selected'] in row['ties']
    assert r['runtime_pushes']==r['runtime_pops']==49 and r['paired_pushes']==98
    assert r['conservative_enumeration_charge']==1707 and r['cumulative_seconds']<15
    assert row['statistics']['qnodes']==0 and row['reason']=='completed_depth'
    assert r['public_transitions']==r['source_queries']==0
    for path,pin in r['source_sha256'].items():assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==pin
