from pathlib import Path
import json,random,hashlib
R=Path.cwd();O=R/'results/dev_aux/task1612';O.mkdir(exist_ok=False);G=R/'results/dev_aux/task1583';states=list(map(tuple,json.loads((G/'states.json').read_bytes())));ix={s:i for i,s in enumerate(states)};v=json.loads((G/'values.json').read_bytes())['value'];edges=[json.loads(x)['moves'] for x in (G/'edges.jsonl').open()];old=json.loads((R/'results/dev_aux/task1586/study.json').read_bytes());old2=json.loads((R/'results/dev_aux/task1601/plan.json').read_bytes());excluded={f['orbit_id'] for plan in [old,old2] for f in plan['families']};families={}
def orbit(s):
 out=[]
 for fx in [False,True]:
  for fy in [False,True]:
   a=[12 if z==12 else (2-z%3 if fx else z%3)+3*(3-z//3 if fy else z//3) for z in s[:8]];out.extend([tuple(a+[s[8]]),tuple(a[4:]+a[:4]+[1-s[8]])])
 return sorted(set(ix[q] for q in out))
for i,s in enumerate(states):
 if sum(x!=12 for x in s[:8])!=5 or sum(x!=12 for x in s[4*s[8]:4*s[8]+4])!=3:continue
 ll=edges[i]
 if len(ll)<2 or len({-v[j] for u,j in ll})<2 or any(v[j]==-1 and not edges[j] for u,j in ll):continue
 ids=orbit(s);key=min(ids)
 if key not in excluded:families.setdefault(key,ids)
keys=sorted(families);random.Random(2026677000).shuffle(keys);out=[]
for f,key in enumerate(keys[:320]):
 ids=families[key];a=min(i for i in ids if states[i][8]==0);s=states[a];b=ix[tuple(s[4:8]+s[:4]+(1-s[8],))];out.append({'family':f,'phase':'TRAIN'+str(f//64+1) if f<192 else 'DEV','orbit_id':key,'all_symmetry_ids':ids,'state_ids':[a,b]})
plan={'status':'FROZEN_BEFORE_QUERIES','question':'Does SAMEcheapfirstchoice objective give stablematerialparameters across three independentTRAINfamily samples?','source_graph':'task1583','seed':2026677000,'TRAIN_cohorts':3,'TRAIN_per_cohort':64,'DEV':128,'families':out,'excluded_previous_orbits':sorted(excluded),'R_grid':[360,720,1440,1728],'B_grid':[360,720,1440],'N':720,'nodes':64,'seconds':240,'max_go':6144,'selector':'Eachcohort globalTRAINmax lowerlexR,B tie; pooledthreeTRAINmean likewise; primaryPOOLED andcohort1/2/3replicationcandidates prespecified secondary, noDEVwinnerselection','DEV_profiles':'Unioncohortselectors,POOLEDselector and720720 baseline only afterALLTRAIN; maximum5','fullpolicy_seconds':3300,'fullpolicy_scope':'Unionselected plusbaseline on SAMEnewDEV128, actualcold64five vsALLopponent/commonperfect4; qualifiedsamecold64cache reuse explicit; unknownneverdraw','objective':'ActualFIRSTcold64 choice, thenBOTHperfectruleplayers; WDL notquantity andnotwholecoldnativepolicy','heldout_scope':'All320rootfullorbits mutuallydisjoint anddisjoint1586/1601. Continuationstatesoverlappossible, noallstatesunexposedclaim.','binary':old['binary'],'binary_sha256':old['binary_sha256'],'variant_ini':old['variant_ini'],'input_hashes':old['input_hashes'],'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()};(O/'study.json').write_text(json.dumps(plan,indent=2));print('FROZEN',len(out),'EXCLUDED',len(excluded),'ELIGIBLE',len(keys))
