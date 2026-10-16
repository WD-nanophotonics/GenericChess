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
from generic_chess.session.serialization import serialize_game_record
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
OUT=Path('results/dev_aux/task2238')
from results.dev_aux.task2238.normal import SeededMaterialSearch
def key(raw):return ''.join(raw[:-1])+str(raw[-1])
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(n,v):
 with(OUT/n).open('x',encoding='utf-8')as f:json.dump(v,f,indent=2)
class Guide:
 def __init__(self):
  start=time.perf_counter();audit=json.loads(Path('results/dev_aux/task2217/result.json').read_text());assert audit['status']=='PASS_COMPLETE_COVERAGE_BELLMAN_RANK_CANONICAL_HISTORY'
  self.reference=compile_ruleset_for_execution(deserialize_ruleset(Path('results/dev_aux/task2214/rules.json').read_text()))
  self.rows={};self.indices={}
  # High-inventory TRAIN/DEV canonical WDL labels are deliberately NOT loaded.
  for line in Path('results/dev_aux/task2216/labels.jsonl').open(encoding='utf-8'):
   r=json.loads(line)
   if len(r['inventory'])<=4:self.rows[key(r['board'])]=r;self.indices[r['index']]=r
  self.seconds=time.perf_counter()-start
class GuidedPlayer:
 def __init__(self,c,ratio,guide,p):
  if execution_differences(guide.reference,c):raise ValueError('unqualified_execution_rules')
  self.compiled=c;self.guide=guide
  def evaluate(pos,target):return float(sum((1 if pc.owner==target else-1)*(ratio if pc.current_type_id=='R'else 1.)for pc in pos.board if pc is not None and pc.current_type_id!='K'))
  self.normal=PaidGraphPhasePlayer(c,evaluate,proof_enabled=False,limits=PhaseLimits(proof_nodes=0,proof_seconds=0.,verification_nodes=0,verification_seconds=0.,normal_seconds=p['normal_seconds']),max_depth=p['normal_depth'])
  self.priority_seed=p['priority_seed'];self.normal.normal=SeededMaterialSearch(c,evaluate,max_depth=p['normal_depth'],priority_seed=self.priority_seed)
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
    if r['label']=='WIN':
     candidates=[e for e in r['actions']if e['child_value']==-1];rank=min(self.guide.indices[e['child']]['rank']for e in candidates);candidates=[e for e in candidates if self.guide.indices[e['child']]['rank']==rank]
    elif r['label']=='LOSS':
     rank=max(self.guide.indices[e['child']]['rank']for e in r['actions']);candidates=[e for e in r['actions']if self.guide.indices[e['child']]['rank']==rank]
    else:candidates=[e for e in r['actions']if e['child_value']==0]
    name=min(candidates,key=lambda e:hashlib.sha256((str(self.priority_seed)+':'+e['action']).encode()).hexdigest())['action']
    legal={uci(a):a for a in s.legal_actions()};b.poll();choice=SessionChoice('ACTION',action=legal[name]);b.poll()
  except _Interrupted:cause=b.reason;choice=None
  except (ValueError,KeyError)as error:reason=str(error);cause='guide_scope_failure';choice=None
  finally:assert _same_state(s.state,state)and _same_state(s.to_record(),before)and s.result==result
  if cancel is not None and cancel():choice=None;cause='cancelled'
  return SessionDecision(choice,'FIXED_LOW_INVENTORY_RANK_GUIDANCE',reason,0,0,0,b.elapsed(),cause,None,before,state,result,admission_seconds=admission)
