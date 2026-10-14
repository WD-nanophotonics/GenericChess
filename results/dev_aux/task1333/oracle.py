from pathlib import Path
import json,chess,time,hashlib,importlib.util
R=Path.cwd();O=R/'results/dev_aux/task1334';O.mkdir(exist_ok=False)
D=json.loads((R/'results/dev_aux/task1333/plan.json').read_bytes());roots=json.loads((R/'results/dev_aux/task1325/roots.json').read_bytes())['roots'][:6]
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

from fractions import Fraction as F
games=[json.loads(v) for v in (R/'results/dev_aux/task1329/games.jsonl').read_text().splitlines()]
def v(q,x):return F(q['terminal']*1000000) if 'terminal' in q else q['R']*x+q['N']
try:
 for root in roots:
  b=chess.Board(root['fen8']);actions={};points=[]
  for g in games:
   if g['root']['seed']==root['seed'] and g['color']==b.turn:
    u=g['actions'][0]['move'];actions.setdefault(u,[]).append(dict(profile=g['arm'],opponent=g['opponent'],labelH24=g['label']))
  for x in [F(1),F(2),F(12,5)]:
   scores={u:min(v(q,x) for q in ls) for u,ls in root['symbolic']['tree'].items()};best=sorted(u for u,z in scores.items() if z==max(scores.values()));points.append(dict(ratio=str(x),best=best,lex=best[0]))
   for u in best:actions.setdefault(u,[]).append(dict(D2ratio=str(x)))
  cache={};records={};scores={};cert=[];before=nodes
  row=dict(seed=root['seed'],root=root,depth=4,status='PARTIAL_UNKNOWN',scores=scores,actions=actions,certificates=cert,D2_points=points);rows.append(row)
  for u in sorted(actions):
   b.push_uci(u)
   try:
    val=-solve(b,3);scores[u]=val
    if val in [-1,1]:cert.append(dict(first=u,value=val,child=proof(b,3)))
   finally:b.pop()
  row.update(status='COMPLETE_SELECTED_UNION_H4',visited_nodes=nodes-before)
except BaseException as ex:error=type(ex).__name__+': '+str(ex)
result=dict(status='COMPLETE' if len(rows)==6 and all(x['status'].startswith('COMPLETE') for x in rows) else 'PARTIAL_LIMIT',rows=rows,nodes=nodes,cachehits=hits,seconds=time.monotonic()-start,error=error,scope=D)
(O/'result.json').write_text(json.dumps(result,indent=2));print('UNION_H4',result['status'],len(rows),nodes,round(result['seconds'],3),error)
