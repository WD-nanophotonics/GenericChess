import json,sys,time,random,hashlib,re
from pathlib import Path
from fractions import Fraction
import cshogi as C
R=Path.cwd();O=R/'results/dev_aux/task508';sys.path.insert(0,str(R/'results/dev_aux/task381'));import audit as V
src=(R/'results/dev_aux/task426/audit.py').read_text(encoding='utf-8');a=src.index('def random_audit(');b=src.index("folder=R/'results/dev_aux/task425'",a);src=src[a:b];src=src.replace("and q['cold_isready'];", ";assert_reset(q,g,qi-1);")
def assert_reset(q,g,index):
 policy=g.get('reset_policy','cold_per_query')
 if policy=='warm_game':assert q['cold_isready']==[] and q['reset_policy']==policy and q['query_index_in_game']==index
 else:assert q['cold_isready'] and q['cold_isready'][-1]=='readyok'
exec(compile(src,'independent_explicit_warm_random_audit','exec'));rows=[];t0=time.perf_counter()
for task in [504,507]:
 folder=R/f'results/dev_aux/task{task}';decl=json.loads((folder/'declaration.json').read_text(encoding='utf-8'));r=json.loads((folder/'result.json').read_text(encoding='utf-8'));d={**decl,'roots':[decl['root']] if task==504 else decl['roots'],'random_seed_base':decl['random_seed_base']};games=[json.loads(x) for x in (folder/'games.jsonl').open(encoding='utf-8')];raw=[json.loads(x) for x in (folder/'queries.jsonl').open(encoding='utf-8')];expected=[];pv=0;draws=0;tables=0
 for g,meta in zip(games,r['rows']):
  if task==504 and meta['opponent']=='unit':pv+=V.game(g);expected.extend(V.bare(q) for q in g['queries'])
  else:n,qs,nd=random_audit(g);pv+=n;draws+=nd;expected.extend(qs)
  if task==507:
   assert g['reset_policy']==meta['policy'] and meta['source']['line']==games.index(g)+1
   for i,q in enumerate(g['queries']):assert_reset(q,g,i)
 assert len(games)==len(r['rows'])==(8 if task==504 else 32) and expected==raw
 for ack in r['price_acks']:
  w=ack['weights'];seen=[]
  for line in ack['prices']:
   if not line.startswith('info string auxprice '):continue
   pc,val,sgn,cap,prom=map(int,line.split()[3:]);pt=pc%16;base=pt-8 if pt in range(9,15) else pt;assert val==w[pt] and sgn==(w[pt] if pc<16 else -w[pt]) and cap==(0 if pt in (0,8,15) else w[pt]+w[base]) and prom==(w[base+8]-w[base] if base in range(1,7) else 0);seen.append(pc);tables+=1
  assert sorted(seen)==list(range(32))
 resources=[]
 for label in (['normal','profiled'] if task==504 else d['policies']):
  ix=[i for i,m in enumerate(r['rows']) if (('profiled' if m['profiled'] else 'normal')==label if task==504 else m['policy']==label)];qs=[q for i in ix for q in games[i]['queries']];nodes=[];depth=[]
  for q in qs:
   info=[l for l in q['lines'] if re.search(r'\bnodes (\d+)',l)];assert info;nodes.append(int(re.search(r'\bnodes (\d+)',info[-1]).group(1)));depth.append(int(re.search(r'\bdepth (\d+)',info[-1]).group(1)))
  resources.append(dict(condition=label,games=len(ix),actual_go=len(qs),reported_final_nodes_sum=sum(nodes),reported_node_range=[min(nodes),max(nodes)],reported_final_depth_sum=sum(depth),reported_depth_range=[min(depth),max(depth)],scope='Reportedcompleteddepth/nodecounters notstrictnominalwork/equaltime/strength. Warm changesheuristicresource condition, no oldcoldsignature conversion.'))
 rows.append(dict(task=task,games=len(games),actual_go=len(raw),PV_move_checks=pv,random_draws=draws,fulltable_entries=tables,resources=resources))
out=dict(status='PASS_NATIVE_PROTOCOL_COST_AUDIT',rows=rows,new_go=0,seconds=time.perf_counter()-t0,scope='Independentnative fullhistory/terminal/material/goal/random/RNG/PV/rawassociation andexplicitresetpolicy; warmemptyisready isintentionaldeclaredcondition, neverfalsifiedasoldcold. Profiled/control phase metadata preserved. No TTallhistory score correctness orglobalhumanvalueproof.');(O/'result.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps(out,indent=2))
