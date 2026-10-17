"""Pure cached-tree alpha-beta work accounting, no Core query or wall rerun."""
from pathlib import Path
from math import inf
import json,time
OUT=Path('results/dev_aux/task2419')
def derive(folder):
 f=Path(f'results/dev_aux/task{folder}');result=json.loads((f/'result.json').read_text());nodes=list(map(json.loads,(f/'nodes.jsonl').read_text().splitlines()));root=json.loads((f/'root.json').read_text());plan=json.loads((f/'plan.json').read_text());rows=[]
 if result['status']!='COMPLETE':return dict(task=folder,status='UNKNOWN_INCOMPLETE_TREE',rows=[])
 for point in plan['grid']:
  count=0;depths=[]
  def walk(i,left,alpha,beta):
   nonlocal count
   count+=1;n=nodes[i]
   if n['status']!='ongoing':return(0. if n['winner']is None else inf if n['winner']==nodes[0]['side']else-inf,None)
   if left==0:
    a,b,c=n['features'];return(a*point[0]+b*point[1]+c,None)
   own=n['side']==nodes[0]['side'];best=-inf if own else inf;chosen=None;found=False
   for choice,j in n['children']:
    score,_=walk(j,left-1,alpha,beta)
    if not found or(own and score>best)or(not own and score<best):best,chosen,found=score,choice,True
    if own:alpha=max(alpha,best)
    else:beta=min(beta,best)
    if alpha>=beta:break
   assert found;return best,chosen
  for depth in(1,2,3):
   before=count;score,choice=walk(0,depth,-inf,inf);depths.append(dict(depth=depth,visits=count-before,cumulative_visits=count,score=score,choice=choice))
   if depth>=2:
    reference=next(r for r in result['rows']if r['price']==point and r['depth']==depth);assert score==reference['score']and choice==reference['choice']
  actual=root['saved']+root['all_saved_matching_points'];known=[s for s in actual if s['price']==point];comparisons=[];seen=set()
  for s in known:
   d=s['normal_receipt'];signature=(d['completed_depth'],d['nodes'])
   if signature in seen:continue
   seen.add(signature);completed=depths[d['completed_depth']-1];assert completed['score']==d['score']and completed['choice']==s['choice']
   if d['completed_depth']==3:assert completed['cumulative_visits']==d['nodes']
   else:assert d['exit_cause']=='time_budget'and completed['cumulative_visits']<=d['nodes']<=depths[2]['cumulative_visits']
   comparisons.append(dict(completed_depth=d['completed_depth'],actual_visits=d['nodes'],actual_seconds=d['seconds'],actual_exit=d['exit_cause'],counterfactual_complete_D3_visits=depths[2]['cumulative_visits'],remaining_visits_to_complete_D3=depths[2]['cumulative_visits']-d['nodes']))
  rows.append(dict(price=point,depths=depths,actual_comparisons=comparisons))
 return dict(task=folder,status='PASS_EXACT_FINITE_TREE_WORK_AND_SAVED_RECEIPTS',rows=rows)
def run():
 t=time.perf_counter();results=[derive(task)for task in(2415,2417)];r=dict(status='PASS_PRUNING_WORK_NOT_WALL_CAUSE_ATTRIBUTION',panels=results,seconds=time.perf_counter()-t,scope='Pureofflineorderedalpha-beta fold of independentlyCore-verifiedfiniteD3trees; exactactualcompletedreceiptvisitcounts/choice/scores. No newsearch/game/reexecutionof1swallprotocol. More deterministicvisits establish differentpruningwork, not OSload/clock cause orfutureactualW-L atanotherbudget. Fixed2channelprices/oldcaps unchanged; no defaultoptimization/humanfit. Rootchoice equalitydoesnotmean equalruntime orallsubtreepolicy.')
 (OUT/'result.json').write_text(json.dumps(r,indent=2));print(json.dumps([dict(task=p['task'],rows=[dict(price=x['price'],D3visits=x['depths'][2]['cumulative_visits'],actual=x['actual_comparisons'])for x in p['rows']])for p in results]))
if __name__=='__main__':run()
