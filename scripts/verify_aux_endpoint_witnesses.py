"""Independent byte-bound consumer of published endpoint witnesses and costs.

Archive source capsules are DATA; no producer, Player or Native build is imported.
"""
from __future__ import annotations
from pathlib import Path
from collections import Counter,defaultdict
import json,gzip,hashlib,math,argparse
from generic_chess.rules.schema import ruleset_from_dict,compute_fingerprint
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from scripts.verify_published_boolean_returns import diagnostic_action
from scripts.research_record import record_value
SOURCE="025c70cb4d35c8d2196b4a8d8dc0c9c1f2da75b8"
def sha(b):return hashlib.sha256(b).hexdigest()
def enc(v):return json.dumps(v,sort_keys=True,separators=(",",":"))
def wire_action(v,c):
    if "kind" not in v:return diagnostic_action(v,c.ruleset_fingerprint)
    return deserialize_game_record(json.dumps(dict(schema_version=1,ruleset_fingerprint=c.ruleset_fingerprint,resigned_by=None,actions=[v]))).actions[0]
def archives(base):
    manifest_raw=(base/"manifest.json").read_bytes();manifest=json.loads(manifest_raw);out={};checks=[]
    for row in manifest["archives"]:
        raw=(base/row["path"]).read_bytes()
        assert sha(raw)==row["sha256"] and len(raw)==row["bytes"]
        decoded=gzip.decompress(raw);assert len(decoded)==row["decoded_bytes"]
        pack=json.loads(decoded);members=pack["members"];assert len(members)==row["members"]
        group={}
        for m in members:
            body=m["original_utf8"].encode()
            assert sha(body)==m["sha256"] and len(body)==m["bytes"]
            assert m["path"]not in group;group[m["path"]]=body
        out[row["path"]]=group;checks.append(dict(path=row["path"],sha256=sha(raw),members=len(group)))
    assert sum(x["members"]for x in checks)==manifest["members"]==608
    return out,dict(source=SOURCE,manifest_sha256=sha(manifest_raw),archives=checks,byte_bound_members=608)
def retained_witnesses(row):
    o=row["observer"];d=row["decision"];assert not o["errors"]
    assert o["query"]==row["query_id"] and o["result_source"]==d["result_source"]
    assert o["completed_depth"]==d["completed_depth"]
    if d["result_source"]!="main_iteration":return []
    accepted=[p for p in o["provenance"]if p["source"]=="main_iteration"]
    assert accepted
    attempt=o["retained_root_attempt"];assert accepted[-1]["root_attempt"]==attempt
    root=next(r for r in o["roots"]if r["attempt"]==attempt)
    assert root["entered"] and root["iteration"]==d["completed_depth"]
    witnesses=[w for w in o["witnesses"]if w["root_attempt"]==attempt and w["return"]=="NORMAL"]
    for w in witnesses:
        assert w["entry"]=="AFTER_ORIGINAL_BUDGET_CHECK" and w["query"]==row["query_id"]
        assert w["requested_iteration"]==d["completed_depth"]
        assert w["baseline_rank"]!=w["candidate_rank"] and min(w["baseline_rank"],w["candidate_rank"])>=0
        assert w["call_id"]>w["parent_id"] and w["return_"]=="NORMAL"
        if w["ply"]==1:assert w["parent_id"]==root["call_id"]
    assert len(witnesses)<=o["retained_changed_entries"]
    return witnesses
def run(base,output):
    groups,binding=archives(Path(base));foundation=groups["foundation.json.gz"];q=groups["qualification.json.gz"]
    inputs_raw=foundation["frozen/inputs.json"];inputs=json.loads(inputs_raw)["rows"]
    protocol=json.loads(q["comparison-protocol.json"]);assert sha(inputs_raw)==protocol["input_sha256"]
    contexts={}
    for row in inputs:
        r=ruleset_from_dict(row["RuleSet"]);assert compute_fingerprint(r)==row["fingerprint"]
        c=compile_legacy_ruleset_for_semantic_execution(r)
        s=GameSession.replay(c,deserialize_game_record(json.dumps(row["record"])))
        contexts[row["id"]]=(c,s,row)
    returns={json.loads(b)["query_id"]:json.loads(b)for p,b in q.items()if p.startswith("qualification/returns/")}
    assert len(returns)==64
    counts=Counter();distinct=set();observed=[];pv_submits=0;selected=0;root_edges=0
    for qid,row in sorted(returns.items()):
        rid=qid.rsplit("-",1)[0];c,root,inp=contexts[rid]
        assert row["record"]==inp["record"] and row["root_fingerprint"]==c.ruleset_fingerprint
        assert row["on"]==(int(qid.rsplit("-",1)[1])in(1,2))
        assert row["freshPlayerTT"]and row["provider_present"]
        d=row["decision"];assert d["runtime_depth_balanced"]and d["runtime_pushes"]==d["runtime_pops"]
        assert d["native_legality_fallbacks"]==d["native_legality_operational_failures"]==0
        assert wire_action(d["action"],c)in root.legal_actions();selected+=1
        pv=GameSession.replay(c,root.to_record())
        for a in d["principal_variation"]:pv.submit(wire_action(a,c));pv_submits+=1
        witnesses=retained_witnesses(row)
        rootw=[w for w in witnesses if w["ply"]==1]
        for w in rootw:
            a=wire_action(w["action"],c);assert a in root.legal_actions()
            child=GameSession.replay(c,root.to_record());child.submit(a);root_edges+=1
            distinct.add((rid,enc(w["action"])))
        for w in witnesses:counts[(w["ply"],w["source"])]+=1
        observed.append(dict(query=qid,retained_normal_changed_events=len(witnesses),independently_legal_root_events=len(rootw),
            omitted_witnesses=row["observer"]["dropped"],full_parent_paths="UNKNOWN:notserialized"))
    computed=[]
    for rid,(c,s,inp)in contexts.items():
        calls=[returns[rid+"-"+str(i)]for i in range(4)]
        eligible=all(x["timing_eligible"]and x["decision"]["completed_depth"]>=2 and x["decision"]["result_source"]=="main_iteration"for x in calls)
        activity=any(retained_witnesses(x)for x in calls[1:3])
        keys=[enc(x["action"])for x in calls]
        stable=keys[0]==keys[3]and keys[1]==keys[2]and keys[0]!=keys[1]
        computed.append(dict(id=rid,family=inp["family"],eligible=eligible,retained_activity_witness=activity,stable_action_difference=stable,calls=[x["query_id"]for x in calls]))
    assert computed==json.loads(q["qualification/groups.json"])
    costs=groups["hash.json.gz"];rows=[json.loads(costs["hash-composition/return-"+str(i).zfill(3)+".json"])for i in range(128)]
    summary=json.loads(costs["hash-composition/summary.json"])
    frozen=json.loads(costs["hash-composition/frozen.json"])
    assert frozen["inputs_sha256"]==sha(inputs_raw)
    assert frozen["Player_queries_before_freeze"]==0
    source_checks=[]
    for name,item in frozen["sources"].items():
        assert sha(item["text"].encode())==item["sha256"]
        source_checks.append(dict(path=name,sha256=item["sha256"]))
    times={"elapsed_seconds","time_to_first_legal_action","time_to_first_completed_iteration",
        "ordering_seconds","legal_generation_seconds","evaluation_seconds","evaluation_profile_cache_hit","quiet_geometry_build_seconds"}
    changes={"runtime_semantic_local_hash_updates","runtime_position_identity_hash_cached","runtime_semantic_full_diff_fallbacks"}
    excluded=set(frozen["plan"]["cost"]["source_counts_excluded_from_equality"])
    assert excluded==changes
    expected_arms=[(0,0),(1,0),(1,1),(0,1),(0,1),(1,1),(1,0),(0,0)]
    totals=defaultdict(lambda:Counter());perfamily=defaultdict(lambda:defaultdict(Counter));complete=[];incomplete=[]
    for start in range(0,128,8):
        batch=rows[start:start+8];inp=inputs[start//8]
        assert all(x["slot"]==start+i and x["record_before"]==inp["record"]for i,x in enumerate(batch))
        for i,x in enumerate(batch):
            assert tuple(map(int,x["arm"]))==expected_arms[i]
            assert x["binary_sha256_checked"]==frozen["binary"]["sha256"]
            d=x["decision"];assert d["runtime_depth_balanced"]and d["runtime_pushes"]==d["runtime_pops"]
            assert bool(d["runtime_semantic_local_hash_updates"])==bool(expected_arms[i][0])
            assert d["runtime_position_identity_hash_cached"]==bool(expected_arms[i][1])
            assert d["native_legality_fallbacks"]==d["native_legality_operational_failures"]==0
            assert d["evaluation_profile_cache_hit"]is False
        good=all(x["decision"]["completed_depth"]==3 and x["decision"]["result_source"]=="main_iteration"for x in batch)
        if not good:incomplete.append(inp["id"]);continue
        signatures=[{k:v for k,v in x["decision"].items()if k not in times|changes}for x in batch]
        assert all(x==signatures[0]for x in signatures)
        complete.append(inp["id"])
        for x in batch:
            arm="".join(str(int(z))for z in x["arm"])
            for metric in("wall","cpu"):
                value=x[metric+"_seconds"];assert math.isfinite(value)and value>=0
                totals[arm][metric]+=value;perfamily[inp["family"]][arm][metric]+=value
    assert len(complete)==summary["complete_parity_groups"]==14
    for arm in totals:
        for metric in("wall","cpu"):assert math.isclose(totals[arm][metric],summary["totals"][arm][metric],rel_tol=1e-14)
    family_ratios={str(f):{metric:x["10"][metric]/x["00"][metric]for metric in("wall","cpu")}for f,x in perfamily.items()}
    result=dict(binding=binding,qualification=dict(returns=64,selected_Core_legal=selected,PV_Core_submit_calls=pv_submits,
        retained_event_counts=[dict(ply=p,source=s,events=n)for(p,s),n in sorted(counts.items())],
        independently_legal_root_event_submissions=root_edges,distinct_input_root_actions=len(distinct),observations=observed,
        eligible_groups=sum(g["eligible"]for g in computed),stable_difference_families=sorted({g["family"]for g in computed if g["eligible"]and g["stable_action_difference"]}),
        truncated_queries=sum(x["observer"]["dropped"]>0 for x in returns.values())),
        cost=dict(captured_source_hashes=source_checks,decision_parity_exclusions=sorted(times|changes),
            loaded_binary_sha256=frozen["binary"]["sha256"],complete_groups=complete,censored_groups=incomplete,totals=dict(totals),local_only_ratios_by_family=family_ratios,
            local_only_wall_ratio=totals["10"]["wall"]/totals["00"]["wall"],local_only_CPU_ratio=totals["10"]["cpu"]/totals["00"]["cpu"],
            cache_added_to_local_wall_ratio=totals["11"]["wall"]/totals["10"]["wall"],
            cache_added_to_local_CPU_ratio=totals["11"]["cpu"]/totals["10"]["cpu"]),
        new_Player_calls=0,new_games=0,limits="Independent hash/arithmetic/sharedCore selected/PV/root-witness replay. Deeper witness action legality, rank orders and fullcausalpaths UNKNOWN withoutparents;normalreturnnotquality;no independent timing/binary execution.")
    Path(output).write_bytes((json.dumps(result,indent=2)+"\n").encode());return result
def consume_sameboard_histories(base,output):
    from generic_chess.core.search_runtime import SearchPathRuntime
    packs,binding=archives(Path(base))
    h=json.loads(packs["hash.json.gz"]["full-history-key-validation.json"])
    inp=json.loads(packs["foundation.json.gz"]["frozen/inputs.json"])["rows"]
    records=h["actual_sameposition_two_cycles"];assert len(records)==2
    fp=records[0]["ruleset_fingerprint"];assert records[1]["ruleset_fingerprint"]==fp
    root=next(r for r in inp if r["fingerprint"]==fp)
    c=compile_legacy_ruleset_for_semantic_execution(ruleset_from_dict(root["RuleSet"]))
    sessions=[GameSession.replay(c,deserialize_game_record(json.dumps(r)))for r in records]
    a,b=sessions
    assert a.state.position==b.state.position and a.state.ply_count==b.state.ply_count==4
    assert a.state.repetition_counts!=b.state.repetition_counts
    assert a.state.terminal_status==b.state.terminal_status
    pairs=[];pushes=0;baseline_roots=None;baseline_children=None
    for local,cache in((False,False),(True,False),(True,True),(False,True)):
        rr=[SearchPathRuntime.from_state(x.state,c,history_witnesses=x._search_witnesses,
            use_plain_leaper_local_hash=local,use_cached_position_identity_hash=cache)for x in sessions]
        x,y=rr
        assert x.current_identity==y.current_identity and x.runtime_hash==y.runtime_hash
        assert x.search_key()!=y.search_key()
        # Core same-position legal action is shared, but child histories must stay distinct.
        actions=a.legal_actions();assert actions==b.legal_actions()
        move=actions[0]
        roots=[r.search_key()for r in rr]
        if baseline_roots is None:baseline_roots=roots
        assert roots==baseline_roots
        guard={baseline_roots[0]:"history-A",baseline_roots[1]:"history-B"}
        assert len(guard)==2 and [guard[k]for k in roots]==["history-A","history-B"]
        for r in rr:r.push(move);pushes+=1
        assert x.position==y.position and x.runtime_hash==y.runtime_hash
        assert x.search_key()!=y.search_key()
        children=[r.search_key()for r in rr]
        if baseline_children is None:baseline_children=children
        assert children==baseline_children
        for r,key in zip(rr,roots):
            r.pop();assert r.search_key()==key and r.depth==0
        pairs.append(dict(local=local,cache=cache,same_position_hash=True,different_root_and_child_history_keys=True,undo_complete=True))
    result=dict(source=SOURCE,literal_records=records,public_replay_submissions=8,runtime_pushes=pushes,runtime_pops=pushes,
        arms=pairs,all_history_counts=[record_value(x.state.repetition_counts)for x in sessions],
        scope="Independent sameboard/sameclock histories remain different in allfourexistingruntimearms;noTTscorelookup,forcedcollision,Player,solver or speedmeasurement.")
    Path(output).write_bytes((json.dumps(result,indent=2)+"\n").encode());return result

def consume_curve(base,protocol_path,output):
    packs,binding=archives(Path(base));m=packs["curve.json.gz"]
    proto_raw=Path(protocol_path).read_bytes();proto=json.loads(proto_raw)
    raw=m["service-curve-inputs.json"];assert sha(raw)==proto["inputs_sha256"]
    inp=json.loads(raw)["rows"];frozen=json.loads(m["service-curve/frozen.json"])
    assert frozen["inputs_sha256"]==sha(raw)
    source=json.loads(m["service-curve/groups.json"])
    selected=[g for g in source if g["stable_choice_difference"]and g["timing_eligible"]]
    assert selected==proto["selection"] and len(selected)==2
    sessions=[]
    for r in inp:
        rule=ruleset_from_dict(r["RuleSet"]);assert compute_fingerprint(rule)==r["fingerprint"]
        c=compile_legacy_ruleset_for_semantic_execution(rule)
        rec=deserialize_game_record(json.dumps(r["record"]))
        assert len(rec.actions)==r["prefix_length"]==3
        sessions.append((c,GameSession.replay(c,rec),r))
    returns=[];pv_submits=0;prefix_submits=0
    for i in range(192):
        row=json.loads(m["service-curve/return-"+str(i).zfill(3)+".json"])
        c,root,r=sessions[i//12];assert row["slot"]==i and row["record_before"]==r["record"]
        assert row["binary_sha256_checked"]==frozen["binary"]["sha256"]
        assert row["on"]==(i%4 in(1,2))
        d=row["decision"];assert d["result_source"]=="main_iteration"
        assert d["runtime_depth_balanced"]and d["runtime_pushes"]==d["runtime_pops"]
        assert d["native_legality_fallbacks"]==d["native_legality_operational_failures"]==0
        assert bool(d["runtime_semantic_local_hash_updates"])==row["on"]
        assert d["runtime_position_identity_hash_cached"]is False
        a=wire_action(d["action"],c);assert a in root.legal_actions()
        assert d["principal_variation"]and wire_action(d["principal_variation"][0],c)==a
        pv=GameSession.replay(c,root.to_record());prefix_submits+=3
        for v in d["principal_variation"]:pv.submit(wire_action(v,c));pv_submits+=1
        returns.append(row)
    for gi,g in enumerate(source):
        calls=returns[gi*4:gi*4+4];keys=[enc(x["decision"]["action"])for x in calls]
        stable=keys[0]==keys[3]and keys[1]==keys[2]and keys[0]!=keys[1]
        assert stable==g["stable_choice_difference"]
        assert g["slots"]==list(range(gi*4,gi*4+4))
    branches=[];replies=0;edges=0
    for g in selected:
        c,root,r=next(x for x in sessions if x[2]["id"]==g["id"])
        actor=root.state.position.side_to_move
        for on,slot in((False,g["slots"][0]),(True,g["slots"][1])):
            row=returns[slot];d=row["decision"];child=GameSession.replay(c,root.to_record());prefix_submits+=3
            child.submit(wire_action(d["action"],c));edges+=1
            literal=record_value(child.state.terminal_status)
            frontier=[];winning=[]
            for a in child.legal_actions():
                assert replies<proto["bounds"]["max_complete_reply_edges"]
                after=GameSession.replay(c,child.to_record());prefix_submits+=len(child.to_record().actions)
                after.submit(a);edges+=1;replies+=1
                status=after.state.terminal_status
                if status.is_terminal and status.winner==1-actor:winning.append(record_value(a))
                frontier.append(dict(reply=record_value(a),terminal=record_value(status)))
            branches.append(dict(id=r["id"],family=r["family"],on=on,slot=slot,actor=actor,
                depth=d["completed_depth"],retained_Q=d["result_ordinary_qdepth"],score=d["score"],
                selected=record_value(wire_action(d["action"],c)),after_selected_terminal=literal,
                opponent_replies=len(frontier),immediate_opponent_wins=len(winning),winning_replies=winning,
                frontier=frontier,actual_source_record=r["record"],full_game_WDL="UNKNOWN"))
    result=dict(source=SOURCE,protocol_sha256=sha(proto_raw),original_returns=192,actual_selected_actions_Core_checked=192,
        literal_PV_Core_plies=pv_submits,actual_prefix_replay_submissions=prefix_submits,
        actual_selected_and_reply_edge_submissions=edges,reply_edges=replies,branches=branches,
        new_Player_calls=0,new_games=0,new_solver=0,
        scope="Literal2plyterminalexposure only;nonterminalUNKNOWN,norollout/quality/strength inference. ArchivedsourceDATAonly;sharedCore replay isnot independentCore implementation.")
    Path(output).write_bytes((json.dumps(result,indent=2)+"\n").encode())
    return result

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--base",type=Path,required=True);p.add_argument("--out",type=Path,required=True);a=p.parse_args()
    v=run(a.base,a.out);print(json.dumps({k:x for k,x in v.items()if k not in("binding","qualification")},indent=2))
