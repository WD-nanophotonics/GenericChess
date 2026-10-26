"""AUX source compatibility table for the published24-context v2 packet.

All rows are included. No new Player, solver, games, candidate choice, tuning or
PV campaign. Saved actual game records may be replayed to qualify outcomes;
those outcomes are never minimax labels for their starting actions.
"""
from collections import Counter,defaultdict
import argparse,gzip,hashlib,json,time
from pathlib import Path
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from scripts.leaper_truth_compatibility import bind_context,digest
from scripts.qualify_leaper_candidate_truth import PublishedTruth
from scripts.research_record import record_value


def read_checked(path,name,manifest):
    raw=Path(path).read_bytes();entry=next(e for e in manifest["files"] if e["path"]==name)
    if len(raw)!=entry["bytes"] or hashlib.sha256(raw).hexdigest()!=entry["sha256"]:
        raise ValueError("published manifest binding differs: "+name)
    return json.loads(gzip.decompress(raw))


def qualify(inputs_path,manifest_path,games_path,summary_path):
    tick=time.perf_counter();manifest=json.loads(Path(manifest_path).read_bytes())
    packet=read_checked(inputs_path,"prepared-v2/inputs.json.gz",manifest)
    games=read_checked(games_path,"population-games/games.json.gz",manifest)
    summary=read_checked(summary_path,"population-games/summary.json.gz",manifest)
    if len(packet["rows"])!=24 or len({r["fingerprint"]for r in packet["rows"]})!=12:
        raise ValueError("not the complete24-context/12-rule packet")
    if len(games)!=summary["planned_games"] or len(games)!=24:raise ValueError("missing saved game slots")
    h6=PublishedTruth(Path("docs/research/data/leaper_h6_initial_truth_20261023"))
    by_game=defaultdict(list)
    for game in games:by_game[game["case_id"]].append(game)
    ids=set();rows=[];counts=Counter();reasons=Counter();long_results=Counter();sessions={};by_id={}
    for raw in packet["rows"]:
        if raw["id"] in ids:raise ValueError("duplicate source context")
        ids.add(raw["id"]);by_id[raw["id"]]=raw
        context=bind_context(raw["RuleSet"],raw["record"]);session=context.session
        if context.identity["ruleset_fingerprint"]!=raw["fingerprint"]:
            raise ValueError("source RuleSet fingerprint differs")
        if record_value(session.to_record())!=raw["record"] or record_value(session.state)!=raw["root"]:
            raise ValueError("source complete record/state differs from literal Core")
        if session.state.ply_count!=raw["prefix_length"] or len(raw["record"]["actions"])!=raw["prefix_length"]:
            raise ValueError("source prelude clock differs")
        actual=[record_value(a) for a in session.legal_actions()]
        if len(actual)!=len(raw["legal_actions"]) or {digest(a) for a in actual}!={digest(a) for a in raw["legal_actions"]}:
            raise ValueError("source full legal frontier differs")
        if type(raw["terminal"]) is not bool or session.state.terminal_status.is_terminal!=raw["terminal"]:raise ValueError("source terminal flag differs")
        compat=h6.check(dict(id=raw["id"],rule=raw["RuleSet"],record=raw["record"]))
        h6_status=compat["compatibility"]
        actions=len(actual)
        # This v2 source packet contains no action WDL/certificate labels. Search
        # scores and later played-game outcomes cannot fill that absence.
        coverage=dict(legal_actions=actions,SOURCE_CLAIM=0,PROOF_CHECKED=0,UNLABELLED=actions)
        counts.update(contexts=1,legal_actions=actions,unlabelled_actions=actions)
        counts["H6:"+h6_status]+=1;counts["root_WDL_UNKNOWN"]+=1
        rows.append(dict(id=raw["id"],family=raw["family"],board_size=raw["n"],availability="AVAILABLE_SOURCE_NOT_ASSIGNED",
                         source_binding="LITERAL_RULE_RECORD_STATE_FRONTIER_CHECKED",context=context.identity,
                         H6_truth_compatibility=dict(status=h6_status,reason=compat["reason"],
                             scope="No H6/repeat2 truth is transplanted to the96ply/repeat4 source."),
                         root_WDL="UNKNOWN",action_label_coverage=coverage,
                         saved_behavior_game_ids=[g["game_id"]for g in by_game[raw["id"]]],
                         exposure=raw["exposure"]))
        sessions[raw["id"]]=session
    if set(by_game)-ids:raise ValueError("game root outside the published source contexts")
    behavior=[]
    for game in games:
        initial=by_id[game["case_id"]]
        if game["initial_record"]!=initial["record"] or game["fingerprint"]!=initial["fingerprint"]:
            raise ValueError("saved game does not start from its exact source record")
        if game["final_record"]["actions"][:len(initial["record"]["actions"])]!=initial["record"]["actions"]:
            raise ValueError("saved game final record loses the initial history")
        session=GameSession.replay(sessions[game["case_id"]].compiled,deserialize_game_record(json.dumps(game["final_record"])))
        if record_value(session.state.terminal_status)!=game["Core_terminal"] or record_value(session.result)!=game["Session_result"]:
            raise ValueError("actual saved game terminal does not replay")
        if session.result.status.value in ("ongoing","no_contest"):raise ValueError("source terminal claim is unresolved/no-contest")
        if game["status"]!="TERMINAL":raise ValueError("unclosed game source slot")
        reasons[session.result.status.value]+=1
        value=0 if session.result.winner is None else 1 if session.result.winner==game["long_seat"]else -1
        long_results[value]+=1
        actual_plies=len(game["final_record"]["actions"])-len(initial["record"]["actions"])
        if actual_plies!=len(game["queries"]):raise ValueError("saved actual move/return count differs")
        counts["saved_actual_plies_replayed"]+=len(game["final_record"]["actions"])
        behavior.append(dict(game_id=game["game_id"],case_id=game["case_id"],long_seat=game["long_seat"],
                             actual_result=record_value(session.result),timing_eligible=game["timing_eligible"],
                             qualification="ACTUAL_GAME_RECORD_REPLAYED_NOT_MINIMAX_PROOF",root_or_action_WDL_label="UNLABELLED"))
    covered={case for case,gg in by_game.items() if gg}
    counts.update(saved_games_replayed=len(behavior),behavior_covered_source_contexts=len(covered),
                  source_contexts_without_games=len(ids-covered),timing_eligible_games=sum(g["timing_eligible"]for g in games))
    if sum(len(g["queries"])for g in games)!=summary["attempts"]:raise ValueError("Player return denominator differs")
    pairs={case:gg for case,gg in by_game.items() if len(gg)==2 and {g["long_seat"]for g in gg}=={0,1}}
    counts["complete_color_pairs"]=len(pairs);counts["complete_timing_eligible_color_pairs"]=sum(all(g["timing_eligible"]for g in gg)for gg in pairs.values())
    return dict(status="PASS",counts=dict(counts),full_rules=len({r["fingerprint"]for r in packet["rows"]}),families=len({r["family"]for r in packet["rows"]}),
                rows=rows,behavior=behavior,actual_terminal_reasons=dict(reasons),long_budget_actual_results=dict(long_results),
                seconds=time.perf_counter()-tick,new_Player_calls=0,new_solver_calls=0,new_games=0,
                source_commit="fd7d7eacbdc2741e766f26b67b0f54018a998aa7",review_commit="68f83ff02067b7d557b12eb1438e066504bfa192",
                scope="All published24contexts/12rules, available not formally assigned. Actual24saved game outcomes are checked trajectory results, not root/action minimax WDL, new games, IID samples or an equal-time algorithm comparison.")


def main():
    p=argparse.ArgumentParser()
    for n in ("inputs","manifest","games","summary","output"):p.add_argument("--"+n,type=Path,required=True)
    a=p.parse_args();result=qualify(a.inputs,a.manifest,a.games,a.summary)
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({k:v for k,v in result.items()if k not in("rows","behavior")}))

if __name__=="__main__":main()
