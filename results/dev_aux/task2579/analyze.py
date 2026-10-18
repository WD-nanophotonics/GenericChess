"""All price effects against SAME boundedq2 opponents; no crosspanel causal claim."""
from pathlib import Path
from collections import Counter,defaultdict
import itertools,json,hashlib
from results.dev_aux.task2568.summary import contrast,bounds
D=Path("results/dev_aux/task2579")
def run():
 p=json.loads((D/"eval-plan.json").read_text());reg=json.loads((D/"registration.json").read_text());ev=json.loads((D/"eval-result.json").read_text());a=json.loads((D/"eval-started.json").read_text());assert a["utc"]>reg["registered_at"]
 for name,h in reg["pins"].items():assert hashlib.sha256(Path(name).read_bytes()).hexdigest()==h
 expected=set(itertools.product([0],(1977,8173,27182,31415),range(511001,511005),(0,1),(m+"|q2"for m in("initial","TD_plain","TD_q2")),p["foes"]))
 assert len(p["slots"])==192 and set(map(tuple,p["slots"]))==expected
 t=json.loads((D/"result.json").read_text());src=Path("results/dev_aux/task2577/result.json");assert t["source_binding_sha"]==hashlib.sha256(src.read_bytes()).hexdigest()
 assert t["arms"]==[a for a in json.loads(src.read_text())["arms"]if a["method"].endswith("|q2")]
 rows={tuple(g["slot"]):g for g in map(json.loads,(D/"eval-games.jsonl").open())};assert len(rows)==ev["actual"];stats=defaultdict(Counter)
 for q in map(json.loads,(D/"eval-queries.jsonl").open()):
  color=q["slot"][3];s=q["search_stats"];assert q["active_q2"]and s["q_limit"]==2
  stats["candidate"if q["actor"]==color else"fixed_q2_foe"].update(dict(queries=1,nodes=q["nodes"],qnodes=s["qnodes"],check_evasion_nodes=s["check_evasion_nodes"],q_cap_still_tactical=s["q_cap_still_tactical"],failed=not q["complete"]))
 assert all(stats[k]["qnodes"]>0 for k in("candidate","fixed_q2_foe"))or ev["actual"]==0
 contrasts={}
 for left,right in(("TD_plain","initial"),("TD_q2","initial"),("TD_q2","TD_plain")):
  a,b=left+"|q2",right+"|q2"
  contrasts[left+"-"+right]=dict(all=contrast(rows,p["slots"],a,b),by_foe={o:contrast(rows,[s for s in p["slots"]if s[5]==o],a,b)for o in p["foes"]},by_seed={str(seed):{o:contrast(rows,[s for s in p["slots"]if s[1]==seed and s[5]==o],a,b)for o in p["foes"]}for seed in(1977,8173,27182,31415)},by_role={str(c):{o:contrast(rows,[s for s in p["slots"]if s[3]==c and s[5]==o],a,b)for o in p["foes"]}for c in(0,1)})
 absolute={}
 for label,o in itertools.product(("initial|q2","TD_plain|q2","TD_q2|q2"),p["foes"]):
  ss=[s for s in p["slots"]if s[4]==label and s[5]==o];cc=Counter();lo=hi=0
  for s in ss:
   g=rows.get(tuple(s));a,b=bounds(g);lo+=a;hi+=b;cc["missing"if g is None else"U"if g["reward"]is None else"W"if g["reward"]>0 else"L"if g["reward"]<0 else"D"]+=1
  absolute[label+"/"+o]=dict(n=len(ss),counts=dict(cc),W_minus_L_bounds=[lo/len(ss),hi/len(ss)],room_to_max=[1-hi/len(ss),1-lo/len(ss)])
 train_roots={json.dumps(g["initial_record"],sort_keys=True)for g in map(json.loads,Path("results/dev_aux/task2576/games.jsonl").open())}
 main_roots={json.dumps(g["initial_record"],sort_keys=True)for g in map(json.loads,Path("results/dev_aux/task2577/eval-games.jsonl").open())}
 roots={json.dumps(g["initial_record"],sort_keys=True)for g in rows.values()}
 exposure=dict(full_roots=len(roots),current_TRAIN_overlaps=len(roots&train_roots),main_EVAL_overlaps=len(roots&main_roots),not_historically_unexposed_guarantee=True)
 r=dict(exposure=exposure,status="PASS_SAME_Q2_FOES_ALL_PRICE_CELLS",EVAL=ev,contrasts=contrasts,absolute_WLD=absolute,query_policies=dict(stats),scope=reg["estimand"]+" AllU/missing retained, finiteboundsnotCI; previousmainusesdifferentroots, nocrosspanelcausalopponenteffect/universalpricesclaim.")
 (D/"summary.json").write_text(json.dumps(r,indent=2));print(json.dumps(dict(status=r["status"],EVAL=ev,contrasts={k:{o:v["bounds"]for o,v in x["by_foe"].items()}for k,x in contrasts.items()},absolute=absolute)))
if __name__=="__main__":run()
