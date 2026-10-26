"""Source-bound proof-consumer controls on the already published history packet."""
from collections import Counter
import argparse,gzip,json,time
from pathlib import Path
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution
from generic_chess.rules.schema import ruleset_from_dict
from scripts.leaper_truth_compatibility import bind_context, compare_contexts, qualify, verify_saved_tree,digest


def run():
    start=time.perf_counter()
    inputs=json.loads(gzip.decompress(Path("docs/research/data/leaper_h6_initial_truth_20261023/inputs.json.gz").read_bytes()))
    raw=Path("docs/research/data/leaper_history_context_20261024/evidence.json.gz").read_bytes()
    packet=json.loads(gzip.decompress(raw));saved=json.loads(packet["documents_utf8"]["context/literal.json"])
    rules={f["fingerprint"]:f["rule"] for f in inputs["families"] if f.get("rule")}
    compiled={fp:compile_legacy_ruleset_for_semantic_execution(r) for fp,r in rules.items()}
    totals=Counter();cases=[]
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
    return dict(status="PASS",counts=dict(totals),cases=cases,seconds=time.perf_counter()-start,
                packet_sha256=__import__("hashlib").sha256(raw).hexdigest(),
                source_document_digest=digest(saved),new_solver_calls=0,new_Player_calls=0,
                scope="Checks existing supplied complete proof labels/transitions, never solves missing states. Old exposed controls only, no PRIMARY candidate.")


def main():
    p=argparse.ArgumentParser();p.add_argument("--output",type=Path,required=True);a=p.parse_args()
    result=run();a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(dict(status=result["status"],counts=result["counts"],seconds=result["seconds"])))

if __name__=="__main__":main()
