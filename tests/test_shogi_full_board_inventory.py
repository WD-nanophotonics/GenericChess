"""Conserved full-stock admission and refusal of an unselected hand law."""
import json
from dataclasses import replace
from pathlib import Path
import pytest
from generic_chess.core.position import Hands
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from scripts.research_state_replay import read_game_state
from scripts.shogi_full_board_inventory import FullBoardInventory
from scripts.resource_mode_context import resource_ledger

@pytest.fixture(scope='module')
def control():
    raw=json.loads((Path(__file__).resolve().parents[1]/'docs/research/data/shogi_full_board_search_20261006.json').read_text())
    c=compile_ruleset_for_execution(build_standard_shogi_ruleset())
    from fractions import Fraction
    return c,read_game_state(raw['root']),{k:Fraction(v) for k,v in raw['weights'].items()},raw

def test_complete_initial_search_is_balanced_and_restored(control):
    c,state,weights,raw=control
    assert raw['complete'] and raw['source_hashes_unchanged'] and raw['root_unchanged']
    assert raw['runtime_pushes']==raw['runtime_pops']==30
    assert raw['reason']=='completed_depth' and raw['statistics']['completed_depth']==1
    assert raw['statistics']['qnodes']==0 and set(raw['evaluations'])=={0}
    assert FullBoardInventory(c,weights).evaluate(state)==0
    assert FullBoardInventory(c,weights).evaluate(replace(state,position=replace(state.position,side_to_move=1)))==0

def test_conserved_capture_custody_cannot_smuggle_a_hand_price(control):
    c,state,weights,_=control
    board=list(state.position.board)
    index=next(i for i,p in enumerate(board) if p and p.owner==1 and p.base_type_id=='P')
    board[index]=None
    p=replace(state.position,board=tuple(board),hands=(Hands((('P',1),)),Hands.empty()))
    # Custody changes preserve the global stock; failure is specifically the
    # missing hand-value contract, not an inventory mismatch.
    resource_ledger(c,p,'shogi')
    with pytest.raises(ValueError,match='held-price'):
        FullBoardInventory(c,weights).evaluate(replace(state,position=p))

def test_missing_stock_and_forged_promotion_are_rejected(control):
    c,state,weights,_=control;e=FullBoardInventory(c,weights)
    board=list(state.position.board)
    index=next(i for i,p in enumerate(board) if p and p.base_type_id=='P')
    pawn=board[index];board[index]=None
    with pytest.raises(ValueError,match='inventory changed'):
        e.evaluate(replace(state,position=replace(state.position,board=tuple(board))))
    board[index]=replace(pawn,current_type_id='TR',promoted=True)
    with pytest.raises(ValueError,match='allowed base origin'):
        e.evaluate(replace(state,position=replace(state.position,board=tuple(board))))
