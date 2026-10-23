"""Contract controls for the rule-coordinate research caller."""
from dataclasses import replace
import pytest
from scripts import leaper_design as L
from scripts.leaper_rule_coordinates import template,physical_action,integer_actions,orthogonally_independent
from generic_chess.session.session import SessionFinishedError


def choose(session,physical):
    return next(a for a in session.legal_actions() if physical_action(L.record_value(a),4)==physical)


def test_onebit_mutation_can_turn_a_forced_winning_action_into_stalemate():
    old=L.GameSession(L.compile_rule(template(3,4,(0,5,3))))
    new=L.GameSession(L.compile_rule(template(7,4,(0,5,3))))
    for s in (old,new):s.submit(choose(s,('K',0,1,None)))
    assert old.state.position.board==new.state.position.board
    assert old.result.status.value=='ongoing'
    assert new.result.status.value=='stalemate' and new.result.winner is None
    assert len(old.legal_actions())==1
    old.submit(old.legal_actions()[0]);old.submit(choose(old,('A',5,6,None)))
    assert old.result.status.value=='checkmate' and old.result.winner==0
    with pytest.raises(SessionFinishedError):new.submit(old.to_record().actions[1])


def test_rule_blind_alias_is_between_two_ongoing_inputs():
    low=L.GameSession(L.compile_rule(template(1,4,(1,9,3))))
    high=L.GameSession(L.compile_rule(template(5,4,(1,9,3))))
    assert low.state.position.board==high.state.position.board
    assert low.result.status.value==high.result.status.value=='ongoing'
    assert low.state.position.ruleset_fingerprint!=high.state.position.ruleset_fingerprint
    assert orthogonally_independent(L.offsets(1))
    high.submit(choose(high,('A',9,11,None)))
    assert high.result.status.value=='checkmate' and high.result.winner==0


def test_more_root_moves_can_have_fewer_two_ply_histories():
    widths=[];branches=[]
    for mask in (1,5):
        compiled=L.compile_rule(template(mask,4,(0,2,13)));ss=L.GameSession(compiled)
        children=L.legal_successors(ss.state,compiled)
        assert all(not child.terminal_status.is_terminal for _,child in children)
        branches.append(len(children));widths.append(sum(len(L.legal_successors(child,compiled)) for _,child in children))
    assert branches[1]>branches[0] and widths[1]<widths[0]


def test_saturated_initial_admission_is_not_static_mate_capacity():
    with pytest.raises(ValueError,match='INITIAL_ANCHOR_ATTACKED'):
        L.compile_rule(template(31,3,(2,1,0)))


def test_integer_control_removes_captured_ordinary_entity():
    choices=dict(integer_actions((9,1,0),1,1,4))
    assert choices[('K',0,1,None)]==(9,None,1)


def test_onebit_input_guard_does_not_hide_changed_royal_or_piece_metadata():
    from scripts.leaper_rule_coordinates import normalize_only_A_moves
    low=template(4,4,(0,1,15));high=template(6,4,(0,1,15))
    assert L.ruleset_to_dict(normalize_only_A_moves(low,high))==L.ruleset_to_dict(low)
    changed_king=replace(high,piece_types=(replace(high.piece_types[0],movement_atoms=high.piece_types[1].movement_atoms),high.piece_types[1]))
    assert L.ruleset_to_dict(normalize_only_A_moves(low,changed_king))!=L.ruleset_to_dict(low)
    changed_A=replace(high,piece_types=(high.piece_types[0],replace(high.piece_types[1],name='different-metadata')))
    assert L.ruleset_to_dict(normalize_only_A_moves(low,changed_A))!=L.ruleset_to_dict(low)


def test_general_directional_attack_criterion_uses_active_nonzero_offsets():
    from scripts.leaper_rule_coordinates import constructive_corner,active_attack_offsets
    assert constructive_corner({(2,0),(3,0)},3) is None
    assert constructive_corner({(2,0),(3,0)},4) is not None
    with pytest.raises(ValueError):active_attack_offsets({(0,0)},4)
    with pytest.raises(ValueError):active_attack_offsets({(1,0)},2)
    witness=constructive_corner({(-1,-3),(0,-3)},4)
    assert witness is not None
    from generic_chess.core.movement import LeapAtom
    from generic_chess.core.identity import repetition_identity_key
    from generic_chess.core.position import HistoryRecord
    from generic_chess.core.semantic_executor import semantic_engine_for
    r=template(1,4,(0,1,15));board=[list(row) for row in r.initial_position];board[0][1]=None
    r=replace(r,initial_position=tuple(map(tuple,board)),piece_types=(r.piece_types[0],replace(r.piece_types[1],movement_atoms=(LeapAtom((-1,-3)),LeapAtom((0,-3))))))
    c=L.compile_rule(r);cells=[None]*16
    for p,owner,tid in ((witness['king0'],0,'K'),(witness['ordinary0'],0,'A'),(witness['king1'],1,'K')):cells[4*p[1]+p[0]]=L.Piece(owner,tid,tid)
    pos=replace(c.initial_position,board=tuple(cells),side_to_move=1);key=repetition_identity_key(pos,c)
    terminal=semantic_engine_for(c).terminal_result(pos,0,((key,1),),(HistoryRecord(key,-1,'',False),))
    assert terminal.status.value=='checkmate' and terminal.winner==0


def test_constructed_attack_pair_keeps_both_distinct_offsets():
    from scripts.leaper_rule_coordinates import constructive_corner
    witness=constructive_corner({(2,0),(3,0)},4)
    p,q=witness['active_attack_pair']
    assert p!=q and abs(p[0]-q[0])+abs(p[1]-q[1])==1


def test_forward2_polynomial_matches_complete_core_tree_and_negative_interactions():
    from scripts.leaper_rule_coordinates import forward2_orbit_polynomial,evaluate_orbit_polynomial
    spec=(0,2,13);coeff=forward2_orbit_polynomial(spec,4)
    assert all(v<=0 for term,v in coeff.items() if ',' in term)
    for mask in (1,3,5,7,17,31):
        c=L.compile_rule(template(mask,4,spec));ss=L.GameSession(c)
        width=sum(len(L.legal_successors(ch,c)) for a,ch in L.legal_successors(ss.state,c))
        assert evaluate_orbit_polynomial(coeff,mask)==width
    assert evaluate_orbit_polynomial(coeff,5)<evaluate_orbit_polynomial(coeff,1)


def test_winning_action_set_and_uniform_action_probability_are_different():
    from fractions import Fraction
    wins=[];rates=[]
    for mask in (5,7):
        c=L.compile_rule(template(mask,4,(1,15,3)));ss=L.GameSession(c);children=L.legal_successors(ss.state,c)
        actions={physical_action(L.record_value(a),4) for a,ch in children if ch.terminal_status.winner==0}
        wins.append(actions);rates.append(Fraction(len(actions),len(children)))
    assert wins[0]==wins[1]=={('A',15,11,None)}
    assert rates==[Fraction(1,7),Fraction(1,8)]
