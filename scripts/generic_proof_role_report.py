"""Role-stratified finite-event analysis; family resampling keeps all roles paired."""
import collections,json,random,statistics,time
from pathlib import Path
from scripts.generic_proof_roles import roles,row_role
from scripts.generic_proof_study_audit import planned_bounds,quantile


def report(folder):
    p=Path(folder);plan=json.loads((p/"plan.json").read_text());rows=[json.loads(x) for x in (p/"run/games.jsonl").read_text().splitlines()]
    selection=json.loads((p/"selection.json").read_text()) if (p/"selection.json").exists() else None
    base=plan.get("baseline_index",0);selected=selection["selected_index"] if selection else 1
    dev=[r for r in rows if r["phase"]=="DEV"];families=[f["family"] for f in plan["families"] if f["phase"]=="DEV"]
    spec={"A":(False,base),"B":(True,base),"C":(False,selected),"D":(True,selected)}
    cells=[];contrasts=[];rng=random.Random(2026101556)
    for role in roles(plan):
        for op in [None]+[o["id"] for o in plan["opponents"]]:
            planned=2*len(families)*(len(plan["opponents"]) if op is None else 1)
            for label,(proof,index) in spec.items():
                data=[r for r in dev if row_role(r)==role and (op is None or r["opponent"]==op) and r["proof"]==proof and r["price_index"]==index]
                cells.append(dict(role=role,opponent=op or "MIXED",cell=label,n=len(data),outcomes=dict(collections.Counter(str(r["payoff"]) for r in data)),net=sum(r["payoff"] or 0 for r in data),actual_game_seconds=sum(r["seconds"] for r in data),**planned_bounds(data,planned,plan)))
    for role in [None]+list(roles(plan)):
        for op in [None]+[o["id"] for o in plan["opponents"]]:
            data=[r for r in dev if (role is None or row_role(r)==role) and (op is None or r["opponent"]==op)]
            by={(r["family"],r["color"],r["opponent"],row_role(r),r["proof"],r["price_index"]):r for r in data}
            for left,right,name in [("A","B","candidate_solver_policy" if "opponent_proof" in plan else "joint_solver_policy"),("A","C","price_plain"),("B","D","price_with_solver")]:
                values=[];missing=[]
                for family in families:
                    changes=[]
                    for color in (0,1):
                        for o in plan["opponents"]:
                            if op is not None and o["id"]!=op:continue
                            for rr in roles(plan):
                                if role is not None and rr!=role:continue
                                a=by.get((family,color,o["id"],rr,*spec[left]));b=by.get((family,color,o["id"],rr,*spec[right]))
                                if a is not None and b is not None:changes.append((b["payoff"] or 0)-(a["payoff"] or 0))
                    expected=2*(len(plan["opponents"]) if op is None else 1)*(len(roles(plan)) if role is None else 1)
                    if len(changes)==expected:values.append(sum(changes)/expected)
                    else:missing.append(family)
                if values:
                    draws=[sum(rng.choice(values) for _ in values)/len(values) for _ in range(5000)]
                    contrasts.append(dict(role=role or "BALANCED",opponent=op or "MIXED",contrast=name,event_delta=statistics.mean(values),family95=[quantile(draws,.025),quantile(draws,.975)],complete_families=len(values),missing_families=missing))
    train=[r for r in rows if r["phase"]=="TRAIN"];scores=[]
    for index,price in enumerate(plan["prices"]):
        for role in roles(plan):
            data=[r for r in train if r["price_index"]==index and row_role(r)==role]
            scores.append(dict(price=price,price_index=index,role=role,n=len(data),net=sum(r["payoff"] or 0 for r in data),outcomes=dict(collections.Counter(str(r["payoff"]) for r in data))))
    equal=[]
    for phase in ("TRAIN","DEV"):
        paid=[r for r in rows if r["phase"]==phase and r["price_index"]==base and r["proof"]==r.get("opponent_proof",r["proof"]) and next(o for o in plan["opponents"] if o["id"]==r["opponent"])["nodes"]==plan["candidate_nodes"]]
        for proof in sorted({r["proof"] for r in paid}):
            by={(r["family"],r["color"],row_role(r)):r for r in paid if r["proof"]==proof};count=equal_paths=equal_rewards=nonzero=0;diffs=[]
            for (family,color,role),a in by.items():
                if role!="TO_MOVE":continue
                b=by.get((family,color,"OTHER"))
                if b is None:continue
                count+=1;sig=lambda r:[(x["actor"],x["decision"]["action"]) for x in r["trajectory"]]
                same=sig(a)==sig(b) and a["end"]==b["end"] and a["terminal"]==b["terminal"]
                equal_paths+=same;opposite=(a["payoff"] is None and b["payoff"] is None) or (a["payoff"] is not None and b["payoff"] is not None and a["payoff"]==-b["payoff"])
                equal_rewards+=opposite;nonzero+=opposite and a["payoff"] not in (None,0)
                if not same or not opposite:diffs.append(dict(family=family,color=color,path_equal=same,payoffs=[a["payoff"],b["payoff"]]))
            equal.append(dict(phase=phase,proof=proof,paired=count,equal_paths=equal_paths,opposite_payoffs=equal_rewards,nonzero_opposite=nonzero,differences=diffs))
    out=dict(status="DESCRIPTIVE_ROLE_REPORT",opponent_policy=("FIXED_"+str(plan["opponent_proof"]) if "opponent_proof" in plan else "CHANGES_WITH_CANDIDATE_PROOF_ARM_LEGACY"),TRAIN_scores=scores,DEV_cells=cells,DEV_contrasts=contrasts,equal_budget_baseline_symmetry=equal,selection=selection,scope="Fixed finite H16 plus already verified physical tails, no infinite-WDL or human-price claim. CI resamples complete independent families with all colors/roles/opponents kept paired; finite unknown contributes zero event, remains unknown for outcome bounds. Per-role/opponent strata exploratory, no multiple-comparison success selection. Timed proof can change actual visited work between otherwise same player inputs.")
    (p/"role_report.json").write_text(json.dumps(out,indent=2),encoding="utf-8")
    print(json.dumps(dict(TRAIN=scores,contrasts=[x for x in contrasts if x["opponent"]=="MIXED"],symmetry=equal)))


if __name__=="__main__":
    import sys;report(sys.argv[1])
