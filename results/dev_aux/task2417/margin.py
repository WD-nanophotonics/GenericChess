"""One complete full-history tree, matched D2/D3 finite-grid choice margins."""
from pathlib import Path
from copy import copy
from math import inf,isfinite
import json,time,datetime,hashlib
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record,serialize_game_record
from generic_chess.session.result import SessionStatus
from scripts.generic_session_win_proof import choices,execute
from scripts.generic_win_proof import _Budget,_Interrupted
from results.dev_aux.task2397.material import channels
from results.dev_aux.task2175.receipt import choice_value
from results.dev_aux.task2392.reader import SharedDeleteStopReader
OUT=Path('results/dev_aux/task2417')
def key(choice):return json.dumps(choice,sort_keys=True)
def vector(position,target):
 f=channels(position,target,excluded_type_ids=frozenset({'K'}));return [f['board'].get('R',0),f['hand'].get('R',0),f['board'].get('N',0)+f['hand'].get('N',0)]
def compute(nodes,point,depth):
 def walk(i,left):
  n=nodes[i]
  if n['status']!='ongoing':return(0. if n['winner']is None else inf if n['winner']==nodes[0]['side']else-inf,i,[])
  if left==0:
   a,b,c=n['features'];return(a*point[0]+b*point[1]+c,i,[])
  assert n['complete'];own=n['side']==nodes[0]['side'];best=None
  for ch,j in n['children']:
   val,leaf,pv=walk(j,left-1)
   if best is None or(own and val>best[0])or(not own and val<best[0]):best=(val,leaf,[ch]+pv)
  assert best is not None;return best
 table=[]
 for ch,j in nodes[0]['children']:
  val,leaf,pv=walk(j,depth-1);table.append(dict(choice=ch,score=val,leaf=leaf,features=nodes[leaf]['features'],terminal_priority=nodes[leaf]['status']!='ongoing',pv=[ch]+pv))
 chosen=next(r for r in table if r['score']==max(x['score']for x in table));return dict(price=point,depth=depth,choice=chosen['choice'],score=chosen['score'],chosen_leaf=chosen['leaf'],all_choices=table)
def run():
 assert not(OUT/'started.json').exists();p=json.loads((OUT/'plan.json').read_text());root=json.loads((OUT/'root.json').read_text());stop=SharedDeleteStopReader(Path.cwd());stop()
 for name,h in p['pins'].items():assert hashlib.sha256(Path(name).read_bytes()).hexdigest()==h
 c=compile_ruleset_for_execution(deserialize_ruleset(Path(root['rules']).read_text()));s=GameSession.replay(c,deserialize_game_record(json.dumps(root['record'])));target=s.state.position.side_to_move;assert len(s.legal_actions())>=2
 began=time.perf_counter();budget=_Budget(p['max_nodes'],p['cap_seconds'],lambda:stop()or False);nodes=[];status='COMPLETE';reason=None
 (OUT/'started.json').write_text(json.dumps(dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),original_cap=p['cap_seconds'],source_sha=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())))
 def build(s,depth):
  budget.visit();i=len(nodes);r=s.result;node=dict(index=i,side=s.state.position.side_to_move,depth_remaining=depth,record=json.loads(serialize_game_record(s.to_record())),state_sha=hashlib.sha256(repr(s.state).encode()).hexdigest(),status=r.status.value,winner=r.winner,features=vector(s.state.position,target),children=[],complete=False);nodes.append(node)
  if r.status is not SessionStatus.ONGOING or depth==0:node['complete']=True;return i
  for choice in choices(s,budget):
   budget.poll();ch=copy(s);execute(ch,choice);budget.poll();j=build(ch,depth-1);node['children'].append((choice_value(choice),j))
  node['complete']=True;return i
 try:build(s,p['depth'])
 except _Interrupted:status='UNKNOWN_INCOMPLETE_DIAGNOSTIC_TREE';reason=budget.reason
 finally:
  with(OUT/'nodes.jsonl').open('x',encoding='utf-8')as f:
   for n in nodes:f.write(json.dumps(n)+'\n')
 rows=[];margins=[];matches=[]
 if status=='COMPLETE':
  rows=[compute(nodes,point,depth)for depth in p['depths']for point in p['grid']]
  actual=root['saved']+root['all_saved_matching_points'];seen=set()
  for saved in actual:
   depth=saved['normal_receipt']['completed_depth'];tag=(tuple(saved['price']),depth)
   if tag in seen:continue
   seen.add(tag);row=next(r for r in rows if r['price']==saved['price']and r['depth']==depth);ok=row['choice']==saved['choice']and row['score']==saved['normal_receipt']['score'];matches.append(dict(price=saved['price'],actual_completed_depth=depth,exact_choice_and_score=ok,actual_nodes=saved['normal_receipt']['nodes'],actual_seconds=saved['normal_receipt']['seconds'],actual_exit=saved['normal_receipt']['exit_cause']));assert ok,(saved,row)
  first,second=[key(r['choice'])for r in root['saved']]
  for r in rows:
   a=next(x for x in r['all_choices']if key(x['choice'])==first);b=next(x for x in r['all_choices']if key(x['choice'])==second);finite=isfinite(a['score'])and isfinite(b['score']);delta=[x-y for x,y in zip(a['features'],b['features'])]if finite else None
   if finite:assert abs(a['score']-b['score']-(delta[0]*r['price'][0]+delta[1]*r['price'][1]+delta[2]))<1e-12
   margins.append(dict(price=r['price'],depth=r['depth'],BASEaction_score=a['score'],SELECTEDaction_score=b['score'],finite=finite,local_PV_feature_difference=delta,leaf_pair=[a['leaf'],b['leaf']],margin=None if not finite else a['score']-b['score'],exact_tie=a['score']==b['score'],terminal_priority=[a['terminal_priority'],b['terminal_priority']]))
 result=dict(status=status,reason=reason,nodes=len(nodes),seconds=time.perf_counter()-began,source_family=root['family'],source_role=root['role'],source_ply=root['ply'],actual_receipt_matches=matches,rows=rows,margins=margins,scope=p['scope']+' FullfiniteD2/D3counterfactualvalues, notreexecutionoftheold1sprotocol/noactualnewgames/pricefit. LocalPVfeatureplane validonlywhilethosecompetitiveleavesremainminimaxactive. Terminalinfinity/drawprioritydistinctfromfinitecoefficients; strictfirstchoice ordering. A switched completeddepth alone doesnotestablishwhatnewgamewouldhavedone.')
 (OUT/'result.json').write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items()if k not in('rows','margins')}));print(json.dumps([dict(price=r['price'],depth=r['depth'],choice=r['choice'],score=r['score'])for r in rows]))
if __name__=='__main__':run()
