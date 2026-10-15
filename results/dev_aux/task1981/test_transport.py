"""Strict transport guard regressions; no new reward games or Native calls."""
from pathlib import Path
from dataclasses import replace
import pytest
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.core.pieces import Piece
from generic_chess.session.session import GameSession
from scripts.generic_inventory_proof_filter import InventoryNoWinFilter
from scripts.generic_inventory_proof_transport import SetupTransportedNoWinFilter,execution_differences
CENSUS='results/dev_aux/task1895';COVERAGE='results/dev_aux/task1896/coverage.json'

def base():return deserialize_ruleset(Path('results/dev_aux/task1872/rules.json').read_text(encoding='utf-8'))
def small(extra=None):
 board=[None]*16;board[0]=Piece(0,'K','K');board[15]=Piece(1,'K','K')
 if extra:board[5]=Piece(0,extra,extra)
 return compile_ruleset_for_execution(replace(base(),initial_position=tuple(tuple(board[i:i+4]) for i in range(0,16,4)),initial_setup_options=()))

def test_new_target_setup_fields_only():
 old=compile_ruleset_for_execution(base())
 for p in ('results/dev_aux/task1967/rules.json','results/dev_aux/task1978/cohort0/rules.json','results/dev_aux/task1978/cohort1/rules.json'):
  c=compile_ruleset_for_execution(deserialize_ruleset(Path(p).read_text(encoding='utf-8')))
  assert old.ruleset_fingerprint!=c.ruleset_fingerprint and execution_differences(old,c)==()
  filt=SetupTransportedNoWinFilter(CENSUS,COVERAGE,c)
  assert filt.fingerprint==c.ruleset_fingerprint and filt.reference_fingerprint==old.ruleset_fingerprint

@pytest.mark.parametrize('extra',[None,'N'])
def test_hit_unknown_and_paid_current_record_replay(extra):
 c=small(extra);s=GameSession(c);f=SetupTransportedNoWinFilter(CENSUS,COVERAGE,c)
 assert f.eligible(s) and not InventoryNoWinFilter(CENSUS,COVERAGE).eligible(s)
 before=s.to_record();r=f(s,max_nodes=1024,seconds=.2,max_depth=64)
 assert r.status=='UNKNOWN' and r.reason=='certified_inventory_no_win' and r.nodes==0
 assert s.to_record()==before and r.certificate is None
 # A different compiled object reusing a qualified fingerprint is rejected.
 forged=GameSession(replace(c,max_ply=c.max_ply-1))
 assert not f.eligible(forged)

def test_rook_is_not_absence_inventory():
 c=small('R');assert not SetupTransportedNoWinFilter(CENSUS,COVERAGE,c).eligible(GameSession(c))

@pytest.mark.parametrize('field,value',[('max_ply',95),('repetition_limit',4),('repetition_policy','continuous_check_loss'),('stalemate_result','loss'),('pass_enabled',True),('capture_disposition','to_hand')])
def test_any_execution_change_rejected(field,value):
 c=small();changed=replace(c,**{field:value})
 assert field in execution_differences(c,changed)
 with pytest.raises(ValueError,match='execution fields differ'):SetupTransportedNoWinFilter(CENSUS,COVERAGE,changed)

def test_mutated_movement_mapping_rejected():
 c=small();changed=replace(c,leap_targets={})
 with pytest.raises(ValueError,match='execution fields differ'):SetupTransportedNoWinFilter(CENSUS,COVERAGE,changed)

@pytest.mark.parametrize('field,value',[('drop_allowed',{}),('promotion_allowed',{'R':()}),('automatic_adjudications',(object(),)),('declarations',(object(),))])
def test_win_creation_mechanisms_cannot_reuse_census(field,value):
 c=small();changed=replace(c,**{field:value})
 with pytest.raises(ValueError,match='execution fields differ'):SetupTransportedNoWinFilter(CENSUS,COVERAGE,changed)

@pytest.mark.parametrize('extra',[None,'N'])
def test_tampered_full_history_is_rejected_before_absence_hit(extra):
 c=small(extra);s=GameSession(c);f=SetupTransportedNoWinFilter(CENSUS,COVERAGE,c)
 s._state=replace(s.state,ply_count=1)  # Deliberately corrupt test fixture only.
 assert f.eligible(s)
 with pytest.raises(ValueError,match='session record does not bind'):f(s,max_nodes=1024,seconds=.2,max_depth=64)
