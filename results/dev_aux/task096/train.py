import json,math,random,time,hashlib
from pathlib import Path
from harness import *
B=Path(__file__).resolve().parent;start=time.perf_counter();seeds=(103,104,105);starts={str(seed):[random.Random(seed).uniform(0,1)] for seed in []}
for seed in seeds:
 rng=random.Random(seed);starts[str(seed)]=[rng.uniform(math.log(.35),math.log(12)) for _ in TYPES]
# Freeze starts, all train/holdout opening actions and protocol before outcome.
train=[make_opening(10000+i) for i in range(8)];heldout=[make_opening(20000+i) for i in range(3)]
decl={"question":"Narrow project Native material-only search: can outcome-selected perturbations improve random leaf weights? Mature Fairy remains blocked.","starts_theta":starts,"starts_weights":{k:make_weights(v) for k,v in starts.items()},"types":TYPES,"normalization":"P=208 fixed; K=0; hand=0; other logratio bounds[log(.25),log(16)]. No expert ordering/ratios in sampling or objective.","iterations":4,"train_openings":train,"heldout_openings":heldout,"nodes_per_move":512,"max_depth":8,"qdepth":0,"max_plies_per_game":160,"tt_mib":4,"execution":"Sequential, fresh engine for each contestant each game, no bind/default profile/learned order/net/tablebase; own fresh game, full Core history import and public legality.","update":"Per seed iteration perturb four nonpawn logweights by independent fixed-seed +/-0.4 Rademacher. Each +/- candidate faces current on same2openings, both colors (4games/candidate). Candidate scoring uses lower=sum knownpoints/4 and upper=(knownpoints+censored)/4. Choose +/- only if its lower>other.upper AND lower>0.5; else hold. No score/mate-distance/cutoff eval target. One update per iteration; no result-dependent extra games/caps.","heldout":"Each final vs own untouched initial on3 disjoint openings bothcolors (6games); no model or condition choice from results.","max_games":114,"stage_wall_cap_seconds":1500,"estimated_cost":"Pilot128node 81plies4.65s;512node/160ply declared114games conservative below25min, fixed1500s interruption cap. No expected>1h run.","limits":"Canonical project Western semantics, repetition_limit100000/max_ply1000, no FIDE no-progress/claim adjudication; rules unchanged. This is not mature engine, no universal convergence/strength/domain claim.","source_pin":"pinned_bebe","native_binary_sha256":"2f97cfb8816bc963163207095bf40ac990169284cd0cfb2e7b545f0a6bf07bf1"}
decl["changed_premise"]="Task095 source-guided None representation removes zero-dynamic feature construction, three actual512node pairs preserve all non-time fields; original task093 partial arm retained, no old cap extension or holdout/target fitting. Same114game/fullselection protocol on declared already exposed train openings; heldout still untouched.";decl["estimated_cost"]="Actual Task0950.025s caller versus0.28-0.33; predicted114x160x0.03~9min plus overhead, fixed1500sec cap, no expected>1hrun.";write(B/"declaration.json",decl);out={"complete":False,"declaration_sha256":hashlib.sha256((B/"declaration.json").read_bytes()).hexdigest(),"runs":[],"total_games":0,"errors":[],"cost":{"wall_seconds":0}}
class StageCap(Exception):pass
def run_game(w0,w1,op,name):
 if time.perf_counter()-start>=1500:raise StageCap("frozen_stage_wall_cap")
 g=play(w0,w1,op);write(B/(name+".json"),g);out["total_games"]+=1
 if g["error"]:out["errors"].append({"game":name,"error":g["error"]})
 return name,g
try:
 for seed in seeds:
  initial=starts[str(seed)];theta=initial[:];rng=random.Random(seed+900000);run={"seed":seed,"initial_theta":initial,"initial_weights":make_weights(initial),"iterations":[],"heldout":[]};out["runs"].append(run)
  for step in range(4):
   delta=[rng.choice((-1,1)) for _ in TYPES];candidates=[[max(math.log(.25),min(math.log(16),t+sign*.4*d)) for t,d in zip(theta,delta)] for sign in (1,-1)];current=make_weights(theta);rec={"iteration":step,"before":current,"delta":delta,"candidates":[],"selected":None};run["iterations"].append(rec)
   for arm,candidate in enumerate(candidates):
    w=make_weights(candidate);entry={"arm":arm,"theta":candidate,"weights":w,"games":[],"known_points":0.,"censored":0,"lower":None,"upper":None};rec["candidates"].append(entry)
    for oi,op in enumerate(train[2*step:2*step+2]):
     for candidate_owner in (0,1):
      name=f"train-s{seed}-i{step}-a{arm}-o{oi}-c{candidate_owner}";path,g=run_game(w if candidate_owner==0 else current,current if candidate_owner==0 else w,op,name);entry["games"].append(path)
      if g["white_score"] is None:entry["censored"]+=1
      else:entry["known_points"]+=g["white_score"] if candidate_owner==0 else 1-g["white_score"]
    entry["lower"]=entry["known_points"]/4;entry["upper"]=(entry["known_points"]+entry["censored"])/4
   for arm,entry in enumerate(rec["candidates"]):
    other=rec["candidates"][1-arm]
    if entry["lower"]>other["upper"] and entry["lower"]>.5:rec["selected"]=arm;theta=entry["theta"][:]
   rec["after"]=make_weights(theta);out["cost"]["wall_seconds"]=time.perf_counter()-start;write(B/"training.json",out);print(seed,step,"selected",rec["selected"],"bounds",[(e["lower"],e["upper"]) for e in rec["candidates"]],"secs",round(time.perf_counter()-start,1),flush=True)
  run["final_theta"]=theta;run["final_weights"]=make_weights(theta);run["updates"]=sum(x["selected"] is not None for x in run["iterations"])
  for oi,op in enumerate(heldout):
   for final_owner in (0,1):
    name=f"heldout-s{seed}-o{oi}-c{final_owner}";path,g=run_game(run["final_weights"] if final_owner==0 else run["initial_weights"],run["initial_weights"] if final_owner==0 else run["final_weights"],op,name);run["heldout"].append({"game":path,"final_owner":final_owner,"points":None if g["white_score"] is None else (g["white_score"] if final_owner==0 else 1-g["white_score"])})
  write(B/"training.json",out)
 out["complete"]=True
except Exception as x:out["stop_reason"]=type(x).__name__+": "+str(x)
finally:
 out["cost"]["wall_seconds"]=time.perf_counter()-start;write(B/"training.json",out);print("DONE",out["complete"],out["total_games"],out.get("stop_reason"),round(out["cost"]["wall_seconds"],1),flush=True)
