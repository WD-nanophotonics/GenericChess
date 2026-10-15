"""Paid full-history caller validation cost attribution, zero new enginego.

Candidate checks all legal action identities, but only the executed transition.
It is a scoped KRN wrapper experiment, not a product/runtime optimization.
"""
import json,time,statistics
from pathlib import Path
from generic_chess.core.movegen import legal_actions
from generic_chess.core.transition import apply_action
from scripts.generic_proof_rnb_bridge import compile_rnb,from_actor,actor_state,uci
from scripts.generic_royal_actor import RoyalActor
from scripts.generic_proof_native_study import mod,sha


def run(folder):
    out=Path(folder);out.mkdir(exist_ok=False);source=Path("results/dev_aux/task1788");p=json.loads((source/"plan.json").read_text());c=compile_rnb(4);model=RoyalActor(4);fs={f["family"]:f for f in p["families"]};chosen={};seen=set()
    for line in (source/"run/games.jsonl").read_text().splitlines():
        row=json.loads(line)
        if row["phase"]!="TRAIN":continue
        state=from_actor(c,fs[row["family"]]["roots"][row["color"]])
        for step in row["trajectory"]:
            action=next(a for a in legal_actions(state,c) if uci(a)==step["decision"]["action"])
            key=repr(state)
            if step["decision"]["source"]=="EXTERNAL_SEARCH" and len(chosen.get(row["family"],[]))<8 and key not in seen:
                chosen.setdefault(row["family"],[]).append((state,uci(action)));seen.add(key)
            state=apply_action(state,action,c)
    cases=[(f,s,u) for f,ss in sorted(chosen.items()) for s,u in ss];assert 0<len(cases)<=64
    plan=dict(status="FROZEN_BEFORE_TIMING",source=str(source/"run/games.jsonl"),source_sha256=sha(source/"run/games.jsonl"),cases=[dict(family=f,actor=actor_state(s),ply=s.ply_count,history_records=len(s.history),action=u,exact_state_sha256=__import__("hashlib").sha256(repr(s).encode()).hexdigest()) for f,s,u in cases],repeats=5,available_paid_states=len(cases),per_family_cases={str(f):len(chosen.get(f,[])) for f in fs if fs[f]["phase"]=="TRAIN"},total_seconds=120,source_code_sha256=sha(__file__),purpose="Can repeated all-child wrapper validation be reduced to all legal identities plus exact chosen transition? Full-history inputs from paidTRAIN only, no reward-based selection or search change.")
    (out/"plan.json").write_text(json.dumps(plan,indent=2),encoding="utf-8");stop=mod("FRONTIER_COST_STOP56","results/dev_aux/task166/run.py").stop;start=time.perf_counter();deadline=start+120;records=[];error=None
    def measure(state,move,full):
        begun=time.perf_counter();expected=dict(model.moves(actor_state(state)));actual={uci(a):a for a in legal_actions(state,c)};assert set(actual)==set(expected)
        for key in actual if full else [move]:assert actor_state(apply_action(state,actual[key],c))==expected[key]
        return time.perf_counter()-begun,len(actual) if full else 1
    try:
        for i,(family,state,move) in enumerate(cases):
            for repeat in range(plan["repeats"]):
                stop()
                if time.perf_counter()>=deadline:raise RuntimeError("frozen_wallcap")
                modes=[True,False] if (i+repeat)%2 else [False,True];pair={}
                for mode in modes:
                    elapsed,transitions=measure(state,move,mode);pair["FULL" if mode else "SELECTED"]=dict(seconds=elapsed,actual_public_transitions=transitions)
                records.append(dict(case=i,family=family,repeat=repeat,**pair))
    except BaseException as exc:error=type(exc).__name__+":"+str(exc)
    full=sum(x["FULL"]["seconds"] for x in records);selected=sum(x["SELECTED"]["seconds"] for x in records)
    result=dict(status="COMPLETE_PAID_CALLER_ATTRIBUTION" if error is None else "PARTIAL_PRESERVED",error=error,paired=len(records),planned_pairs=len(cases)*5,full_seconds=full,selected_seconds=selected,selected_to_full_ratio=selected/full if full else None,full_public_transitions=sum(x["FULL"]["actual_public_transitions"] for x in records),selected_public_transitions=sum(x["SELECTED"]["actual_public_transitions"] for x in records),records=records,native_go=0,seconds=time.perf_counter()-start,scope="All legal-set equality retained, exact chosen child/full history agree. This measures different validation work, not same-work engine speedup or observed whole-game gain. Both modes replay already-paid states; futureclosedloop trial needed before adoption. Concurrent1792 and ordinary projects limit wall interpretation.")
    (out/"result.json").write_text(json.dumps(result,indent=2),encoding="utf-8");print(json.dumps({k:v for k,v in result.items() if k!="records"}))


if __name__=="__main__":
    import sys;run(sys.argv[1])
