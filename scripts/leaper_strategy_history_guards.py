"""Proof-local count guards on the fixed published H6/repeat2 worlds only.

A sufficient-condition study, not a TT key, cache, general rule compiler or new
solver. Source strategies are already supplied; target values never guide moves.
"""
from collections import Counter
import argparse,gzip,json,time,hashlib
from pathlib import Path
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution
from generic_chess.rules.schema import ruleset_from_dict
from scripts.leaper_truth_compatibility import bind_context,verify_bound_tree,digest
from scripts.verify_leaper_truth_controls import trim_supplied_tree


def _derive_fixed_world_guard(source,nodes,bound,direction,*,value_seat=0):
    # This theorem is only evaluated on the frozen, previously admitted plain
    # Leaper worlds below. Its assumptions are not a new generic admission gate.
    c=source.session.compiled
    if c.max_ply!=6 or c.repetition_limit!=2 or c.repetition_policy!="draw":
        raise ValueError("outside fixed H6/repeat2 draw scope")
    if any(getattr(c,k,None) for k in ("declarations","automatic_adjudications","consecutive_action_adjudications","repeated_cycle_target_conditions","no_progress_draw")):
        raise ValueError("history has additional adjudication mechanisms")
    checked=verify_bound_tree(source,nodes,bound,direction=direction,value_seat=value_seat)
    root_counts=dict(source.session.state.repetition_counts);q=c.repetition_limit
    weak=(direction=="lower" and bound<=0) or (direction=="upper" and bound>=0)
    requirements={}
    for node in nodes:
        state=node["state"];status=state["terminal_status"]["status"]
        key=state["history"][-1]["position_key"]
        future=dict(state["repetition_counts"]).get(key,0)-root_counts.get(key,0)
        if future<0:raise ValueError("fixed-domain counts were reset unexpectedly")
        if weak:
            if status=="repetition":requirements[key]=max(requirements.get(key,0),q-future)
        elif status=="ongoing":
            limit=q-future-1;requirements[key]=min(requirements.get(key,q),limit)
    return dict(kind="MIN_PRIOR_COUNTS" if weak else "MAX_PRIOR_COUNTS",requirements=requirements,
                source_proof_digest=checked["certificate_sha256"],
                scope="Sufficient guards for this supplied proof only under the fixed position-local H6 draw rules. Not whole-game equivalence or heuristic/TT reuse.")


def _satisfies(guard,context):
    counts=dict(context.session.state.repetition_counts)
    if guard["kind"]=="MIN_PRIOR_COUNTS":return all(counts.get(k,0)>=v for k,v in guard["requirements"].items())
    return all(counts.get(k,0)<=v for k,v in guard["requirements"].items())


def study(revalidation_path):
    tick=time.perf_counter()
    input_bytes=Path("docs/research/data/leaper_h6_initial_truth_20261023/inputs.json.gz").read_bytes()
    if hashlib.sha256(input_bytes).hexdigest()!="75ce22f0ce2b4bc522a8f1e0149d5e68a138eefc45468068779e84146720956b":
        raise ValueError("guard theorem study requires the fixed published H6 source")
    inputs=json.loads(gzip.decompress(input_bytes))
    packet=json.loads(gzip.decompress(Path("docs/research/data/leaper_history_context_20261024/evidence.json.gz").read_bytes()))
    saved=json.loads(packet["documents_utf8"]["context/literal.json"])
    raw=Path(revalidation_path).read_bytes();prior=json.loads(raw)
    expected={(r["case"],r["arm"],r["source_origin"],r["value_seat"],r["direction"],r["bound"]):r for r in prior["matrix"]}
    if prior["source_document_digest"]!=digest(saved):raise ValueError("simulation matrix source differs")
    rules={f["fingerprint"]:f["rule"] for f in inputs["families"] if f.get("rule")}
    compiled={fp:compile_legacy_ruleset_for_semantic_execution(ruleset_from_dict(r)) for fp,r in rules.items()}
    counts=Counter();rows=[];seen=set();conservative_witness=None
    for case in saved["cases"]:
        for arm in (0,1):
            aa=[r["arms"][arm] for r in case["rows"]]
            cc=[bind_context(rules[a["fingerprint"]],a["final_record"],compiled=compiled[a["fingerprint"]]) for a in aa]
            for origin in (0,1):
                source,target=cc[origin],cc[1-origin];a=aa[origin]
                for seat in (0,1):
                    sv=a["value"] if seat==0 else -a["value"]
                    for direction in ("lower","upper"):
                        for bound in (-1,0,1):
                            if (direction=="lower" and bound>sv) or (direction=="upper" and bound<sv):continue
                            key=case["label"],arm,origin,seat,direction,bound
                            if key in seen:raise ValueError("duplicate matrix row")
                            seen.add(key)
                            cert=trim_supplied_tree(a["complete_tree"],source.identity["state_sha256"],bound,direction=direction,value_seat=seat)
                            guard=_derive_fixed_world_guard(source,cert,bound,direction,value_seat=seat)
                            if not _satisfies(guard,source):raise ValueError("a source proof fails its own derived guard")
                            passed=_satisfies(guard,target);actual=expected[key]["result"]["status"]=="REVALIDATED_FINITE_STRATEGY_BOUND"
                            if passed and not actual:raise ValueError("sufficient guard allowed a failed simulation")
                            if not passed and actual and conservative_witness is None:
                                from scripts.leaper_truth_compatibility import revalidate_bound_strategy
                                replay=revalidate_bound_strategy(source,target,cert,bound,direction=direction,value_seat=seat)
                                conservative_witness=dict(case=case["label"],arm=arm,source_origin=origin,value_seat=seat,direction=direction,bound=bound,
                                                          source_context=source.identity,target_context=target.identity,source_certificate=cert,
                                                          guard=guard,target_replay=replay)
                            counts["guard_pass_and_revalidated" if passed else "guard_fail_but_revalidated" if actual else "guard_fail_and_not_proved"]+=1
                            counts["requirements:"+str(len(guard["requirements"]))]+=1
                            rows.append(dict(case=case["label"],arm=arm,source_origin=origin,value_seat=seat,direction=direction,bound=bound,
                                             guard=guard,target_satisfies=passed,actual_simulation_passed=actual))
    if seen!=set(expected):raise ValueError("matrix coverage differs")
    return dict(status="PASS",counts=dict(counts),rows=rows,conservative_witness=conservative_witness,seconds=time.perf_counter()-tick,
                revalidation_sha256=hashlib.sha256(raw).hexdigest(),new_solver_calls=0,new_Player_calls=0,
                scope="Fixed old contexts and proof-local sufficient conditions only. Failed guard invokes no value conclusion; no runtime key/cache or claim of measured acceleration.")


def main():
    p=argparse.ArgumentParser();p.add_argument("--revalidation",type=Path,required=True);p.add_argument("--output",type=Path,required=True);a=p.parse_args()
    result=study(a.revalidation);a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(dict(status=result["status"],counts=result["counts"],seconds=result["seconds"])))

if __name__=="__main__":main()
