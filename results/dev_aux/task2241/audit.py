"""Closed journals replay with ORIGINAL-family clustering and explicit missing bounds."""
from pathlib import Path
from collections import defaultdict,Counter
import json,hashlib,sys,time,numpy as np
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record,serialize_game_record
from generic_chess.session.result import SessionStatus
from results.dev_aux.task2153.stop_evidence import EvidenceStopReader
OUT=Path('results/dev_aux/task2241')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def run(task):
 start=time.perf_counter();stop=EvidenceStopReader(Path.cwd());folder=Path(f'results/dev_aux/task{task}');p=json.loads((folder/'plan.json').read_text());done=json.loads((folder/'completion.json').read_text());games=[json.loads(l)for l in(folder/'games.jsonl').read_text().splitlines()];moves=[json.loads(l)for l in(folder/'moves.jsonl').read_text().splitlines()];assert len(games)==done['games']and len(moves)==done['decisions'];assert done['missing']==p['expected_games']-len(games);assert sha(folder/'transfer.py')==p['source_sha']
 inputs={t:{r['family']:r for r in json.loads(Path(f'results/dev_aux/task{t}/inputs.json').read_text())['roots']}for t in p['contexts']}
 for t in p['contexts']:assert sha(f'results/dev_aux/task{t}/inputs.json')==p['input_hashes'][str(t)]
 expected={(t,r['family'],ratio,foe,role)for t in p['contexts']for r in inputs[t].values()if r['split']=='DEV'for ratio in p['profiles']for foe in p['opponent_prices']for role in p['candidate_colors']};assert len(expected)==p['expected_games'];actual={(g['context'],g['family'],g['ratio'],g['opponent_ratio'],g['candidate_color'])for g in games};assert len(actual)==len(games)and actual<=expected
 ms=defaultdict(list);depths=Counter();sources=Counter();steps=0
 for m in moves:ms[m['slot']].append(m)
 for i,g in enumerate(games):
  stop();assert time.perf_counter()-start<300;assert g['slot']==i;root=inputs[g['context']][g['family']];assert sha(root['rules'])==root['rules_sha'];s=GameSession(compile_ruleset_for_execution(deserialize_ruleset(Path(root['rules']).read_text())));assert hashlib.sha256(repr(s.state).encode()).hexdigest()==root['state_sha'];actions=deserialize_game_record(json.dumps(g['record'])).actions;mm=ms[i];assert len(actions)==g['moves']and len(mm)in(len(actions),len(actions)+1)
  for ply,a in enumerate(actions):
   m=mm[ply];assert m['ply']==ply and m['context']==g['context']and m['family']==g['family']and m['ratio']==g['ratio']and m['opponent_ratio']==g['opponent_ratio']and m['candidate_color']==g['candidate_color'];assert m['root_state_sha']==hashlib.sha256(repr(s.state).encode()).hexdigest()and m['side']==s.state.position.side_to_move and m['is_candidate']==(m['side']==g['candidate_color']);cfg=p['candidate'if m['is_candidate']else'opponent'];assert m['normal_visits']<=cfg['normal_nodes'];actors=sum(pc is not None for pc in s.state.position.board)
   if m['source']=='FIXED_LOW_INVENTORY_RANK_GUIDANCE':assert actors<=4 and m['normal_visits']==0
   elif m['source']=='FULL_SESSION_MATERIAL_SEARCH':assert actors>4;depths[(g['context'],m['is_candidate'],m['normal_depth'])]+=1
   sources[m['source']]+=1;s.submit(a);steps+=1;assert m['after_state_sha']==hashlib.sha256(repr(s.state).encode()).hexdigest()
  if len(mm)>len(actions):assert g['reason']=='NO_CHOICE_UNFINISHED'and mm[-1]['after_state_sha']==mm[-1]['root_state_sha']
  assert json.loads(serialize_game_record(s.to_record()))==g['record']and s.result.status.value==g['status']and s.result.winner==g['winner'];reward=None if s.result.status is SessionStatus.ONGOING else 0 if s.result.winner is None else 1 if s.result.winner==g['candidate_color']else-1;assert reward==g['reward'];assert g['outcome']==('U'if reward is None else'D'if reward==0 else'W'if reward==1 else'L')
 summary={};rng=np.random.default_rng(2026101677)
 for context in p['contexts']:
  index={(g['family'],g['ratio'],g['opponent_ratio'],g['candidate_color']):g for g in games if g['context']==context};families=defaultdict(list);orientations=defaultdict(list);unknownpairs=0
  for root in inputs[context].values():
   if root['split']!='DEV':continue
   parent=root.get('parent_family',root['family'])
   for foe in p['opponent_prices']:
    for role in p['candidate_colors']:
     a=index.get((root['family'],1.,foe,role));b=index.get((root['family'],2.,foe,role));lo,hi=-2.,2.
     if a is not None and b is not None and a['reward']is not None and b['reward']is not None:lo=hi=b['reward']-a['reward']
     else:unknownpairs+=1
     families[parent].append((lo,hi));orientations[root.get('orientation',0)].append((lo,hi))
  lows=np.array([sum(x[0]for x in vv)/len(vv)for _,vv in sorted(families.items())]);highs=np.array([sum(x[1]for x in vv)/len(vv)for _,vv in sorted(families.items())]);ci=None
  if unknownpairs==0:
   boot=lows[rng.integers(0,len(lows),size=(10000,len(lows)))].mean(axis=1);ci=[float(x)for x in np.quantile(boot,[.025,.975])]
  summary[context]=dict(original_independent_family_blocks=len(families),available_context_layouts=len(inputs[context]),planned_layouts=sum(r['split']=='DEV'for r in inputs[context].values()),unknown_or_missing_pairs=unknownpairs,profiles={str(r):dict(n=sum(g['ratio']==r for g in index.values()),WLDU=dict(Counter(g['outcome']for g in index.values()if g['ratio']==r)))for r in p['profiles']},paired_mean_gain_lower=float(lows.mean()),paired_mean_gain_upper=float(highs.mean()),descriptive_family_bootstrap95=ci,family_effect_bounds={str(k):[sum(x[0]for x in v)/len(v),sum(x[1]for x in v)/len(v)]for k,v in families.items()},orientation_effect_bounds={str(k):[sum(x[0]for x in v)/len(v),sum(x[1]for x in v)/len(v)]for k,v in orientations.items()})
 result=dict(status='PASS_CLOSED_PUBLIC_RECORD_REPLAY_ORIGINAL_FAMILY_BLOCKS',task=task,complete=done['status']=='COMPLETE',games=len(games),missing_slots=len(expected-actual),missing_slot_keys=sorted(expected-actual),actual_moves=steps,sources=dict(sources),normal_depth_counts=[dict(context=t,is_candidate=can,depth=d,count=n)for(t,can,d),n in depths.items()],summary=summary,seconds=time.perf_counter()-start,scope='No producer/refit ornewindependentoutcomes. D4orientations andseedcontexts are withinoriginalfamilyreplicates, notextraindependentfamilies. Bootstrapdescriptiveandconditional onfrozenpanel; missing/UNKNOWNretainfullrewardbounds, neverDRAW. Spatialtransformcontrolisnotdirectcausal tieintervention; seededprioritychangesordering/pruning aswellasties, actualdepthsretained.')
 with(OUT/f'task{task}-audit.json').open('x')as f:json.dump(result,f,indent=2)
 print(json.dumps({k:v for k,v in result.items()if k not in('missing_slot_keys','normal_depth_counts','sources')}))
if __name__=='__main__':run(int(sys.argv[1]))
