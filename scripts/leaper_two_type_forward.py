"""Prospective two-type finite forward experiment; no learner or WDL oracle."""
from __future__ import annotations
from dataclasses import replace
from pathlib import Path
from datetime import datetime,timezone
import json,time,random,argparse,traceback
from scripts import leaper_design as L
from scripts.semantic_probe_cost import unit_evaluator
from generic_chess.rules.schema import RuleInitialSetupOption
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.ai.evaluation.evaluator import Evaluator
from generic_chess.ai.evaluation.config import EvaluationConfig
from tools.local_agent.common import write_json
from tools.local_agent import session

def now():return datetime.now(timezone.utc).isoformat()
RATIOS={f'B{b}':b for b in (250,500,750,1000,1500,2000,4000)}
def profiles(c,b):
 u=unit_evaluator(c);p=replace(u._profile,board_value_by_type={'K':0,'A':1000,'B':b},hand_value_by_base_type={'K':0,'A':900,'B':int(.9*b)})
 # Fixed unit ordering for all leaf-price candidates isolates the declared leaf substitution.
 return L.LeafOrderAdapter(Evaluator(c,p,u._config),u),L.record_value(p),L.record_value(u._config)
def player(c,b):
 e,_,_=profiles(c,b)
 return L.AlphaBetaPlayer(c,evaluator_override=e,tuning=SearchTuning(),use_disk_cache=False,use_native_semantic_legality=True,use_native_semantic_availability=False,use_native_semantic_check=False)
def prepare(path):
 assert not path.exists()
 base=L.definition(2,1);layouts=[(1,5,23,19),(2,6,22,18),(5,7,19,17),(6,10,18,14)];boards=[]
 for a,b,x,y in layouts:
  cells=[None]*25
  for ix,owner,tid in ((0,0,'K'),(a,0,'A'),(b,0,'B'),(24,1,'K'),(x,1,'A'),(y,1,'B')):cells[ix]=L.Piece(owner,tid,tid)
  boards.append(tuple(tuple(cells[5*r:5*r+5])for r in range(5)))
 r=replace(base,board_size=5,initial_position=boards[0],initial_setup_options=tuple(RuleInitialSetupOption('mu'+str(i),b)for i,b in enumerate(boards[1:],1)),drop_allowed={t:((False,)*25,)*2 for t in ('A','B')},max_ply=64,repetition_limit=4)
 c=L.compile_rule(r);roots=[]
 for i in range(4):
  s=L.GameSession(c,None if i==0 else 'mu'+str(i));assert not s.state.terminal_status.is_terminal
  assert L.GameSession.replay(c,s.to_record()).state==s.state
  roots.append(dict(index=i,record=L.record_value(s.to_record()),state=L.record_value(s.state),state_sha256=L.state_sha(s.state),legal_count=len(s.legal_actions())))
 frozen={p:profiles(c,b)[1:]for p,b in RATIOS.items()}
 write_json(path,dict(question='Prospective relative leaf prices in a fixed two-type full-rule family, both sides retain ordinary actors; no truth-selected mu.',rule=L.ruleset_to_dict(r),fingerprint=L.compute_fingerprint(r),roots=roots,profiles=frozen,mu='Four explicitly listed fresh layouts, equal finite weights, not iid sampled rules; all retained independent of outputs.',scope='Plain King8/FerzA/WazirB remove, H64/repeat4; no promotion/drop/aux in this scoped prototype. Full history remains intact. One price A=1000 fixed, B250/500/750/1000/1500/2000/4000; unit1000 ordering fixed; opponent same unit leaf/order. No learning, exact truth or default change.'))
 return L.load(path)
def game(inputs,slot,path,deadline,nodes=8192):
 assert not path.exists();world=L.load(inputs);c=L.compile_rule(L.ruleset_from_dict(world['rule']));root=world['roots'][slot['root']];s=L.GameSession.replay(c,L.deserialize_game_record(json.dumps(root['record'])))
 ps={0:player(c,RATIOS[slot['policy']]),1:player(c,1000)};start=now();tick=time.perf_counter();qs=[];censor=None
 # AlphaBeta is deterministic; seeds are execution/tie stream labels only and not independent replications.
 while not s.state.terminal_status.is_terminal:
  if session.stopped():censor='user_stop';break
  if time.perf_counter()>=deadline:censor='whole_cap';break
  side=s.state.position.side_to_move;legal=s.legal_actions();t=time.perf_counter();d=ps[side].choose_action(s,L.SearchLimits(max_depth=64,max_nodes=nodes,max_time_seconds=3,quiescence_max_depth=0,quiescence_hard_max_depth=8))
  q=dict(actor=side,root_ply=s.state.ply_count,state_sha256=L.state_sha(s.state),legal_count=len(legal),decision=L.record_value(d),action=L.record_value(d.action),seconds=time.perf_counter()-t)
  qs.append(q);write_json(path,dict(status='RUNNING',slot=slot,started_at=start,initial_record=root['record'],queries=qs,current_record=L.record_value(s.to_record())))
  if d.action is None:censor='no_action';break
  assert d.action in legal;s.submit(d.action)
 row=dict(status='CLOSED',slot=slot,started_at=start,ended_at=now(),seconds=time.perf_counter()-tick,initial_record=root['record'],queries=qs,final_record=L.record_value(s.to_record()),final_state=L.record_value(s.state),terminal=L.record_value(s.result),censor=censor,value=L.outcome_value(s.result,0,censor),nodes_limit=nodes)
 write_json(path,row);print('GAME',slot,row['terminal']['status'],row['value'],len(qs),round(row['seconds'],3),flush=True);return row

def run(inputs,regfile,d):
 assert not d.exists();d.mkdir(parents=True);reg=L.load(regfile);assert L.sha(inputs)==reg['input_sha256'] and L.sha(Path(__file__))==reg['source_sha256'];assert reg['expected_total_seconds']<7200
 tick=time.perf_counter();out=dict(status='RUNNING',started_at=now(),slots=[dict(x,status='not_started')for x in reg['slots']]);write_json(d/'results.json',out)
 try:
  for i,x in enumerate(out['slots']):
   if session.stopped()or time.perf_counter()-tick>=reg['cap_seconds']:break
   try:
    row=game(inputs,{k:v for k,v in x.items()if k!='status'},d/f'game-{i:03d}.json',tick+reg['cap_seconds'],reg['nodes']);x.update(status='finished',value=row['value'],seconds=row['seconds'],censor=row['censor'])
   except Exception as e:x.update(status='failed',error=repr(e));write_json(d/f'error-{i:03d}.json',dict(error=repr(e),traceback=traceback.format_exc()))
   write_json(d/'results.json',out)
 finally:
  out.update(status='CLOSED',ended_at=now(),seconds=time.perf_counter()-tick,missing=[i for i,x in enumerate(out['slots'])if x['status']!='finished'or x['value']is None]);write_json(d/'results.json',out)
 return out
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('mode',choices=['prepare','game','run']);ap.add_argument('--input',type=Path,required=True);ap.add_argument('--output',type=Path);ap.add_argument('--registration',type=Path);ap.add_argument('--root',type=int,default=0);ap.add_argument('--policy',default='B1000');a=ap.parse_args()
 if a.mode=='prepare':prepare(a.input)
 elif a.mode=='game':game(a.input,dict(root=a.root,policy=a.policy,seed=202610241901),a.output,time.perf_counter()+300)
 else:run(a.input,a.registration,a.output)
