import json,time,sys,math,statistics
from pathlib import Path
R=Path.cwd();O=R/'results/dev_aux/task573';start=time.perf_counter();s=(R/'results/dev_aux/task522/audit.py').read_text();s=s[s.index('def tables('):s.index('nativegames=0')];exec(compile(s,'independentqualACK','exec'));rows=[]
for task in [559,569]:
 r=json.loads((R/f'results/dev_aux/task{task}/result.json').read_bytes());assert r['status']=='PASS';entries=tables(r['price_acks']);rawcount=sum(1 for _ in (R/f'results/dev_aux/task{task}/queries.jsonl').open());assert rawcount==r['actual_go'];rows.append(dict(task=task,actual_go=rawcount,full_price_ACK_entries=entries))
r=json.loads((R/'results/dev_aux/task570/result.json').read_bytes());ref=json.loads((R/'results/dev_aux/task560/result.json').read_bytes())['source_prior'];ds=[]
for x in r['source_prior_descriptors']:
 row={k:x[k] for k in ['route','training_opponent','family']}
 for label,axes in [('base6',range(2,8)),('promoted6',range(9,15)),('all12',list(range(2,8))+list(range(9,15)))]:
  row[label]={stage:statistics.mean(math.log(x[stage][a]/ref[a])**2 for a in axes) for stage in ['initial','endpoint']}
 row['base_piece_ratios_to_pawn']={name:x['endpoint'][a]/90 for name,a in [('L',2),('N',3),('S',4),('B',5),('R',6),('G',7)]};ds.append(row)
out=dict(status='PASS',qualification=rows,all_descriptor_splits=ds,new_go=0,seconds=time.perf_counter()-start,scope='AllpriceACKresponse tables plusrawquerycounts independentlyrechecked, ALL8descriptivefree12/base6/promoted6distances andbaseprice/P ratios reported withoutchoosingbestreference/model. Fixedofficialsource prior notindependenthumanconsensus, neverfitness/parameterselection. Basecoverage notidentifiability proof; rarepromotion cannot byitselfdismissobservedbasicpriceordering errors.')
(O/'result.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps(out))
