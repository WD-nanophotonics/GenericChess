"""Independent full-or-partial NEWNN direct-priority control consumer."""
from pathlib import Path
from collections import defaultdict,Counter
import json,hashlib,time,numpy as np
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record,serialize_game_record
from generic_chess.session.result import SessionStatus
from results.dev_aux.task2153.stop_evidence import EvidenceStopReader
OUT=Path('results/dev_aux/task2282')
def run():
 start=time.perf_counter();stop=EvidenceStopReader(Path.cwd());read=lambda p:json.loads(Path(p).read_text(encoding='utf-8-sig'));folder=Path('results/dev_aux/task2282');p=read(folder/'plan.json');done=read(folder/'completion.json');roots=read(folder/'inputs.json')['roots'];byroot={r['family']:r for r in roots};games=[json.loads(x)for x in(folder/'games.jsonl').read_text().splitlines()];moves=[json.loads(x)for x in(folder/'moves.jsonl').read_text().splitlines()];assert hashlib.sha256((folder/'inputs.json').read_bytes()).hexdigest()==p['inputs_sha'];assert hashlib.sha256((folder/'transfer.py').read_bytes()).hexdigest()==p['source_sha'];expected=[]
 for seed in p['seeds']:
  for root in roots:
   for foe in p['opponent_prices']:
    for role in p['candidate_colors']:
     profiles=p['profiles']if(root['family']+role)%2==0 else list(reversed(p['profiles']))
     for price in profiles:expected.append((seed,root['family'],price,foe,role))
 assert len(expected)==512 and [(g['context'],g['family'],g['ratio'],g['opponent_ratio'],g['candidate_color'])for g in games]==expected[:len(games)];assert len(games)==done['games']and len(moves)==done['decisions']and done['missing']==512-len(games)
 if done['status']=='COMPLETE':assert len(games)==512
 mm=defaultdict(list)
 for m in moves:mm[m['slot']].append(m)
 depths=Counter();sources=Counter();steps=0
 for slot,g in enumerate(games):
  stop();assert time.perf_counter()-start<240;assert g['slot']==slot;root=byroot[g['family']];assert root['split']=='TRAIN';c=compile_ruleset_for_execution(deserialize_ruleset(Path(root['rules']).read_text()));s=GameSession.replay(c,deserialize_game_record(json.dumps(root['record'])));prefix=s.to_record().actions;final=deserialize_game_record(json.dumps(g['record']));assert final.actions[:len(prefix)]==prefix;actions=final.actions[len(prefix):];assert len(actions)==g['moves']and len(mm[slot])in(len(actions),len(actions)+1)
  for i,(a,m)in enumerate(zip(actions,mm[slot])):
   assert m['ply']==i and m['context']==g['context']and m['family']==g['family']and m['ratio']==g['ratio']and m['opponent_ratio']==g['opponent_ratio']and m['candidate_color']==g['candidate_color'];assert m['root_state_sha']==hashlib.sha256(repr(s.state).encode()).hexdigest()and m['side']==s.state.position.side_to_move and m['is_candidate']==(m['side']==g['candidate_color']);cfg=p['candidate'if m['is_candidate']else'opponent'];assert m['normal_visits']<=cfg['normal_nodes'];s.submit(a);assert m['after_state_sha']==hashlib.sha256(repr(s.state).encode()).hexdigest();sources[(g['context'],m['source'])]+=1;depths[(g['context'],m['source'],m['normal_depth'])]+=1;steps+=1
  if len(mm[slot])>len(actions):assert mm[slot][-1]['root_state_sha']==mm[slot][-1]['after_state_sha']and g['reason']=='NO_CHOICE_UNFINISHED'
  reward=None if s.result.status is SessionStatus.ONGOING else 0 if s.result.winner is None else 1 if s.result.winner==g['candidate_color']else -1;assert reward==g['reward']and s.result.status.value==g['status']and s.result.winner==g['winner']and json.loads(serialize_game_record(s.to_record()))==g['record'];assert g['outcome']==('U'if reward is None else'D'if reward==0 else'W'if reward==1 else'L')
 idx={(g['context'],g['family'],g['ratio'],g['opponent_ratio'],g['candidate_color']):g for g in games};summary={};rng=np.random.default_rng(20261017782282)
 for seed in p['seeds']:
  effects=[];unknown=0
  for root in roots:
   bounds=[]
   for foe in p['opponent_prices']:
    for role in p['candidate_colors']:
     a=idx.get((seed,root['family'],1.,foe,role));b=idx.get((seed,root['family'],2.,foe,role))
     if a is None or b is None or a['reward']is None or b['reward']is None:bounds.append((-2.,2.));unknown+=1
     else:bounds.append((b['reward']-a['reward'],)*2)
   effects.append((sum(x[0]for x in bounds)/4,sum(x[1]for x in bounds)/4))
  lo=np.array([x[0]for x in effects]);hi=np.array([x[1]for x in effects]);ci=None
  if unknown==0:ci=[float(x)for x in np.quantile(lo[rng.integers(0,32,size=(10000,32))].mean(axis=1),[.025,.975])]
  summary[str(seed)]=dict(family_blocks=32,unknown_or_missing_pairs=unknown,net_lower=float(lo.mean()),net_upper=float(hi.mean()),descriptive95=ci,positive_families=int(sum(lo>0)),negative_families=int(sum(hi<0)),profiles={str(price):dict(Counter(g['outcome']for g in games if g['context']==seed and g['ratio']==price))for price in p['profiles']})
 result=dict(status='PASS_CLOSED_NN_DIRECT_PRIORITY_FULL_OR_PARTIAL_CONTROL',producer_status=done['status'],games=len(games),expected=512,missing=512-len(games),actual_moves=steps,summary=summary,normal_depths=[dict(seed=s,source=k,depth=d,count=n)for(s,k,d),n in depths.items()],seconds=time.perf_counter()-start,scope='ALL32TRAIN/newNNboundary2/2prefrozenseeds, exactsequence/fullactualprefixrecords/roles/limits/rewards/UNKNOWN. Separate32familyclustersperseed, NOT64independentfamilies. No fit/rootreplacement/DEVquery. Stableorderchangespruning/work; actualdepthretained. Descriptiveintervals withmissingfullbounds; notall-orderstability/universalmagnitude orcausallyisolatedtiebreakscore.')
 with(OUT/'audit.json').open('x')as f:json.dump(result,f,indent=2)
 print(json.dumps({k:v for k,v in result.items()if k!='normal_depths'}))
if __name__=='__main__':run()
