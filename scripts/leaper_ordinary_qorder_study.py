"""Ordinary-only Q ordering under actual DEFAULT/PVS/Q4 and Nativeboth.
Research caller only; no backend, policy or default changes. Capsules are data.
"""
from pathlib import Path
from datetime import datetime,timezone
from collections import defaultdict,Counter
import json,gzip,time,hashlib,traceback
from scripts import leaper_design as L
from scripts.leaper_delayed_capture_witness import replay
from scripts.pure_leaper_search_study import append
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.ai.limits import SearchLimits
from generic_chess.ai.benchmark.runner import play_game,RunConfig
from generic_chess.ai.benchmark.profiles import PROFILES
from tools.local_agent.common import write_json
from tools.local_agent import session

def stamp():return datetime.now(timezone.utc).isoformat()
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def tuning(arm):
 return SearchTuning(use_pvs=True,use_ordered_qsearch=arm=='both',use_ordered_qsearch_in_check=False)
def player(c,arm):
 assert arm in ('baseline','both')
 return AlphaBetaPlayer(c,use_disk_cache=False,use_ordering=True,tuning=tuning(arm),use_native_semantic_availability=True,use_native_semantic_check=True)
def metrics(p):
 n=p.native_legality_provider
 return dict(provider=n is not None,availability=n.availability_metrics if n else {},check=n.check_metrics if n else {})
def delta(a,b):return {group:{k:v-a[group].get(k,0) for k,v in b[group].items()} for group in ('availability','check')}
def context(data,key):
 g=next((c for c in data['games'] if c['key']==key),None)
 if g:r=L.ruleset_from_dict(g['rule']);record=g['record']
 else:
  q=next(c for c in data['quality']['cases'] if c['key']==key);r=L.ruleset_from_dict(data['quality']['rules'][q['rule_sha256']]);record=q['record']
 c=L.compile_rule(r);return c,replay(c,record)

def run(d,phase):
 plan=L.load(d/'qualification-plan.json');data=L.load(d/'inputs.json');assert sha(d/'inputs.json')==plan['inputs_sha256']
 for p,h in plan['sources'].items():assert sha(p)==h,p
 if phase=='fitness':assert L.load(d/'qualification-assessment.json')['passed'];plan=L.load(d/'fitness-plan.json')
 assert not(d/(phase+'-receipt.json')).exists() and not(d/(phase+'-queries.jsonl')).exists()
 tick=time.perf_counter();started=stamp();count=0;games_done=0;status='FAILED';current=None
 class Stop(RuntimeError):pass
 class Cancel:
  last=0.;flag=False
  def is_cancelled(self):
   t=time.perf_counter()
   if t-self.last>=.25:self.last=t;self.flag=session.stopped() or t-tick>=plan['batch_seconds']
   return self.flag
 cancel=Cancel()
 def query(c,s,arm,label,limits,p=None,token=None):
  nonlocal count
  if cancel.is_cancelled():raise Stop('role/batch stop')
  before=L.record_value(s.to_record());begin=stamp();qt=time.perf_counter();cpu=time.process_time();p=p or player(c,arm);setup=time.perf_counter()-qt;m=metrics(p)
  try:dec=p.choose_action(s,limits,cancel_token=token or cancel)
  except BaseException:
   append(d/(phase+'-failures.jsonl'),dict(id=count,label=label,arm=arm,before_record=before,started_at=begin,ended_at=stamp(),seconds=time.perf_counter()-qt,metrics=metrics(p),traceback=traceback.format_exc()));raise
  row=dict(id=count,label=label,arm=arm,enabled=arm!='baseline',started_at=begin,ended_at=stamp(),seconds=time.perf_counter()-qt,setup_seconds=setup,cpu_seconds=time.process_time()-cpu,before_record=before,state_sha256=L.state_sha(s.state),limits=L.record_value(limits),decision=L.record_value(dec),profile=L.record_value(p.evaluation_profile),tuning=L.record_value(p._tuning),use_ordering=p._use_ordering,provider_present=m['provider'],provider_delta=delta(m,metrics(p)))
  append(d/(phase+'-queries.jsonl'),row);count+=1
  if row['ended_at']>begin:session.record_work(begin,row['ended_at'],'research',f'{d.as_posix()}/{phase}-queries.jsonl actual ordinaryQorder Nativeboth/PVS query{count};frozen limits and actual service deltas')
  assert before==L.record_value(s.to_record()) and dec.runtime_pushes==dec.runtime_pops
  pv=replay(c,before)
  for a in dec.principal_variation:assert a in pv.legal_actions();pv.submit(a)
  assert dec.action in s.legal_actions() or dec.choice_kind=='DECLARATION'
  return dec,row
 try:
  if phase=='qualification':
   for slot in plan['qualification']:
    current=slot;c,s=context(data,slot['case']);query(c,s,slot['arm'],slot,SearchLimits(max_depth=plan['qualification_depth'],max_nodes=plan['qualification_nodes'],max_time_seconds=plan['qualification_seconds']))
   # Cancellation at an actual cooperative poll during search, same count all arms.
   for arm in ('baseline','both'):
    class PollCancel:
     calls=0
     def is_cancelled(self):self.calls+=1;return self.calls>=100
    token=PollCancel();c,s=context(data,plan['qualification'][0]['case']);query(c,s,arm,dict(cancel_after_polls=100),SearchLimits(max_depth=16,max_nodes=200000,max_time_seconds=15),token=token)
  else:
   cases={c['key']:c for c in data['quality']['cases']}
   for i,slot in enumerate(plan['slots']):
    current=slot;c,s=context(data,slot['case']);limits=SearchLimits(max_time_seconds=1.5)if slot['budget']=='fixed1.5'else SearchLimits(max_nodes=50000,max_time_seconds=30)
    dec,row=query(c,s,slot['arm'],slot,limits)
    case=cases[slot['case']];labels={json.dumps(a['action'],sort_keys=True):a['truth']['value']*(1 if s.state.position.side_to_move==0 else -1)for a in case['labelled_actions']}
    assert set(labels)=={json.dumps(L.record_value(a),sort_keys=True)for a in s.legal_actions()}
    assert max(labels.values())==case['root_own_WDL']
    append(d/'quality.jsonl',dict(slot=slot,query_id=row['id'],root_own_WDL=case['root_own_WDL'],chosen_own_WDL=labels[json.dumps(L.record_value(dec.action),sort_keys=True)]))
    if (i+1)%16==0:print('NATIVE-QUALITY',i+1,'/',len(plan['slots']),slot['budget'],flush=True)
   gc={c['key']:c for c in data['games']}
   for i,key in enumerate(plan['game_cases']):
    case=gc[key];c,s=context(data,key)
    for color in ((0,1)if i%2==0 else(1,0)):
     current=key+'-native'+str(color)
     class Arm:
      def __init__(self,enabled):self.enabled=enabled;self.player=player(c,'both'if enabled else'baseline');self.last_session=None
      def choose_action(self,s,limits):self.last_session=s;return query(c,s,'both'if self.enabled else'baseline',dict(game=current,case=key),limits,self.player)[0]
     a=Arm(True);b=Arm(False);gs=stamp();gt=time.perf_counter()
     outcome,events=play_game(c,s.to_record().actions,key,current,color,a,b,RunConfig(PROFILES['baseline'],PROFILES['baseline'],(),seconds=2,nodes=None,max_plies=96))
     final=a.last_session or b.last_session or s
     append(d/'games.jsonl',dict(game=current,case=key,candidate_color=color,started_at=gs,ended_at=stamp(),seconds=time.perf_counter()-gt,outcome=L.record_value(outcome),eligible=outcome.eligible,events=L.record_value(events),initial_record=L.record_value(s.to_record()),final_record=L.record_value(final.to_record()),final_result=L.record_value(final.result)))
     games_done+=1;print('NATIVE-GAME',games_done,'/24',current,outcome.result,outcome.plies,outcome.eligible,flush=True)
  status='CLOSED'
 except Stop:status='STOPPED_UNKNOWN'
 except BaseException:
  write_json(d/(phase+'-failure.json'),dict(at=stamp(),current=current,queries=count,traceback=traceback.format_exc()));raise
 finally:write_json(d/(phase+'-receipt.json'),dict(status=status,current=current,queries=count,games=games_done,started_at=started,ended_at=stamp(),seconds=time.perf_counter()-tick,plan_sha256=sha(d/('qualification-plan.json'if phase=='qualification'else'fitness-plan.json'))))

def qualify(d):
 plan=L.load(d/'qualification-plan.json');rows=[json.loads(x)for x in(d/'qualification-queries.jsonl').read_text().splitlines()]
 assert L.load(d/'qualification-receipt.json')['status']=='CLOSED'and len(rows)==len(plan['qualification'])+2
 groups=defaultdict(dict)
 for r in rows[:len(plan['qualification'])]:groups[r['label']['case']][r['arm']]=r
 results=[]
 for key,rr in groups.items():
  a,b=rr['baseline'],rr['both']
  for r in(a,b):
   assert r['decision']['completed_depth']==plan['qualification_depth'],(key,r['arm'],r['decision']['completed_depth'])
   assert r['decision']['result_source']=='main_iteration'
   assert r['provider_present']and r['use_ordering']and r['tuning']==L.record_value(tuning(r['arm']))
   assert r['provider_delta']['availability'].get('declines',0)==0
  assert a['profile']==b['profile']and a['decision']['score']==b['decision']['score'],key
  results.append(dict(case=key,baseline_seconds=a['seconds'],candidate_seconds=b['seconds'],baseline_events=a['decision']['nodes']+a['decision']['qnodes'],candidate_events=b['decision']['nodes']+b['decision']['qnodes'],same_action=a['decision']['action']==b['decision']['action'],score=a['decision']['score']))
 for r in rows[-2:]:assert r['decision']['termination_reason']=='cancelled'and r['decision']['runtime_pushes']==r['decision']['runtime_pops']
 write_json(d/'qualification-assessment.json',dict(passed=True,queries=len(rows),pairs=results,cancellation='Both cancelled cooperatively, balanced runtime, unchanged full root; no claim identical frontier',contract='Requested completeD4 exact root score/profile; legal actual PV and full history preserved. Ordering may change action ties/work/TT. No WDL strength claim.'))
 print('QORDER QUALIFIED',results,flush=True)
def freeze(d):
 assert L.load(d/'qualification-assessment.json')['passed'];assert not(d/'fitness-plan.json').exists();data=L.load(d/'inputs.json')
 keys=[c['key']for c in data['quality']['cases']]
 slots=[dict(case=k,budget=b,arm=a)for b in('fixed1.5','balanced50k')for i,k in enumerate(keys)for a in(('baseline','both')if i%2==0 else('both','baseline'))]
 write_json(d/'fitness-plan.json',dict(at=stamp(),slots=slots,game_cases=[c['key']for c in data['games']],batch_seconds=4200,inputs_sha256=sha(d/'inputs.json'),qualification_sha256=sha(d/'qualification-assessment.json'),controller='Both Nativeavailability+check, DEFAULTdynamic/PVStrue/Q4hard8/use_ordering true; only ordinaryQordering differs; in_checkQorderingFalse both; fresh quality players, persistent perarm games',tuning={a:L.record_value(tuning(a))for a in('baseline','both')},exposure='64 known correlated TRAIN histories oneRuleSet plus6known gameRuleSets; not holdout/strength',limits='64paired1.5sec +64paired50k/30sec +24games2sec/96actualCoremaxply; no refill/capextension',decision='New premise Nativeboth/PVStrue ordinary-only increment. Preserve regressions/censors/ineligible; no product/default activation. Full logical chain <=6600s forecast including prior600 profile/source; >=7200USER confirmation before expansion.'))
 print('QORDER FROZEN',len(slots),'quality slots +24games',flush=True)
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('phase',choices=['qualification','qualify','freeze','fitness']);p.add_argument('--directory',type=Path,required=True);a=p.parse_args()
 if a.phase in('qualification','fitness'):run(a.directory,a.phase)
 else:globals()[a.phase](a.directory)
