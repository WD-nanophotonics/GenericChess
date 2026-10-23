"""Adversarial theorem-scope and actual Core controls for the colour proof."""
from copy import deepcopy
from dataclasses import replace
from itertools import product
from pathlib import Path
import pytest

from generic_chess.core.pieces import Piece
from generic_chess.core.transition import legal_successors
from scripts.leaper_retrograde import fresh_state
from scripts.leaper_explorer_truth import load
from scripts.leaper_colour_certificate import admit,propose,verify,geometry_table,invariant,colour

FP='afa86fe58d3e842962208916173e6487fe21412ef347fbdc851b6f633590d039'


@pytest.fixture(scope='module')
def inputs():
    truth=load(Path('docs/research/data/leaper_explorer_truth_20261023/truth.json.gz'))
    return truth,propose(truth,FP)


def test_geometry_completeness_for_both_colours():
    assert len(geometry_table(4,0))==len(geometry_table(4,1))==78


def test_each_abstract_escape_is_actual_core_legal_even_with_dense_hostile_pieces(inputs):
    truth,_=inputs;_,c=admit(truth['rules'][FP]);template=c.initial_position
    # For every abstract anchor pair and both colours, exercise actual Core
    # legality under fully occupied coloured squares, once per ordinary type.
    # These are explicitly CONSTRUCTED proof controls, not reachable starts,
    # new play layouts, a PRIMARY screening campaign or training data.
    checked=0
    for shade,name in product((0,1),('A','B')):
        for king,enemy,target in geometry_table(4,shade):
            board=[Piece(1,name,name)if colour(i,4)==shade else None for i in range(16)]
            board[king]=Piece(0,'K','K');board[enemy]=Piece(1,'K','K')
            pos=replace(template,board=tuple(board),side_to_move=0)
            state=fresh_state(pos,c)
            assert state.terminal_status.winner is None
            assert any(ch.position.board[target]==Piece(0,'K','K')for _,ch in legal_successors(state,c))
            checked+=1
    assert checked==312


def test_same_rules_can_mate_when_ordinary_pieces_have_two_colours(inputs):
    truth,_=inputs;_,c=admit(truth['rules'][FP]);template=c.initial_position
    # CONSTRUCTED four-actor mate: K0a1, K1c2, A1b2, B1a4.
    # It is outside the original initial colour invariant and is NOT asserted
    # reachable. This prevents promoting a layout-bound proof to a rule-wide
    # statement over every possible placement.
    board=[None]*16
    for square,owner,name in ((0,0,'K'),(6,1,'K'),(5,1,'A'),(12,1,'B')):
        board[square]=Piece(owner,name,name)
    pos=replace(template,board=tuple(board),side_to_move=0)
    state=fresh_state(pos,c)
    assert state.terminal_status.winner==1
    assert state.terminal_status.status.value=='checkmate'
    with pytest.raises(ValueError,match='outside invariant'):invariant(pos,4,1)


def test_friendly_blocker_of_other_colour_can_also_enable_mate(inputs):
    truth,_=inputs;_,c=admit(truth['rules'][FP]);template=c.initial_position
    # K0a1,A0a2,K1c2,B1c1: the friendly A blocks the last safe escape.
    # Each seat individually has only one ordinary colour. The theorem must
    # require one GLOBAL colour across both seats, not a per-owner colour.
    board=[None]*16
    for square,owner,name in ((0,0,'K'),(4,0,'A'),(6,1,'K'),(2,1,'B')):
        board[square]=Piece(owner,name,name)
    pos=replace(template,board=tuple(board),side_to_move=0)
    state=fresh_state(pos,c)
    assert state.terminal_status.status.value=='checkmate'and state.terminal_status.winner==1
    from generic_chess.core.attacks import is_in_check
    assert not is_in_check(pos,1,c)


def test_two_colour_control_has_an_ongoing_one_ply_core_predecessor(inputs):
    truth,_=inputs;_,c=admit(truth['rules'][FP]);template=c.initial_position
    # Same original material roster, a CONSTRUCTED different arrangement.
    # It is deliberately not a GameSession record from the original opening.
    board=[None]*16
    for square,owner,name in ((0,0,'K'),(15,0,'A'),(11,0,'B'),(6,1,'K'),(10,1,'A'),(12,1,'B')):
        board[square]=Piece(owner,name,name)
    pos=replace(template,board=tuple(board),side_to_move=1)
    state=fresh_state(pos,c)
    assert not state.terminal_status.is_terminal
    from generic_chess.core.attacks import is_in_check
    assert not is_in_check(pos,0,c)and not is_in_check(pos,1,c)
    assert any(ch.terminal_status.winner==1 for _,ch in legal_successors(state,c))


@pytest.mark.parametrize('change',['missing','duplicate','unsafe','wrong_source','wrong_colour'])
def test_corrupted_certificates_reject(inputs,change):
    truth,base=inputs;cert=deepcopy(base)
    if change=='missing':cert['geometry'].pop()
    if change=='duplicate':cert['geometry'].append(cert['geometry'][0])
    if change=='unsafe':cert['geometry'][0][2]=cert['geometry'][0][0]
    if change=='wrong_source':cert['truth_digest']='0'*64
    if change=='wrong_colour':cert['ordinary_colour']=0
    with pytest.raises(ValueError):verify(truth,cert)


@pytest.mark.parametrize('change',['odd_leap','king_moves','stalemate_loss','extra_fields','drops'])
def test_unsupported_semantics_cannot_inherit_proof(inputs,change):
    truth,_=inputs;raw=deepcopy(truth['rules'][FP])
    if change=='odd_leap':raw['piece_types'][1]['movement_atoms'].append(dict(kind='leap',offset=[1,0]))
    if change=='king_moves':raw['piece_types'][0]['movement_atoms'].pop()
    if change=='stalemate_loss':raw['stalemate_result']='loss'
    if change=='extra_fields':raw['unknown_rule_loss']=True
    if change=='drops':raw['drop_allowed']['A'][0][0]=True
    with pytest.raises((ValueError,AssertionError)):admit(raw)
