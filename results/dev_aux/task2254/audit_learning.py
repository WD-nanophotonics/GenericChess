"""Closed full OR partial learning audit; planned missing outcomes stay intervals."""
from pathlib import Path
from collections import defaultdict,Counter
import json,hashlib,time,sys,numpy as np
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record,serialize_game_record
from generic_chess.session.result import SessionStatus
from scripts.generic_session_win_proof import SessionChoice
from results.dev_aux.task2175.receipt import choice_value
from results.dev_aux.task2153.stop_evidence import EvidenceStopReader
OUT=Path('results/dev_aux/task2254')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text())
def run(task):
 start=time.perf_counter();stop=EvidenceStopReader(Path.cwd());folder=Path(f'results/dev_aux/task{task}');p=read(folder/'plan.json');done=read(folder/'completion.json');roots=read(folder/'inputs.json')['roots'];byroot={r['family']:r for r in roots};games=[json.loads(l)for l in(folder/'games.jsonl').read_text().splitlines()];moves=[json.loads(l)for l in(folder/'moves.jsonl').read_text().splitlines()];assert len(games)==done['games']and len(moves)==done['decisions'];assert sha(folder/'inputs.json')==p['inputs_sha']
 for name,h in p['pins'].items():assert sha(name)==h
 assert not({r['group']for r in roots if r['split']=='TRAIN'}&{r['group']for r in roots if r['split']=='DEV'})
 expectedTR=[]
 for r in roots:
  if r['split']!='TRAIN':continue
  for fi,foe in enumerate(p['opponents']):
   for role in(0,1):
    off=(r['family']+fi+role)%len(p['grid'])
    for ratio in p['grid'][off:]+p['grid'][:off]:expectedTR.append(('TRAIN',r['family'],ratio,foe,role))
 assert len(expectedTR)==p['expected_TRAIN_games']==640
 tr=[g for g in games if g['phase']=='TRAIN'];dev=[g for g in games if g['phase']=='DEV'];assert len(tr)==done['TRAIN_games']and len(dev)==done['DEV_games'];selection=None;profiles=None;expectedDEV=[];selector_checks={}
 if len(tr)==640:
  selection=read(folder/'TRAIN-selection.json');freeze=read(folder/'DEV-profile-freeze.json');raw=(folder/'games.jsonl').read_bytes().splitlines(keepends=True);assert hashlib.sha256(b''.join(raw[:640])).hexdigest()==freeze['TRAIN_journal_sha']and sha(folder/'TRAIN-selection.json')==freeze['selection_sha']and freeze['DEV_queries_before_freeze']==0
  means={}
  for ratio in p['grid']:
   rr=[g for g in tr if g['ratio']==ratio];assert len(rr)==128;u=sum(g['reward']is None for g in rr);score=sum(g['reward']or 0 for g in rr);means[ratio]=dict(lower=(score-u)/128,upper=(score+u)/128,W=sum(g['outcome']=='W'for g in rr),L=sum(g['outcome']=='L'for g in rr),D=sum(g['outcome']=='D'for g in rr),U=u,n=128)
   assert means[ratio]==selection['TRAIN_actual_WL_intervals'][str(ratio)]
  expectedselections=[]
  for initial in p['initial_prices']:
   current=initial;trace=[initial]
   for _ in range(100):
    idx=p['grid'].index(current);adjacent=[p['grid'][j]for j in(idx-1,idx+1)if 0<=j<len(p['grid'])and means[p['grid'][j]]['lower']>means[current]['upper']]
    if not adjacent:break
    current=adjacent[0];trace.append(current)
   else:raise AssertionError('selectorcycle')
   alternatives=[r for r in p['grid']if means[r]['lower']>means[initial]['upper']];global_price=sorted(alternatives,key=lambda r:(-means[r]['lower'],p['grid'].index(r)))[0]if alternatives else initial;expectedselections.append(dict(initial=initial,adjacent_selected=current,adjacent_trace=trace,global_selected=global_price))
  assert expectedselections==selection['selections'];profiles=sorted({1.}|{r[k]for r in expectedselections for k in('adjacent_selected','global_selected')});assert profiles==freeze['profiles']
  for r in roots:
   if r['split']!='DEV':continue
   for fi,foe in enumerate(p['opponents']):
    for role in(0,1):
     off=(r['family']+fi+role)%len(profiles)
     for ratio in profiles[off:]+profiles[:off]:expectedDEV.append(('DEV',r['family'],ratio,foe,role))
  assert len(expectedDEV)==freeze['expected_games'];selector_checks=dict(independently_recomputed=True,selections=expectedselections)
 else:assert not dev and not done['selector_executed']and not(folder/'TRAIN-selection.json').exists()and not(folder/'DEV-profile-freeze.json').exists()
 sequence=expectedTR+expectedDEV;actual=[(g['phase'],g['family'],g['ratio'],g['opponent_ratio'],g['candidate_color'])for g in games];assert actual==sequence[:len(actual)]
 if done['status']=='COMPLETE':assert len(tr)==640 and len(dev)==len(expectedDEV)
 ms=defaultdict(list)
 for m in moves:ms[m['slot']].append(m)
 count=0;depths=Counter();sources=Counter()
 for slot,g in enumerate(games):
  stop();assert time.perf_counter()-start<300;assert g['slot']==slot;root=byroot[g['family']];assert root['split']==g['phase']and sha(root['rules'])==root['rules_sha'];s=GameSession(compile_ruleset_for_execution(deserialize_ruleset(Path(root['rules']).read_text())));actions=deserialize_game_record(json.dumps(g['record'])).actions;mm=ms[slot];assert len(actions)==g['moves']and len(mm)in(len(actions),len(actions)+1)
  for i,(a,m)in enumerate(zip(actions,mm)):
   assert m['ply']==i and m['phase']==g['phase']and m['family']==g['family']and m['ratio']==g['ratio']and m['opponent_ratio']==g['opponent_ratio']and m['candidate_color']==g['candidate_color'];assert m['root_state_sha']==hashlib.sha256(repr(s.state).encode()).hexdigest()and m['side']==s.state.position.side_to_move;assert m['choice']==choice_value(SessionChoice('ACTION',action=a))and not m['finite_WIN_certificate'];assert m['normal_visits']<=p['normal_nodes']
   s.submit(a);assert m['after_state_sha']==hashlib.sha256(repr(s.state).encode()).hexdigest()and m['actual_result']==dict(status=s.result.status.value,winner=s.result.winner);sources[m['source']]+=1;depths[(m['source'],m['normal_completed_depth'])]+=1;count+=1
  if len(mm)>len(actions):assert mm[-1]['choice']is None and g['ending']=='NO_CHOICE_UNFINISHED'
  assert json.loads(serialize_game_record(s.to_record()))==g['record']and s.result.status.value==g['actual_status']and s.result.winner==g['winner'];reward=None if s.result.status is SessionStatus.ONGOING else 0 if s.result.winner is None else 1 if s.result.winner==g['candidate_color']else-1;assert reward==g['reward'];assert g['outcome']==('U'if reward is None else'D'if reward==0 else'W'if reward==1 else'L')
 paired={};rng=np.random.default_rng(2026101677);idx={(g['family'],g['ratio'],g['opponent_ratio'],g['candidate_color']):g for g in dev}
 for ratio in profiles or[]:
  families=defaultdict(list);missing=0
  for root in roots:
   if root['split']!='DEV':continue
   for foe in p['opponents']:
    for role in(0,1):
     a=idx.get((root['family'],1.,foe,role));b=idx.get((root['family'],ratio,foe,role));bounds=(-2.,2.)
     if ratio==1.:bounds=(0.,0.)
     elif a is not None and b is not None and a['reward']is not None and b['reward']is not None:bounds=(b['reward']-a['reward'],)*2
     else:missing+=1
     families[root['family']].append(bounds)
  lo=np.array([sum(x[0]for x in v)/len(v)for _,v in sorted(families.items())]);hi=np.array([sum(x[1]for x in v)/len(v)for _,v in sorted(families.items())]);ci=None
  if missing==0:
   boot=lo[rng.integers(0,len(lo),size=(10000,len(lo)))].mean(axis=1);ci=[float(x)for x in np.quantile(boot,[.025,.975])]
  paired[str(ratio)]=dict(original_family_blocks=len(families),unknown_or_missing_pairs=missing,mean_lower=float(lo.mean()),mean_upper=float(hi.mean()),descriptive_bootstrap95=ci)
 result=dict(status='PASS_CLOSED_ACTUAL_LEARNING_WITH_PLANNED_MISSING_BOUNDS',task=task,producer_status=done['status'],games=len(games),actual_moves=count,TRAIN_games=len(tr),missing_TRAIN=640-len(tr),DEV_games=len(dev),planned_DEV=None if profiles is None else len(expectedDEV),missing_DEV=None if profiles is None else len(expectedDEV)-len(dev),selector_checks=selector_checks,sources=dict(sources),normal_depths=[dict(source=s,depth=d,count=n)for(s,d),n in depths.items()],profiles={str(r):dict(TRAIN=dict(Counter(g['outcome']for g in tr if g['ratio']==r)),DEV=dict(Counter(g['outcome']for g in dev if g['ratio']==r)))for r in p['grid']},DEV_paired_vs_unity=paired,seconds=time.perf_counter()-start,scope='IndependentactualSessionreplay/sequence/full-or-partialslotcoverage/selectorreimplementation. Partial/missing/UNKNOWNstayfullbounds; no selectivecompleted-familyfilter orfakeDRAW. DEVafter640TR/prefixhash;newinventory/ruleexposureexplicit, notuniversalprice. No producers/refit/newrewardgames.')
 with(OUT/f'task{task}-audit.json').open('x')as f:json.dump(result,f,indent=2)
 print(json.dumps({k:v for k,v in result.items()if k not in('normal_depths','profiles','selector_checks','sources')}))
if __name__=='__main__':run(int(sys.argv[1]))
