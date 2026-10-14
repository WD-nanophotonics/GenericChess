from pathlib import Path
import json,collections,random,statistics,math
from fractions import Fraction as F
R=Path.cwd();O=R/'results/dev_aux/task1428';O.mkdir(exist_ok=False);P=R/'results/dev_aux/task1421'
assert json.loads((P/'result.json').read_bytes())['complete']
gs=[json.loads(v) for v in (P/'games.jsonl').read_text().splitlines()];assert len(gs)==1536
key=lambda g:(g['root']['seed'],g['color'],g['opponent']);names=['V_Shalf','U_Shalf','V_Sone','U_Sone','V_Stwo','U_Stwo']
by={p:{key(g):g for g in gs if g['arm']==p} for p in names};seeds=sorted({k[0] for k in by[names[0]]});assert len(seeds)==64
y=lambda g:F((g['label']=='W')-(g['label']=='L'))
def delta(p,q,w):
 return {s:sum((w if opp=='unit_search' else 1-w)*sum(y(by[p][s,c,opp])-y(by[q][s,c,opp]) for c in [False,True])/2 for opp in ['unit_search','uniform_random']) for s in seeds}
rows=[];robust=None
for ws in ['0','1/2','1']:
 w=F(ws);dd={scale:delta('V_S'+scale,'U_S'+scale,w) for scale in ['half','one','two']};dd['PRIMARY_TWO_MINUS_HALF']={s:dd['two'][s]-dd['half'][s] for s in seeds}
 means={k:sum(v.values())/64 for k,v in dd.items()};vv={k:[float(v[s]) for s in seeds] for k,v in dd.items()};rng=random.Random(2026519500);boot={k:[] for k in dd};maxdev=[]
 sd={k:statistics.stdev(vv[k])/8 for k in ['half','one','two']}
 for _ in range(10000):
  ids=rng.choices(range(64),k=64);bm={k:sum(v[i] for i in ids)/64 for k,v in vv.items()}
  for k in dd:boot[k].append(bm[k])
  maxdev.append(max(abs(bm[k]-float(means[k]))/sd[k] if sd[k] else 0 for k in ['half','one','two']))
 for k in dd:
  b=sorted(boot[k]);rows.append(dict(comparison=k,weight=ws,mean=str(means[k]),nominal_bootstrap95=[b[249],b[9749]],family_deltas={s:str(x) for s,x in dd[k].items()}))
 if ws=='1/2':
  z=sorted(maxdev)[9499];bands={k:[float(means[k])-z*sd[k],float(means[k])+z*sd[k]] for k in ['half','one','two']}
  robust=dict(status='POSTHOC_DOT_REQUESTED_SIMULTANEOUS3_GAIN_SENSITIVITY',method='Familyshared10000 nonparametricresamples, centeredmaxabs bootstrap standardizedbyoriginalSE; approximate not exactcoverage; primaryunchanged',maxT95=z,bands=bands,worst_observed_gain=str(min(means[k] for k in ['half','one','two'])),worst_conservative_lower=min(v[0] for v in bands.values()))
counts={p:{opp:dict(collections.Counter(g['label'] for g in gs if g['arm']==p and g['opponent']==opp)) for opp in ['unit_search','uniform_random']} for p in names}
first={}
for p in names:
 for seed in seeds:
  xx=[g for g in gs if g['arm']==p and g['root']['seed']==seed and g['actions'] and g['actions'][0]['actor']==g['color']]
  assert len(xx)==2 and xx[0]['actions'][0]['move']==xx[1]['actions'][0]['move']
  first[p,seed]=xx[0]['actions'][0]['move']
changes={role+':'+a+'->'+b:sum(first[role+'_S'+a,s]!=first[role+'_S'+b,s] for s in seeds) for role in ['V','U'] for a,b in [('half','one'),('one','two'),('half','two')]}
out=dict(status='FIXED_RATIO_LEAF_SCALE_FINITE_WL',rows=rows,counts=counts,simultaneous_robustness=robust,root_first_candidate_changes=changes,new_go=0,scope='Oneprimaryendpointinteraction mixed; individualgainssubgroupssecondary. Fixednative720+teacher720, varying leafRNB absoluteunits only. Attribution cannot name214 alone; selective/leaf-nativecalibration. C unresolved!=draw/infiniteWDL. No pricefit/resultsselection.')
(O/'result.json').write_text(json.dumps(out,indent=2));print('counts',counts,'changes',changes);print([{k:v for k,v in x.items() if k!='family_deltas'} for x in rows]);print('ROBUST',robust)
