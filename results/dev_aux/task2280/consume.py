"""Independent closed distribution/first-divergence and stored TRAINprobe audit."""
from pathlib import Path
from collections import Counter
from copy import copy
import json,time,hashlib
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.session.result import SessionStatus
from scripts.generic_proof_rnb_bridge import actor_state,uci,orbit
from results.dev_aux.task2153.stop_evidence import EvidenceStopReader
OUT=Path('results/dev_aux/task2280')
def key(b):return ''.join(b[:-1])+str(b[-1])
def run():
 assert not(OUT/'result.json').exists();start=time.perf_counter();stop=EvidenceStopReader(Path.cwd());labels={};read=lambda p:json.loads(Path(p).read_text(encoding='utf-8-sig'))
 for i,line in enumerate(Path('results/dev_aux/task2249/labels.jsonl').open(encoding='utf-8')):
  if i%1024==0:stop();assert time.perf_counter()-start<180
  r=json.loads(line);labels[key(r['board'])]=r
 value={'WIN':1,'DRAW':0,'LOSS':-1};roots={r['family']:r for r in read('results/dev_aux/task2258/inputs.json')['roots']};probe=[json.loads(x)for x in Path('results/dev_aux/task2259/queries.jsonl').read_text().splitlines()];assert len(probe)==160 and all(roots[q['family']]['split']=='TRAIN'for q in probe)
 for q in probe:
  stop();root=roots[q['family']];c=compile_ruleset_for_execution(deserialize_ruleset(Path(root['rules']).read_text()));s=GameSession.replay(c,deserialize_game_record(json.dumps(root['record'])));legal={uci(a):a for a in s.legal_actions()};assert q['action']in legal and q['normal_depth']==3 and q['visits']<=8192;s.submit(legal[q['action']]);assert -value[labels[key(actor_state(s.state))]['label']]==q['canonical_action_quality']
 children=0
 for r in read('results/dev_aux/task2270/inputs.json')['roots']:
  stop();c=compile_ruleset_for_execution(deserialize_ruleset(Path(r['rules']).read_text()));s=GameSession.replay(c,deserialize_game_record(json.dumps(r['record'])));assert len(s.to_record().actions)==1 and list(actor_state(s.state))==r['board']and hashlib.sha256(repr(s.state).encode()).hexdigest()==r['state_sha'];l=labels[key(actor_state(s.state))];assert l['label']==r['target_label']and l['rank']==r['canonical_rank'];assert r['group']==min(key(t)for t in orbit(tuple(r['board'])))and r['order_sha']==hashlib.sha256(('RN78-newfoe-validation:'+r['group']).encode()).hexdigest();utilities=[]
  for a in s.legal_actions():
   t=copy(s);t.submit(a);assert t.result.status is SessionStatus.ONGOING;utilities.append(-value[labels[key(actor_state(t.state))]['label']]);children+=1
  assert len(utilities)>=2 and len(set(utilities))>=2 and sorted(utilities)==sorted(r['target_action_utilities'])
 games=[json.loads(x)for x in Path('results/dev_aux/task2261/games.jsonl').read_text().splitlines()];idx={(g['phase'],g['family'],g['ratio'],g['opponent_ratio'],g['candidate_color']):g for g in games};pairs=read('results/dev_aux/task2278/pairs.json');assert len(pairs)==192;changes=Counter()
 for row in pairs:
  stop();assert time.perf_counter()-start<180;root=roots[row['family']];a=idx[(row['phase'],row['family'],1.,row['opponent_ratio'],row['candidate_color'])];b=idx[(row['phase'],row['family'],2.,row['opponent_ratio'],row['candidate_color'])];left=deserialize_game_record(json.dumps(a['record'])).actions;right=deserialize_game_record(json.dumps(b['record'])).actions;s=GameSession(compile_ruleset_for_execution(deserialize_ruleset(Path(root['rules']).read_text())));common=0
  for x,y in zip(left,right):
   if x!=y:break
   s.submit(x);common+=1
  assert row['common_total_plies']==common and row['actual_reward_delta']==b['reward']-a['reward']
  if row['diverged']:
   assert common<len(left)and common<len(right)and s.state.position.side_to_move==row['candidate_color'];quality=[]
   for child,action in zip(row['children'],[left[common],right[common]]):
    t=copy(s);t.submit(action);utility=-value[labels[key(actor_state(t.state))]['label']];assert utility==child['canonical_actor_utility']and uci(action)==child['action'];quality.append(utility)
   assert quality[1]-quality[0]==row['canonical_quality_delta'];changes[(row['phase'],quality[0],quality[1],row['actual_reward_delta'])]+=1
  else:assert left==right and a['reward']==b['reward']
 panels=[]
 for phase in ['TRAIN','DEV']:
  for label in ['WIN','DRAW']:
   for price in [1.,2.]:
    rr=[g for g in games if g['phase']==phase and g['ratio']==price and roots[g['family']]['target_label']==label];panels.append(dict(phase=phase,reference_root_label=label,price=price,games=len(rr),actual_outcomes=dict(Counter(g['outcome']for g in rr)),net_W_minus_L=sum(g['reward']for g in rr)))
 result=dict(status='PASS_STORED_TRAIN_PROBE_NEW_PREFIXES_AND_192_FIRST_DIFFERENCES',stored_probe_calls=160,new_validation_roots=32,new_validation_actual_children=children,closed_pairs=192,contingency=[dict(phase=p,canonical_before=a,canonical_after=b,actual_reward_delta=d,count=n)for(p,a,b,d),n in sorted(changes.items())],root_strata=panels,seconds=time.perf_counter()-start,scope='No price/proof/player producers. Independentactualfullroot/legality/canonicalquality/existingclosedrecorddivergences. Allqualityimprovements atfirstdivergence are LOSS(-1)->DRAW(0), NONEreferenceWINchildren, so no newpositiveproofneeded. Reference0notactualDRAWreward; posthocassociationnotcausalmediation. New32conditionalmu predicates andstored160TRAINcalls checked, no unseenrule/human/metricpriceclaim.')
 (OUT/'result.json').write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items()if k not in('contingency','root_strata')}))
if __name__=='__main__':run()
