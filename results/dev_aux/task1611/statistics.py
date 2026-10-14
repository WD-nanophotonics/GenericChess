from pathlib import Path
import json,collections,random
R=Path.cwd();O=R/'results/dev_aux/task1617';O.mkdir(exist_ok=False);P=R/'results/dev_aux/task1615';run=json.loads((P/'result.json').read_bytes());assert run['status']=='COMPLETE';selectors=run['selected'];base=json.loads((P/'R720_B720_DEV_result.json').read_bytes());profiles=[json.loads(f.read_bytes()) for f in sorted(P.glob('*_DEV_result.json'))];fd={};summ=[]
for p in profiles:
 key=p['R'],p['B'];dd=collections.defaultdict(list)
 for (f,a),(ff,b) in zip(base['root_values'],p['root_values']):assert f==ff;dd[f].append(b-a)
 d=[sum(z)/2 for f,z in sorted(dd.items())];fd[key]=d;summ.append({'R_B':key,'primaryPOOLED':list(key)==selectors['POOLED'],'mean':p['mean'],'gain':sum(d)/128,'WDL':p['WDL']})
rng=random.Random(2026677002);bs={k:[] for k in fd};errors=[]
for _ in range(10000):
 ids=rng.choices(range(128),k=128);ee=[]
 for k,d in fd.items():
  z=sum(d[i] for i in ids)/128;bs[k].append(z);ee.append(abs(z-sum(d)/128))
 errors.append(max(ee))
errors.sort();radius=errors[9499]
for x in summ:
 k=tuple(x['R_B']);bs[k].sort();x['family95']=[bs[k][249],bs[k][9749]];x['shared95']=[x['gain']-radius,x['gain']+radius]
# BootstrapTRAINselection uncertainty fromunchangedraw outcomevectors; noDEVfits.
F=R/'results/dev_aux/task1613';coh=[]
for phase in ['TRAIN1','TRAIN2','TRAIN3']:
 ps=[json.loads(f.read_bytes()) for f in sorted(F.glob('*_'+phase+'_result.json'))];vectors={};eq=collections.defaultdict(list)
 for p in ps:
  dd=collections.defaultdict(list)
  for fam,v in p['root_values']:dd[fam].append(v)
  vals=tuple(sum(z)/2 for fam,z in sorted(dd.items()));key=p['R'],p['B'];vectors[key]=vals;eq[vals].append(key)
 rng=random.Random(2026677100+int(phase[-1]));winner=collections.Counter()
 for _ in range(10000):
  sample=rng.choices(range(64),k=64);score={k:sum(d[i] for i in sample) for k,d in vectors.items()};winner[min(score,key=lambda k:(-score[k],k))]+=1
 coh.append({'phase':phase,'fixedTRAIN_selected':selectors[phase],'bootstrap_selector_counts':{str(k):v for k,v in sorted(winner.items())},'outcome_vector_equivalence_classes':[{'prices':p,'mean':sum(v)/64} for v,p in eq.items()]})
out={'status':'COMPLETE_SAME_OBJECTIVE_COHORT_STABILITY_AND_FULLPOLICY_DEV','selectors':selectors,'fullpolicy_DEV':summ,'shared95_radius':radius,'TRAIN_selector_bootstrap':coh,'actual_new_go':run['actual_new_go'],'incremental_seconds':run['seconds'],'scope':'Three disjointTRAINrootfamily samples SAMEcheapfirstchoice objective, pooledprimaryfixed, commonDEV; noDEVwinnerselection. bootstrapselection descriptive traininguncertainty, notnewindependenttrainingexecutions. Fullactualcold64five/common4 exactWDL, knowncoldcache reuse, notfromscratchtime.'};(O/'result.json').write_text(json.dumps(out,indent=2));print({k:v for k,v in out.items() if k!='TRAIN_selector_bootstrap'});print([(x['phase'],x['bootstrap_selector_counts']) for x in coh])
