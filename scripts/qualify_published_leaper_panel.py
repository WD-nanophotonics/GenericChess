"""Literal source binding for an explicitly supplied historical PRIMARY panel.

No Player/solver execution, candidate selection or conversion of source labels
into independently re-solved truth. Diagnostic action dumps are bound by exact
public Core action equality before conversion to canonical action IDs.
"""
from collections import Counter
import argparse,gzip,hashlib,json,time
from pathlib import Path
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.core.actions import action_to_dict
from scripts.leaper_truth_compatibility import bind_context,action_coverage,digest
from scripts.research_record import record_value


def qualify_panel(inputs_path,envelope_path):
    tick=time.perf_counter()
    raw=Path(inputs_path).read_bytes();decoded=gzip.decompress(raw);packet=json.loads(decoded)
    envelope=json.loads(gzip.decompress(Path(envelope_path).read_bytes()))
    if hashlib.sha256(decoded).hexdigest()!=envelope["source_input_hash"]:
        raise ValueError("branch envelope does not bind the published complete input bytes")
    compiled={k:compile_legacy_ruleset_for_semantic_execution(ruleset_from_dict(rule)) for k,rule in packet["rules"].items()}
    for k,rule in packet["rules"].items():
        # The published dictionary key hashes sorted JSON WITH default spaces;
        # it is neither compact JSON SHA nor semantic RuleSet fingerprint.
        if hashlib.sha256(json.dumps(rule,sort_keys=True).encode()).hexdigest()!=k:
            raise ValueError("rule source payload SHA differs")
    counts=Counter();rows=[];contexts=set();fingerprints=set();episodes=set()
    for row in packet["cases"]:
        rule=packet["rules"][row["rule_sha256"]];c=compiled[row["rule_sha256"]]
        ctx=bind_context(rule,row["record"],compiled=c);identity=ctx.identity
        if identity["state_sha256"]!=row["state_sha256"]:raise ValueError("historical full-state replay differs")
        if identity["ply"]!=row["absolute_ply"] or identity["side_to_move"]!=row["actor"]:
            raise ValueError("historical ply/actor annotation differs")
        if identity["max_ply"]-identity["ply"]!=row["remaining"]:
            raise ValueError("historical remaining clock differs")
        if identity["repetition_counts"]!=row["incoming_counts"]:
            raise ValueError("historical incoming count map differs")
        if row["root_own_WDL"]!=(row["root_global_WDL"] if row["actor"]==0 else -row["root_global_WDL"]):
            raise ValueError("historical label perspective differs")
        labels=[];source_actions=set();unknown_labels=0
        for label in row["labelled_actions"]:
            matched=[a for a in ctx.session.legal_actions() if record_value(a)==label["action"]]
            if len(matched)!=1:raise ValueError("diagnostic action does not bind uniquely to literal Core")
            canonical=action_to_dict(matched[0]);key=digest(canonical)
            if key in source_actions:raise ValueError("duplicate source action label")
            source_actions.add(key);value=label["truth"].get("value")
            if type(value) is int and value in (-1,0,1):labels.append(dict(action=canonical,wdl_bounds=[value,value]))
            else:unknown_labels+=1
        if source_actions!={digest(a) for a in ctx.legal_actions}:raise ValueError("historical action frontier not complete")
        coverage=action_coverage(ctx,labels,[row["root_global_WDL"]]*2,value_seat=0)
        counts["contexts"]+=1;counts["legal_actions"]+=coverage["legal_actions"];counts["known_source_action_labels"]+=coverage["labelled_actions"]
        counts["unknown_source_labels"]+=unknown_labels
        counts["all_action_values_equal"]+=int(len({tuple(r["wdl_bounds"]) for r in coverage["rows"]})==1)
        contexts.add(identity["state_sha256"]);fingerprints.add(identity["ruleset_fingerprint"]);episodes.add(row["source_episode"])
        rows.append(dict(key=row["key"],context=identity,coverage=coverage,
                         qualification="LITERAL_CONTEXT/FRONTIER_CHECKED;SOURCE_WDL_CLAIM_NOT_RESOLVED"))
    target=next(r for r in packet["cases"] if r["key"]==envelope["source_key"])
    if target["record"]!=envelope["root_record"] or target["rule_sha256"]!=envelope["rule_sha256"]:
        raise ValueError("prepared branch root is not the exact published source record")
    if len(contexts)!=len(rows):raise ValueError("duplicate contexts need explicit weighting")
    return dict(status="PASS",counts=dict(counts),distinct_full_states=len(contexts),distinct_rules=len(fingerprints),source_episodes=sorted(episodes),
                source_payload_sha256=hashlib.sha256(raw).hexdigest(),source_decoded_sha256=hashlib.sha256(decoded).hexdigest(),
                rows=rows,prepared_branch_root=next(r for r in rows if r["key"]==envelope["source_key"]),
                input_packet_status=packet["status"],new_primary_candidate_status="AWAITING_FROZEN_INPUT",seconds=time.perf_counter()-tick,
                new_Player_calls=0,new_solver_calls=0,
                scope="Historical one-rule/two-trajectory panel only, not new holdout or independent rule samples. Source claims retained; no H6 transfer and no updated Player/campaign execution.")


def main():
    p=argparse.ArgumentParser();p.add_argument("--inputs",type=Path,required=True);p.add_argument("--envelope",type=Path,required=True);p.add_argument("--output",type=Path,required=True);a=p.parse_args()
    result=qualify_panel(a.inputs,a.envelope);a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(dict(status=result["status"],counts=result["counts"],distinct_rules=result["distinct_rules"],seconds=result["seconds"])))

if __name__=="__main__":main()
