"""Read-only exact finite-panel reaggregation for unknown reward intervals."""
from pathlib import Path
from collections import Counter
import hashlib,json
ROOT=Path(__file__).resolve().parents[3]
TASK=Path(__file__).parent
INPUTS={
 "task2606":ROOT/"results/dev_aux/task2606/eval-games.jsonl",
 "task2609":ROOT/"results/dev_aux/task2609/eval-games.jsonl",
 "task2610":ROOT/"results/dev_aux/task2610/attempt-2/eval-games.jsonl",
}
CONTRASTS=(("TD95","initial"),("LocalLambda","initial"),("LocalLambda","TD95"))

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def exact_or_interval(a,b):
    alo,ahi=(-1,1) if a is None else (a,a)
    blo,bhi=(-1,1) if b is None else (b,b)
    return alo-bhi,ahi-blo

def old_interval(a,b):
    if a is None or b is None:return -2,2
    return a-b,a-b

def panel(path):
    rows=[json.loads(line) for line in path.read_text(encoding="utf-8-sig").splitlines() if line]
    table={}
    wdls={}
    for row in rows:
        rule,seed,family,color,endpoint,_foe=row["slot"]
        key=(rule,seed,family,color,endpoint)
        if key in table:raise AssertionError(f"duplicate slot: {key}")
        value=row["reward"]
        if value is not None and value not in (-1,0,1):raise AssertionError(f"bad reward: {value}")
        table[key]=value
        c=wdls.setdefault(endpoint,Counter())
        c["UNKNOWN" if value is None else {-1:"LOSS",0:"DRAW",1:"WIN"}[value]]+=1
    endpoints=set(k[4] for k in table)
    bases={(r,s,f,c) for r,s,f,c,e in table}
    for base in bases:
        for endpoint in endpoints:
            if (*base,endpoint) not in table:raise AssertionError(f"missing matched endpoint: {base}/{endpoint}")
    out=[]
    for left,right in CONTRASTS:
        old_lo=old_hi=tight_lo=tight_hi=0
        unknown_left=unknown_right=both=0
        n=0
        for r,s,f,c in sorted(bases):
            a=table[(r,s,f,c,left)];b=table[(r,s,f,c,right)]
            lo,hi=exact_or_interval(a,b);olo,ohi=old_interval(a,b)
            tight_lo+=lo;tight_hi+=hi;old_lo+=olo;old_hi+=ohi;n+=1
            unknown_left+=a is None;unknown_right+=b is None;both+=(a is None and b is None)
        out.append({
          "contrast":f"{left}-{right}","strata":n,
          "unknown_left":unknown_left,"unknown_right":unknown_right,"both_unknown":both,
          "old_blanket_mean_bound":[old_lo/n,old_hi/n],
          "tight_mean_bound":[tight_lo/n,tight_hi/n],
          "tight_sum_bound":[tight_lo,tight_hi]
        })
    return {"rows":len(rows),"wdl_by_endpoint":{k:dict(v) for k,v in wdls.items()},"contrasts":out}

def main():
    started=json.loads((TASK/"started.json").read_text(encoding="utf-8-sig"))
    for name,expected in started["source_sha256"].items():
        if sha(ROOT/name)!=expected: raise AssertionError(f"source hash mismatch: {name}")
    results={name:panel(path) for name,path in INPUTS.items()}
    result={
      "task":"DEV_AUX2615","status":"COMPLETE_READ_ONLY_REAGGREGATION",
      "input_sha256":{name:sha(path) for name,path in INPUTS.items()},
      "source_sha256":{name:sha(ROOT/name) for name in (
        "results/dev_aux/task2606/analyze.py",
        "results/dev_aux/task2609/audit_eval.py",
        "results/dev_aux/task2610/compare_panels.py")},
      "panels":results,
      "interpretation":"Exact finite-panel bounds from fixed saved rewards, not confidence intervals, independent root samples, or population effects.",
      "old_outputs_unchanged":True
    }
    (TASK/"result.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps(result,indent=2))
if __name__=="__main__":main()
