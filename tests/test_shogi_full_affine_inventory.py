from frozen_research_sources import source_digest
"""Full custody, shared uncertainty and actual frozen complete root coverage."""
import hashlib,json
from dataclasses import replace
from fractions import Fraction as F
from pathlib import Path
import pytest
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from scripts.shogi_full_affine_inventory import FullAffineInventory,robust_dominators,BASES,BOX
from scripts.shared_min_envelope_certificate import affine_box_min
from scripts.research_state_replay import read_game_state
ROOT=Path(__file__).resolve().parents[1]

@pytest.fixture(scope='module')
def control():
    raw=json.loads((ROOT/'docs/research/data/shogi_full_capture_affine_20261006.json').read_text())
    old=json.loads((ROOT/'docs/research/data/shogi_full_board_search_20261006.json').read_text())
    compiled=compile_ruleset_for_execution(build_standard_shogi_ruleset())
    return raw,old,compiled,FullAffineInventory(compiled,{t:F(v) for t,v in old['weights'].items()})

def static_view(record):
    # Inventory checks consume positions, not a fabricated historical proof.
    return read_game_state(dict(**record,repetition_counts=[],history=[]))

def test_complete_legal_capture_reference_and_cumulative_budget(control):
    raw,old,_,e=control
    assert raw['complete'] and raw['source_hashes_unchanged'] and raw['initial_restored']
    assert len(raw['prefix'])==4 and len(raw['rows'])==len(raw['root_actions'])==32
    assert raw['runtime_pushes']==raw['runtime_pops']==36 and raw['cumulative_pushes']==66<=128
    assert raw['conservative_enumeration_charge']==3985<=5000 and raw['cumulative_seconds']<15
    assert raw['root_row']==[-7711,-1,0,0,0,0,0,0]
    assert e.row(static_view(raw['root']))==tuple(raw['root_row'])
    for key,leaf in raw['leaves'].items():assert e.row(static_view(leaf))==tuple(raw['rows'][key])
    winner='legacy_031:g22:b2-b5'
    assert raw['certificate']['strict_dominators']==[winner]
    assert raw['rows'][winner]==[0]*8
    assert set(raw['certificate']['margins'][winner].values())=={'7711'}
    assert robust_dominators(raw['rows'],owner=0)['strict_dominators']==[winner]
    assert not robust_dominators(raw['rows'],owner=1)['strict_dominators']
    for path,pin in raw['source_sha256'].items():assert source_digest(ROOT, path, pin) == pin

def test_owner_zero_rows_keep_shared_custody_and_current_base_separate(control):
    raw,_,_,e=control;state=static_view(raw['root'])
    row=e.row(state)
    assert e.row(replace(state,position=replace(state.position,side_to_move=1)))==row
    board=list(state.position.board);index=next(i for i,p in enumerate(board) if p and p.owner==0 and p.base_type_id=='P')
    pawn=board[index];board[index]=replace(pawn,current_type_id='TP',promoted=True)
    promoted=e.row(replace(state,position=replace(state.position,board=tuple(board))))
    assert promoted[0]-row[0]==e.weights['TP']-e.weights['P'] and promoted[1:]==row[1:]
    board[index]=replace(pawn,current_type_id='TR',promoted=True)
    with pytest.raises(ValueError,match='allowed base origin'):
        e.row(replace(state,position=replace(state.position,board=tuple(board))))
    board[index]=None
    with pytest.raises(ValueError,match='inventory changed'):
        e.row(replace(state,position=replace(state.position,board=tuple(board))))

def test_shared_feature_cancellation_and_crossing_do_not_choose_a_hand_law():
    first=(3,100,0,0,0,0,0,0);second=(1,100,0,0,0,0,0,0)
    assert affine_box_min(first,BOX)+affine_box_min(tuple(-v for v in second),BOX)<0
    result=robust_dominators({'a':first,'b':second},owner=0)
    assert result['strict_dominators']==['a'] and result['margins']['a']['b']==2
    switching={'a':(0,1,0,0,0,0,0,0),'b':(50000,0,0,0,0,0,0,0)}
    assert robust_dominators(switching,owner=0)['strict_dominators']==[]
    assert BASES==('P','L','N','S','G','B','R')

@pytest.mark.parametrize('owner',[True,-1,2])
def test_invalid_owner_fails_closed(owner):
    with pytest.raises(ValueError):robust_dominators({'a':(0,)*8},owner=owner)

def test_nonexact_or_incomplete_rows_rejected(control):
    _,old,c,_=control;weights={t:F(v) for t,v in old['weights'].items()}
    weights['P']=0.5
    with pytest.raises(ValueError):FullAffineInventory(c,weights)
    for row in ((0,)*7,(True,)+(0,)*7,(0.5,)+(0,)*7):
        with pytest.raises(ValueError):robust_dominators({'a':row},owner=0)
