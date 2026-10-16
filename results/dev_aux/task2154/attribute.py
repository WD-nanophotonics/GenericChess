"""Posthoc paired trajectory/foe/initial-value attribution; never a new selector."""
from pathlib import Path
from collections import defaultdict,Counter
import json,time
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.session.session import GameSession
from results.dev_aux.task2068.teacher import CanonicalTeacher
OUT=Path('results/dev_aux/task2154')
def run():
 start=time.perf_counter();teacher=CanonicalTeacher('results/dev_aux/task2093','results/dev_aux/task2094','results/dev_aux/task2095');outputs={}
 for task in(2139,2149):
  root=Path(f'results/dev_aux/task{task}');p=json.loads((root/'plan.json').read_text(encoding='utf-8'));inputs=json.loads((root/'inputs.json').read_text(encoding='utf-8'))['roots'];gg=list(map(json.loads,(root/'games.jsonl').read_text(encoding='utf-8').splitlines()));moves=defaultdict(list)
  for m in map(json.loads,(root/'moves.jsonl').read_text(encoding='utf-8').splitlines()):moves[m['physical_id']].append(m)
  values={};initial=Counter();foes=defaultdict(Counter);groups=defaultdict(dict);paired=[];aggregate=Counter();outcomes=defaultdict(Counter)
  for inp in inputs:
   s=GameSession(compile_ruleset_for_execution(deserialize_ruleset(Path(inp['rules']).read_text(encoding='utf-8'))));v=teacher.label(s);assert v.quality=='EXACT_CANONICAL_FRESH_ROOT';values[inp['family']]=v.value;initial[inp['phase']+'_'+str(v.value)]+=1
  for g in gg:
   key=(g['phase'],g['family'],g['opponent_ratio'],g['candidate_side']);groups[key][g['ratio']]=g
   if g['phase']=='TRAIN':foes[str(g['opponent_ratio'])][str(g['ratio'])]+=g['score']
   vi=values[g['family']]if g['candidate_side']==0 else-values[g['family']]
   outcomes[g['phase']+'_price'+str(g['ratio'])][str(vi)+'->'+g['outcome']]+=1
  for key,prices in groups.items():
   baseline=prices[1.]
   for price,g in prices.items():
    if price==1.:continue
    a,b=moves[baseline['physical_id']],moves[g['physical_id']];i=next((i for i in range(min(len(a),len(b)))if a[i]['choice']!=b[i]['choice']),None)
    if i is None:
     assert baseline['record']==g['record']and baseline['score']==g['score'];category='IDENTICAL_ACTUAL_TRAJECTORY'
    else:
     assert a[i]['before_state_sha']==b[i]['before_state_sha']
     if a[i]['source']==b[i]['source']=='MATERIAL_SEARCH'and a[i]['completed_depth']==b[i]['completed_depth']==2:
      assert a[i]['side']==b[i]['side']==g['candidate_side'],'fixedopponentnormalfirstdivergenceatidenticalprefix'
      category='CANDIDATE_PRICE_NORMAL_COMPLETED2'
     else:category='PROOF_OR_OTHER_WALL_POLICY_DIVERGENCE'
    row=dict(phase=key[0],family=key[1],foe=key[2],candidate=key[3],price=price,category=category,first_different_ply=i,baseline_score=baseline['score'],candidate_score=g['score'],gain=g['score']-baseline['score'])
    if i is not None:row.update(baseline_source=a[i]['source'],candidate_source=b[i]['source'])
    paired.append(row);aggregate[category]+=1;aggregate['outcome_changed_pairs']+=row['gain']!=0
  outputs[str(task)]=dict(initial_root_WDL=dict(initial),TRAIN_score_sums_by_fixed_foe={k:dict(v)for k,v in foes.items()},first_difference_categories=dict(aggregate),canonical_initial_to_actual_outcomes={k:dict(v)for k,v in outcomes.items()},comparisons=paired)
 out=dict(status='PASS_POSTHOC_PAIRED_PRICE_TRAJECTORY_AND_FIXEDFOE_ATTRIBUTION',tasks=outputs,seconds=time.perf_counter()-start,scope='No new games/search/selection. CanonicalinitialrootWDL is exact; arbitraryplayedhistorypositionlabels NOTused. Allpairsrole/foefixed; identityreusesnotindependent. Firstnormaldecisiondivergence withcompleted2 is priceaction sensitivity, NOTbenefit. Aggregatezero can maskoppositefamily/foe contributions.')
 (OUT/'result.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps({t:{k:v for k,v in o.items()if k in('initial_root_WDL','TRAIN_score_sums_by_fixed_foe','first_difference_categories')}for t,o in outputs.items()}),flush=True)
if __name__=='__main__':run()
