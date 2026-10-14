from pathlib import Path
import json,collections,hashlib
R=Path.cwd();P=R/'results/dev_aux/task1587';O=R/'results/dev_aux/task1603';O.mkdir(exist_ok=False);train=[json.loads(f.read_bytes()) for f in sorted(P.glob('*_TRAIN_result.json'))];assert len(train)==12;groups=collections.defaultdict(list);means=collections.defaultdict(list);adj=[];byprice={}
for x in train:
 key=x['R'],x['B'];vector=tuple(y for fam,y in x['root_values']);groups[vector].append(key);means[sum(vector)].append(key);byprice[key]=vector
for r,b in byprice:
 for rr,bb in byprice:
  if (r==rr and abs([360,720,1440].index(b)-[360,720,1440].index(bb))==1) or (b==bb and abs([360,720,1440,1728].index(r)-[360,720,1440,1728].index(rr))==1):
   if (r,b)<(rr,bb):adj.append({'a':[r,b],'b':[rr,bb],'different_root_WDL':sum(a!=z for a,z in zip(byprice[r,b],byprice[rr,bb])),'net_difference':(sum(byprice[rr,bb])-sum(byprice[r,b]))/128})
out={'status':'PASS_ALL12_TRAIN_VECTOR_IDENTIFIABILITY_SNAPSHOT','equivalent_outcome_vector_price_groups':[{'prices':k,'mean':sum(v)/128,'root_vector_sha256':hashlib.sha256(json.dumps(v).encode()).hexdigest()} for v,k in groups.items()],'equal_mean_price_groups':{str(k/128):v for k,v in means.items()},'adjacent_parameter_sensitivity':adj,'new_go':0,'scope':'SameTRAINlandscape no independenttrainingreplications; vectorequivalence onlyoutcomes notpolicyequivalence. Doesnotchange frozenTRAINselector orfitDEV.'};(O/'result.json').write_text(json.dumps(out,indent=2));print('vectorclasses',len(groups),'identicalgroups',[x for x in groups.values() if len(x)>1]);print('equalmean',[(k/128,v) for k,v in means.items() if len(v)>1])
