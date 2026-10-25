"""Frozen research draw cutoff quality and actual paired-game cost, no defaults."""
from pathlib import Path
from contextlib import nullcontext
from datetime import datetime,timezone
from collections import Counter
import gzip,json,time,hashlib,traceback
from scripts import leaper_design as L
from scripts.leaper_delayed_capture_witness import replay
from scripts.leaper_draw_cutoff import ProvenDrawCutoff
from scripts.pure_leaper_search_study import append
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.ai.limits import SearchLimits
from generic_chess.ai.benchmark.runner import play_game,RunConfig
from generic_chess.ai.benchmark.profiles import PROFILES
from generic_chess.core.actions import action_from_dict
from tools.local_agent.common import write_json
from tools.local_agent import session

def stamp():return datetime.now(timezone.utc).isoformat()
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def prepare(d):
 d.mkdir(exist_ok=False)
 old=json.loads(gzip.decompress(Path('docs/research/data/leaper_scalar_frontier_20261025/real-budget/inputs.json.gz').read_bytes()))
 canon=json.loads(gzip.decompress(Path('.local_agent/f538-canonical-evidence.json.gz').read_bytes()));pc=canon['price_control']
 games=L.load(Path('.local_agent/lmr-f538/inputs.json'))['cases']
 data=dict(quality=old,canonical=dict(rule=canon['rules'][pc['root_record']['ruleset_fingerprint']],record=pc['root_record'],bad_action=pc['bad_action'],safe_action=pc['safe_action']),games=games)
 write_json(d/'inputs.json',data)
 keys=[c['key']for c in old['cases']];selected=[k for i,k in enumerate(keys)if i%2==0 or k in ('next-role-p49','next-role-p53')]
 slots=[]
 for budget,chosen in [('fixed1.5',keys),('balanced50k',selected)]:
  for i,k in enumerate(chosen):
   for arm in ((False,True)if i%2==0 else(True,False)):slots.append(dict(case=k,enabled=arm,budget=budget))
 for arm in (False,True):slots.append(dict(case='canonical-control',enabled=arm,budget='canonical50k'))
 sources={f:sha(f)for f in ['scripts/leaper_draw_cutoff.py','scripts/leaper_draw_observer.py','scripts/leaper_draw_study.py','generic_chess/ai/alphabeta/search.py']}
 write_json(d/'plan.json',dict(at=stamp(),question='Does a separately qualified trueDRAW0 nonroot cutoff improve actual pureLeaper query/game cost without damaging source-attributed actionWDL or actual game outcomes?',inputs_sha256=sha(d/'inputs.json'),sources=sources,slots=slots,game_cases=[c['key']for c in games],game_seconds=2,game_maxplies=96,batch_seconds=4200,quality_node_seconds=30,quality_nodes=50000,quality_time_seconds=1.5,forecast=dict(basis='Closed prior64default/refined1.5 total187.58s;64paired50k1783.70s;24games2095.08s. New50k everyother+known49/53, samecontrollerPVStrue botharms nothistoricalPVSoff.',point_query_seconds=187.58+1783.70*len(selected)/64+2095.08+60,reserve_seconds=420,whole_chain_prior_preparation_reserve_seconds=1200,whole_chain_current_engineering_seconds=900,whole_chain_review_reserve_seconds=480,expected_total_seconds=187.58+1783.70*len(selected)/64+2095.08+60+420+1200+900+480,threshold_seconds=7200),scope='Research-only, H64/96/128/repeat4/draw ordinaryK8 4/5/6 plainleap/remove; setups constructor-only normalized, FULL fingerprint/history retained. Old64exposed correlatedTRAIN cases, notholdout. Canonical onlybadWINproof/safeDrawclosure attribution, otheractionsUNKNOWN. Games6knownrules/12fullhistories24colorpairs; no Elo/allclassclaim.',acceptance='No activation unless current matchedquality hasnoWDLregression andactualgame/cost evidence isuseful; retainallnegatives/missing/ineligible. All frozen phases measure distinctquality/cost endpoints; no thresholdtuning/refill. Stophard4200/rolestop or actualchain forecast>=120; no newcap from results.'))
 print('prepared',len(slots),'qualityslots',len(selected),'balancedroots')

def run(d):
 plan=L.load(d/'plan.json');data=L.load(d/'inputs.json');assert sha(d/'inputs.json')==plan['inputs_sha256']
 assert plan['forecast']['expected_total_seconds']<7200
 for p,h in plan['sources'].items():assert sha(p)==h,p
 assert not(d/'queries.jsonl').exists() and not(d/'receipt.json').exists()
 tick=time.perf_counter();start=stamp();count=0;games_done=0;status='FAILED';phase='quality';current_game=None
 cases={c['key']:c for c in data['quality']['cases']};gc={c['key']:c for c in data['games']}
 class Stop(RuntimeError):pass
 class Cancel:
  last=0.;flag=False
  def is_cancelled(self):
   t=time.perf_counter()
   if t-self.last>=.25:self.last=t;self.flag=session.stopped() or t-tick>=plan['batch_seconds']
   return self.flag
 cancel=Cancel()
 def guard():
  if cancel.is_cancelled():raise Stop('role/batch cap; partial andunfilledUNKNOWN')
 def query(c,r,s,enabled,label,limits,player=None):
  nonlocal count
  guard();before=L.record_value(s.to_record());begin=stamp();qt=time.perf_counter();cpu=time.process_time()
  policy=ProvenDrawCutoff(r,c)if enabled else None
  player=player or AlphaBetaPlayer(c,use_disk_cache=False,tuning=SearchTuning(use_pvs=True))
  with policy if policy else nullcontext():decision=player.choose_action(s,limits,cancel_token=cancel)
  row=dict(id=count,label=label,enabled=enabled,started_at=begin,ended_at=stamp(),seconds=time.perf_counter()-qt,cpu_seconds=time.process_time()-cpu,before_record=before,state_sha256=L.state_sha(s.state),limits=L.record_value(limits),decision=L.record_value(decision),profile=L.record_value(player.evaluation_profile),tuning=L.record_value(SearchTuning(use_pvs=True)),policy_counts=dict(policy.counts)if policy else {},gate_seconds=policy.gate_seconds if policy else 0)
  append(d/'queries.jsonl',row);count+=1
  session.record_work(row['started_at'],row['ended_at'],'research',f'{d.as_posix()}/queries.jsonl actualCore query{count};frozen trueDRAW0 quality/game experiment, no oldslotrefill')
  assert before==L.record_value(s.to_record())
  pv=replay(c,before)
  for a in decision.principal_variation:assert a in pv.legal_actions();pv.submit(a)
  assert decision.action in s.legal_actions() or decision.choice_kind=='DECLARATION'
  assert decision.runtime_pushes==decision.runtime_pops
  return decision,row
 try:
  for i,slot in enumerate(plan['slots']):
   guard()
   if slot['case']=='canonical-control':
    case=data['canonical'];r=L.ruleset_from_dict(case['rule']);c=L.compile_rule(r);s=replay(c,case['record'])
   else:
    case=cases[slot['case']];r=L.ruleset_from_dict(data['quality']['rules'][case['rule_sha256']]);c=L.compile_rule(r);s=replay(c,case['record']);assert L.state_sha(s.state)==case['state_sha256']
   limits=SearchLimits(max_time_seconds=plan['quality_time_seconds'])if slot['budget']=='fixed1.5'else SearchLimits(max_nodes=plan['quality_nodes'],max_time_seconds=plan['quality_node_seconds'])
   dec,row=query(c,r,s,slot['enabled'],slot,limits)
   if slot['case']=='canonical-control':
    known='bad_proved_opponent_WIN'if dec.action==action_from_dict(case['bad_action'])else'safe_proved_DRAW'if dec.action==action_from_dict(case['safe_action'])else'UNKNOWN_other_action'
    append(d/'quality.jsonl',dict(slot=slot,query_id=row['id'],chosen_certificate=known))
   else:
    # Input labels use seat0 global values. Preserve actual actor perspective.
    legal={json.dumps(L.record_value(a),sort_keys=True):a for a in s.legal_actions()}
    labels={json.dumps(a['action'],sort_keys=True):a['truth']['value']*(1 if s.state.position.side_to_move==0 else -1) for a in case['labelled_actions']}
    assert set(legal)==set(labels)
    chosen=labels[json.dumps(L.record_value(dec.action),sort_keys=True)]
    assert max(labels.values())==case['root_own_WDL']
    append(d/'quality.jsonl',dict(slot=slot,query_id=row['id'],root_own_WDL=case['root_own_WDL'],chosen_own_WDL=chosen))
   if (i+1)%8==0:print('DRAW-QUALITY',i+1,'/',len(plan['slots']),slot['budget'],flush=True)
  phase='games'
  for i,key in enumerate(plan['game_cases']):
   case=gc[key];r=L.ruleset_from_dict(case['rule']);c=L.compile_rule(r);initial=replay(c,case['record'])
   for color in ((0,1)if i%2==0 else(1,0)):
    guard();current_game=key+'-draw'+str(color)
    class Arm:
     def __init__(self,enabled):self.enabled=enabled;self.player=AlphaBetaPlayer(c,use_disk_cache=False,tuning=SearchTuning(use_pvs=True));self.last_session=None
     def choose_action(self,s,limits):self.last_session=s;return query(c,r,s,self.enabled,dict(game=current_game,case=key),limits,self.player)[0]
    candidate=Arm(True);control=Arm(False);gs=stamp();gt=time.perf_counter()
    outcome,events=play_game(c,initial.to_record().actions,key,current_game,color,candidate,control,RunConfig(PROFILES['baseline'],PROFILES['baseline'],(),seconds=plan['game_seconds'],nodes=None,max_plies=plan['game_maxplies']))
    final=candidate.last_session or control.last_session or initial
    append(d/'games.jsonl',dict(game=current_game,case=key,candidate_color=color,started_at=gs,ended_at=stamp(),seconds=time.perf_counter()-gt,outcome=L.record_value(outcome),eligible=outcome.eligible,events=L.record_value(events),initial_record=L.record_value(initial.to_record()),final_record=L.record_value(final.to_record()),final_result=L.record_value(final.result)))
    games_done+=1;print('DRAW-GAME',games_done,'/24',current_game,outcome.result,outcome.plies,outcome.eligible,flush=True);current_game=None
  status='CLOSED'
 except Stop:status='STOPPED_UNKNOWN'
 except BaseException:
  write_json(d/'failure.json',dict(at=stamp(),phase=phase,queries=count,traceback=traceback.format_exc()));raise
 finally:
  write_json(d/'receipt.json',dict(status=status,phase=phase,current_game=current_game,queries=count,games=games_done,started_at=start,ended_at=stamp(),seconds=time.perf_counter()-tick,plan_sha256=sha(d/'plan.json')))
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('phase',choices=['prepare','run']);p.add_argument('--directory',type=Path,required=True);a=p.parse_args();globals()[a.phase](a.directory)
