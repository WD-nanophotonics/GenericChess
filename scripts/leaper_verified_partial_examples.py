"""Literal old-proof examples for composing partial action truth.

These are source-exposed consumer controls, not a selected quality panel. Every
prefix and continuation is already present in the public saved proof packet.
"""
from collections import deque
import argparse,gzip,json,time
from pathlib import Path
from generic_chess.core.actions import action_from_dict
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import serialize_game_record
from scripts.leaper_truth_compatibility import (bind_context,digest,verify_bound_tree,
    verify_action_bound,action_coverage,verify_saved_tree)
from scripts.verify_leaper_truth_controls import trim_supplied_tree


def examples():
    tick=time.perf_counter()
    inputs=json.loads(gzip.decompress(Path("docs/research/data/leaper_h6_initial_truth_20261023/inputs.json.gz").read_bytes()))
    packet=json.loads(gzip.decompress(Path("docs/research/data/leaper_history_context_20261024/evidence.json.gz").read_bytes()))
    old=json.loads(packet["documents_utf8"]["context/literal.json"])
    rules={f["fingerprint"]:f["rule"] for f in inputs["families"] if f.get("rule")}
    results={}
    for case in old["cases"]:
        for row in case["rows"]:
            for arm in row["arms"]:
                rule=rules[arm["fingerprint"]];compiled=compile_legacy_ruleset_for_semantic_execution(ruleset_from_dict(rule))
                original=bind_context(rule,arm["final_record"],compiled=compiled)
                by={digest(n["state"]):n for n in arm["complete_tree"]}
                root_key=original.identity["state_sha256"]
                verify_saved_tree(original,arm["complete_tree"])
                queue=deque([(root_key,())]);seen=set()
                while queue:
                    key,path=queue.popleft()
                    if key in seen:continue
                    seen.add(key);node=by[key];side=node["state"]["position"]["side_to_move"]
                    for ch in node["children"]:queue.append((digest(ch["state"]),path+(ch["action"],)))
                    relative=node["value"] if side==0 else -node["value"]
                    if len(node["children"])<2:continue
                    session=GameSession.replay(compiled,original.session.to_record())
                    for action in path:session.submit(action_from_dict(action))
                    context=bind_context(rule,json.loads(serialize_game_record(session.to_record())),compiled=compiled)
                    if context.identity["state_sha256"]!=key:raise ValueError("saved internal-node prefix differs")
                    choices=[ch for ch in node["children"] if (by[digest(ch["state"])]["value"] if side==0 else -by[digest(ch["state"])]["value"])==relative]
                    edge=choices[0];child=by[digest(edge["state"])]
                    if relative==1 and "one_WIN_label" not in results:
                        cert=trim_supplied_tree(arm["complete_tree"],digest(child["state"]),1,value_seat=side)
                        checked=verify_action_bound(context,edge["action"],cert,1,value_seat=side)
                        coverage=action_coverage(context,[checked],value_seat=side)
                        selected=next(r for r in coverage["rows"] if r["action"]==edge["action"])
                        if selected["classification"]!="OPTIMAL_SOURCE_CLAIM" or coverage["unlabelled_actions"]<1:
                            raise ValueError("verified WIN partial coverage does not identify optimality")
                        results["one_WIN_label"]=dict(rule=rule,record=json.loads(serialize_game_record(session.to_record())),
                            context=context.identity,selected_action=edge["action"],certificate=cert,checked=checked,coverage=coverage,
                            source_full_tree_nodes=len(arm["complete_tree"]),interpretation="Locally verified selected WIN bound; other action values unknown. This proves WDL optimality only.")
                    if relative==0 and "nonloss_is_not_exact_DRAW" not in results:
                        cert=trim_supplied_tree(arm["complete_tree"],digest(child["state"]),0,value_seat=side)
                        checked=verify_action_bound(context,edge["action"],cert,0,value_seat=side)
                        unknown=action_coverage(context,[checked],value_seat=side)
                        with_root=action_coverage(context,[checked],[0,0],value_seat=side)
                        selected=next(r for r in unknown["rows"] if r["action"]==edge["action"])
                        if selected["classification"]!="UNKNOWN":continue
                        if next(r for r in with_root["rows"] if r["action"]==edge["action"])["classification"]!="OPTIMAL_SOURCE_CLAIM":raise ValueError("exact root composition differs")
                        results["nonloss_is_not_exact_DRAW"]=dict(context=context.identity,action=edge["action"],checked=checked,
                            unknown_root=unknown,exact_DRAW_root=with_root,
                            interpretation="Verified action nonloss alone does not establish exact DRAW or optimality; separately verified exact DRAW root closes the gap.")
                if original.session.state.position.side_to_move==0 and arm["value"]==-1 and "cooperative_path_is_not_strategy" not in results:
                    queue=deque([(root_key,[])]);found=None
                    while queue:
                        key,path=queue.popleft();node=by[key]
                        if not node["children"] and node["value"]>=0:found=path+[dict(state=node["state"],children=[])];break
                        for child in node["children"]:
                            queue.append((digest(child["state"]),path+[dict(state=node["state"],children=[child])]))
                    if found:
                        try:verify_bound_tree(original,found,0)
                        except ValueError as error:
                            if "universal certificate" not in str(error):raise
                            results["cooperative_path_is_not_strategy"]=dict(context=original.identity,
                                source_exact_value=-1,path_nodes=len(found),rejection=str(error),
                                interpretation="An actual old complete-tree path can reach nonloss while the source root is LOSS; omitted defenses invalidate a nonloss strategy claim.")
                        else:raise ValueError("cooperative line incorrectly accepted as strategy")
                if len(results)==3:
                    return dict(status="PASS",examples=results,seconds=time.perf_counter()-tick,new_solver_calls=0,new_Player_calls=0,
                        scope="Existing supplied proof controls only, actual literal prefix/action checks. No new candidate or game/solver campaign.")
    raise ValueError("published proof pool did not provide all intended controls")


def main():
    p=argparse.ArgumentParser();p.add_argument("--output",type=Path,required=True);a=p.parse_args()
    result=examples();a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(dict(status=result["status"],examples=list(result["examples"]),seconds=result["seconds"])))

if __name__=="__main__":main()
