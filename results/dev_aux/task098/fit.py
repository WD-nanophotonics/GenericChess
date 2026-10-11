import hashlib,json,math,sys,time
from pathlib import Path
import chess
R=Path.cwd();sys.path.insert(0,str(R/"results/dev_aux/task096"));from harness import *
B=Path(__file__).resolve().parent;source=R/"results/dev_aux/task096";training=json.loads((source/"training.json").read_bytes());assert training["complete"] and not training["errors"]
def uci(a):
 f,t=a["from"],a["to"];return chess.square_name(chess.square(*f))+chess.square_name(chess.square(*t))+(a.get("promotion_target_id") or "").lower()
counts={};samples=[];used_games=[];trajectories=[];excluded=[];types=("P","N","B","R","Q")
for p in sorted(source.glob("train-*.json")):
 d=json.loads(p.read_bytes());counts[d["status"]]=counts.get(d["status"],0)+1
 if not d["terminal"]:excluded.append({"game":p.stem,"reason":"censored"});continue
 board=chess.Board();gs=[];actions=d["opening"]["actions"]+d["actions"]
 for j,a in enumerate(actions):
  m=chess.Move.from_uci(uci(a));assert m in board.legal_moves;board.push(m)
  if j+1>len(d["opening"]["actions"]) and (j+1-len(d["opening"]["actions"]))%8==0 and board.halfmove_clock>=4 and not board.is_game_over(claim_draw=False):
   x=[len(board.pieces(chess.PIECE_SYMBOLS.index(k.lower()),chess.WHITE))-len(board.pieces(chess.PIECE_SYMBOLS.index(k.lower()),chess.BLACK)) for k in types];gs.append({"game":p.stem,"ply":j+1,"x":x,"y":d["white_score"],"fen":board.fen()})
 if not gs:excluded.append({"game":p.stem,"reason":"no_predeclared_quiet_samples"});continue
 used_games.append(p.stem);trajectories.append(hashlib.sha256(json.dumps(actions,sort_keys=True).encode()).hexdigest())
 for s in gs:s["weight"]=1/len(gs);samples.append(s)
def rank(mat):
 a=[list(map(float,row)) for row in mat];r=0
 for col in range(5):
  k=next((k for k in range(r,len(a)) if abs(a[k][col])>1e-8),None)
  if k is None:continue
  a[r],a[k]=a[k],a[r];v=a[r][col];a[r]=[x/v for x in a[r]]
  for k in range(len(a)):
   if k!=r:
    v=a[k][col];a[k]=[x-v*y for x,y in zip(a[k],a[r])]
  r+=1
  if r==len(a):break
 return r
write(B/"dataset.json",{"counts":counts,"used_games":used_games,"distinct_trajectories":len(set(trajectories)),"samples":samples,"excluded":excluded,"feature_rank":rank([s["x"] for s in samples]) if samples else 0,"source_training_sha256":hashlib.sha256((source/"training.json").read_bytes()).hexdigest()})
def loss_grad(theta):
 weights=[208*math.exp(t) for t in theta];loss=0.;g=[0.]*4
 for s in samples:
  z=(208*s["x"][0]+sum(w*x for w,x in zip(weights,s["x"][1:])))/1040;z=max(-60,min(60,z));pred=1/(1+math.exp(-z));loss+=s["weight"]*(max(z,0)-s["y"]*z+math.log1p(math.exp(-abs(z))))
  for j in range(4):g[j]+=s["weight"]*(pred-s["y"])*weights[j]*s["x"][j+1]/1040
 den=max(1,len(used_games));return loss/den,[x/den for x in g]
start=time.perf_counter();out={"complete":False,"samples":len(samples),"used_games":len(used_games),"fits":[],"heldout":[],"scope":"Outcome-only observational fit from random-material teacher games, not causal values or mature search."};write(B/"fit.json",out)
for seed in (103,104,105):
 theta=training["runs"][(103,104,105).index(seed)]["initial_theta"][:];initial=theta[:];trace=[]
 for step in range(100):
  loss,g=loss_grad(theta);trace.append({"step":step,"loss":loss,"gradient":g,"theta":theta[:]});theta=[max(math.log(.25),min(math.log(16),t-.1*v)) for t,v in zip(theta,g)]
 out["fits"].append({"seed":seed,"initial_theta":initial,"final_theta":theta,"initial_weights":make_weights(initial),"final_weights":make_weights(theta),"loss_initial":loss_grad(initial)[0],"loss_final":loss_grad(theta)[0],"trace":trace,"outcome_signal":any(abs(v)>1e-12 for s in trace for v in s["gradient"])})
write(B/"fit.json",out)
# Freeze fresh heldout starts before any match; never use them in fit or selection.
openings=[make_opening(30000+i) for i in range(4)];write(B/"heldout-openings.json",openings)
try:
 for fit in out["fits"]:
  rec={"seed":fit["seed"],"games":[]};out["heldout"].append(rec)
  for oi,op in enumerate(openings):
   for owner in (0,1):
    if time.perf_counter()-start>600:raise TimeoutError("frozen600sec fit/heldout stage cap")
    name=f"heldout-s{fit['seed']}-o{oi}-c{owner}";g=play(fit["final_weights"] if owner==0 else fit["initial_weights"],fit["initial_weights"] if owner==0 else fit["final_weights"],op);write(B/(name+".json"),g);rec["games"].append({"game":name,"final_owner":owner,"points":None if g["white_score"] is None else (g["white_score"] if owner==0 else 1-g["white_score"])});write(B/"fit.json",out)
  print(fit["seed"],fit["initial_weights"],"to",fit["final_weights"],"loss",fit["loss_initial"],fit["loss_final"],"heldout",[x["points"] for x in rec["games"]],flush=True)
 out["complete"]=True
except Exception as x:out["error"]=type(x).__name__+": "+str(x)
finally:
 out["wall_seconds"]=time.perf_counter()-start;write(B/"fit.json",out);print("DONE",out["complete"],len(samples),len(used_games),out.get("error"),round(out["wall_seconds"],1),flush=True)
