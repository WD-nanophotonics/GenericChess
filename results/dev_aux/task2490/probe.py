
"""Prefrozen all-family D5 initial-choice sensitivity/cost panel, not WDL training."""
from pathlib import Path
from dataclasses import fields
import json,time,hashlib,datetime,traceback
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from results.dev_aux.task2148.normal import SessionCompleteMaterialSearch
from results.dev_aux.task2397.material import material
from results.dev_aux.task2175.receipt import choice_value
from results.dev_aux.task2392.reader import SharedDeleteStopReader
OUT=Path('results/dev_aux/task2490')
def run():
 assert not(OUT/'started.json').exists()
 p=json.loads((OUT/'plan.json').read_text());assert Path(p['source_d4']+'/completion.json').exists()
 for n,h in p['pins'].items():assert hashlib.sha256(Path(n).read_bytes()).hexdigest()==h
 roots=json.loads(Path(p['input']).read_text());slots=json.loads(Path(p['source_d4']+'/slots.json').read_text());old=[json.loads(x)for x in Path(p['source_d4']+'/decisions.jsonl').read_text().splitlines()]
 stop=SharedDeleteStopReader(Path.cwd());stop();t=time.perf_counter();rows=[];controls=[];status='COMPLETE';error=None
 (OUT/'started.json').write_text(json.dumps(dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),original_cap=p['one_cap_seconds'],source_sha=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())))
 def cancel():stop();return time.perf_counter()-t>=p['one_cap_seconds']
 def query(root,point,Nhand=1.):
  c=compile_ruleset_for_execution(deserialize_ruleset(Path(root['rules']).read_text()));s=GameSession.replay(c,deserialize_game_record(json.dumps(root['record'])));assert hashlib.sha256(repr(s.state).encode()).hexdigest()==root['state_sha']
  a,b=point;normal=SessionCompleteMaterialSearch(c,lambda pos,side:material(pos,side,{'R':a,'N':1.},{'R':b,'N':Nhand},excluded_type_ids={'K'}),max_depth=5)
  r=normal.choose(s,max_nodes=p['normal_nodes'],seconds=min(p['query_seconds'],max(0.,p['one_cap_seconds']-(time.perf_counter()-t))),cancel=cancel)
  return {f.name:(choice_value(getattr(r,f.name))if f.name=='choice'else getattr(r,f.name))for f in fields(r)}
 try:
  with(OUT/'queries.jsonl').open('x')as stream:
   # Four previously Core-replayed completeD5 controls; not four new games.
   for task,point,nh in[(2471,[.75,0],1.),(2471,[1.5,.75],1.),(2472,[.75,.75],1.),(2472,[.75,.75],2.)]:
    if cancel():status='PARTIAL_GLOBAL_CAP';break
    rr=json.loads(Path(f'results/dev_aux/task{task}/root.json').read_text());r=query(rr,point,nh)
    ref=next(x for x in json.loads(Path(f'results/dev_aux/task{task}/result.json').read_text())['rows']if x['depth']==5 and x['price']==point+([nh]if task==2472 else[]))
    complete=r['completed_depth']==5
    if complete:assert r['choice']==ref['choice']and r['score']==ref['score']
    controls.append(dict(task=task,price=point,Nhand=nh,complete_D5=complete,actual_receipt=r,exact_complete_tree_match=complete))
   for family,root in enumerate(roots):
    if status!='COMPLETE':break
    for price in p['grid']:
     if cancel():status='PARTIAL_GLOBAL_CAP';break
     slot=next(s for s in slots if s['root']==family and s['candidate_color']==0 and[s['ratio'],s['hand_ratio']]==price)
     saved=next((d for d in old if d['slot']==slot['slot']and d['ply']==0),None)
     if saved is not None:assert saved['root_record']==root['record']and saved['root_state_sha']==root['state_sha']
     r=query(root,price);d4=None if saved is None else saved['normal_receipt']
     row=dict(index=len(rows),family=family,price=price,root_state_sha=root['state_sha'],D4_source_slot=slot['slot'],D4_saved_receipt=d4,D5_new_receipt=r,complete_D5=r['completed_depth']==5,choice_changed_from_actual_D4=None if d4 is None or d4['completed_depth']!=4 or r['completed_depth']!=5 else d4['choice']!=r['choice'])
     rows.append(row);stream.write(json.dumps(row)+'\n');stream.flush()
    print(json.dumps(dict(family=family,queried=len(rows),completed_D5=sum(x['complete_D5']for x in rows),changed=sum(x['choice_changed_from_actual_D4']is True for x in rows),seconds=time.perf_counter()-t)),flush=True)
 except BaseException as e:
  status='INTERRUPTED_'+type(e).__name__;error=dict(type=type(e).__name__,message=str(e))
  private=Path('.local_agent/runtime-errors');private.mkdir(exist_ok=True);(private/'2490-first.txt').write_text(traceback.format_exc())
  raise
 finally:
  result=dict(status=status,expected_queries=96,actual_queries=len(rows),missing=96-len(rows),completed_D5=sum(x['complete_D5']for x in rows),changed_from_actual_D4=sum(x['choice_changed_from_actual_D4']is True for x in rows),controls=controls,error=error,seconds=time.perf_counter()-t,scope=p['scope']+' FourseparatecompleteD5Coretreecontrols explicitlycounted; notWDLgames. Budget+depthcounterfactuals only, unfinishedD5 retainsreceipt/missingdistinct; no forcedWINlabel, no generalpricebenefit.')
  (OUT/'result.json').write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items()if k!='controls'}))
if __name__=='__main__':run()
