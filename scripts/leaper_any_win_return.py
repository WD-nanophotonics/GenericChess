"""Existing any-root-win objective at frozen real pure-Leaper node budgets.
No backend/controller code changes; full exposed guard, all missing slots UNKNOWN.
"""
from pathlib import Path
from dataclasses import asdict
from datetime import datetime,timezone
import argparse,json,hashlib,time,traceback
from scripts import leaper_design as L
from scripts.leaper_delayed_capture_witness import replay
from scripts.leaper_real_budget_refinement import limits_for
from scripts.pure_leaper_search_study import append
from tools.local_agent.common import write_json
from tools.local_agent.session import stopped
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.ai.evaluation.config import MATE_THRESHOLD

def stamp():return datetime.now(timezone.utc).isoformat()
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def run(d):
 p=L.load(d/'plan.json');data=L.load(d/'inputs.json');assert sha(__file__)==p['source_sha256']and sha(d/'inputs.json')==p['inputs_sha256']
 for f,h in p['dependencies'].items():assert sha(f)==h
 assert not(d/'receipt.json').exists()and not(d/'queries.jsonl').exists()
 assert L.load(Path(p['prior_receipt']))['status']=='CLOSED'
 cases={c['key']:c for c in data['cases']};tick=time.perf_counter();begin=stamp();count=attempted=0;status='FAILED'
 class Stop:
  last=0.;flag=False
  def is_cancelled(self):
   now=time.perf_counter()
   if now-self.last>=.25:self.last=now;self.flag=stopped()or now-tick>=p['batch_seconds']
   return self.flag
 try:
  for slot in p['slots']:
   if Stop().is_cancelled():raise RuntimeError('role/batch stop; unfinished UNKNOWN; no refill')
   setup=time.perf_counter();case=cases[slot['key']];c=L.compile_rule(L.ruleset_from_dict(data['rules'][case['rule_sha256']]));s=replay(c,case['record']);assert L.state_sha(s.state)==case['state_sha256'];tuning=SearchTuning(stop_after_root_win=slot['arm']=='anywin');player=AlphaBetaPlayer(c,use_disk_cache=False,tuning=tuning);raw,limits=limits_for(slot['budget']);assert asdict(limits)==p['budgets'][slot['budget']];setup_seconds=time.perf_counter()-setup;start=stamp();qt=time.perf_counter();qc=time.process_time();attempted+=1;dec=player.choose_action(s,limits,cancel_token=Stop());end=stamp();row=dict(slot=slot,started_at=start,ended_at=end,seconds=time.perf_counter()-qt,cpu_seconds=time.process_time()-qc,setup_seconds=setup_seconds,caller_seconds=time.perf_counter()-setup,decision=L.record_value(dec),state_sha256=L.state_sha(s.state),tuning=L.record_value(tuning),evaluation_profile=L.record_value(player.evaluation_profile));append(d/'queries.jsonl',row);count+=1
   pv=replay(c,case['record'])
   for a in dec.principal_variation:assert a in pv.legal_actions();pv.submit(a)
   labels={json.dumps(x['action'],sort_keys=True):x['truth']['value']for x in case['labelled_actions']};value=labels[json.dumps(L.record_value(dec.action),sort_keys=True)];correct=value==case['root_global_WDL'];q=dict(slot=slot,chosen_global_WDL=value,correct=correct,score_in_win_band=dec.score>=MATE_THRESHOLD,pv_steps=len(dec.principal_variation),runtime_balanced=dec.runtime_depth_balanced,actual_goal_stop=dec.termination_reason=='root_win_found',node_target_time_censored=dec.termination_reason=='time_limit');append(d/'qualification.jsonl',q)
   assert dec.runtime_depth_balanced and dec.runtime_pushes==dec.runtime_pops
   if dec.score>=MATE_THRESHOLD:assert correct,'Win-band action fails fixed independent published WDL labels; stop cost interpretation'
   print('ANYWIN',count,slot['budget'],slot['key'],slot['arm'],dec.completed_depth,value,dec.termination_reason,round(row['seconds'],3),flush=True)
  status='CLOSED'
 except Exception:write_json(d/'failure.json',dict(at=stamp(),attempted=attempted,queries=count,traceback=traceback.format_exc()));raise
 finally:write_json(d/'receipt.json',dict(status=status,started_at=begin,ended_at=stamp(),seconds=time.perf_counter()-tick,attempted=attempted,queries=count,source_sha256=p['source_sha256']))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--directory',required=True,type=Path);run(p.parse_args().directory)
