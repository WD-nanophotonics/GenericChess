"""All-cell matched TRAIN/DEPLOY context contrasts, costs and headroom."""
from pathlib import Path
from collections import Counter,defaultdict
import json,itertools,hashlib,sys
from results.dev_aux.task2568.summary import contrast,bounds
from results.dev_aux.task2571.trajectory import compare
D=Path("results/dev_aux/task2576");E=Path("results/dev_aux/task2577")
SEEDS=(1977,8173,27182,31415);CONTEXTS=("plain","q2");METHODS=("initial","TD_plain","TD_q2")
def load(p):return json.loads(Path(p).read_text())
def effect_of_matching(rows,slots,foe=None,seed=None):
 keys=sorted({(s[1],s[2],s[3],s[5])for s in slots if(foe is None or s[5]==foe)and(seed is None or s[1]==seed)})
 cells=[]
 for s,f,c,o in keys:
  a,b,d,e=[bounds(rows.get((0,s,f,c,label,o)))for label in("TD_q2|q2","TD_plain|q2","TD_q2|plain","TD_plain|plain")]
  cells.append(dict(seed=s,family=f,color=c,foe=o,bounds=[a[0]-b[1]-d[1]+e[0],a[1]-b[0]-d[0]+e[1]]))
 return dict(n=len(cells),bounds=[sum(x["bounds"][i]for x in cells)/max(1,len(cells))for i in(0,1)],cells=cells)
def run(stop_root=None):
 reg=load(D/"registration.json");p=load(D/"plan.json");ep=load(E/"eval-plan.json");t=load(D/"result.json");ev=load(E/"eval-result.json");binding=load(E/"result.json")
 assert load(D/"started.json")["utc"]>reg["registered_at"]and load(E/"eval-started.json")["utc"]>reg["registered_at"]
 for name,h in reg["pins"].items():assert hashlib.sha256(Path(name).read_bytes()).hexdigest()==h,name
 assert binding["training_sha"]==hashlib.sha256((D/"result.json").read_bytes()).hexdigest()
 src={(a["seed"],a["method"]):a for a in t["arms"]}
 for a in binding["arms"]:
  from results.dev_aux.task2576.train import initial
  assert a["weights"]==(initial(a["seed"])if a["original_method"]=="initial"else src[a["seed"],a["original_method"]]["weights"])
 expected=set(itertools.product([0],SEEDS,range(501001,501007),(0,1),(m+"|"+c for m in METHODS for c in CONTEXTS),ep["foes"]))
 assert len(ep["slots"])==576 and set(map(tuple,ep["slots"]))==expected
 rows={tuple(g["slot"]):g for g in map(json.loads,(E/"eval-games.jsonl").open())};assert len(rows)==ev["actual"]
 out={}
 for ctx in CONTEXTS:
  out[ctx]={}
  for left,right in (("TD_plain","initial"),("TD_q2","initial"),("TD_q2","TD_plain")):
   a,b=left+"|"+ctx,right+"|"+ctx
   out[ctx][left+"-"+right]=dict(all=contrast(rows,ep["slots"],a,b),by_foe={o:contrast(rows,[s for s in ep["slots"]if s[5]==o],a,b)for o in ep["foes"]},by_seed={str(seed):{o:contrast(rows,[s for s in ep["slots"]if s[1]==seed and s[5]==o],a,b)for o in ep["foes"]}for seed in SEEDS},by_role={str(c):{o:contrast(rows,[s for s in ep["slots"]if s[3]==c and s[5]==o],a,b)for o in ep["foes"]}for c in(0,1)},by_family={str(f):contrast(rows,[s for s in ep["slots"]if s[2]==f],a,b)for f in range(501001,501007)})
 stats=defaultdict(Counter)
 for q in map(json.loads,(E/"eval-queries.jsonl").open()):
  *_,color,label,o=q["slot"];candidate=q["actor"]==color;quiet=candidate and label.endswith("|q2");assert q["candidate_q2"]==quiet
  st=q["search_stats"];assert st["q_limit"]==2
  if not quiet:assert st["qnodes"]==st["q_truncated_leaf_labels"]==st["q_cap_still_tactical"]==0
  stats[label+("/candidate"if candidate else"/fixed_plain_foe")].update(dict(queries=1,nodes=q["nodes"],qnodes=st["qnodes"],check_evasion_nodes=st["check_evasion_nodes"],q_cap_still_tactical=st["q_cap_still_tactical"],failed=not q["complete"]))
 absolute={}
 for label,o in itertools.product([m+"|"+c for m in METHODS for c in CONTEXTS],ep["foes"]):
  slots=[s for s in ep["slots"]if s[4]==label and s[5]==o];cc=Counter();lo=hi=0
  for s in slots:
   g=rows.get(tuple(s));a,b=bounds(g);lo+=a;hi+=b;cc["missing"if g is None else"U"if g["reward"]is None else"W"if g["reward"]>0 else"L"if g["reward"]<0 else"D"]+=1
  absolute[label+"/"+o]=dict(n=len(slots),counts=dict(cc),W_minus_L_bounds=[lo/len(slots),hi/len(slots)],room_to_max=[1-hi/len(slots),1-lo/len(slots)])
 trajectories={}
 for ctx in CONTEXTS:
  for a,b in(("TD_plain","initial"),("TD_q2","initial"),("TD_q2","TD_plain")):
   cells=[dict(seed=s,family=f,color=c,foe=o,**compare(rows.get((0,s,f,c,a+"|"+ctx,o)),rows.get((0,s,f,c,b+"|"+ctx,o))))for s,f,c,o in itertools.product(SEEDS,range(501001,501007),(0,1),ep["foes"])]
   trajectories[ctx+"/"+a+"-"+b]=dict(counts=dict(Counter(x["kind"]for x in cells)),cells=cells)
 train=defaultdict(Counter);loss=Counter();train_roots=set()
 for g in map(json.loads,(D/"games.jsonl").open()):
  k=str((g["seed"],g["method"]));train[k].update(dict(games=1,nodes=g["nodes"],queries=g["queries"],observed=g["observed"],terms=g["stats"]["samples"],terminal=g["outcome"]is not None,U=g["outcome"]is None,updates=g["weights"]!=g["initial_weights"]))
  if g["stats"]["loss"]is not None:loss[k]+=g["stats"]["loss"]*g["stats"]["samples"]
  train_roots.add(json.dumps(g["initial_record"],sort_keys=True))
 roots={json.dumps(g["initial_record"],sort_keys=True)for g in rows.values()}
 trainloss={k:dict(counts=dict(v),changing_data_weighted_loss=loss[k]/max(1,v["terms"]))for k,v in train.items()}
 order={m:[sorted(range(5),key=lambda j:a["weights"][j])for a in t["arms"]if a["method"]==m]for m in("TD_plain","TD_q2")}
 r=dict(status="PASS_ALL_CONTEXT_BINDINGS_AND_PAID_CELLS",TRAIN=t,EVAL=ev,contrasts=out,matching_interaction={o:effect_of_matching(rows,ep["slots"],o)for o in ep["foes"]},all_seed_interactions={str(s):{o:effect_of_matching(rows,ep["slots"],o,s)for o in ep["foes"]}for s in SEEDS},absolute_WLD=absolute,query_policy_costs=dict(stats),TRAIN_loss=trainloss,price_order_unanimity={m:len(v)==4 and len(set(map(tuple,v)))==1 for m,v in order.items()},exposure=dict(current_TRAIN_records=len(train_roots),EVAL_records=len(roots),overlap=len(train_roots&roots)),paid_nodes=t["nodes"]+ev["nodes"],producer_seconds=t["seconds"]+ev["seconds"],scope="Finite same-budget TRAINprotocol interaction under fixedplainfoes. Allprice/seed/role/contextcells; rewardbounds notCIs. q2approximate, actorquerycaps equal butactualcost/episodes/TDterms differ. No population/causalgradient/universalpriceorder claim. Engineering/audits/transportadditional.")
 (E/"summary.json").write_text(json.dumps(r,indent=2));(E/"trajectory-divergence.json").write_text(json.dumps(dict(status="PASS_FIXED_FOE_FIRST_DIVERGENCE",pairs=trajectories),indent=2))
 print(json.dumps(dict(status=r["status"],EVAL=ev,contrasts={c:{m:{o:v["bounds"]for o,v in x["by_foe"].items()}for m,x in ms.items()}for c,ms in out.items()},interaction={o:v["bounds"]for o,v in r["matching_interaction"].items()},paid_nodes=r["paid_nodes"],seconds=r["producer_seconds"])))
if __name__=="__main__":run()
