from pathlib import Path
import json
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from scripts.generic_session_cached_phase_player import SessionCachedPhasePlayer
from scripts.generic_session_phase_player import PhaseLimits
from results.dev_aux.task2100.campaign import evaluate
from results.dev_aux.task2136.legal_fallback import LegalFallbackPhasePlayer

def observed():
 root=Path('results/dev_aux/task2134');g=json.loads((root/'games.jsonl').read_text().splitlines()[-1]);r=json.loads((root/'inputs.json').read_text())['roots'][g['family']];c=compile_ruleset_for_execution(deserialize_ruleset(Path(r['rules']).read_text(encoding='utf-8')));return c,GameSession.replay(c,deserialize_game_record(json.dumps(g['record'])))

def player(cls,c):return cls(c,evaluate(1.),proof_enabled=False,max_depth=2,limits=PhaseLimits(normal_seconds=0.))

def test_observed_ongoing_prefix_gets_actual_legal_fallback_when_normal_has_no_time():
 c,s=observed();before=s.to_record();old=player(SessionCachedPhasePlayer,c).choose(s,max_nodes=64,seconds=.75);new=player(LegalFallbackPhasePlayer,c).choose(s,max_nodes=64,seconds=.75)
 assert old.choice is None and new.choice is not None and new.source=='PRECOMPUTED_LEGAL_FALLBACK';assert new.choice.action in s.legal_actions();assert s.to_record()==before;assert dict(new.phase_limits)['normal_seconds']==0. and dict(new.phase_limits)['total_seconds']==.75

def test_explicit_cancel_cannot_emit_fallback():
 c,s=observed();r=player(LegalFallbackPhasePlayer,c).choose(s,max_nodes=64,seconds=.75,cancel=lambda:True);assert r.choice is None and r.exit_cause=='cancelled'

def test_no_total_budget_cannot_invent_unvalidated_fallback():
 c,s=observed();r=player(LegalFallbackPhasePlayer,c).choose(s,max_nodes=64,seconds=0.);assert r.choice is None

def test_foreign_rules_no_fallback_even_when_parent_exits_for_zero_normal_time():
 c,s=observed();other=compile_ruleset_for_execution(deserialize_ruleset(Path('results/dev_aux/task2134/rules-0.json').read_text(encoding='utf-8')));assert c.ruleset_fingerprint!=other.ruleset_fingerprint;r=player(LegalFallbackPhasePlayer,other).choose(s,max_nodes=64,seconds=.75);assert r.choice is None


def test_admission_cancel_pulse_is_latched_before_parent_or_fallback():
 c,s=observed();calls=0
 def pulse():
  nonlocal calls
  calls+=1
  return calls==3
 r=player(LegalFallbackPhasePlayer,c).choose(s,max_nodes=64,seconds=.75,cancel=pulse);assert r.choice is None and r.exit_cause=='cancelled'
