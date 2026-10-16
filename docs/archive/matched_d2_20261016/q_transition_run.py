from pathlib import Path
import json,sys,time,importlib.util,os,statistics
R=Path.cwd();P=R/".local_agent/matched-d2-20261016";Q=P/"q1-transition";O=R/".local_agent/playability-mu-20261016";sys.path[:0]=[str(R),str(O)]
import assessment as a
p=a.p
from scripts.research_record import record_value,write_record
modules={};raw={}
for arm in["counter","fullchecked"]:
 spec=importlib.util.spec_from_file_location(arm+"._native_core",Q/(arm+"_native_core.pyd"));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);modules[arm]=m
fn=modules["counter"].semantic_engine_search
def capture(*args,**kw):
 z=fn(*args,**kw);raw.clear();raw.update(record_value(z));return z
modules["counter"].semantic_engine_search=capture
plan=json.loads((Q/"plan.json").read_bytes());rows=[];start=time.perf_counter()
for case in plan["cases"]:
 d,c,s,nr=a.load(P/case["root"]);nrs=dict(normal=nr,**{k:p.nc.compile_native_semantic_rules(c,backend_module=m)for k,m in modules.items()})
 for rep in range(2):
  part=[]
  for arm in(["normal","counter","fullchecked"]if rep==0 else["fullchecked","counter","normal"]):
   p.stopped()
   if time.perf_counter()-start>=600:raise TimeoutError("Frozen600scap")
   n=nrs[arm];e=p.SemanticSearchEngine(c,n,board_values=d["board_values"],hand_values=d["hand_values"],tt_megabytes=16,ordering_cache_enabled=False);before=p.digest(s);t=time.perf_counter()
   res=e.search(s,p.SearchLimits(max_depth=3,max_nodes=131072,max_time_seconds=None,quiescence_max_depth=1,quiescence_hard_max_depth=8),root_window_pruning=True);sec=time.perf_counter()-t
   row=dict(seed=case["seed"],board=case["board"],root=case["root"],rep=rep,arm=arm,result=record_value(res),seconds=sec,pv_edges=p.audit(s,n,res),root_restored=before==p.digest(s))
   if arm=="counter":row["metrics"]={k:v for k,v in raw.items()if k.startswith("private_q_")}
   assert row["root_restored"];rows.append(row);part.append(row)
   with(Q/"rows.jsonl").open("a",encoding="utf-8",newline="\n")as f:f.write(json.dumps(row)+"\n");f.flush();os.fsync(f.fileno())
  reference={k:v for k,v in part[0]["result"].items()if k!="elapsed_seconds"}
  assert all({k:v for k,v in r["result"].items()if k!="elapsed_seconds"}==reference for r in part),(case["seed"],rep)
 print("QTRANS",case["seed"],len(rows),flush=True)
write_record(Q/"results.json",dict(complete=True,rows=rows,seconds=time.perf_counter()-start))
summary=[]
for b in[4,8,12,16]:
 rs=[x for x in rows if x["board"]==b];normal=[x for x in rs if x["arm"]=="normal"];full=[x for x in rs if x["arm"]=="fullchecked"];counter=[x for x in rs if x["arm"]=="counter"];metrics={k:sum(x["metrics"][k]for x in counter)for k in["private_q_trials","private_q_quiet","private_q_recommits"]}
 summary.append(dict(board=b,full_normal_caller_ratio=sum(x["seconds"]for x in full)/sum(x["seconds"]for x in normal),full_normal_kernel_ratio=sum(x["result"]["elapsed_seconds"]for x in full)/sum(x["result"]["elapsed_seconds"]for x in normal),metrics=metrics,quiet_fraction=metrics["private_q_quiet"]/metrics["private_q_trials"]if metrics["private_q_trials"]else None))
write_record(Q/"summary.json",dict(complete=True,actual_queries=48,non_time_equal_triples=16,rows=summary,scope="Counteralterednooutputs; fullcheckedfiniteoutputsameatfixednodes; coststudy8exposedfamiliesonly, no strength/defaultorsemanticclaim."))
print("QTRANS_CLOSED",time.perf_counter()-start,summary,flush=True)
