"""Revalidate old supplied strategies across old paired histories, not new solving."""
from collections import Counter
import argparse,gzip,json,time
from pathlib import Path
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution
from generic_chess.rules.schema import ruleset_from_dict
from scripts.leaper_truth_compatibility import bind_context,revalidate_bound_strategy,digest
from scripts.verify_leaper_truth_controls import trim_supplied_tree


def run():
    tick=time.perf_counter()
    inputs=json.loads(gzip.decompress(Path("docs/research/data/leaper_h6_initial_truth_20261023/inputs.json.gz").read_bytes()))
    packet=json.loads(gzip.decompress(Path("docs/research/data/leaper_history_context_20261024/evidence.json.gz").read_bytes()))
    saved=json.loads(packet["documents_utf8"]["context/literal.json"])
    rules={f["fingerprint"]:f["rule"] for f in inputs["families"] if f.get("rule")}
    compiled={fp:compile_legacy_ruleset_for_semantic_execution(ruleset_from_dict(r)) for fp,r in rules.items()}
    counts=Counter();matrix=[];witnesses={};shortcut_control=None
    for case in saved["cases"]:
        for arm in (0,1):
            aa=[r["arms"][arm] for r in case["rows"]]
            contexts=[bind_context(rules[a["fingerprint"]],a["final_record"],compiled=compiled[a["fingerprint"]]) for a in aa]
            for origin in (0,1):
                source,target=contexts[origin],contexts[1-origin];a=aa[origin];target_value=aa[1-origin]["value"]
                for seat in (0,1):
                    sv=a["value"] if seat==0 else -a["value"]
                    tv=target_value if seat==0 else -target_value
                    for direction in ("lower","upper"):
                        for bound in (-1,0,1):
                            if (direction=="lower" and bound>sv) or (direction=="upper" and bound<sv):continue
                            cert=trim_supplied_tree(a["complete_tree"],source.identity["state_sha256"],bound,direction=direction,value_seat=seat)
                            result=revalidate_bound_strategy(source,target,cert,bound,direction=direction,value_seat=seat)
                            accepted=result["status"]=="REVALIDATED_FINITE_STRATEGY_BOUND"
                            # Existing full-tree labels are a posthoc control, never used to guide target simulation.
                            if accepted and ((direction=="lower" and tv<bound) or (direction=="upper" and tv>bound)):
                                raise ValueError("revalidation contradicts already checked target certificate")
                            bound_true=(tv>=bound if direction=="lower" else tv<=bound)
                            counts[("accepted" if accepted else "not_proved")+(":target_bound_true" if bound_true else ":target_bound_false")]+=1
                            source_repeats=any(n["state"]["terminal_status"]["status"]=="repetition" for n in cert)
                            if not source_repeats:counts[("accepted" if accepted else "not_proved")+":no_source_repetition"]+=1
                            if (shortcut_control is None and not accepted and not source_repeats and
                                    seat==0 and direction=="upper" and bound==-1 and tv==0 and
                                    result.get("reason")=="target terminal violates the source bound"):
                                relaxed=revalidate_bound_strategy(source,target,cert,0,direction="upper",value_seat=0)
                                if relaxed["status"]!="REVALIDATED_FINITE_STRATEGY_BOUND":raise ValueError("weak-bound counterfactual failed")
                                shortcut_control=dict(source_certificate=cert,source_context=source.identity,target_context=target.identity,
                                                      exact_loss_attempt=result,nonwin_attempt=relaxed,
                                                      interpretation="No repetition in this source LOSS proof does not imply exact three-valued LOSS survives another incoming history. The same strategy verifies only the weaker non-WIN upper bound on this target.")
                            counts[result["status"]]+=1
                            if result["status"]=="NOT_PROVED_BY_THIS_CERTIFICATE":counts["failure:"+result["reason"]]+=1
                            else:
                                counts["successful_different_history"]+=int(result["default_context_comparison"]["status"]=="INCOMPATIBLE")
                                counts["early_terminal_prunings"]+=result["simulation_counts"]["early_terminals"]
                            row=dict(case=case["label"],arm=arm,source_origin=origin,value_seat=seat,direction=direction,bound=bound,
                                     source_value=sv,target_value_posthoc=tv,result={k:v for k,v in result.items() if k!="target_certificate"})
                            matrix.append(row)
                            category=("accepted_with_different_history" if accepted else "failed_bound_or_frontier")
                            if category not in witnesses:witnesses[category]=dict(row=row,source_certificate=cert,result=result)
    return dict(status="PASS",counts=dict(counts),matrix=matrix,witnesses=witnesses,shortcut_control=shortcut_control,seconds=time.perf_counter()-tick,
                source_document_digest=digest(saved),new_solver_calls=0,new_Player_calls=0,
                scope="All fixed paired old proof contexts, both seats and all valid source one-sided bounds; no generated rule, target-guided move choice, missing-state solve or production TT deployment.")


def main():
    p=argparse.ArgumentParser();p.add_argument("--output",type=Path,required=True);a=p.parse_args();result=run()
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(dict(status=result["status"],counts=result["counts"],seconds=result["seconds"])))

if __name__=="__main__":main()
