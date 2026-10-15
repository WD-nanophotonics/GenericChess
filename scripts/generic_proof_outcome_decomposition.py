"""Paired actual W/L/draw/unknown transitions; no horizon extension or refit."""
import collections,json,random,statistics
from pathlib import Path
from scripts.generic_proof_roles import row_role
from scripts.generic_proof_study_audit import quantile


def run(folders,outfile):
    batches=[];matrix=collections.Counter();cells={"B":collections.Counter(),"D":collections.Counter()};N=0
    for folder in folders:
        p=Path(folder);plan=json.loads((p/"plan.json").read_text());selected=json.loads((p/"selection.json").read_text())["selected_index"];base=plan.get("baseline_index",0)
        rows=[json.loads(x) for x in (p/"run/games.jsonl").read_text().splitlines() if json.loads(x)["phase"]=="DEV"]
        by={(r["family"],r["color"],row_role(r),r["opponent"],r["price_index"]):r for r in rows if r["proof"]};vectors=[]
        for f in [f for f in plan["families"] if f["phase"]=="DEV"]:
            values=[]
            for color in (0,1):
                for role in plan.get("candidate_roles",["TO_MOVE"]):
                    for op in plan["opponents"]:
                        a=by[f["family"],color,role,op["id"],base];b=by[f["family"],color,role,op["id"],selected]
                        label=lambda r:{1:"W",-1:"L",0:"DRAW",None:"UNKNOWN"}[r["payoff"]]
                        la,lb=label(a),label(b);matrix[la+"->"+lb]+=1;cells["B"][la]+=1;cells["D"][lb]+=1;N+=1
                        values.append(dict(win=int(lb=="W")-int(la=="W"),loss=int(lb=="L")-int(la=="L"),unknown=int(lb=="UNKNOWN")-int(la=="UNKNOWN"),net=(b["payoff"] or 0)-(a["payoff"] or 0)))
            vectors.append({k:statistics.mean(v[k] for v in values) for k in values[0]})
        batches.append(vectors)
    rng=random.Random(2026101556);contrasts={}
    for metric in ("win","loss","unknown","net"):
        obs=[r[metric] for batch in batches for r in batch]
        samples=[statistics.mean(rng.choice(batch)[metric] for batch in batches for _ in batch) for _ in range(5000)]
        contrasts[metric]=dict(delta=statistics.mean(obs),conditional_family95=[quantile(samples,.025),quantile(samples,.975)])
    result=dict(status="COMPLETE_PAIRED_ACTUAL_OUTCOME_DECOMPOSITION",paired_games=N,cells={k:dict(v) for k,v in cells.items()},transition_matrix=dict(matrix),contrasts=contrasts,scope="Conditional frozen TRAIN-selected B-to-D, same actual planned pairs and familystrata. UNKNOWN stays distinct. Win-only increase is a finite-policy actual win-event difference, not infinite win probability. Loss->UNKNOWN is displayed, not called a proven improvement in infinite WDL. No newgo/refit or post-result extension.")
    Path(outfile).write_text(json.dumps(result,indent=2),encoding="utf-8");print(json.dumps(result))


if __name__=="__main__":
    import sys;run(sys.argv[1:-1],sys.argv[-1])
