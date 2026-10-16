from pathlib import Path
import json,collections,datetime,sys
P=Path(sys.argv[1])if len(sys.argv)>1 else Path(".local_agent/matched-d2-20261016");v={"WIN":1,"LOSS":-1,"DRAW":0};coeffs={"B-A":{"B":1,"A":-1},"D-C":{"D":1,"C":-1},"C-A":{"C":1,"A":-1},"D-B":{"D":1,"B":-1},"I":{"D":1,"C":-1,"B":-1,"A":1}};panels={}
for name,file in[("d3q0",P/"results.json"),("d3q1",P/"future-q1/results.json"),("d6both",P/"future-depth6/results.json")]:
 d=json.loads(file.read_bytes());assert d["complete"]
 if name=="d6both":
  for q in[0,1]:panels["d6q"+str(q)]=[g for g in d["rows"]if g["future_q"]==q]
 else:panels[name]=d["rows"]
out={}
for name,gs in panels.items():
 rows={}
 for k,coef in coeffs.items():
  fixed=0;radius=0;unknown_games=[];canceled=[]
  for g in gs:
   weight=sum(coef.get(c,0)for c in g["cells"])
   if g["outcome"]=="UNKNOWN":
    if weight:radius+=abs(weight);unknown_games.append(dict(game_id=g["game_id"],seed=g["seed"],weight=weight))
    elif any(c in coef for c in g["cells"]):canceled.append(g["game_id"])
   else:fixed+=weight*v[g["outcome"]]
  rows[k]=dict(finite_observed_net=fixed,unknown_radius=radius,hypothetical_net_outer_interval=[fixed-radius,fixed+radius],mean_outer_interval=[(fixed-radius)/8,(fixed+radius)/8],noncanceling_unknown_games=unknown_games,canceling_shared_unknown_games=canceled)
 out[name]=rows
x=dict(complete=True,computed_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),analysis="Exploratoryafteralllabels, no plannedpower/equivalence/humanfit.",panels=out,assumption="Hypotheticalunobservedterminaltargets in[-1,1]; sameactualsharedtrajectorymusthaveONEtargetacrosscellaliases. Thisisdependentouter-sensitivityanalysis, notproofthatallboundsarefeasiblelegalcontinuations orstatisticalconfidence/optimalWDL. No gameextended, UNKNOWNnotrelabeled.")
(P/"unknown-sensitivity.json").write_bytes((json.dumps(x,indent=2)+"\n").encode());print({k:{a:b["hypothetical_net_outer_interval"]for a,b in z.items()}for k,z in out.items()})
