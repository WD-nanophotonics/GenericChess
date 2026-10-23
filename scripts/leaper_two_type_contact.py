"""Prospective contact mu: direct A/B capture alternatives, no oracle filtering."""
from pathlib import Path
from dataclasses import replace
import json
from scripts import leaper_design as L
from scripts.leaper_two_type_forward import profiles,RATIOS
from generic_chess.rules.schema import RuleInitialSetupOption
from tools.local_agent.common import write_json

def prepare(source,target):
 assert not target.exists();old=L.load(source);r=L.ruleset_from_dict(old['rule']);boards=[]
 for b0 in (15,16,21,10):
  cells=[None]*25
  for ix,owner,tid in ((20,0,'K'),(12,0,'A'),(b0,0,'B'),(24,1,'K'),(6,1,'A'),(8,1,'B')):cells[ix]=L.Piece(owner,tid,tid)
  boards.append(tuple(tuple(cells[y*5:y*5+5])for y in range(5)))
 rule=replace(r,initial_position=boards[0],initial_setup_options=tuple(RuleInitialSetupOption('contact'+str(i),b)for i,b in enumerate(boards[1:],1)));c=L.compile_rule(rule);roots=[]
 for i in range(4):
  s=L.GameSession(c,None if i==0 else 'contact'+str(i));assert not s.state.terminal_status.is_terminal
  roots.append(dict(index=i,record=L.record_value(s.to_record()),state=L.record_value(s.state),state_sha256=L.state_sha(s.state),legal_count=len(s.legal_actions())))
  assert L.GameSession.replay(c,s.to_record()).state==s.state
 out=dict(old,question='Do prospective direct A/B capture choices make relative material prices affect actual full-game behavior, unlike the closed quiet-home mu?',rule=L.ruleset_to_dict(rule),fingerprint=L.compute_fingerprint(rule),roots=roots,profiles={k:profiles(c,b)[1:]for k,b in RATIOS.items()},mu='Four explicit contact layouts, K0=20/A0=12/K1=24/A1=6/B1=8, ownB15/16/21/10; uniform finite weights. Constructed by geometric capture relation, never by WDL labels or selected terminal outcomes.',scope='Same King8/Ferz/Wazir/remove/H64/repeat4 movement and terminal semantics; only fresh setup law changes and fullRuleSet identity follows. Both sides have A/B. Relative leaf prices and fixed unit ordering remain as registered. Not blind/representative natural starts or a learning admission gate.')
 write_json(target,out);return out
if __name__=='__main__':
 prepare(Path('.local_agent/ab-two-type-inputs-frozen.json'),Path('.local_agent/ab-contact-inputs.json'))
