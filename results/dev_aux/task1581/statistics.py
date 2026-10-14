from pathlib import Path
import json,collections,random,hashlib
R=Path.cwd();P=R/'results/dev_aux/task1587';O=R/'results/dev_aux/task1596';O.mkdir(exist_ok=False);r=json.loads((P/'result.json').read_bytes());assert r['status']=='COMPLETE' and r['TRAIN_profiles']==12 and r['all_owned_engines_closed'];selection=json.loads((P/'selection.json').read_bytes());train=[json.loads(f.read_bytes()) for f in sorted(P.glob('*_TRAIN_result.json'))];dev=[json.loads(f.read_bytes()) for f in sorted(P.glob('*_DEV_result.json'))];assert len(train)==12
vectors=collections.defaultdict(list);means=collections.defaultdict(list)
for x in train:
 vec=tuple(y for f,y in x['root_values']);vectors[vec].append([x['R'],x['B']]);means[sum(vec)].append([x['R'],x['B']])
maxsum=max(means);best=min(means[maxsum]);assert selection['globalTRAIN']==best
vg=[{'prices':prices,'root_vector_sha256':hashlib.sha256(json.dumps(vec).encode()).hexdigest(),'mean':sum(vec)/len(vec),'WDL':dict(collections.Counter(vec))} for vec,prices in vectors.items()];top=[x for x in train if [x['R'],x['B']] in means[maxsum]];tradeoff=[]
for i,a in enumerate(top):
 for b in top[i+1:]:tradeoff.append({'a':[a['R'],a['B']],'b':[b['R'],b['B']],'different_roots':sum(x!=y for (_,x),(_,y) in zip(a['root_values'],b['root_values']))})
endpointcounts=collections.Counter(tuple(x['endpoint']) for x in selection['strict_adjacent_paths'].values());base=next(x for x in dev if x['R']==720 and x['B']==720);contrasts=[];fd={};raw={}
for x in dev:
 key=x['R'],x['B'];dd=collections.defaultdict(list);wdltrans=collections.Counter()
 for (f,a),(ff,b) in zip(base['root_values'],x['root_values']):assert f==ff;dd[f].append(b-a);wdltrans[a,b]+=1
 vals=[sum(z)/2 for f,z in sorted(dd.items())];assert len(vals)==128;fd[key]=vals;raw[key]={'R':key[0],'B':key[1],'mean':x['mean'],'mean_gain':sum(vals)/128,'WDL':x['WDL'],'WDL_transition_from_baseline':{str(k):v for k,v in wdltrans.items()},'primary':list(key)==best}
rng=random.Random(2026675001);maxdev=[];bs={k:[] for k in fd}
for _ in range(10000):
 sample=rng.choices(range(128),k=128);errors=[]
 for k,vals in fd.items():
  av=sum(vals[i] for i in sample)/128;bs[k].append(av);errors.append(abs(av-raw[k]['mean_gain']))
 maxdev.append(max(errors))
maxdev.sort();radius=maxdev[9499]
for k,x in raw.items():
 bs[k].sort();x['family95']=[bs[k][249],bs[k][9749]];x['shared95_allendpoint_band']=[x['mean_gain']-radius,x['mean_gain']+radius];contrasts.append(x)
out={'status':'COMPLETE_FIXED_TRAIN_SELECTOR_AND_VECTOR_IDENTIFIABILITY_DIAGNOSIS','selected':best,'TRAIN_highest_mean':maxsum/128,'TRAIN_highest_prices':means[maxsum],'TRAIN_vector_classes':vg,'TRAIN_equalmax_pair_tradeoffs':tradeoff,'strict_adjacent_endpoint_counts':{str(k):v for k,v in endpointcounts.items()},'DEV_contrasts':contrasts,'allendpoint_shared95_radius':radius,'scope':'ActualcompositeWDL; rootfamilyunit, colorsNOTindependent. Paths sameTRAINlandscape attractoranalysis not12independenttrainingruns. Identicalvectorsnotidenticalpolicies. NoDEVselection/humanfit; rootfamiliesheldout only, continuationoverlap andfixedsearchnumericthresholdlimits remain.'};(O/'result.json').write_text(json.dumps(out,indent=2));print({k:v for k,v in out.items() if k!='TRAIN_vector_classes'})
