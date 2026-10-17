"""Replay every saved reference-tree edge and independently fold finite scores."""
from pathlib import Path
from copy import copy
from math import inf
import json,hashlib,time
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record,serialize_game_record
from generic_chess.session.result import SessionStatus
from scripts.generic_session_win_proof import choices,execute
from scripts.generic_win_proof import _Budget
from results.dev_aux.task2397.material import material
from results.dev_aux.task2175.receipt import choice_value
from results.dev_aux.task2392.reader import SharedDeleteStopReader
OUT=Path('results/dev_aux/task2418')
def run():
 tick=time.perf_counter();stop=SharedDeleteStopReader(Path.cwd());folder=Path('results/dev_aux/task2417');result=json.loads((folder/'result.json').read_text());nodes=list(map(json.loads,(folder/'nodes.jsonl').read_text().splitlines()));root=json.loads((folder/'root.json').read_text());c=compile_ruleset_for_execution(deserialize_ruleset(Path(root['rules']).read_text()));session=GameSession.replay(c,deserialize_game_record(json.dumps(root['record'])));budget=_Budget(1000000,300.,lambda:stop()or False);seen=set();edges=0;actual_leaves={};actual_positions={}
 def replay(i,s):
  nonlocal edges
  budget.visit();actual_positions[i]=s.state.position;n=nodes[i];assert i==n['index']and i not in seen;seen.add(i);assert n['record']==json.loads(serialize_game_record(s.to_record()))and n['state_sha']==hashlib.sha256(repr(s.state).encode()).hexdigest()and n['status']==s.result.status.value and n['winner']==s.result.winner
  if n['depth_remaining']==0 or s.result.status is not SessionStatus.ONGOING:
   actual_leaves[i]=s
  if n['complete']and n['depth_remaining']and s.result.status is SessionStatus.ONGOING:
   legal=list(choices(s,budget));assert [choice_value(x)for x in legal]==[ch for ch,j in n['children']]
   for ch,(_,j)in zip(legal,n['children']):
    child=copy(s);execute(child,ch);assert nodes[j]['depth_remaining']==n['depth_remaining']-1;edges+=1;replay(j,child)
 # This consumer requires the finite reference tree to be complete; UNKNOWN is reported without asserting completeness.
 if result['status']!='COMPLETE':
  (OUT/'result.json').write_text(json.dumps(dict(status='UNKNOWN_REFERENCE_TREE_INCOMPLETE',nodes=len(nodes),scope='No rerun/capextension; finitechoicecellnotestablished.'),indent=2));return
 replay(0,session);assert len(seen)==len(nodes)
 # Independently evaluate each persisted node's actual Position, with2397typedfeatures, not producer vector arithmetic.

 checked=[];target=nodes[0]['side']
 for row in result['rows']:
  budget.poll();point=row['price'];depth=row['depth'];b={'R':point[0],'N':1.};h={'R':point[1],'N':1.};values={};leaves={}
  for i in reversed(range(len(nodes))):
   n=nodes[i];distance=3-n['depth_remaining'];rstatus=n['status']
   if distance>depth:continue
   if rstatus!='ongoing':values[i]=0. if n['winner']is None else inf if n['winner']==target else-inf;leaves[i]=i
   elif distance==depth:
    values[i]=material(actual_positions[i],target,b,h,excluded_type_ids={'K'});leaves[i]=i
   else:
    child_values=[values[j]for ch,j in n['children']];best=(max if n['side']==target else min)(child_values);j=next(j for ch,j in n['children']if values[j]==best);values[i]=best;leaves[i]=leaves[j]
  best=max(values[j]for ch,j in nodes[0]['children']);choice,j=next((ch,j)for ch,j in nodes[0]['children']if values[j]==best);assert choice==row['choice']and best==row['score']and leaves[j]==row['chosen_leaf']
  for original,(ch,j)in zip(row['all_choices'],nodes[0]['children']):assert original['choice']==ch and original['score']==values[j]and original['leaf']==leaves[j]
  checked.append(dict(price=point,depth=depth,root_score=best,all_root_actions=len(row['all_choices'])))
 vectors=[r['local_PV_feature_difference'][:2]for r in result['margins']if r['finite']];nonzero=[v for v in vectors if any(v)];rank=0 if not nonzero else 2 if any(a[0]*b[1]!=a[1]*b[0]for a in nonzero for b in nonzero)else 1
 out=dict(status='PASS_COMPLETE_CORE_TREE_MATCHED_DEPTH_MARGIN_REPLAY',nodes=len(nodes),actual_edges=edges,price_depth_folds=checked,finite_competing_feature_rank=rank,actual_receipt_matches=result['actual_receipt_matches'],seconds=time.perf_counter()-tick,scope='ActualfullhistoryCoreedgecompleteness and independentbottom-up2397material folds, no newsearch/game. Featuredirectionrank conditionaloncompetitivePVpairs, notunique/globalidentification. Terminalpriority/ties explicit. PriorTRAINsolegainD3vsD2; currentRESERVEfirstmatchedD3divergencepost-fitdiagnostic, noadditionalgames/refit. Localfeaturedirectionranknotglobaluniqueprice.')
 (OUT/'result.json').write_text(json.dumps(out,indent=2));print(json.dumps(out))
if __name__=='__main__':run()
