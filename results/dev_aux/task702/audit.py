import json,sys,time,math,random,hashlib,itertools

from pathlib import Path

from fractions import Fraction
F=Fraction

R=Path.cwd();O=R/'results/dev_aux/task702';D=R/'results/dev_aux/task700/execution_inputs.json';d=json.loads(D.read_bytes());start=time.perf_counter()

for n in [360,364,381]:sys.path.insert(0,str(R/f'results/dev_aux/task{n}'))

import adapter as A,run as G,audit as V

s=(R/'results/dev_aux/task522/audit.py').read_text(encoding='utf-8');exec(compile(s[s.index('def tables('):s.index('nativegames=0')],'tablesonly','exec'));s=(R/'results/dev_aux/task600/audit.py').read_text(encoding='utf-8');s=s[s.index('def game('):s.index('for task,opp in')].replace('cap=12;','cap=g["cap"];').replace("dict(kind='cap12' if cap==12 else 'cap24',winner=None)","dict(kind='cap'+str(cap),winner=None)");counts=dict(games=0,actual_go=0,PV_moves=0,Python_actual_actions=0,random_draws=0,sorted_legal_arrays=0,price_ACK_entries=0,batches=0,proposal_rounds=0,prefixes=0);exec(compile(s,'independentphysical','exec'));summ={};sources={}

for task in [701]:

 P=R/f'results/dev_aux/task{task}';raw=iter((P/'queries.jsonl').open(encoding='utf-8'));gs=[]

 for i,text in enumerate((P/'games.jsonl').open(encoding='utf-8'),1):

  g=json.loads(text);d['seed_base']=d['seed_bases'][g['replica']];assert g['seed_base']==d['seed_base'] and g['cap']==24 and g['root']==d['roots'][g['root']['index']];z=game(g,'random',raw);b,k,ch,mo=G.full_root(g['root'])

  for a in g['actions'][:12]:

   assert G.terminal(b,k,ch,mo) is None;m=A.shogi.Move.from_usi(a['move']);assert m in b.legal_moves;mo.append(b.turn);b.push(m);ch.append(b.is_check());k.append(G.key(b))

  q12=G.quantity(b,g['color']);q24=z['raw_quantity'];fitness=F(q12+q24,38);assert q12==g['quantity12'] and q24==g['quantity24'] and str(fitness)==g['fitness'];z.update(replica=g['replica'],quantity12=q12,quantity24=q24,fitness=str(fitness));gs.append(z);counts['prefixes']+=1

  if i%1024==0:print('multiPython',task,i,round(time.perf_counter()-start,1),flush=True)

 assert next(raw,None) is None;counts['price_ACK_entries']+=tables(json.loads((P/'price_acks.json').read_bytes()));summ[task]=gs;sources[task]={n:hashlib.sha256((P/n).read_bytes()).hexdigest() for n in ['games.jsonl','queries.jsonl','price_acks.json','result.json']};(O/f'physical_stage_{task}.json').write_text(json.dumps(dict(stage=task,counts=dict(counts),source_sha256=sources[task]),indent=2),encoding='utf-8')


frozen=json.loads((R/'results/dev_aux/task700/all_profiles_frozen.json').read_bytes());assert frozen['before_any_new_probes']
for n,sha in frozen['source_endpoints_sha256'].items():assert hashlib.sha256((R/f'results/dev_aux/task{n}/endpoints.json').read_bytes()).hexdigest()==sha
result=json.loads((R/'results/dev_aux/task701/result.json').read_bytes());assert result['status']=='COMPLETE_ALL_AXIS_ROLLBACKS' and result['profiles']==frozen['profiles'];cells=[(ri,f,c) for ri in [0,1] for f in d['roots'] for c in [0,1]]
for row in result['rows']:
 rg=[summ[701][x['line']-1] for x in row['batch']['sources']];assert [(g['replica'],g['root'],g['color']) for g in rg]==cells and all(g['weights']==row['batch']['weights'] for g in rg);assert row['batch']['goals']==[g['fitness'] for g in rg]
profiles={n:p['weights'] for p in frozen['profiles'] for n in p['names']}
for task,label in [(686,'A'),(695,'B')]:
 for e in json.loads((R/f'results/dev_aux/task{task}/endpoints.json').read_bytes())['endpoints']:
  name=label+'-'+e['start'];assert profiles[name+'-endpoint']==e['endpoint'] and profiles[e['start']+'-initial']==e['initial']
  for axis in d['axes']:
   w=list(e['endpoint']);w[axis]=e['initial'][axis];assert profiles[name+'-rollback-'+str(axis)]==w

out=dict(status='PASS_ALL_ACTUAL_12_AXIS_ROLLBACKS',counts=counts,source_sha256=sources,new_go=0,seconds=time.perf_counter()-start,scope='ALL701actualH24 paths independentPython rules/PV/fullhistory/metadata/material/terminal/RNG/legalarrays/reset/ACK plusALLphysicalH12prefix/count/fitness and ALL48logicalrollbacks/4endpoints/2initials, exactfullvectoraliases. TwofullydisjointRNGsets averaged BEFOREselection, allprofiles beforeexploratory675geometry probes. Allclippedpricealiases explicitsources notnewgames. No source/humanfitness oruniversalvalueproof.');(O/'result.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in out.items() if k!='source_sha256'}))

