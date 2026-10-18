"""Paid actual terminal deployment of ALL endpoints and initial baselines."""
from pathlib import Path
import json,time,hashlib,datetime,sys
from results.dev_aux.task2565.train import model,compiled,environment,prefix,restore
from results.dev_aux.task2504.search import TrainingSearch
from results.dev_aux.task2392.reader import SharedDeleteStopReader

def run(directory):
 d=Path(directory);p=json.loads((d/'eval-plan.json').read_text());assert not(d/'eval-started.json').exists();train=json.loads(Path('results/dev_aux/task2568/result.json').read_text());arms={(a['generator_seed'],a['seed'],a['method']):a for a in train['arms']};binding=dict(training_sha=hashlib.sha256(Path('results/dev_aux/task2568/result.json').read_bytes()).hexdigest(),plan_sha=hashlib.sha256((d/'eval-plan.json').read_bytes()).hexdigest(),all_models=arms and list(train['arms']));(d/'eval-binding.json').write_text(json.dumps(binding,indent=2));(d/'eval-started.json').write_text(json.dumps(dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat())));stop=SharedDeleteStopReader(Path.cwd());stop();began=time.perf_counter();rows=[];missing=[];status='COMPLETE';ccs={gs:compiled(gs)for gs in p['rules']}
 with(d/'eval-games.jsonl').open('x')as gf,(d/'eval-queries.jsonl').open('x')as qf:
  for slot in p['slots']:
   gs,seed,family,color,treatment,foename=slot;key=(gs,seed,'TD'if treatment=='initial'else treatment)
   if key not in arms:missing.append(slot);continue
   if time.perf_counter()-began>=p['cap_seconds']:status='PARTIAL_CAP';break
   a=arms[key];w=a['initial']if treatment=='initial'else a['weights'];m=model(p['domain'],w);foe=model(p['domain'],p['foes'][foename]);e=environment(gs,ccs[gs]);prefix(e,gs,family,p['prefix_plies']);initial=e.record();nq=0;nodes=0;ending='HORIZON_UNKNOWN'
   for ply in range(p['H']):
    stop()
    if e.terminal()is not None:ending='ACTUAL_TERMINAL';break
    wall=p['cap_seconds']-(time.perf_counter()-began)
    if wall<=0:ending='GLOBAL_CAP_UNKNOWN';status='PARTIAL_CAP';break
    actor=e.player();current=m if actor==color else foe;record=e.record();order=gs*100000000+family*1000+ply+p['ordering_seed_offset'];r=TrainingSearch(p['depth'],quiet=False).search(e,current,nodes=p['nodes_per_query'],seconds=min(wall,p['seconds_per_query']),seed=order,cancel=stop);assert e.record()==record;nodes+=r.nodes;nq+=1
    if r.complete:e.push(r.action)
    qf.write(json.dumps(dict(slot=slot,ply=ply,actor=actor,weights=list(current.weights),record_before=record,record_after=e.record(),complete=r.complete,value=r.value,pv_phi=r.pv_phi,pv_terminal=r.pv_terminal,nodes=r.nodes,seconds=r.seconds,ordering_seed=order,reason=r.reason,effective_nodes=p['nodes_per_query'],effective_seconds=min(wall,p['seconds_per_query'])),separators=(',',':'))+'\n');qf.flush()
    if not r.complete:ending='SEARCH_RESOURCE_UNKNOWN';break
   actual=e.terminal()
   if actual is not None:ending='ACTUAL_TERMINAL'
   replay=restore(gs,ccs[gs],e.record());assert replay.record()==e.record()and replay.terminal()==actual
   row=dict(slot=slot,weights=w,initial_record=initial,record=e.record(),outcome=actual,reward=None if actual is None else actual*(1 if color==0 else-1),ending=ending,nodes=nodes,queries=nq);rows.append(row);gf.write(json.dumps(row,separators=(',',':'))+'\n');gf.flush()
   if len(rows)%16==0:print(json.dumps(dict(games=len(rows),seconds=time.perf_counter()-began)),flush=True)
   if status!='COMPLETE':break
 missing=[s for s in p['slots']if s not in [r['slot']for r in rows]];result=dict(status=status,expected=len(p['slots']),actual=len(rows),missing=len(missing),missing_slots=missing,actual_terminal=sum(r['outcome']is not None for r in rows),unknown=sum(r['outcome']is None for r in rows),nodes=sum(r['nodes']for r in rows),queries=sum(r['queries']for r in rows),seconds=time.perf_counter()-began);(d/'eval-result.json').write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items()if k!='missing_slots'}))
if __name__=='__main__':run(sys.argv[1])
