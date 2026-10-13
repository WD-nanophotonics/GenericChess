import json,sys,time,math,random,hashlib,itertools

from pathlib import Path

from fractions import Fraction
F=Fraction

R=Path.cwd();O=R/'results/dev_aux/task697';D=R/'results/dev_aux/task694/declaration.json';d=json.loads(D.read_bytes());start=time.perf_counter()

for n in [360,364,381]:sys.path.insert(0,str(R/f'results/dev_aux/task{n}'))

import adapter as A,run as G,audit as V

s=(R/'results/dev_aux/task522/audit.py').read_text(encoding='utf-8');exec(compile(s[s.index('def tables('):s.index('nativegames=0')],'tablesonly','exec'));s=(R/'results/dev_aux/task600/audit.py').read_text(encoding='utf-8');s=s[s.index('def game('):s.index('for task,opp in')].replace('cap=12;','cap=g["cap"];').replace("dict(kind='cap12' if cap==12 else 'cap24',winner=None)","dict(kind='cap'+str(cap),winner=None)");counts=dict(games=0,actual_go=0,PV_moves=0,Python_actual_actions=0,random_draws=0,sorted_legal_arrays=0,price_ACK_entries=0,batches=0,proposal_rounds=0,prefixes=0);exec(compile(s,'independentphysical','exec'));summ={};sources={}

qualified=json.loads((R/'results/dev_aux/task688/result.json').read_bytes());assert qualified['status']=='PASS_ALL_MULTI_DRAW_HORIZON_LEARNING_DEV'
manifest=json.loads((R/'results/dev_aux/task694/cached_source_manifest.json').read_bytes())
for name,sha in manifest['sha256'].items():assert hashlib.sha256((R/'results/dev_aux/task686'/name).read_bytes()).hexdigest()==sha
for name,sha in qualified['source_sha256']['686'].items():assert hashlib.sha256((R/'results/dev_aux/task686'/name).read_bytes()).hexdigest()==sha
summ[686]=[json.loads(t) for t in (R/'results/dev_aux/task686/games.jsonl').open(encoding='utf-8')]
for task in [695,696]:

 P=R/f'results/dev_aux/task{task}';raw=iter((P/'queries.jsonl').open(encoding='utf-8'));gs=[]

 for i,text in enumerate((P/'games.jsonl').open(encoding='utf-8'),1):

  g=json.loads(text);d['seed_base']=d['seed_bases'][g['replica']];assert g['seed_base']==d['seed_base'] and g['cap']==24 and g['root']==d['roots'][g['root']['index']];z=game(g,'random',raw);b,k,ch,mo=G.full_root(g['root'])

  for a in g['actions'][:12]:

   assert G.terminal(b,k,ch,mo) is None;m=A.shogi.Move.from_usi(a['move']);assert m in b.legal_moves;mo.append(b.turn);b.push(m);ch.append(b.is_check());k.append(G.key(b))

  q12=G.quantity(b,g['color']);q24=z['raw_quantity'];fitness=F(q12,19);assert q12==g['quantity12'] and q24==g['quantity24'] and str(fitness)==g['fitness'];z.update(replica=g['replica'],quantity12=q12,quantity24=q24,fitness=str(fitness));gs.append(z);counts['prefixes']+=1

  if i%1024==0:print('multiPython',task,i,round(time.perf_counter()-start,1),flush=True)

 assert next(raw,None) is None;counts['price_ACK_entries']+=tables(json.loads((P/'price_acks.json').read_bytes()));summ[task]=gs;sources[task]={n:hashlib.sha256((P/n).read_bytes()).hexdigest() for n in ['games.jsonl','queries.jsonl','price_acks.json','result.json']};(O/f'physical_stage_{task}.json').write_text(json.dumps(dict(stage=task,counts=dict(counts),source_sha256=sources[task]),indent=2),encoding='utf-8')

 if task==696:break

 ep=json.loads((P/'endpoints.json').read_bytes());assert ep['declaration_sha256']==hashlib.sha256(D.read_bytes()).hexdigest();train=[f for f in d['roots'] if f['phase']=='train'];cells=[(r,f,c) for r in [0,1] for f in train for c in [0,1]]

 for initial in d['initial_profiles']:

  w=list(initial['weights']);base=None;updates=[u for u in ep['updates'] if u['start']==initial['name']];assert len(updates)==12

  for i,u in enumerate(updates):

   axis=d['axes'][i];assert u['iteration']==i and u['axis']==axis and u['start_weights']==w;expected=[]

   for mult in d['multipliers']:

    ww=list(w);ww[axis]=max(32,min(4096,math.floor(w[axis]*mult+.5)));expected.append(ww)

   cs=u['candidates'];assert [x['weights'] for x in cs]==expected

   for c in cs:

    rg=[summ[int(x['file'].split('/')[-2][4:])][x['line']-1] for x in c['sources']];assert [(g['replica'],g['root'],g['color']) for g in rg]==cells;assert all(g['weights']==c['weights'] for g in rg);assert c['objective']=='actual_two_draw_quantity12_only' and c['goals']==[str(F(g['quantity12'],19)) for g in rg] and c['quantity12']==[g['quantity12'] for g in rg] and c['quantity24']==[g['quantity24'] for g in rg] and c['terminations']==[g['termination'] for g in rg];assert F(c['mean_goal'])==sum(F(g['quantity12'],19) for g in rg)/64;counts['batches']+=1

   mu=[F(x['mean_goal']) for x in cs];best=max(range(7),key=lambda j:mu[j]);assert best==u['selected_index'] and mu[best]-mu[0]==F(u['accepted_gain']);assert base is None or mu[0]==base;w=list(cs[best]['weights']);base=mu[best];assert w==u['after_weights'];counts['proposal_rounds']+=1

  assert next(x['endpoint'] for x in ep['endpoints'] if x['start']==initial['name'])==w

freeze=json.loads((R/'results/dev_aux/task694/all_endpoints_frozen.json').read_bytes());assert freeze['before_any_new_development'] and freeze['endpoint_sha256']==hashlib.sha256((R/'results/dev_aux/task695/endpoints.json').read_bytes()).hexdigest();result=json.loads((R/'results/dev_aux/task696/result.json').read_bytes());dev=[f for f in d['roots'] if f['phase']=='development'];cells=[(r,f,c) for r in [0,1] for f in dev for c in [0,1]]

for row in result['rows']:

 rg=[summ[696][x['line']-1] for x in row['batch']['sources']];assert [(g['replica'],g['root'],g['color']) for g in rg]==cells and all(g['weights']==row['batch']['weights'] for g in rg);assert row['batch']['goals']==[g['fitness'] for g in rg]

out=dict(status='PASS_ALL_PAIRED_H12_CONTROL_CACHED_AND_NEW',counts=counts,source_sha256=sources,new_go=0,seconds=time.perf_counter()-start,scope='ALL695/696NEWactualH24 paths plus exactqualified686cached full-vector source hashes independentPython rules/PV/fullhistory/metadata/material/terminal/RNG/legalarrays/reset/ACK plusALLphysicalH12prefix/count/fitness andALL24coordinateupdates/168logicalcandidates. H12-only objective on SAMEtwofullydisjointRNGsets averaged BEFOREselection, allBendpoints beforeNEWBdev; Adevalreadyexposed during Bexecution, exploratory pairedcomparison. Allclippedpricealiases explicitsources notnewgames. No source/humanfitness oruniversalvalueproof.');(O/'result.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in out.items() if k!='source_sha256'}))

