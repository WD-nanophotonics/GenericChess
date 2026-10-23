"""Regression controls for the scoped parity certificate; no game truth solver."""
import json
from dataclasses import replace
from scripts import leaper_design as L
from scripts.leaper_e0_panel import rule
from scripts.leaper_parity_scope import escapes,scope_rule,adjacent,xy
from generic_chess.core.pieces import Piece
from generic_chess.core.coordinates import Square
from generic_chess.core.position import GameState,HistoryRecord
from generic_chess.core.identity import repetition_identity_key
from generic_chess.core.semantic_executor import semantic_engine_for
from generic_chess.core.terminal import TerminalStatus

def test_scoped_geometry_preserves_capture_escape():
    # White A next to bare King is capturable. Its own before-capture attack
    # map must not be consulted after it leaves the board.
    e=escapes((1,2),(1,0),(0,0),set(L.offsets(1)))
    assert (1,0) in e and (0,1) not in e
    # The previous fixture K(2,1) actually PROTECTS A(1,0): distance1.
    # It guards capture but leaves the perpendicular escape, as the proof says.
    protected=escapes((2,1),(1,0),(0,0),set(L.offsets(1)))
    assert (1,0) not in protected and (0,1) in protected
    for king,expected in [((1,2),{(1,0)}),((2,1),{(0,1)})]:
        c=L.compile_rule(rule(1,0));b=[None]*16
        for sq,owner,t in [(king,0,'K'),((1,0),0,'A'),((0,0),1,'K')]:b[4*sq[1]+sq[0]]=Piece(owner,t,t)
        pos=replace(c.initial_position,board=tuple(b),side_to_move=1)
        from generic_chess.core.movegen import legal_actions_from_position
        assert {(a.to_square.file,a.to_square.rank) for a in legal_actions_from_position(pos,c)}==expected

def test_single_parity_scope_does_not_label_mixed_sets():
    for mask in (1,2,4,6,8,9,16):assert scope_rule(L.ruleset_to_dict(rule(mask,0),include_metadata=True),mask)[0]
    for mask in (3,5,10,12,31):assert scope_rule(L.ruleset_to_dict(rule(mask,0),include_metadata=True),mask)==(False,'mixed_parity')

def test_no_scope_transfer_across_scoring_and_history_rules():
    r=rule(1,0)
    variants=[replace(r,stalemate_result='loss'),replace(r,repetition_policy='continuous_check_loss'),replace(r,capture_disposition='capture_to_hand'),replace(r,max_ply=128),replace(r,pass_enabled=True)]
    for v in variants:assert scope_rule(L.ruleset_to_dict(v,include_metadata=True),1)==(False,'semantic_template_mismatch')

def test_mixed_geometry_has_literal_terminal_positive():
    r=rule(5,0);b=[None]*16
    for index,owner,t in ((6,0,'K'),(8,0,'A'),(0,1,'K')):b[index]=Piece(owner,t,t)
    r=replace(r,initial_position=tuple(tuple(b[4*i:4*i+4]) for i in range(4)))
    # Synthetic checked placement is not used as a valid initial session.
    # Compile a legal source, then replace only its Position with this control.
    c=L.compile_rule(rule(5,0));p=replace(c.initial_position,board=tuple(b),side_to_move=1)
    key=repetition_identity_key(p,c);engine=semantic_engine_for(c)
    result=engine.terminal_result(p,0,((key,1),),(HistoryRecord(key,-1,'',False),))
    assert result.status is TerminalStatus.CHECKMATE and result.winner==0
    # Even at repeat/clock, mate has priority. These counters are a local
    # terminal-priority probe, NOT an asserted reachable complete history.
    assert engine.terminal_result(p,64,((key,4),),(HistoryRecord(key,-1,'',False),)).status is TerminalStatus.CHECKMATE
