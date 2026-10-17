"""Matched fixed-opponent policy shift, allmodels/checkpoints retained."""
from pathlib import Path
from collections import Counter
from dataclasses import replace
import json,time
from generic_chess.rules.compiler import compile_ruleset
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.session.session import GameSession
D=Path('results/dev_aux/task2529');T=Path('results/dev_aux/task2527')
def run():
 start=time.perf_counter();a=json.loads((D/'evaluation-audit.json').read_text());b=json.loads((D/'foe-audit.json').read_text());p=json.loads(Path('results/dev_aux/task2528/plan.json').read_text());q=json.loads(Path('results/dev_aux/task2531/plan.json').read_text());assert p['slots']==q['slots']and p['families']==q['families']and p['ordering_seed_offset']==q['ordering_seed_offset'];assert all(p[k]==q[k]for k in('H','depth','nodes_per_query','seconds_per_query','prefix_plies','training'))
 def rows(task):
  return{tuple(r['slot']):r for line in Path(f'results/dev_aux/{task}/games.jsonl').open()if(r:=json.loads(line))}
 x=rows('task2528');y=rows('task2531');cc={gs:compile_ruleset(ruleset_from_dict(json.loads((T/f'rules-{gs}.json').read_text())))for gs in p['generator_seeds']if(T/f'rules-{gs}.json').exists()};counts=Counter()
 for slot in p['slots']:
  key=tuple(slot);u=x.get(key);v=y.get(key)
  if u is None or v is None:counts['missing_pair']+=1;continue
  assert u['initial_record']==v['initial_record']and u['weights']==v['weights']and u['channels']==v['channels'];uu=deserialize_game_record(json.dumps(u['record']));vv=deserialize_game_record(json.dumps(v['record']));i=next((i for i,(c,d)in enumerate(zip(uu.actions,vv.actions))if c!=d),None)
  if i is None:
   if uu.actions==vv.actions:counts['identical_full_records']+=1
   else:assert u['reward']is None or v['reward']is None;counts['censor_strict_prefix']+=1
  else:
   s=GameSession.replay(cc[slot[0]],replace(uu,actions=uu.actions[:i],resigned_by=None,declaration=None));assert s.state.position.side_to_move!=slot[3];counts['foe_first_difference']+=1
 result=dict(status='PASS_MATCHED_FIXED_OPPONENT_SWITCH',planned=len(p['slots']),counts=dict(counts),interaction_curves=[dict(level=u['level'],foe_minus_uniform_gain_bounds=[v['pooled_gain_bounds'][0]-u['pooled_gain_bounds'][1],v['pooled_gain_bounds'][1]-u['pooled_gain_bounds'][0]])for u,v in zip(a['curves'],b['curves'])],scope='ALLsamefamilies/roles/checkpoints/weights/queryconditions; firstactualdivergencesonFOEturn. U/missingconservativeboundarithmetic, notimputedoutcomes. SamefourTRAIN-exposedrules/fourbindingfamilies, notindependentnewfamilyreplication; randomfoeNOTknownstronger. DifferenceinlearningbenefitunderTWOfixedopponents, notuniversalpolicyrobustness/equivalence.',seconds=time.perf_counter()-start);(D/'foe-shift.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
if __name__=='__main__':run()
