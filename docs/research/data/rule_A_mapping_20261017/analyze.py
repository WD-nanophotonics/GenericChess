"""Exact physical bounds and coupled-recipient family uncertainty for the adaptive recipe."""
from pathlib import Path
from collections import Counter,defaultdict
import sys,json,random,time,os
R=Path.cwd();sys.path.insert(0,str(R));from tools.local_agent.common import write_json
D=R/'.local_agent/rule-aware-utility-20261017';started=time.perf_counter();p=json.loads((D/'plan.json').read_bytes());done=json.loads((D/'result.json').read_bytes());physical={g['slot']:g for g in map(json.loads,(D/'games.jsonl').read_bytes().splitlines())};slots=json.loads((D/'slots.json').read_bytes())['slots'];by={}
for i,key in enumerate(slots):by[tuple(key)]=physical.get(i,dict(slot=i,rule=key[0],family=key[1],label=key[2],candidate_owner=key[3],foe=key[4],reward=None,record=None,ending='UNSTARTED_UNKNOWN'))
assert len(by)==len(slots)==3264

def bound(pairs):
 coeff=Counter();seen={}
 for a,b in pairs:
  for k,g in [(1,a),(-1,b)]:coeff[g['slot']]+=k*(1 if g['candidate_owner']==0 else -1);seen[g['slot']]=g
 known=radius=0
 for slot,c in coeff.items():
  g=seen[slot]
  if g['reward']is None:radius+=abs(c)
  else:known+=c*g['reward']*(1 if g['candidate_owner']==0 else -1)
 return [(known-radius)/len(pairs),(known+radius)/len(pairs)]
rows=[]
for foe in p['foes']:
 for method in ['fixed5','free6']:
  for comp in ['mapped-direct','static-mapped','static-direct']:
   pairs=[];groups=defaultdict(list)
   for rid,v in p['variants'].items():
    for f in p['families']:
     for seed in p['seeds']:
      for owner in (0,1):
       left='mapped_'+method+str(seed)if comp=='mapped-direct'else'rule_static_v2';right=method+str(seed)if comp!='static-mapped'else'mapped_'+method+str(seed);a=by[rid,f,left,owner,foe];b=by[rid,f,right,owner,foe];pairs.append((a,b));groups[v['recipient'],f].append((a,b))
   gb={k:bound(v)for k,v in groups.items()};rng=random.Random(2026101724);bb=[]
   for _ in range(2000):
    selected=[gb[g,rng.choice(p['families'])]for g in sorted({v['recipient']for v in p['variants'].values()})for _ in p['families']];bb.append([sum(x[j]for x in selected)/len(selected)for j in (0,1)])
   rows.append(dict(foe=foe,method=method,contrast=comp,pairs=len(pairs),bounds=bound(pairs),conditional_recipient_family_95_envelope=[sorted(x[0]for x in bb)[49],sorted(x[1]for x in bb)[1949]],by_role={str(c):bound([(a,b)for a,b in pairs if a['candidate_owner']==c])for c in (0,1)},by_seed={str(seed):bound([(a,b)for a,b in pairs if a['label'].endswith(str(seed))or b['label'].endswith(str(seed))])for seed in p['seeds']},by_variant={rid:bound([(a,b)for a,b in pairs if a['rule']==rid])for rid in p['rules']},same_full_record_pairs=sum(a['record']is not None and a['record']==b['record']for a,b in pairs)))
counts=Counter();caller=kernel=0.
for line in (D/'queries.jsonl').open():
 q=json.loads(line);counts['queries']+=1;counts['nodes']+=q['nodes'];counts['fallbacks']+=q['used_fallback'];counts['completedD2']+=q['completed_depth']==2;caller+=q['caller_seconds'];kernel+=q['kernel_seconds']
write_json(D/'analysis.json',dict(status='COMPLETE_ADAPTIVE_RULE_A_MAPPING_UTILITY'if len(physical)==3264 and done['status']=='COMPLETE'else'PARTIAL_ALL_PLANNED_SLOTS_RETAINED',planned=3264,actual=len(physical),missing=3264-len(physical),unknown=sum(g['reward']is None for g in physical.values()),contrasts=rows,query_counts=dict(counts),caller_seconds=caller,kernel_seconds=kernel,seconds=time.perf_counter()-started,scope='SeparateADAPTIVEfresh291001..4 utilityfollowupafter96feasibility/earlier7040study; all12nonidentityvariants/4sourceinitials/2methods/2roles/2foes andstatic, noUnitcandidate/virtualcopy. ActualallphysicalUNKNOWN andmissing[-1,+1], repeatedstaticcoefficients combinedBEFOREbounds.16recipient-familyresamplesKEEPall3donors/allseeds/roles, fourfixedsourcecontexts notpopulationconfidence. No parameterfit/bestseed/default/oldcaprefill/newlearner. Requestedlimits equal,actualwork/costmeasured.'))
for r in rows:print(r['foe'],r['method'],r['contrast'],r['bounds'],r['conditional_recipient_family_95_envelope'])
