"""Frozen movement-transfer cohorts and linked-family intervals; no search/training."""
from pathlib import Path
from collections import defaultdict,Counter
import json,sys,random,time,os
R=Path.cwd();sys.path.insert(0,str(R));D=R/'.local_agent/movement-transfer-20261017';STOP=Path(os.environ.get('GC_REPLAY_STOP_ROOT',str(R)))
from tools.local_agent.common import write_json
start=time.perf_counter();p=json.loads((D/'plan.json').read_bytes());physical={g['slot']:g for g in map(json.loads,(D/'games.jsonl').read_bytes().splitlines())};slots=json.loads((D/'slots.json').read_bytes())['slots'];logical={}
assert len(physical)==len(slots)==7040
for i,(rid,f,label,owner,foe)in enumerate(slots):
 g=physical[i];logical[rid,f,label,owner,foe]=g
 if label=='unit'and foe=='uniform':logical[rid,f,label,1,foe]=dict(g,candidate_owner=1,reward=None if g['reward']is None else -g['reward'])
assert len(logical)==7168

def bound(groups):
 coeff=defaultdict(int);n=0
 for terms in groups:
  n+=1
  for c,g in terms:coeff[g['slot']]+=c*(1 if g['candidate_owner']==0 else -1)
 known=radius=0
 for slot,c in coeff.items():
  g=physical[slot]
  if g['reward']is None:radius+=abs(c)
  else:known+=c*g['reward']*(1 if g['candidate_owner']==0 else -1)
 return [(known-radius)/n,(known+radius)/n]

def envelope(groups,seed):
 by=defaultdict(list)
 for recipient,f,terms in groups:by[recipient,f].append(terms)
 bb={k:bound(v)for k,v in by.items()};rng=random.Random(seed);out=[]
 for _ in range(2000):
  selected=[bb[recipient,rng.choice(p['families'])]for recipient in sorted({v['recipient']for v in p['variants'].values()})for _ in p['families']]
  out.append([sum(x[j]for x in selected)/len(selected)for j in (0,1)])
 return [sorted(x[0]for x in out)[49],sorted(x[1]for x in out)[1949]]

rows=[];specs=[('static-unit',['rule_static_v2'],['unit']),('fixed-initial',['fixed5'+str(s)for s in p['seeds']],['initial'+str(s)for s in p['seeds']]),('free-initial',['free6'+str(s)for s in p['seeds']],['initial'+str(s)for s in p['seeds']]),('free-fixed',['free6'+str(s)for s in p['seeds']],['fixed5'+str(s)for s in p['seeds']]),('static-fixed',['rule_static_v2']*4,['fixed5'+str(s)for s in p['seeds']]),('static-free',['rule_static_v2']*4,['free6'+str(s)for s in p['seeds']])]
for foe in p['foes']:
 for cohort in ['identity','nonidentity']:
  for comparison,lefts,rights in specs:
   groups=[];perrole=defaultdict(list);perseed=defaultdict(list);pervariant=defaultdict(list)
   for rid,v in p['variants'].items():
    if v['identity_control']!=(cohort=='identity'):continue
    for f in p['families']:
     for k,(left,right)in enumerate(zip(lefts,rights)):
      for owner in (0,1):
       terms=[(1,logical[rid,f,left,owner,foe]),(-1,logical[rid,f,right,owner,foe])];groups.append((v['recipient'],f,terms));perrole[owner].append(terms);perseed[p['seeds'][k]if len(lefts)==4 else 'unfitted'].append(terms);pervariant[rid].append(terms)
   rows.append(dict(foe=foe,cohort=cohort,comparison=comparison,pairs=len(groups),bounds=bound(x[2]for x in groups),conditional_recipient_family_95_envelope=envelope(groups,2026101722),by_role={str(k):bound(v)for k,v in perrole.items()},by_seed={str(k):bound(v)for k,v in perseed.items()},by_variant={k:bound(v)for k,v in pervariant.items()}))
 # Difference of finite gains, with each identity physical baseline reused across all3donors explicitly.
 for method in ['fixed5','free6']:
  groups=[];perrole=defaultdict(list)
  for rid,v in p['variants'].items():
   if v['identity_control']:continue
   base=f"{v['recipient']}-A{v['recipient']}"
   for f in p['families']:
    for seed in p['seeds']:
     for owner in (0,1):
      terms=[(1,logical[rid,f,method+str(seed),owner,foe]),(-1,logical[rid,f,'initial'+str(seed),owner,foe]),(-1,logical[base,f,method+str(seed),owner,foe]),(1,logical[base,f,'initial'+str(seed),owner,foe])];groups.append((v['recipient'],f,terms));perrole[owner].append(terms)
  rows.append(dict(foe=foe,cohort='nonidentity_gain_minus_identity_gain',comparison=method+'-initial-difference',pairs=len(groups),bounds=bound(x[2]for x in groups),conditional_recipient_family_95_envelope=envelope(groups,2026101723),by_role={str(k):bound(v)for k,v in perrole.items()}))
for n in ['rollout','advisor','slack']:
 f=json.loads((STOP/'.local_agent'/(n+'.json')).read_bytes());assert not f.get('stopped')and not f.get('user_paused')
write_json(D/'cohort-analysis.json',dict(status='COMPLETE_ALL_PREDECLARED_IDENTITY_NONIDENTITY_COHORTS',rows=rows,logical_cells=7168,physical_cells=7040,seconds=time.perf_counter()-start,scope='UNKNOWN physical variables retained[-1,+1] and exact Unitrolecopy/sign/sharedinitial/identity reuse combined BEFOREbounds. Four fixed recipients/four fixed seeds; 32 recipient-family resampling groups KEEPallthree donors, bothroles andseedscoupled. Conditional descriptive2000resamples, not rulepopulationconfidence. Difference-of-gains includes changedlegalprefixstates/distributions: not purecausal ruleeffect nor newmovementingredients. No newgame/search/fitting/filtering or bestmodel selection.'))
for x in rows:print(x['foe'],x['cohort'],x['comparison'],x['bounds'],x['conditional_recipient_family_95_envelope'])
