"""Paired fixed-visit public-vs-mutable AND/OR mechanism attribution.

No new Native calls. Same rules/full roots/actions/terminal policy/algorithm.
Only complete non-time-limited pairs support fixed-work cost interpretation.
"""
import collections,json,time,statistics
from dataclasses import asdict
from pathlib import Path
from scripts.generic_proof_rnb_bridge import compile_rnb,from_actor
from scripts.generic_win_proof import prove_win,PROVEN_WIN
from scripts.generic_public_win_proof import prove_win_public,verify_public_certificate
from scripts.generic_proof_native_study import mod,sha


def run(folder):
    out=Path(folder);out.mkdir(exist_ok=False);source=Path("results/dev_aux/task1788/plan.json");p=json.loads(source.read_text());fs=[f for f in p["families"] if f["phase"]=="TRAIN"]
    plan=dict(status="FROZEN_BEFORE_CALLS",source_plan=str(source),source_sha256=sha(source),families=fs,node_caps=[64,256,1024],per_call_seconds=2.,total_seconds=300.,algorithm="iterative AND/OR depth16 both paths",ordering="Alternate first backend byfamily+color+capindex",purpose="Choose whether public path is practical as opt-in unsupported-history fallback. No WDL label source or production default. Fixed-work matching/cost, not Elo or exclusive machine timing.",sources={x:sha(x) for x in ["scripts/generic_win_proof.py","scripts/generic_public_win_proof.py","scripts/generic_proof_public_path.py","scripts/generic_public_path_cost.py"]})
    (out/"plan.json").write_text(json.dumps(plan,indent=2),encoding="utf-8")
    stop=mod("COST_PUBLIC_STOP56","results/dev_aux/task166/run.py").stop;start=time.perf_counter();deadline=start+plan["total_seconds"];c=compile_rnb(4);rows=[];error=None
    with (out/"calls.jsonl").open("x",encoding="utf-8") as log:
        try:
            for f in fs:
                for color,raw in enumerate(f["roots"]):
                    state=from_actor(c,raw)
                    for ci,cap in enumerate(plan["node_caps"]):
                        backends=[("RUNTIME",prove_win),("PUBLIC",prove_win_public)]
                        if (f["family"]+color+ci)%2:backends.reverse()
                        for name,fn in backends:
                            stop()
                            if time.perf_counter()>=deadline:raise RuntimeError("frozen_wallcap")
                            result=fn(c,state,max_nodes=cap,seconds=plan["per_call_seconds"],max_depth=16,cancel=lambda:time.perf_counter()>=deadline)
                            data=asdict(result);data.pop("certificate");tree=repr(result.certificate.tree) if result.certificate else None
                            assert result.pushes==result.pops and result.nodes<=cap
                            receipt=None
                            if result.status==PROVEN_WIN:
                                receipt=verify_public_certificate(c,state,result.certificate,seconds=2.)
                                assert receipt["verified"]
                            row=dict(family=f["family"],color=color,cap=cap,backend=name,tree=tree,result=data,verification=receipt);rows.append(row);log.write(json.dumps(row)+"\n");log.flush()
        except BaseException as exc:error=type(exc).__name__+":"+str(exc)
    paired=[]
    for f in fs:
        for color in (0,1):
            for cap in plan["node_caps"]:
                data=[r for r in rows if (r["family"],r["color"],r["cap"])==(f["family"],color,cap)]
                if len(data)!=2:continue
                a=next(r for r in data if r["backend"]=="RUNTIME");b=next(r for r in data if r["backend"]=="PUBLIC")
                fields=("status","nodes","completed_depth","pushes","pops","terminal_kind","winner","peak_depth")
                matched=all(a["result"][k]==b["result"][k] for k in fields) and a["tree"]==b["tree"]
                paired.append(dict(family=f["family"],color=color,cap=cap,matched_work_and_tree=matched,ratio=b["result"]["seconds"]/a["result"]["seconds"],runtime_seconds=a["result"]["seconds"],public_seconds=b["result"]["seconds"],cutoffs=[a["result"]["reason"],b["result"]["reason"]]))
    groups=[]
    for cap in plan["node_caps"]:
        pp=[r for r in paired if r["cap"]==cap and r["matched_work_and_tree"]]
        groups.append(dict(cap=cap,matched=len(pp),planned=2*len(fs),ratio_of_total_seconds=sum(r["public_seconds"] for r in pp)/sum(r["runtime_seconds"] for r in pp) if pp else None,median_paired_ratio=statistics.median(r["ratio"] for r in pp) if pp else None))
    result=dict(status="COMPLETE_FIXED_WORK_CONTROL" if error is None else "PARTIAL_PRESERVED",error=error,calls=len(rows),planned_calls=len(fs)*2*len(plan["node_caps"])*2,paired=paired,groups=groups,native_go=0,seconds=time.perf_counter()-start,conditions="Paired/counterbalanced under ordinary concurrent project work including1791. No machine exclusivity, noise-free speedup, or arbitrary-history cost claim.")
    (out/"result.json").write_text(json.dumps(result,indent=2),encoding="utf-8");print(json.dumps({k:v for k,v in result.items() if k!="paired"}))


if __name__=="__main__":
    import sys;run(sys.argv[1])
