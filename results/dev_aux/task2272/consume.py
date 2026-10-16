"""Independent NEWfamilies/newfoes fixed-price validation; no fit producer."""
from pathlib import Path
from collections import Counter,defaultdict
import json,hashlib,time,numpy as np
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record,serialize_game_record
from generic_chess.session.result import SessionStatus
from scripts.generic_session_win_proof import SessionChoice
from results.dev_aux.task2175.receipt import choice_value
from results.dev_aux.task2153.stop_evidence import EvidenceStopReader
OUT=Path('results/dev_aux/task2272')
def run():
 assert not (OUT/'result.json').exists();start=time.perf_counter();stop=EvidenceStopReader(Path.cwd());folder=Path('results/dev_aux/task2271');read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'));p=read(folder/'plan.json');done=read(folder/'completion.json');roots=read(folder/'inputs.json')['roots'];byroot={r['family']:r for r in roots};freeze=read(folder/'selected-price-freeze.json');sha=lambda x:hashlib.sha256(Path(x).read_bytes()).hexdigest()
 assert freeze['prices']==p['grid']==[1.,2.] and freeze['opponents']==p['opponents']==[1.5,4.] and freeze['new_queries_before_freeze']==0 and sha(freeze['source_TRAIN_selection'])==freeze['source_TRAIN_sha'];assert sha(folder/'inputs.json')==p['inputs_sha'];assert all(sha(k)==v for k,v in p['pins'].items())
 prior={r['group'] for task in (2251,2257,2258) for r in read(Path(f'results/dev_aux/task{task}/inputs.json'))['roots']};assert len(roots)==32 and len({r['group']for r in roots})==32 and not ({r['group']for r in roots}&prior)
 games=[json.loads(x)for x in(folder/'games.jsonl').read_text().splitlines()];moves=[json.loads(x)for x in(folder/'moves.jsonl').read_text().splitlines()];expected=[]
 for root in roots:
  assert root['split']=='VALIDATION'
  for fi,foe in enumerate(p['opponents']):
   for role in (0,1):
    off=(root['family']+fi+role)%2;grid=p['grid'][off:]+p['grid'][:off]
    for ratio in grid:expected.append((root['family'],ratio,foe,role))
 assert len(expected)==256 and [(g['family'],g['ratio'],g['opponent_ratio'],g['candidate_color'])for g in games]==expected[:len(games)]
 assert done['games']==len(games) and done['decisions']==len(moves)
 if done['status']=='COMPLETE':assert len(games)==256
 mm=defaultdict(list)
 for m in moves:mm[m['slot']].append(m)
 sources=Counter();depths=Counter();steps=0
 for slot,g in enumerate(games):
  stop();assert time.perf_counter()-start<240;root=byroot[g['family']];assert g['slot']==slot and g['phase']=='VALIDATION' and sha(root['rules'])==root['rules_sha'];c=compile_ruleset_for_execution(deserialize_ruleset(Path(root['rules']).read_text()));s=GameSession.replay(c,deserialize_game_record(json.dumps(root['record'])));prefix=s.to_record().actions;final=deserialize_game_record(json.dumps(g['record']));assert final.actions[:len(prefix)]==prefix;actions=final.actions[len(prefix):];assert len(actions)==g['moves'] and len(mm[slot]) in (len(actions),len(actions)+1)
  for i,(action,m)in enumerate(zip(actions,mm[slot])):
   assert m['ply']==i and m['phase']=='VALIDATION' and m['family']==g['family'] and m['ratio']==g['ratio'] and m['opponent_ratio']==g['opponent_ratio'] and m['candidate_color']==g['candidate_color'];assert m['root_state_sha']==hashlib.sha256(repr(s.state).encode()).hexdigest() and m['side']==s.state.position.side_to_move and m['is_candidate']==(m['side']==g['candidate_color']);assert m['choice']==choice_value(SessionChoice('ACTION',action=action)) and m['normal_visits']<=8192 and not m['finite_WIN_certificate'];s.submit(action);assert m['after_state_sha']==hashlib.sha256(repr(s.state).encode()).hexdigest();sources[m['source']]+=1;depths[(m['source'],m['normal_completed_depth'])]+=1;steps+=1
  if len(mm[slot])>len(actions):assert mm[slot][-1]['choice']is None
  assert json.loads(serialize_game_record(s.to_record()))==g['record'];reward=None if s.result.status is SessionStatus.ONGOING else 0 if s.result.winner is None else 1 if s.result.winner==g['candidate_color']else -1;assert reward==g['reward'] and s.result.status.value==g['actual_status'] and s.result.winner==g['winner'];assert g['outcome']==('U'if reward is None else'D'if reward==0 else'W'if reward==1 else'L')
 idx={(g['family'],g['ratio'],g['opponent_ratio'],g['candidate_color']):g for g in games};rng=np.random.default_rng(20261017782772);contrasts={}
 for foes in [[1.5,4.],[1.5],[4.]]:
  values=[];missing=0
  for root in roots:
   bounds=[]
   for foe in foes:
    for role in (0,1):
     a=idx.get((root['family'],1.,foe,role));b=idx.get((root['family'],2.,foe,role))
     if a is None or b is None or a['reward']is None or b['reward']is None:bounds.append((-2.,2.));missing+=1
     else:bounds.append((b['reward']-a['reward'],)*2)
   values.append((sum(v[0]for v in bounds)/len(bounds),sum(v[1]for v in bounds)/len(bounds)))
  lo=np.array([v[0]for v in values]);hi=np.array([v[1]for v in values]);ci=None
  if missing==0:ci=[float(v)for v in np.quantile(lo[rng.integers(0,32,size=(10000,32))].mean(axis=1),[.025,.975])]
  contrasts[str(foes)]=dict(family_blocks=32,missing_or_unknown_pairs=missing,net_lower=float(lo.mean()),net_upper=float(hi.mean()),descriptive95=ci,positive_families=int(sum(lo>0)),negative_families=int(sum(hi<0)),zero_families=int(sum((lo==0)&(hi==0))))
 result=dict(status='PASS_NEW32_FAMILIES_NEW_FOES_FIXED_PRICE_VALIDATION',producer_status=done['status'],games=len(games),planned=256,missing=256-len(games),moves=steps,profiles={str(r):dict(Counter(g['outcome']for g in games if g['ratio']==r))for r in p['grid']},contrasts=contrasts,sources=dict(sources),normal_depths=[dict(source=s,depth=d,count=n)for(s,d),n in depths.items()],seconds=time.perf_counter()-start,scope='Independentexactslots/neworbitexclusions/selectedTRAINhash/pins/fullactualprefixrecords/moves/W-L/UNKNOWN andfamilyclustercontrasts. ALLnewprice-unqueried32families andfoes1.5/4, no fit/selector/producer. Conditionalreference-exposedmu/prepaidguideonly, notgenericonlineproof oruniversalmagnitude. Missing/unknownretainfullbounds; CIdescriptiveonly.')
 with(OUT/'result.json').open('x')as f:json.dump(result,f,indent=2)
 print(json.dumps({k:v for k,v in result.items()if k not in('normal_depths','sources')}))
if __name__=='__main__':run()
