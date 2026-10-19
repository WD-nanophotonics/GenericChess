"""Explain effective TD information per paid search node, without new labels."""
from pathlib import Path
from collections import defaultdict,Counter
from math import tanh,sqrt
import json,sys
def run(directory="results/dev_aux/task2580"):
 d=Path(directory);p=json.loads((d/"plan.json").read_text());t=json.loads((d/"result.json").read_text());sig=json.loads((d/"signals.json").read_text());counts=defaultdict(Counter);gram={};credits=defaultdict(list)
 for row in sig:
  key=str(tuple(row["key"]));credits[key].append(row["credit"])
  assert row["credit"][0]==0
 for q in map(json.loads,(d/"queries.jsonl").open()):
  key=str((q["seed"],q["method"]));cc=counts[key];st=q["search_stats"];cc.update(dict(all_queries=1,all_nodes=q["nodes"],failed_queries=not q["complete"],qnodes=st["qnodes"],still_tactical_cutoffs=st["q_cap_still_tactical"],check_evasion_nodes=st["check_evasion_nodes"]))
  cc["candidate_queries"if q["actor"]==q["color"]else"fixed_foe_queries"]+=1
  cc["candidate_nodes"if q["actor"]==q["color"]else"fixed_foe_nodes"]+=q["nodes"]
  if not q["observed"]:continue
  cc["observed"]+=1
  if q["pv_terminal"]:cc["terminal_PV_zero_gradient"]+=1;continue
  phi=q["pv_phi"][1:];grad=[x*(1-tanh(q["value"]/10.)**2)/10 for x in phi];cc["zero_free_material_gradient"]+=all(x==0 for x in grad);cc["nonzero_free_material_gradient"]+=any(x!=0 for x in grad);cc["grad_norm2"]+=sum(x*x for x in grad)
  for j in range(4):cc["excited_"+("N","B","R","Q")[j]]+=grad[j]!=0
  mat=gram.setdefault(key,[[0.]*4 for _ in range(4)])
  for j in range(4):
   for k in range(4):mat[j][k]+=grad[j]*grad[k]
 losses=defaultdict(Counter);curves=defaultdict(list)
 for g in map(json.loads,(d/"games.jsonl").open()):
  key=str((g["seed"],g["method"]));st=g["stats"];cc=losses[key];cc["terms"]+=st["samples"];cc["weighted_loss"]+=st["samples"]*(st["loss"]or 0);cc["games"]+=1;cc["terminal"]+=g["outcome"]is not None;cc["U"]+=g["outcome"]is None
  curves[key].append(dict(episode=g["index"],paid_nodes=g["total_nodes"],TD_terms=st["samples"],changing_data_loss=st["loss"],terminal=g["outcome"]is not None,weights=g["weights"]))
 def rank(a):
  a=[list(row)for row in a];pivot=0;scale=max([abs(x)for r in a for x in r]or[0])
  for j in range(4):
   k=max(range(pivot,4),key=lambda k:abs(a[k][j]))if pivot<4 else 0
   if pivot==4 or abs(a[k][j])<=max(1e-14,scale*1e-10):continue
   a[pivot],a[k]=a[k],a[pivot];v=a[pivot][j];a[pivot]=[x/v for x in a[pivot]]
   for i in range(pivot+1,4):
    v=a[i][j];a[i]=[x-v*y for x,y in zip(a[i],a[pivot])]
   pivot+=1
  return pivot
 out={}
 for a in t["arms"]:
  k=str((a["seed"],a["method"]));c=counts[k];l=losses[k];cr=credits[k];net=[sum(v[j]for v in cr)for j in range(5)];absolute=[sum(abs(v[j])for v in cr)for j in range(5)];mat=gram.get(k,[[0.]*4 for _ in range(4)])
  out[k]=dict(counts=dict(c),loss=dict(l),weighted_training_loss=l["weighted_loss"]/max(1,l["terms"]),paid_nodes=a["nodes"],seconds=a["seconds"],nonzero_observations_per_Mnodes=c["nonzero_free_material_gradient"]*1e6/max(1,a["nodes"]),valid_TD_terms_per_Mnodes=l["terms"]*1e6/max(1,a["nodes"]),gradient_gram=mat,numerical_gram_rank=rank(mat),episode_recommendation_net=net,episode_recommendation_absolute=absolute,episode_credit_coherence=[abs(x)/y if y else None for x,y in zip(net,absolute)])
 result=dict(status="PASS_EFFECTIVE_INFORMATION_ACCOUNTING",arms=out,scope="Descriptivechanging-data diagnostics of ALLpaidqueries and independently reconstructed episodecredits. Freegradientexcitation/rank/coherence isnotidentifiability/convergence/strengthproof; terminalPVzero gradientcanstillcreditearliertrace. No newtarget/reward/modelselection.")
 (d/"information.json").write_text(json.dumps(result,indent=2));(d/"training-curves.json").write_text(json.dumps(dict(curves=curves,scope="Allclosedepisodes, changing-data TRAINloss; no bestcheckpoint/heldoutaccuracy."),indent=2));print(json.dumps({k:dict(nodes=v["paid_nodes"],nonzero_per_M=v["nonzero_observations_per_Mnodes"],terms_per_M=v["valid_TD_terms_per_Mnodes"],gramrank=v["numerical_gram_rank"])for k,v in out.items()}))
if __name__=="__main__":run(sys.argv[1]if len(sys.argv)>1 else"results/dev_aux/task2580")
