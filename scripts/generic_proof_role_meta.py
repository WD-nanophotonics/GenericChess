"""Conditional two-cohort family-block meta; no newgo or DEV candidate choice."""
import json,random,statistics
from pathlib import Path
from scripts.generic_proof_roles import roles,row_role
from scripts.generic_proof_study_audit import quantile,incomplete


def run(folders,outfile):
    batches=[];descriptions=[]
    for folder in folders:
        p=Path(folder);plan=json.loads((p/"plan.json").read_text());result=json.loads((p/"result.json").read_text());assert result["status"]=="COMPLETE"
        selected=json.loads((p/"selection.json").read_text())["selected_index"];base=plan.get("baseline_index",0)
        rows=[json.loads(x) for x in (p/"run/games.jsonl").read_text().splitlines() if json.loads(x)["phase"]=="DEV"]
        assert not any(incomplete(r,plan) for r in rows)
        by={(r["family"],r["color"],r["opponent"],row_role(r),r["proof"],r["price_index"]):r for r in rows};batch=[]
        for f in [f for f in plan["families"] if f["phase"]=="DEV"]:
            counts={};delta={}
            for role in [None]+list(roles(plan)):
                for op in [None]+[o["id"] for o in plan["opponents"]]:
                    for left,right,label in [( (False,base),(True,base),"solver_policy"),((False,base),(False,selected),"price_plain"),((True,base),(True,selected),"price_with_solver")]:
                        changes=[]
                        for color in (0,1):
                            for o in plan["opponents"]:
                                if op is not None and o["id"]!=op:continue
                                for rr in roles(plan):
                                    if role is not None and rr!=role:continue
                                    a=by[f["family"],color,o["id"],rr,*left];b=by[f["family"],color,o["id"],rr,*right]
                                    changes.append((b["payoff"] or 0)-(a["payoff"] or 0))
                        delta[str((role or "BALANCED",op or "MIXED",label))]=statistics.mean(changes)
            batch.append(delta)
        batches.append(batch);descriptions.append(dict(folder=folder,selected=plan["prices"][selected],families=len(batch),opponent_policy="fixed" if "opponent_proof" in plan else "jointly switches on solver contrast"))
    rng=random.Random(2026101556);contrasts=[]
    for key in batches[0][0]:
        values=[row[key] for batch in batches for row in batch]
        sampled=[]
        for _ in range(5000):
            draw=[rng.choice(batch)[key] for batch in batches for _ in batch];sampled.append(statistics.mean(draw))
        contrasts.append(dict(key=key,event_delta=statistics.mean(values),family95=[quantile(sampled,.025),quantile(sampled,.975)]))
    result=dict(status="COMPLETE_CONDITIONAL_STRATIFIED_META",cohorts=descriptions,contrasts=contrasts,scope="Each frozen TRAIN choice fixed within its independent DEVcohort; bootstrap stratifies family blocks by cohort and retains all roles/colors/opponents. Only two training cohorts, not a confidence interval covering retraining uncertainty or universal price. Strata exploratory. Legacy solver contrast changes both players; only new fixed-opponent studies isolate candidate contribution. No cross-mu pooling unless explicitly declared.")
    Path(outfile).write_text(json.dumps(result,indent=2),encoding="utf-8");print(json.dumps(result))


if __name__=="__main__":
    import sys;run(sys.argv[1:-1],sys.argv[-1])
