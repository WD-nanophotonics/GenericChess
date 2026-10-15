"""Paid TRAIN information diagnostic; no WDL-based root selection or newgo."""
import collections,json,random,statistics
from pathlib import Path
from scripts.generic_proof_roles import roles,row_role
from scripts.generic_proof_study_audit import incomplete


def diagnostic(folder):
    p=Path(folder);plan=json.loads((p/"plan.json").read_text());rows=[json.loads(x) for x in (p/"run/games.jsonl").read_text().splitlines() if json.loads(x)["phase"]=="TRAIN"]
    fs=[f["family"] for f in plan["families"] if f["phase"]=="TRAIN"];nr=2*len(roles(plan))*len(plan["opponents"])
    assert all(sum(r["family"]==f and r["price_index"]==i for r in rows)==nr for f in fs for i in range(len(plan["prices"])))
    assert not any(incomplete(r,plan) for r in rows)
    scores={f:[sum(r["payoff"] or 0 for r in rows if r["family"]==f and r["price_index"]==i) for i in range(len(plan["prices"]))] for f in fs}
    rng=random.Random(2026101556);frequency=collections.Counter()
    for _ in range(5000):
        sampled=[rng.choice(fs) for _ in fs];v=[sum(scores[f][i] for f in sampled) for i in range(len(plan["prices"]))]
        frequency[min(range(len(v)),key=lambda i:(-v[i],plan["prices"][i]))]+=1
    by={(r["family"],r["color"],r["opponent"],row_role(r),r["price_index"]):r for r in rows};base=plan.get("baseline_index",0);pairs=changes=actionchanges=both=0;items=[]
    for f in fs:
        per=[]
        for color in (0,1):
            for op in plan["opponents"]:
                for role in roles(plan):
                    a=by[f,color,op["id"],role,base]
                    for i in range(len(plan["prices"])):
                        if i==base:continue
                        b=by[f,color,op["id"],role,i];pairs+=1
                        event=(a["payoff"] or 0)!=(b["payoff"] or 0);changes+=event
                        # OTHER candidate's first own turn may be after opponent
                        # chose a different move. Only compare identical states.
                        aa=next((x for x in a["trajectory"] if x["actor"][-1]==a["candidate_side"]),None)
                        bb=next((x for x in b["trajectory"] if x["actor"][-1]==b["candidate_side"]),None)
                        prefix=lambda r:[(x["actor"],x["decision"]["action"]) for x in r["trajectory"][:next((j for j,x in enumerate(r["trajectory"]) if x["actor"][-1]==r["candidate_side"]),len(r["trajectory"]))]]
                        comparable=aa is not None and bb is not None and aa["actor"]==bb["actor"] and prefix(a)==prefix(b)
                        changed=comparable and aa["decision"]["action"]!=bb["decision"]["action"]
                        actionchanges+=changed;both+=comparable
                        per.append(dict(role=role,opponent=op["id"],color=color,price_index=i,comparable_first_own_state=comparable,first_own_action_changed=changed,event_changed=event,payoffs=[a["payoff"],b["payoff"]]))
        rv={role:[sum(r["payoff"] or 0 for r in rows if r["family"]==f and row_role(r)==role and r["price_index"]==i) for i in range(len(plan["prices"]))] for role in roles(plan)}
        canceled=[]
        for i in range(len(plan["prices"])):
            effects=[rv[role][i]-rv[role][base] for role in roles(plan)]
            if sum(effects)==0 and any(effects):canceled.append(dict(price_index=i,role_effects=effects))
        items.append(dict(family=f,scores=scores[f],flat_scores=len(set(scores[f]))==1,role_scores=rv,opposite_role_effect_cancellations=canceled,comparisons=per))
    paid=json.loads((p/"result.json").read_text())
    assert paid["status"]=="COMPLETE", "full measured batch incomplete; do not claim complete density"
    full_seconds=paid["seconds"];nonflat=sum(not x["flat_scores"] for x in items)
    density=dict(full_paid_study_seconds=full_seconds,includes="All executed TRAIN and DEV games plus run setup, no subset-time denominator. Standalone qualification and Agent engineering separate.",nonflat_family_vectors=nonflat,nonflat_vectors_per_paid_second=nonflat/full_seconds,sum_family_grid_net_ranges_per_paid_second=sum(max(v)-min(v) for v in scores.values())/full_seconds,role_canceled_families=sum(bool(x["opposite_role_effect_cancellations"]) for x in items),meaning="Exposed TRAIN objective variation/cost diagnostic only, not learning gain or stable signal; actual independent DEV gains remain necessary.")
    out=dict(status="COMPLETE_TRAIN_ONLY_DIAGNOSTIC",actual_result_density=density,TRAIN_families=len(fs),bootstrap_grid_selection_frequency=dict(frequency),bootstrap_replicates=5000,flat_families=sum(x["flat_scores"] for x in items),paid_pair_comparisons=pairs,event_changed_pairs=changes,identical_first_own_state_pairs=both,first_own_action_changes=actionchanges,families=items,scope="Descriptive exposed TRAIN only, no new engine queries, filtering, DEVselection or claim of independent online training. Bootstrap keeps all colors/opponents/roles of sampled family together. Exact prior actor/action prefix also required for first-own-state comparison; same-board different-history is never an action-response control.")
    (p/"role_diagnostic.json").write_text(json.dumps(out,indent=2),encoding="utf-8")
    print(json.dumps({k:v for k,v in out.items() if k!="families"}))


if __name__=="__main__":
    import sys;diagnostic(sys.argv[1])
