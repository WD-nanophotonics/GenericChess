from pathlib import Path
import json,collections
P=Path(".local_agent/matched-d2-20261016");Q=P/"cross-future";plan=json.loads((Q/"plan.json").read_bytes());seed=plan["selected_seed"];cellcase=plan["cases"][0]
out={}
for name,file in[("00",P/"results.json"),("11",P/"future-q1/results.json")]:
 d=json.loads(file.read_bytes());assert d["complete"]
 for cell in"CD":out[name+"-"+cell]=next(g for g in d["rows"]if g["seed"]==seed and cell in g["cells"])
d=json.loads((Q/"results.json").read_bytes());assert d["complete"]
for g in d["rows"]:
 for cell in g["cells"]:out[str(g["actor_q"])+str(g["opponent_q"])+"-"+cell]=g
for k,g in out.items():
 assert g["parent_sha256"]==cellcase["state_sha256"]and g["forced_action"]==cellcase["forced_actions"][k[-1]]
diff=[]
for cell in"CD":
 for lo,hi in[("00","10"),("00","01"),("10","11"),("01","11")]:
  a,b=out[lo+"-"+cell],out[hi+"-"+cell];found=None
  for i,(x,y)in enumerate(zip(a["rows"],b["rows"])):
   assert x["before_sha256"]==y["before_sha256"]
   if x.get("action")!=y.get("action"):
    found=dict(step=i,side=x["side"],role="ORIGINAL_ACTOR"if x["side"]==a["actor"]else"OPPONENT",before_sha256=x["before_sha256"],completed_depths=[x["result"]["completed_depth"],y["result"]["completed_depth"]],action_lo=x.get("action"),action_hi=y.get("action"));break
  diff.append(dict(cell=cell,lo=lo,hi=hi,first_difference=found))
x=dict(complete=True,seed=seed,original_actor=next(iter(out.values()))["actor"],table={mode:{c:out[mode+"-"+c]["outcome"]for c in"CD"}for mode in["00","10","01","11"]},physical_games_new=4,existing_diagonal_games_reused=4,first_differences=diff,retained_depths_by_mode={mode:dict(collections.Counter(str(r["result"]["completed_depth"])for c in"CD"for r in out[mode+"-"+c]["rows"]))for mode in["00","10","01","11"]},interpretation="Case34101C: ownq1 convertsLOSS toWINwithopponentq0/q1; D: opponentq1alone causesWINtoLOSS, ownq1restoresWIN. Bothconversion andresponseinteraction occur, no singlepriceorqblame. FirstID terminalflipcase selected, notclaimedexplanationof34202negativeD-Coraggregatepopulation.",label_tiers="Observed ruleterminal WIN/LOSS exacttrajectoryfact. Inference tooptimalQ/crosspolicyvalue unproved/approximate. UNKNOWN remainsunknown; no newWDLgate.")
(Q/"summary.json").write_bytes((json.dumps(x,indent=2)+"\n").encode());print(json.dumps(x,indent=2))
