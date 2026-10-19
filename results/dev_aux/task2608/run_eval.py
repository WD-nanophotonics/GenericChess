"""Paid actual-terminal W/L/D evaluation of fixed task2606 models."""
from pathlib import Path
import json,time,hashlib,datetime,sys
from results.dev_aux.task2606.train import model,compiled,environment,prefix,restore
from results.dev_aux.task2504.search import TrainingSearch
from results.dev_aux.task2392.reader import SharedDeleteStopReader

def run(directory):
 d=Path(directory);p=json.loads((d/'eval-plan.json').read_text());reg=json.loads((d/'registration.json').read_text());manifest=json.loads((d/'root-manifest.json').read_text());train=json.loads(Path('results/dev_aux/task2606/result.json').read_text())
 assert reg['state']=='REGISTERED_BEFORE_EVALUATION' and train['status']=='COMPLETE';assert hashlib.sha256((d/'eval-plan.json').read_bytes()).hexdigest()==reg['eval_plan_sha256'];assert hashlib.sha256((d/'root-manifest.json').read_bytes()).hexdigest()==reg['root_manifest_sha256'];assert hashlib.sha256(Path('results/dev_aux/task2606/result.json').read_bytes()).hexdigest()==reg['model_result_sha256']
 for name,h in reg['source_pins'].items():assert hashlib.sha256(Path(name).read_bytes()).hexdigest()==h,name
 assert not(d/'eval-started.json').exists();arms={(a['generator_seed'],a['seed'],a['method']):a for a in train['arms']};binding={'model_result_sha256':reg['model_result_sha256'],'eval_plan_sha256':reg['eval_plan_sha256'],'root_manifest_sha256':reg['root_manifest_sha256'],'models':len(arms)};(d/'eval-binding.json').write_text(json.dumps(binding,indent=2));(d/'eval-started.json').write_text(json.dumps({'utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}));stop=SharedDeleteStopReader(Path.cwd());stop();began=time.perf_counter();rows=[];status='COMPLETE'
 with(d/'eval-games.jsonl').open('x')as gf,(d/'eval-queries.jsonl').open('x')as qf:
  ccs={gs:compiled(gs)for gs in p['rules']}
  for slot in p['slots']:
   gs,seed,family,color,treatment,foe_name=slot
   a=arms[(gs,seed,'TD95')];w=a['initial']if treatment=='initial'else arms[(gs,seed,treatment)]['weights'];m=model('generic',w);foe=model('generic',p['foes'][foe_name]);e=environment(gs,ccs[gs]);prefix(e,gs,family,p['prefix_plies']);initial=e.record();assert initial==manifest['roots'][f'{gs}:{family}'];nodes=0;nq=0;ending='HORIZON_UNKNOWN'
   if time.perf_counter()-began>=p['cap_seconds']:status='PARTIAL_CAP';break
   for ply in range(p['H']):
    stop()
    if e.terminal()is not None:ending='ACTUAL_TERMINAL';break
    wall=p['cap_seconds']-(time.perf_counter()-began)
    if wall<=0:ending='GLOBAL_CAP_UNKNOWN';status='PARTIAL_CAP';break
    actor=e.player();current=m if actor==color else foe;record=e.record();order=gs*100000000+family*1000+ply+972608000;r=TrainingSearch(p['depth'],quiet=False).search(e,current,nodes=p['nodes_per_query'],seconds=min(wall,p['seconds_per_query']),seed=order,cancel=stop);assert e.record()==record;nodes+=r.nodes;nq+=1
    if r.complete:e.push(r.action)
    qf.write(json.dumps({'slot':slot,'ply':ply,'actor':actor,'weights':list(current.weights),'record_before':record,'record_after':e.record(),'complete':r.complete,'value':r.value,'pv_phi':r.pv_phi,'pv_terminal':r.pv_terminal,'nodes':r.nodes,'seconds':r.seconds,'ordering_seed':order,'reason':r.reason},separators=(',',':'))+'\n');qf.flush()
    if not r.complete:ending='SEARCH_RESOURCE_UNKNOWN';break
   actual=e.terminal();
   if actual is not None:ending='ACTUAL_TERMINAL'
   replay=restore(gs,ccs[gs],e.record());assert replay.record()==e.record()and replay.terminal()==actual
   row={'slot':slot,'weights':w,'initial_record':initial,'record':e.record(),'outcome':actual,'reward':None if actual is None else actual*(1 if color==0 else -1),'ending':ending,'nodes':nodes,'queries':nq};rows.append(row);gf.write(json.dumps(row,separators=(',',':'))+'\n');gf.flush()
   if len(rows)%16==0:print(json.dumps({'games':len(rows),'seconds':time.perf_counter()-began}),flush=True)
   if status!='COMPLETE':break
 missing=[s for s in p['slots']if s not in [r['slot']for r in rows]];result={'status':status,'expected':len(p['slots']),'actual':len(rows),'missing':len(missing),'missing_slots':missing,'actual_terminal':sum(r['outcome']is not None for r in rows),'unknown':sum(r['outcome']is None for r in rows),'nodes':sum(r['nodes']for r in rows),'queries':sum(r['queries']for r in rows),'seconds':time.perf_counter()-began};(d/'eval-result.json').write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items()if k!='missing_slots'}))
if __name__=='__main__':run(sys.argv[1])