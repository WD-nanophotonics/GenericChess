from pathlib import Path
import json,collections
R=Path.cwd();O=R/'results/dev_aux/task1610';O.mkdir(exist_ok=False);S=json.loads((R/'results/dev_aux/task1601/plan.json').read_bytes());states=json.loads((R/'results/dev_aux/task1583/states.json').read_bytes());stock={}
for fam in S['families']:
 s=states[fam['state_ids'][0]];stock[fam['family']]=''.join(k for i,k in [(1,'R'),(2,'N'),(3,'B')] if s[i]!=12)+'_vs_'+''.join(k for i,k in [(5,'r'),(6,'n'),(7,'b')] if s[i]!=12)
P=R/'results/dev_aux/task1606';a=json.loads((P/'R720_B720_DEV_result.json').read_bytes());b=json.loads((P/'R1440_B360_DEV_result.json').read_bytes());groups=collections.defaultdict(list)
for (f,x),(ff,y) in zip(a['root_values'],b['root_values']):assert f==ff;groups[stock[f]].append((x,y))
out={'status':'COMPLETE_ZERO_GO_FROZEN_DEV_STOCK_STRATA','rows':[{'stock':k,'roots':len(z),'families':len(z)//2,'baseline_mean':sum(a for a,b in z)/len(z),'selected_mean':sum(b for a,b in z)/len(z),'gain':sum(b-a for a,b in z)/len(z),'WDL_transitions':{str(k):n for k,n in collections.Counter(z).items()}} for k,z in sorted(groups.items())],'scope':'Descriptive frozenDEV composition; bothR andB changed, notcausalindividualpiece attribution or newprice selection. Sameactual5policy/common4oracle; zero nativego.'};(O/'result.json').write_text(json.dumps(out,indent=2));print(out)
