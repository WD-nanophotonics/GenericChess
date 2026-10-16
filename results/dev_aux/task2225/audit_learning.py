"""Independent journal/actual Session/selection consumer and paired statistics."""
from pathlib import Path
from collections import Counter,defaultdict
import json,time,hashlib,sys,importlib,numpy as np
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record,serialize_game_record
from generic_chess.session.result import SessionStatus
from scripts.generic_session_win_proof import SessionChoice
from scripts.generic_proof_rnb_bridge import orbit
from results.dev_aux.task2175.receipt import choice_value
OUT=Path('results/dev_aux/task2225')
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def audit(task):
 folder=Path(f'results/dev_aux/task{task}');p=read(folder/'plan.json');done=read(folder/'completion.json');inp=read(folder/'inputs.json');roots={r['family']:r for r in inp['roots']};rows=[json.loads(l)for l in(folder/'games.jsonl').read_text().splitlines()];moves=[json.loads(l)for l in(folder/'moves.jsonl').read_text().splitlines()];module=importlib.import_module(f'results.dev_aux.task{task}.study')
 assert done['status']=='COMPLETE'and len(rows)==done['games']and len(moves)==done['decisions'];assert [r['slot']for r in rows]==list(range(len(rows)))
 assert sha(folder/'inputs.json')==p['inputs_sha']
 for name,digest in p['pins'].items():assert sha(name)==digest
 tr=[g for g in rows if g['phase']=='TRAIN'];dev=[g for g in rows if g['phase']=='DEV'];assert len(tr)==p['expected_TRAIN_games']and all(g['phase']=='TRAIN'for g in rows[:len(tr)])
 selection=module.select(tr,p);assert selection==read(folder/'TRAIN-selection.json');freeze=read(folder/'DEV-profile-freeze.json');assert sha(folder/'TRAIN-selection.json')==freeze['selection_sha']
 raw=(folder/'games.jsonl').read_bytes().splitlines(keepends=True);assert hashlib.sha256(b''.join(raw[:len(tr)])).hexdigest()==freeze['TRAIN_journal_sha'];assert freeze['DEV_queries_before_freeze']==0 and len(dev)==freeze['expected_games']
 train_groups={r['group']for r in inp['roots']if r['split']=='TRAIN'};dev_groups={r['group']for r in inp['roots']if r['split']=='DEV'};assert not(train_groups&dev_groups)
 expected={(r['family'],ratio,foe,role)for r in inp['roots']if r['split']=='TRAIN'for ratio in p['grid']for foe in p['opponents']for role in(0,1)}
 assert {(g['family'],g['ratio'],g['opponent_ratio'],g['candidate_color'])for g in tr}==expected
 expected={(r['family'],ratio,foe,role)for r in inp['roots']if r['split']=='DEV'for ratio in freeze['profiles']for foe in p['opponents']for role in(0,1)}
 assert {(g['family'],g['ratio'],g['opponent_ratio'],g['candidate_color'])for g in dev}==expected
 byslot=defaultdict(list)
 for m in moves:byslot[m['slot']].append(m)
 count=0;sources=Counter();terminals=Counter();depths=Counter();replay_start=time.perf_counter()
 for g in rows:
  root=roots[g['family']];assert root['split']==g['phase']and sha(root['rules'])==root['rules_sha'];c=compile_ruleset_for_execution(deserialize_ruleset(Path(root['rules']).read_text()));s=GameSession(c);assert hashlib.sha256(repr(s.state).encode()).hexdigest()==root['state_sha'];actions=deserialize_game_record(json.dumps(g['record'])).actions;ms=byslot[g['slot']]
  assert len(actions)==g['moves']and len(ms)==len(actions)
  for i,(a,m)in enumerate(zip(actions,ms)):
   assert m['ply']==i and m['family']==g['family']and m['ratio']==g['ratio']and m['opponent_ratio']==g['opponent_ratio']and m['candidate_color']==g['candidate_color']
   assert m['root_state_sha']==hashlib.sha256(repr(s.state).encode()).hexdigest()and m['side']==s.state.position.side_to_move and m['is_candidate']==(m['side']==g['candidate_color'])
   assert choice_value(SessionChoice('ACTION',action=a))==m['choice']and m['finite_WIN_certificate']is False
   actor_count=sum(pc is not None for pc in s.state.position.board);assert actor_count==m['actor_count']
   if m['source']=='FIXED_LOW_INVENTORY_RANK_GUIDANCE':assert actor_count<=4 and m['normal_visits']==0
   else:assert actor_count>4 and m['normal_visits']<=p['normal_nodes']and(m['normal_completed_depth']or 0)<=p['normal_depth']
   s.submit(a);assert m['after_state_sha']==hashlib.sha256(repr(s.state).encode()).hexdigest();assert m['actual_result']==dict(status=s.result.status.value,winner=s.result.winner);sources[m['source']]+=1;depths[str(m['normal_completed_depth'])]+=1;count+=1
  assert json.loads(serialize_game_record(s.to_record()))==g['record']and s.result.status.value==g['actual_status']and s.result.winner==g['winner']
  expected_reward=None if s.result.status is SessionStatus.ONGOING else 0 if s.result.winner is None else 1 if s.result.winner==g['candidate_color']else-1
  assert expected_reward==g['reward'];terminals[g['actual_status']]+=1
 # Only finite tested-grid trajectory equivalence, never a continuum/unique ratio.
 indexed={(g['family'],g['ratio'],g['opponent_ratio'],g['candidate_color']):g for g in tr};plateaus=[]
 for a,b in((.25,.5),(2.,4.)):
  pairs=[(g,indexed[(g['family'],b,g['opponent_ratio'],g['candidate_color'])])for g in tr if g['ratio']==a]
  plateaus.append(dict(prices=[a,b],pairs=len(pairs),identical_records=sum(x['record']==y['record']for x,y in pairs),identical_actual_outcomes=sum(x['reward']==y['reward']for x,y in pairs)))
 ratios={}
 for phase,data in(('TRAIN',tr),('DEV',dev)):
  ratios[phase]={str(r):dict(n=sum(g['ratio']==r for g in data),WLDU={o:sum(g['ratio']==r and g['outcome']==o for g in data)for o in'WLDU'},mean_W_minus_L=sum(g['reward']or 0 for g in data if g['ratio']==r)/sum(g['ratio']==r for g in data))for r in sorted({g['ratio']for g in data})}
 # Paired family blocks retain foe/color dependence; descriptive resampling only.
 profiles=freeze['profiles'];baseline={ (g['family'],g['opponent_ratio'],g['candidate_color']):g for g in dev if g['ratio']==1.};paired={};rng=np.random.default_rng(2026101676)
 for ratio in profiles:
  families=defaultdict(list)
  for g in dev:
   if g['ratio']!=ratio:continue
   b=baseline[(g['family'],g['opponent_ratio'],g['candidate_color'])];assert g['reward']is not None and b['reward']is not None;families[g['family']].append(g['reward']-b['reward'])
  values=np.array([sum(v)/len(v)for _,v in sorted(families.items())]);boot=values[rng.integers(0,len(values),size=(10000,len(values)))].mean(axis=1)
  paired[str(ratio)]=dict(family_effects={str(k):sum(v)/len(v)for k,v in families.items()},mean=float(values.mean()),descriptive_family_bootstrap95=[float(x)for x in np.quantile(boot,[.025,.975])],positive=int((values>0).sum()),negative=int((values<0).sum()),zero=int((values==0).sum()))
 return dict(status='PASS_ACTUAL_RECORDS_ALL_MOVES_SELECTION_AND_SPLIT',task=task,games=len(rows),actual_moves=count,public_replay_seconds=time.perf_counter()-replay_start,sources=dict(sources),actual_terminals=dict(terminals),normal_completed_depths=dict(depths),plateau_trajectories=plateaus,ratios=ratios,DEV_paired_vs_unity=paired,scope='Independentclosedjournal/publicSessionreplay, notnewstatisticalgames. Actualrulemaxply96/repetition;guideisfixedACTIONpolicyNOTWINcertificate/reward. Price-unqueriedDEVwithinoneexposedrule/structuralmu, notnewruleholdout. Familybootstrapdescriptive, dependencebeyondD4/colorsandcost/timinglimits remain; no universaluniquepriceorcontinuumequivalence.')
if __name__=='__main__':
 task=int(sys.argv[1]);result=audit(task)
 with(OUT/f'task{task}-audit.json').open('x',encoding='utf-8')as f:json.dump(result,f,indent=2)
 print(json.dumps({k:result[k]for k in('status','games','actual_moves','public_replay_seconds','DEV_paired_vs_unity')}))
