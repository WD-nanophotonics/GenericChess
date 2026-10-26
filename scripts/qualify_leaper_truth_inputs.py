"""Read-only qualification of published H6 inputs; no solving or Player calls."""
from __future__ import annotations
from collections import Counter
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import time
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution
from generic_chess.rules.schema import ruleset_from_dict
from scripts.leaper_truth_compatibility import bind_context, digest, action_coverage


def load(path):
    raw=Path(path).read_bytes()
    return json.loads(gzip.decompress(raw) if str(path).endswith(".gz") else raw)


def qualify_corpus(directory):
    start=time.perf_counter(); directory=Path(directory)
    inputs=load(directory/"inputs.json.gz");truth=load(directory/"truth.json.gz")
    if digest(inputs)!=truth["source_digest"]:
        raise ValueError("truth does not bind the actual complete inputs")
    rows={r["id"]:r for r in truth["roots"]}
    if len(rows)!=len(truth["roots"]) or len(rows)!=len(inputs["rows"]):
        raise ValueError("duplicate or missing root source bindings")
    counts=Counter(); families=[]; identities=set();records=set(); action_count=Counter()
    for family in inputs["families"]:
        if family.get("rule") is None:
            families.append(dict(family=family["family"],status="UNKNOWN_MISSING_RULE",
                                 source_status=family["status"]))
            continue
        fingerprint=family["fingerprint"]
        rule=ruleset_from_dict(family["rule"])
        compiled=compile_legacy_ruleset_for_semantic_execution(rule)
        if compiled.ruleset_fingerprint!=fingerprint:
            raise ValueError("family fingerprint differs")
        if digest(truth["rules"][fingerprint])!=digest(family["rule"]):
            raise ValueError("truth RuleSet does not bind input RuleSet")
        fc=Counter(); classes=Counter()
        for source in inputs["rows"]:
            if source["family"]!=family["family"]:continue
            context=bind_context(family["rule"],source["full_record"],compiled=compiled)
            if context.identity["state_sha256"]!=source["state_sha256"]:
                raise ValueError("literal replay differs from frozen full state")
            if digest(source["full_state"])!=source["state_sha256"]:
                raise ValueError("source full state annotation differs")
            row=rows[source["state_sha256"]]
            if row["fingerprint"]!=fingerprint or row["record"]!=source["full_record"]:
                raise ValueError("truth full record/fingerprint differs")
            coverage=action_coverage(context,row["action_bounds"],row["wdl_bounds"],value_seat=0)
            if coverage["labelled_actions"]!=coverage["legal_actions"]:
                raise ValueError("frozen complete action truth has a coverage gap")
            for r in coverage["rows"]:classes[r["classification"]]+=1
            for key in ("legal_actions","labelled_actions","exact_action_labels","unlabelled_actions"):
                fc[key]+=coverage[key]
            fc["roots"]+=1
            identities.add(context.identity["state_sha256"])
            records.add((fingerprint,context.identity["record_sha256"]))
            action_count[len(context.legal_actions)]+=1
        counts.update(fc)
        families.append(dict(family=family["family"],fingerprint=fingerprint,
                             status="COMPATIBLE_SOURCE_CLAIM",counts=dict(fc),
                             action_classifications=dict(classes)))
        print(json.dumps(dict(family=family["family"],roots=fc["roots"],elapsed=time.perf_counter()-start)),flush=True)
    return dict(format="aux-truth-input-qualification-v1",status="PASS",
                sources={name:hashlib.sha256((directory/name).read_bytes()).hexdigest()
                         for name in ("inputs.json.gz","truth.json.gz")},
                counts=dict(counts), distinct_full_states=len(identities),
                distinct_full_records=len(records), action_count_histogram=dict(action_count),
                families=families,seconds=time.perf_counter()-start,
                scope="Literal replay and source-bound action coverage only. No independent minimax re-solve, new candidate or holdout.",
                new_Player_calls=0,new_solver_calls=0,new_games=0)


def main():
    parser=argparse.ArgumentParser();parser.add_argument("--directory",type=Path,default=Path("docs/research/data/leaper_h6_initial_truth_20261023"));parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args(); result=qualify_corpus(args.directory)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")

if __name__=="__main__":main()
