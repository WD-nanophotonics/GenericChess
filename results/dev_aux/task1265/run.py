from pathlib import Path
import json,chess,time,hashlib,importlib.util
R=Path.cwd();O=R/'results/dev_aux/task1266';O.mkdir(exist_ok=False)
D=json.loads((R/'results/dev_aux/task1265/plan.json').read_bytes());specs=json.loads((R/'results/dev_aux/task1251/plan.json').read_bytes())['roots']
sp=importlib.util.spec_from_file_location('stophelper',R/'results/dev_aux/task166/run.py');P=importlib.util.module_from_spec(sp);sp.loader.exec_module(P)
start=time.monotonic();deadline=start+D['max_seconds'];nodes=hits=0;cache={};records={};rows=[];error=None
class Limit(Exception):pass
def key(b,d):return (b.board_fen(),b.turn,d)
def terminal(b,legal):
 if not legal:return -1 if b.is_check() else 0
 if b.is_insufficient_material():return 0
 return None
def solve(b,d):
 global nodes,hits
 k=key(b,d)
 if k in cache:hits+=1;return cache[k]
 nodes+=1
 if nodes%256==0:
  P.stop()
  if nodes>D['node_limit'] or time.monotonic()>deadline:raise Limit('bounded_oracle_limit')
 legal=sorted(m.uci() for m in b.legal_moves);t=terminal(b,legal)
 if t is not None or d==0:
  val=t if t is not None else 0;cache[k]=val;records[k]=dict(value=val,terminal=t is not None,legal=legal,moves=[]);return val
 best=-2;ms=[]
 for u in legal:
  b.push_uci(u)
  try:v=-solve(b,d-1)
  finally:b.pop()
  ms.append([u,v]);best=max(best,v)
  if best==1:break
 cache[k]=best;records[k]=dict(value=best,terminal=False,legal=legal,moves=ms);return best
def proof(b,d):
 rec=records[key(b,d)];v=rec['value'];assert v in [-1,1]
 if rec['terminal']:
  assert v==-1 and b.is_checkmate();return dict(fen=b.fen(),depth=d,value=v,terminal='CHECKMATE')
 mm=rec['moves'][:]
 if v==1:mm=[next(x for x in mm if x[1]==1)]
 else:assert [x[0] for x in mm]==rec['legal'] and all(x[1]==-1 for x in mm)
 out=[]
 for u,q in mm:
  b.push_uci(u)
  try:p=proof(b,d-1)
  finally:b.pop()
  out.append(dict(move=u,child=p))
 return dict(fen=b.fen(),depth=d,value=v,terminal=None,children=out,authority='onechosenwinningaction' if v==1 else 'ALLlegaldefenses')
try:
 for spec in specs:
  root=spec['root'];b=chess.Board(root['fen8']);assert b.halfmove_clock==0 and len(b.move_stack)==0
  cache={};records={};scores={};cert=[];before=nodes
  row=dict(seed=root['seed'],variant=root['variant'],root=root,color=spec['color'],depth=4,status='PARTIAL_UNKNOWN',scores=scores,cached_choices=spec['actions'],certificates=cert)
  rows.append(row)
  for u in sorted(m.uci() for m in b.legal_moves):
   b.push_uci(u)
   try:
    v=-solve(b,3);scores[u]=v
    if v in [-1,1]:cert.append(dict(first=u,value=v,child=proof(b,3)))
   finally:b.pop()
  row.update(status='COMPLETE_EXACT_FINITE_H4',best_value=max(scores.values()),choice_values={p:scores[u] for p,u in spec['actions'].items()},visited_nodes=nodes-before)
except BaseException as ex:error=type(ex).__name__+': '+str(ex)
result=dict(status='COMPLETE' if all(x['status'].startswith('COMPLETE') for x in rows) and len(rows)==len(specs) else 'PARTIAL_LIMIT',rows=rows,nodes=nodes,cachehits=hits,seconds=time.monotonic()-start,error=error,scope=D)
(O/'result.json').write_text(json.dumps(result,indent=2));print('H4',result['status'],len(rows),nodes,hits,round(result['seconds'],3),error)
