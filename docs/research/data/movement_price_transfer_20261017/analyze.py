"""Coupled actual-outcome analysis for the prospectively frozen mature comparator."""
from pathlib import Path
from collections import defaultdict,Counter
import json,sys,random,time
R=Path.cwd();sys.path.insert(0,str(R));from tools.local_agent.common import write_json
D=R/'.local_agent/movement-transfer-20261017';start=time.perf_counter();p=json.loads((D/'plan.json').read_bytes());done=json.loads((D/'result.json').read_bytes());physical={r['slot']:r for r in map(json.loads,(D/'games.jsonl').read_bytes().splitlines())};slots=json.loads((D/'slots.json').read_bytes())['slots'];logical={}
for slot,(gs,f,label,owner,foe)in enumerate(slots):
 g=physical.get(slot,dict(slot=slot,rule=gs,family=f,label=label,candidate_owner=owner,foe=foe,reward=None,record=None,ending='UNSTARTED_UNKNOWN',queries=0,nodes=0));logical[gs,f,label,owner,foe]=g
 if label=='unit'and foe=='uniform':
  z=dict(g,candidate_owner=1,reward=None if g['reward']is None else-g['reward'],logical_role_copy_only=True);logical[gs,f,label,1,foe]=z
assert len(logical)==7168

def bound(pairs):
 coeff=defaultdict(int);byid={}
 for left,right in pairs:
  for sign,g in((1,left),(-1,right)):
   coeff[g['slot']]+=sign*(1 if g['candidate_owner']==0 else -1);byid[g['slot']]=physical.get(g['slot'],g)
 known=radius=0
 for k,c in coeff.items():
  g=byid[k]
  if g['reward']is None:radius+=abs(c)
  else:known+=c*g['reward']*(1 if g['candidate_owner']==0 else-1)
 n=len(pairs);return [(known-radius)/n,(known+radius)/n]
summary=[]
for foe in p['foes']:
 for label in p['profiles']:
  rows=[g for (gs,f,t,o,v),g in logical.items()if t==label and v==foe];counts=Counter('U'if r['reward']is None else'W'if r['reward']==1 else'L'if r['reward']==-1 else'D'for r in rows);summary.append(dict(foe=foe,label=label,cells=len(rows),outcomes=dict(counts),known_reward_sum=sum(r['reward']or 0 for r in rows),physical_slots=len({r['slot']for r in rows})))
specs=[('static-unit',['rule_static_v2'],['unit']),('fixed-initial',['fixed5'+str(s)for s in p['seeds']],['initial'+str(s)for s in p['seeds']]),('free-initial',['free6'+str(s)for s in p['seeds']],['initial'+str(s)for s in p['seeds']]),('free-fixed',['free6'+str(s)for s in p['seeds']],['fixed5'+str(s)for s in p['seeds']]),('static-fixed',['rule_static_v2']*4,['fixed5'+str(s)for s in p['seeds']]),('static-free',['rule_static_v2']*4,['free6'+str(s)for s in p['seeds']])];contrasts=[];divergences=[]
for foe in p['foes']:
 for name,lefts,rights in specs:
  pairs=[];groups=defaultdict(list);counts=Counter()
  for left,right in zip(lefts,rights):
   for gs in p['rules']:
    for family in p['families']:
     for owner in(0,1):
      a=logical[gs,family,left,owner,foe];b=logical[gs,family,right,owner,foe];pair=(a,b);pairs.append(pair);groups[gs,family].append(pair);counts['same_full_records']+=a['record']is not None and a['record']==b['record'];known=a['reward']is not None and b['reward']is not None;counts['resolved_pairs']+=known;counts['resolved_better']+=known and a['reward']>b['reward'];counts['resolved_worse']+=known and a['reward']<b['reward']
      if a['record']is not None and b['record']is not None and a['record']!=b['record']:
       aa=a['record']['actions'];bb=b['record']['actions'];first=next((i for i,(x,y)in enumerate(zip(aa,bb))if x!=y),None)
       if first is not None:assert first%2==owner,'Firstdiffonfixedfoeturn';divergences.append(dict(foe=foe,comparison=name,rule=gs,family=family,owner=owner,left=left,right=right,left_slot=a['slot'],right_slot=b['slot'],absolute_ply=first))
       else:counts['length_only_differences']+=1
  # Physical games from different rule/family groups are disjoint; reuse remains
  # inside each group. Sample entire family groups including ALL seeds/roles.
  group_bounds={k:bound(v)for k,v in groups.items()};rng=random.Random(2026101719);boot=[]
  for _ in range(2000):
   selected=[]
   for recipient in sorted({v['recipient'] for v in p['variants'].values()}):
    for _ in p['families']:
     family=rng.choice(p['families']);selected.extend(group_bounds[gs,family] for gs in p['rules'] if p['variants'][gs]['recipient']==recipient)
   boot.append([sum(z[j]for z in selected)/len(selected)for j in(0,1)])
  low=sorted(x[0]for x in boot);high=sorted(x[1]for x in boot);contrasts.append(dict(foe=foe,name=name,pairs=len(pairs),bounds=bound(pairs),conditional_fixed_rules_fixed_seeds_family_95_envelope=[low[49],high[1949]],per_rule={str(gs):bound([x for x in pairs if x[0]['rule']==gs])for gs in p['rules']},counts=dict(counts),scope='UNKNOWNphysicalvariables[-1,+1]; explicitUnitoppositerolereusecoefficientsaggregatedbeforebounds. Staticrepeatedacrossseedcontrastsnotindependentobservations. 2000recipient-familyresamplesretainALL4donors/FOURfixedinitials, notpopulationconfidence/newmovementingredients/uniqueprice/equivalence.'))
qcounts=Counter();kernel=caller=maximum=0.;depths=Counter()
for line in(D/'queries.jsonl').open():
 q=json.loads(line);qcounts['queries']+=1;qcounts['fallbacks']+=q['used_fallback'];qcounts['nodes']+=q['nodes'];depths[q['completed_depth']]+=1;kernel+=q['kernel_seconds'];caller+=q['caller_seconds'];maximum=max(maximum,q['caller_seconds'])
result=dict(status='COMPLETE_FROZEN_SERVED_CANDIDATE_ANALYSIS'if done['status']=='COMPLETE'else'PARTIAL_FROZEN_ALLSLOTS_RETAINED',planned_physical=7040,returned_physical=len(physical),logical_cells=len(logical),profiles=summary,contrasts=contrasts,query_counts=dict(qcounts),depths=dict(depths),kernel_seconds=kernel,caller_seconds=caller,max_caller_seconds=maximum,first_divergences=len(divergences),all_first_action_differences_on_candidate_turn=True,seconds=time.perf_counter()-start,scope='NewcommonNative256served-candidate diagnostic. No oldAUXfitnessrerun/alltrajectoryfloatidentity/modelselection/default/fit/AUXwrites. Fullrules/history retained within16predeclaredmovementvariants/4exposedrecipients; originalcaps/missing/U retained. Costsnotcompleteengineering/tokenorstrongersearch/WDLproof.');write_json(D/'analysis.json',result);write_json(D/'first-divergences.json',dict(rows=divergences));print(json.dumps({k:v for k,v in result.items()if k not in('profiles','contrasts')}));print(json.dumps(contrasts,indent=2))
