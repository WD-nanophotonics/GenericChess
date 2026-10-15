import sys
from pathlib import Path
sys.path=[p for p in sys.path if Path(p).resolve()!=Path(__file__).resolve().parent]
import json,importlib.util,time,ast,re
R=Path.cwd();sp=importlib.util.spec_from_file_location('D',R/'results/dev_aux/task1720/driver.py');D=importlib.util.module_from_spec(sp);sp.loader.exec_module(D)
p=json.loads((R/sys.argv[1]).read_bytes());d=D.Driver(p,R/sys.argv[2]);train=[];dev=[];paths=[];selected={};error=None;evaluated={}
prices=list(map(tuple,p['prices']))
def score(price):
 price=tuple(price)
 if price not in evaluated:
  z=d.evaluate(price,'TRAIN');train.append(z);evaluated[price]=sum(x['payoff'] or 0 for x in d.rows if x['phase']=='TRAIN' and tuple(x['price'])==price)
 return evaluated[price]
def neighbors(price):
 out=[]
 for i in p.get('active_coordinates',(0,3)):
  vals=sorted({v[i] for v in prices});j=vals.index(price[i])
  for k in (j-1,j+1):
   if 0<=k<len(vals):
    q=list(price);q[i]=vals[k];q=tuple(q);assert q in prices;out.append(q)
 return sorted(out)
try:
 tree=ast.parse((R/'results/dev_aux/task1688/qualify_literal_fixed.py').read_text(encoding='utf-8-sig'));fn=next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name=='ref');ns={};exec(compile(ast.Module(body=[fn],type_ignores=[]),'literal','exec'),ns);ref=ns['ref']
 for f in p['families']:
  for root in f['roots']:
   state=tuple(root);assert ref(state)==d.T.moves(state)
   for u,t in ref(state):assert ref(t)==d.T.moves(t)
 d.start_engine();d.e.send('setoption name UCI_Variant value aux_pawn8');va=d.e.ready();assert any(z.startswith('info string variant aux_pawn8 files 8 ranks 8 ') for z in va);perft=[]
 for f in p['families'][:16]:
  state=tuple(f['roots'][0]);d.e.send('position fen '+d.T.fen(state));d.e.send('go perft 1');raw=d.e.until(lambda z:z.startswith('Nodes searched:'));actual={m.group(1):int(m.group(2)) for z in raw if (m:=re.fullmatch(r'([a-h][1-8][a-h][1-8][rnb]?): (\d+)',z))};assert actual=={u:1 for u,t in ref(state)};perft.append(dict(state=state,raw=raw))
 (d.O/'qualification.json').write_text(json.dumps(dict(status='PASS',literal_roots=160,all_children=True,perft=perft)))
 for price in sorted(map(tuple,p['prices'])):
  for f in p['families'][:2]:
   state=tuple(f['roots'][0]);d.choose(state,price,64);d.e.send('position fen '+d.T.fen(state));d.e.send('go perft 1');raw=d.e.until(lambda z:z.startswith('Nodes searched:'));actual={m.group(1):int(m.group(2)) for z in raw if (m:=re.fullmatch(r'([a-h][1-8][a-h][1-8][rnb]?): (\d+)',z))};assert actual=={u:1 for u,t in ref(state)};perft.append(dict(price=price,state=state,raw=raw))
 (d.O/'qualification.json').write_text(json.dumps(dict(status='PASS',literal_roots=2*len(p['families']),all_children=True,perft=perft)))
 score(p['baseline'])
 for init in p['initial_prices']:
  current=tuple(init);score(current);path=dict(initial=init,rounds=[])
  for rnd in range(p['max_rounds']):
   choices=neighbors(current)
   for q in choices:score(q)
   best=min(choices,key=lambda q:(-score(q),q));accepted=score(best)>score(current)
   path['rounds'].append(dict(round=rnd,current=current,current_score=score(current),proposals=[dict(price=q,score=score(q)) for q in choices],best=best,best_score=score(best),accepted=accepted))
   if not accepted:break
   current=best
  path.update(endpoint=current,endpoint_score=score(current));paths.append(path);(d.O/'paths_partial.json').write_text(json.dumps(paths,indent=2))
 selected={f'PATH{i}':tuple(x['endpoint']) for i,x in enumerate(paths)};selected['POOLED']=min(selected.values(),key=lambda q:(-score(q),q))
 (d.O/'selection.json').write_text(json.dumps(dict(selected=selected,paths=paths,evaluated={str(k):v for k,v in evaluated.items()}),indent=2))
 for price in sorted(set(selected.values())|{tuple(p['baseline'])}):dev.append(d.evaluate(price,'DEV'))
except BaseException as ex:error=type(ex).__name__+':'+str(ex)
finally:d.close()
out=dict(status='COMPLETE' if error is None else 'PARTIAL_PRESERVED',error=error,actual_go=d.queries,cache_hits=d.hits,actual_reported_nodes=d.newnodes,seconds=time.perf_counter()-d.start,exit_code=d.e.p.poll() if d.e else None,TRAIN=train,DEV=dev,selected=selected,paths=paths,actual_games=len(d.rows),unique_train_prices=len(evaluated),source_sha256=D.sha(str(Path(__file__).relative_to(R))))
(d.O/'result.json').write_text(json.dumps(out,indent=2));print('FINAL', {k:v for k,v in out.items() if k not in ('TRAIN','DEV','paths')})

