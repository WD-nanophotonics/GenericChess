"""Independent quiet-root conditions and first-divergence mechanism audit.
Consumes saved complete records; no new outcomes or price selection.
"""
from pathlib import Path
from collections import defaultdict,Counter
from copy import copy
import json,hashlib
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.session.result import SessionStatus
from scripts.generic_proof_rnb_bridge import actor_state,orbit
from scripts.generic_royal_actor import RoyalActor
OUT=Path('results/dev_aux/task2232')
def statekey(raw):return ''.join(raw[:-1])+str(raw[-1])
def run():
 new=json.loads(Path('results/dev_aux/task2228/inputs.json').read_text());old=json.loads(Path('results/dev_aux/task2220/inputs.json').read_text());oldgroups={r['group']for r in old['roots']};groups=set();actor=RoyalActor(4);checks=[]
 for r in new['roots']:
  c=compile_ruleset_for_execution(deserialize_ruleset(Path(r['rules']).read_text()));s=GameSession(c);raw=actor_state(s.state);g=min(statekey(x)for x in orbit(raw));assert g==r['group']and g not in oldgroups and g not in groups;groups.add(g);literal=dict(actor.moves(raw));assert len(literal)==len(s.legal_actions())
  assert not actor.attacked(raw,actor.king(raw,0),1)and not actor.attacked(raw,actor.king(raw,1),0)
  for name,ch in literal.items():assert sum(x!='.'for x in ch[:-1])==5
  for a in s.legal_actions():
   child=copy(s);child.submit(a);assert child.result.status is SessionStatus.ONGOING
  checks.append(dict(family=r['family'],legal_actions=len(literal),no_capture=True,no_oneply_terminal=True,disjoint_orbit=True))
 games=[json.loads(l)for l in Path('results/dev_aux/task2229/games.jsonl').read_text().splitlines()];inputs={r['family']:r for r in new['roots']};indexed={(g['family'],g['opponent_ratio'],g['candidate_color'],g['ratio']):g for g in games};rows=[]
 for key,g in indexed.items():
  if g['ratio']!=1.:continue
  h=indexed[key[:-1]+(2.,)];root=inputs[g['family']];c=compile_ruleset_for_execution(deserialize_ruleset(Path(root['rules']).read_text()));s=GameSession(c);aa=deserialize_game_record(json.dumps(g['record'])).actions;bb=deserialize_game_record(json.dumps(h['record'])).actions;prefix=0
  for a,b in zip(aa,bb):
   if a!=b:break
   s.submit(a);prefix+=1
  divergence=prefix<min(len(aa),len(bb));raw=actor_state(s.state);capture_options=[name for name,ch in actor.moves(raw)if sum(x!='.'for x in ch[:-1])<sum(x!='.'for x in raw[:-1])]
  guide=[]
  for game,actions in[(g,aa),(h,bb)]:
   ss=GameSession(c);first=None
   for i,a in enumerate(actions):
    if first is None and sum(pc is not None for pc in ss.state.position.board)<=4:first=i
    ss.submit(a)
   guide.append(dict(ratio=game['ratio'],first_guide_ply=first,final_status=ss.result.status.value,actual_reward=game['reward']))
  rows.append(dict(family=g['family'],opponent_ratio=g['opponent_ratio'],candidate_color=g['candidate_color'],same_complete_record=g['record']==h['record'],first_divergence_ply=prefix if divergence else None,common_prefix=prefix,side_at_divergence=s.state.position.side_to_move if divergence else None,is_candidate_divergence=(s.state.position.side_to_move==g['candidate_color'])if divergence else None,capture_options_at_divergence=capture_options if divergence else[],actors_at_divergence=sum(x!='.'for x in raw[:-1])if divergence else None,reward_gain=h['reward']-g['reward'],guide_entries=guide))
 result=dict(status='PASS_16QUIET_ROOTS_DISJOINT_PUBLIC_TERMINALS_AND64_PAIRED_PREFIXES',structural_checks=checks,pairs=len(rows),divergent_pairs=sum(not r['same_complete_record']for r in rows),reward_changing_pairs=sum(r['reward_gain']!=0 for r in rows),first_divergences_at_quiet=sum(r['first_divergence_ply']is not None and not r['capture_options_at_divergence']for r in rows),first_divergences_on_candidate=sum(r['is_candidate_divergence']is True for r in rows),rows=rows,scope='NEWroots beginwithoutcapture. Laterprice-sensitivechoices maystill be capture tactics. Firstdivergence/rewardassociation notcausalmediationproof orstrategicvalueidentification. Guideentryalone notWINcertificate. No additionalgames/labels/refit.')
 (OUT/'result.json').write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items()if k not in('rows','structural_checks')}))
if __name__=='__main__':run()
