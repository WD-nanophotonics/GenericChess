import json,re,hashlib,collections
from pathlib import Path
R=Path.cwd();B=Path(__file__).resolve().parent;out={"complete":False,"checks":[],"failures":[]}
t=json.loads((R/"results/dev_aux/task096/training.json").read_bytes())
def check(label,test):
 if not test:raise AssertionError(label)
 out["checks"].append(label)
check("trial actually complete",t["complete"] and not t["errors"] and t["total_games"]==114)
check("declaration hash",t["declaration_sha256"]==hashlib.sha256((R/"results/dev_aux/task096/declaration.json").read_bytes()).hexdigest())
games=[]
for path in sorted((R/"results/dev_aux/task096").glob("*.json")):
 d=json.loads(path.read_bytes())
 if "actions" not in d:continue
 check(path.stem+" records aligned",len(d["actions"])==len(d["metrics"]) and not d["error"] and len(d["actions"])<=160)
 check(path.stem+" actual backend",all(not m["used_fallback"] for m in d["metrics"]))
 games.append(d)
for run in t["runs"]:
 for iteration in run["iterations"]:
  recomputed=[]
  for arm in iteration["candidates"]:
   known=0.;censored=0
   for name in arm["games"]:
    d=json.loads((R/"results/dev_aux/task096"/(name+".json")).read_bytes());owner=int(name[-1])
    if d["white_score"] is None:censored+=1
    else:known+=d["white_score"] if owner==0 else 1-d["white_score"]
   lo=known/4;hi=(known+censored)/4
   check("candidate bound"+str((run["seed"],iteration["iteration"],arm["arm"])),lo==arm["lower"] and hi==arm["upper"])
   recomputed.append((lo,hi))
  eligible=[a for a,(lo,hi) in enumerate(recomputed) if lo>recomputed[1-a][1] and lo>.5]
  check("selection"+str((run["seed"],iteration["iteration"])),iteration["selected"]==(eligible[-1] if eligible else None))
 check("unchanged final"+str(run["seed"]),run["updates"]==0 and run["initial_weights"]==run["final_weights"])
out["summary"]={"games":len(games),"status":dict(collections.Counter(d["status"] for d in games)),"nodes":sum(m["nodes"] for d in games for m in d["metrics"]),"search_moves":sum(len(d["metrics"]) for d in games),"updates":sum(r["updates"] for r in t["runs"]),"wall_seconds":t["cost"]["wall_seconds"]}
# Public payload review excludes raw consultation/account material and compiled binaries.
files=[];banned=re.compile(rb"[UTC]0[A-Z0-9]{9}|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}|[B]EGIN [A-Z ]*PRIVATE KEY|access_token\s*[=:]|api_key\s*[=:]")
for number in range(91,105):
 for path in sorted((R/"results/dev_aux"/f"task{number:03d}").rglob("*")):
  if not path.is_file() or "__pycache__" in path.parts:continue
  if path==B/"review.json":continue
  check("public payload "+path.relative_to(R).as_posix(),path.suffix not in (".exe",".dll",".pyd",".pyc") and banned.search(path.read_bytes()) is None)
  files.append(dict(path=path.relative_to(R).as_posix(),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),bytes=path.stat().st_size))
out["manifest"]=files;out["check_count"]=len(out["checks"]);out["complete"]=True
(B/"review.json").write_bytes((json.dumps(out,indent=2)+"\n").encode());print(json.dumps({k:v for k,v in out.items() if k not in ("checks","manifest")}))
