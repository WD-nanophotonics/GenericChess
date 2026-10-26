"""Source-bound proof-consumer controls on the already published history packet."""
from collections import Counter
import argparse,gzip,json,time
from pathlib import Path
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution
from generic_chess.rules.schema import ruleset_from_dict
from scripts.leaper_truth_compatibility import bind_context, compare_contexts, qualify, verify_saved_tree,verify_bound_tree,verify_action_bound,digest



def trim_supplied_tree(nodes,root_key,bound,*,direction="lower",value_seat=0):
    """Extract a strategy from existing labels only; the consumer verifies it.

    No absent state/action is constructed or assigned a value. This helper is
    used only on old exposed proof controls, never experiential start selection.
    """
    by={digest(n["state"]):n for n in nodes};pending=[root_key];seen=set();answer=[]
    def holds(value):
        v=value if value_seat==0 else -value
        return v>=bound if direction=="lower" else v<=bound
    while pending:
        key=pending.pop()
        if key in seen:continue
        seen.add(key);source=by[key];children=source["children"]
        if children:
            existential=(source["state"]["position"]["side_to_move"]==value_seat)==(direction=="lower")
            if existential:
                choices=[ch for ch in children if holds(by[digest(ch["state"])]["value"])]
                if not choices:raise ValueError("source labels supply no strategy for this bound")
                children=choices[:1]
            pending.extend(digest(ch["state"]) for ch in children)
        answer.append(dict(state=source["state"],children=children))
    return answer

def run():
    start=time.perf_counter()
    inputs=json.loads(gzip.decompress(Path("docs/research/data/leaper_h6_initial_truth_20261023/inputs.json.gz").read_bytes()))
    raw=Path("docs/research/data/leaper_history_context_20261024/evidence.json.gz").read_bytes()
    packet=json.loads(gzip.decompress(raw));saved=json.loads(packet["documents_utf8"]["context/literal.json"])
    rules={f["fingerprint"]:f["rule"] for f in inputs["families"] if f.get("rule")}
    compiled={fp:compile_legacy_ruleset_for_semantic_execution(r) for fp,r in rules.items()}
    totals=Counter();cases=[];bound_counts=Counter();bound_rows=[]
    for case in saved["cases"]:
        contexts=[[],[]]
        rows=[]
        for origin,row in enumerate(case["rows"]):
            for arm,a in enumerate(row["arms"]):
                fp=a["fingerprint"]
                c=bind_context(rules[fp],a["final_record"],compiled=compiled[fp])
                if c.identity["state_sha256"]!=digest(a["final_state"]):raise ValueError("saved full-state differs")
                proof=verify_saved_tree(c,a["complete_tree"])
                if proof["root_value"]!=a["value"]:raise ValueError("saved root label differs from checked proof")
                coverage=qualify(c,c,proof["action_labels"],[proof["root_value"]]*2)
                for seat in (0,1):
                    actual_value=proof["root_value"] if seat==0 else -proof["root_value"]
                    for direction in ("lower","upper"):
                        for bound in (-1,0,1):
                            if (direction=="lower" and bound>actual_value) or (direction=="upper" and bound<actual_value):continue
                            trimmed=trim_supplied_tree(a["complete_tree"],c.identity["state_sha256"],bound,direction=direction,value_seat=seat)
                            checked=verify_bound_tree(c,trimmed,bound,direction=direction,value_seat=seat)
                            bound_counts.update(checked["counts"]);bound_counts["certificates"]+=1
                            bound_rows.append(dict(case=case["label"],origin=origin,arm=arm,**checked))
                root_node=next(n for n in a["complete_tree"] if digest(n["state"])==c.identity["state_sha256"])
                if root_node["children"]:
                    edge=root_node["children"][0]
                    child=next(n for n in a["complete_tree"] if n["state"]==edge["state"])
                    trimmed=trim_supplied_tree(a["complete_tree"],digest(child["state"]),child["value"])
                    action_proof=verify_action_bound(c,edge["action"],trimmed,child["value"])
                    if action_proof["wdl_bounds"][0]!=child["value"]:raise ValueError("parent-action proof binding differs")
                    bound_counts["parent_action_bindings"]+=1
                contexts[arm].append(c)
                totals.update(proof["counts"]);totals["trees"]+=1
                rows.append(dict(origin=origin,arm=arm,context=c.identity,proof=proof,coverage=coverage))
        mismatches=[]
        for arm,cc in enumerate(contexts):
            mismatch=compare_contexts(cc[0],cc[1]);totals["history_pairs"]+=1
            if mismatch["status"]!="INCOMPATIBLE":raise ValueError("different histories incorrectly share labels")
            if cc[0].identity["position_sha256"]!=cc[1].identity["position_sha256"]:raise ValueError("control not same Position")
            mismatches.append(dict(arm=arm,comparison=mismatch,same_position=True,
                                   same_ply=cc[0].identity["ply"]==cc[1].identity["ply"]))
        cases.append(dict(label=case["label"],histories=rows,comparisons=mismatches))
    return dict(status="PASS",counts=dict(totals),cases=cases,bound_counts=dict(bound_counts),bound_proofs=bound_rows,seconds=time.perf_counter()-start,
                packet_sha256=__import__("hashlib").sha256(raw).hexdigest(),
                source_document_digest=digest(saved),new_solver_calls=0,new_Player_calls=0,
                scope="Checks existing supplied complete proof labels/transitions, never solves missing states. Old exposed controls only, no PRIMARY candidate.")


def main():
    p=argparse.ArgumentParser();p.add_argument("--output",type=Path,required=True);a=p.parse_args()
    result=run();a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(dict(status=result["status"],counts=result["counts"],seconds=result["seconds"])))

if __name__=="__main__":main()
