"""Actual finite-rule W-L prices with fixed, explicitly scoped endgame guidance.

The low-inventory guide is a precomputed RULE policy, not a graph WIN receipt.
It never supplies reward. Every outcome comes from actual public GameSession.
No generic/default adoption or human-price fit; table prepayment is retained.
"""
from pathlib import Path
from dataclasses import replace,asdict
from copy import copy
from collections import Counter
import json,time,hashlib,random,math
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.serialization import deserialize_ruleset,serialize_ruleset
from generic_chess.core.pieces import Piece
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import serialize_game_record,deserialize_game_record
from generic_chess.session.result import SessionStatus
from scripts.generic_session_win_proof import SessionChoice,replay_bound
from scripts.generic_session_proof_player import SessionDecision,commit_session_decision
from scripts.generic_session_phase_player import PhaseLimits
from scripts.generic_win_proof import _Budget,_Interrupted,_same_state
from scripts.generic_inventory_proof_transport import execution_differences
from scripts.generic_proof_rnb_bridge import actor_state,uci,orbit
from scripts.generic_royal_actor import RoyalActor
from results.dev_aux.task2210.player import PaidGraphPhasePlayer
from results.dev_aux.task2153.stop_evidence import EvidenceStopReader
from results.dev_aux.task2175.receipt import choice_value
OUT=Path('results/dev_aux/task2271')
def key(raw):return ''.join(raw[:-1])+str(raw[-1])
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(n,v):
 with(OUT/n).open('x',encoding='utf-8')as f:json.dump(v,f,indent=2)
class Guide:
 def __init__(self):
  start=time.perf_counter();audit=json.loads(Path('results/dev_aux/task2250/result.json').read_text());assert audit['status']=='PASS_COMPLETE_COVERAGE_BELLMAN_RANK_CANONICAL_HISTORY'
  self.reference=compile_ruleset_for_execution(deserialize_ruleset(Path('results/dev_aux/task2248/rules.json').read_text()))
  self.rows={};self.indices={}
  # High-inventory TRAIN/DEV canonical WDL labels are deliberately NOT loaded.
  for line in Path('results/dev_aux/task2249/labels.jsonl').open(encoding='utf-8'):
   r=json.loads(line)
   if len(r['inventory'])<=4:self.rows[key(r['board'])]=r;self.indices[r['index']]=r
  self.seconds=time.perf_counter()-start
class GuidedPlayer:
 def __init__(self,c,ratio,guide,p):
  if execution_differences(guide.reference,c):raise ValueError('unqualified_execution_rules')
  self.compiled=c;self.guide=guide
  def evaluate(pos,target):return float(sum((1 if pc.owner==target else-1)*(ratio if pc.current_type_id=='R'else 1.)for pc in pos.board if pc is not None and pc.current_type_id!='K'))
  self.normal=PaidGraphPhasePlayer(c,evaluate,proof_enabled=False,limits=PhaseLimits(proof_nodes=0,proof_seconds=0.,verification_nodes=0,verification_seconds=0.,normal_seconds=p['normal_seconds']),max_depth=p['normal_depth'])
 def observe(self,before,choice,after):self.normal.observe(before,choice,after)
 def choose(self,s,*,max_nodes,seconds,cancel=None):
  n=sum(pc is not None for pc in s.state.position.board)
  if n>4:return self.normal.choose(s,max_nodes=max_nodes,seconds=seconds,cancel=cancel)
  b=_Budget(max_nodes,seconds,cancel);before=s.to_record();state=s.state;result=s.result;choice=None;reason='rank_policy_not_certificate';cause='policy';start=time.perf_counter();admission=0.
  try:
   b.poll();replay_bound(s);admission=time.perf_counter()-start;b.poll()
   if result.status is not SessionStatus.ONGOING:cause='actual_session_terminal'
   else:
    p=s.state.position
    if p.aux_state or any(h.total()for h in p.hands)or any(pc is not None and(pc.promoted or pc.base_type_id!=pc.current_type_id)for pc in p.board):raise ValueError('unsupported_guide_state')
    r=self.guide.rows[key(actor_state(s.state))]
    if r['label']=='WIN':name=r['winning_action']
    elif r['label']=='LOSS':name=max(r['actions'],key=lambda e:(self.guide.indices[e['child']]['rank'],e['action']))['action']
    else:name=min(e['action']for e in r['actions']if e['child_value']==0)
    legal={uci(a):a for a in s.legal_actions()};b.poll();choice=SessionChoice('ACTION',action=legal[name]);b.poll()
  except _Interrupted:cause=b.reason;choice=None
  except (ValueError,KeyError)as error:reason=str(error);cause='guide_scope_failure';choice=None
  finally:assert _same_state(s.state,state)and _same_state(s.to_record(),before)and s.result==result
  if cancel is not None and cancel():choice=None;cause='cancelled'
  return SessionDecision(choice,'FIXED_LOW_INVENTORY_RANK_GUIDANCE',reason,0,0,0,b.elapsed(),cause,None,before,state,result,admission_seconds=admission)
def run():
 assert not(OUT/'started.json').exists();p=json.loads((OUT/'plan.json').read_text());assert sha(OUT/'inputs.json')==p['inputs_sha']
 for name,h in p['pins'].items():assert sha(name)==h
 start=time.perf_counter();deadline=start+p['one_cap_seconds'];stop=EvidenceStopReader(Path.cwd());save('started.json',dict(utc=__import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat(),plan_sha=sha(OUT/'plan.json')));guide=Guide();roots=json.loads((OUT/'inputs.json').read_text())['roots'];games=[];decisions=0;status='COMPLETE';selection=None;active=None
 def cancel():stop();return time.perf_counter()>=deadline
 def game(root,ratio,foe,role,phase,jf,mf):
  nonlocal decisions,status,active
  began=time.perf_counter();slot=len(games);c=compile_ruleset_for_execution(deserialize_ruleset(Path(root['rules']).read_text()));s=GameSession.replay(c,deserialize_game_record(json.dumps(root['record'])));assert hashlib.sha256(repr(s.state).encode()).hexdigest()==root['state_sha']
  players=[GuidedPlayer(c,ratio if side==role else foe,guide,p)for side in(0,1)];reason='H_UNFINISHED';moves=0;sources=Counter();active=dict(slot=slot,family=root['family'],session=s)
  for ply in range(p['H']):
   if s.result.status is not SessionStatus.ONGOING:reason='ACTUAL_RULE_TERMINAL';break
   if cancel():reason='GLOBAL_CAP_UNFINISHED';status='PARTIAL_GLOBAL_CAP';break
   side=s.state.position.side_to_move;before_sha=hashlib.sha256(repr(s.state).encode()).hexdigest();d=players[side].choose(s,max_nodes=p['normal_nodes'],seconds=min(p['step_seconds'],max(0.,deadline-time.perf_counter())),cancel=cancel)
   row=dict(slot=slot,family=root['family'],phase=phase,ratio=ratio,opponent_ratio=foe,candidate_color=role,ply=ply,side=side,is_candidate=side==role,actor_count=sum(pc is not None for pc in s.state.position.board),root_state_sha=before_sha,choice=choice_value(d.choice),source=d.source,reason=d.proof_reason,exit_cause=d.exit_cause,seconds=d.seconds,normal_visits=d.search_nodes,normal_completed_depth=None if d.normal_receipt is None else d.normal_receipt.completed_depth,admission_seconds=d.admission_seconds,normal_seconds=d.normal_seconds,finite_WIN_certificate=False)
   if d.choice is None:
    reason='NO_CHOICE_UNFINISHED';row['actual_result']=dict(status=s.result.status.value,winner=s.result.winner);mf.write(json.dumps(row)+'\n');mf.flush();decisions+=1;break
   if cancel():reason='GLOBAL_CAP_UNFINISHED';status='PARTIAL_GLOBAL_CAP';break
   commit_session_decision(s,d,players,cancel=cancel);moves+=1;sources[d.source]+=1;row['after_state_sha']=hashlib.sha256(repr(s.state).encode()).hexdigest();row['actual_result']=dict(status=s.result.status.value,winner=s.result.winner)
   mf.write(json.dumps(row)+'\n');mf.flush();decisions+=1
  terminal=s.result.status is not SessionStatus.ONGOING
  if terminal:reason='ACTUAL_RULE_TERMINAL'
  outcome='U'if not terminal else'D'if s.result.winner is None else'W'if s.result.winner==role else'L'
  reward=None if not terminal else 0 if s.result.winner is None else 1 if s.result.winner==role else-1
  row=dict(slot=slot,family=root['family'],phase=phase,ratio=ratio,opponent_ratio=foe,candidate_color=role,outcome=outcome,reward=reward,ending=reason,actual_status=s.result.status.value,winner=s.result.winner,moves=moves,seconds=time.perf_counter()-began,sources=dict(sources),record=json.loads(serialize_game_record(s.to_record())))
  games.append(row);jf.write(json.dumps(row)+'\n');jf.flush();active=None
  if len(games)%32==0:print(json.dumps(dict(games=len(games),phase=phase,decisions=decisions,seconds=time.perf_counter()-start,WLDU=dict(Counter(x['outcome']for x in games)))),flush=True)
 def complete():
  return dict(status=status,games=len(games),VALIDATION_games=sum(g['phase']=='VALIDATION'for g in games),expected_validation_games=p['expected_validation_games'],DEV_games=sum(g['phase']=='DEV'for g in games),seconds=time.perf_counter()-start,guide_load_seconds=guide.seconds,decisions=decisions,outcomes=dict(Counter(g['outcome']for g in games)),selector_executed=selection is not None,scope=p['scope'])
 try:
  with(OUT/'games.jsonl').open('x',encoding='utf-8')as jf,(OUT/'moves.jsonl').open('x',encoding='utf-8')as mf:
   for root in[r for r in roots if r['split']=='VALIDATION']:
    for fi,foe in enumerate(p['opponents']):
     for role in(0,1):
      off=(root['family']+fi+role)%len(p['grid']);grid=p['grid'][off:]+p['grid'][:off]
      for ratio in grid:
       if cancel():status='PARTIAL_GLOBAL_CAP';break
       game(root,ratio,foe,role,'VALIDATION',jf,mf)
       if status!='COMPLETE':break
      if status!='COMPLETE':break
     if status!='COMPLETE':break
    if status!='COMPLETE':break
   save('completion.json',complete());print(json.dumps(complete()),flush=True)
 except BaseException as error:
  status='INTERRUPTED_OR_FAILED';data=complete();data.update(error_type=type(error).__name__,message=str(error))
  if active is not None:data['active_partial']=dict(slot=active['slot'],family=active['family'],record=json.loads(serialize_game_record(active['session'].to_record())))
  save('failure.json',data);raise
if __name__=='__main__':import sys;{'run':run}[sys.argv[1]]()
