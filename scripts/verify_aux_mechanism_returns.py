"""Independent fixed-input consumer of eight published mechanism returns.

No experiment producer imports, Player, run_root_search, Native build or timing.
"""
from __future__ import annotations
from pathlib import Path
from collections import Counter
import argparse,gzip,json,hashlib,subprocess
from generic_chess.rules.schema import ruleset_from_dict,compute_fingerprint
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.core.coordinates import square_to_index
from generic_chess.ai.evaluation.config import EvaluationConfig
from generic_chess.ai.evaluation.profile import build_ruleset_profile
from generic_chess.ai.evaluation.evaluator import Evaluator
from scripts.verify_published_boolean_returns import diagnostic_action
from scripts.research_record import record_value
SOURCE="31060392c62f051aeb851ccf3ee96365ea177c20"
BASE="docs/research/data/leaper_threat_admission_20261029/"
def sha(b):return hashlib.sha256(b).hexdigest()
def enc(v):return json.dumps(record_value(v),sort_keys=True,separators=(",",":")).encode()
def archive():
    raw=lambda p:subprocess.check_output(["git","show",SOURCE+":"+BASE+p])
    mb=raw("manifest.json");m=json.loads(mb);b=raw(m["bundle"]["path"])
    assert sha(b)==m["bundle"]["sha256"] and len(b)==m["bundle"]["bytes"]
    v=json.loads(gzip.decompress(b));members={x["path"]:x for x in v["members"]}
    expected={x["path"]:x for x in m["members"]}
    assert len(members)==len(v["members"])==94 and set(members)==set(expected)
    result={}
    for path,row in members.items():
        body=row["text"].encode("utf8")
        assert sha(body)==row["sha256"]==expected[path]["sha256"] and len(body)==row["bytes"]==expected[path]["bytes"]
        result[path]=body
    return result,dict(source=SOURCE,manifest_sha256=sha(mb),bundle_sha256=sha(b),byte_bound_members=94)
def run(output):
    m,binding=archive();get=lambda n:json.loads(m["mechanism-witness/"+n])
    inp=get("input-before-Core.json")["row"];r=ruleset_from_dict(inp["RuleSet"])
    assert compute_fingerprint(r)==inp["fingerprint"]
    c=compile_legacy_ruleset_for_semantic_execution(r)
    root_record=deserialize_game_record(json.dumps(inp["record"]))
    assert len(root_record.actions)==0
    root=GameSession.replay(c,root_record)
    assert root.state.ply_count==0 and not root.state.terminal_status.is_terminal
    assert not root.available_declarations()
    static_cfg=EvaluationConfig(**get("four-search-freeze.json")["config"])
    default_cfg=EvaluationConfig()
    assert (static_cfg.dynamic_mobility_weight,static_cfg.anchor_escape_weight,static_cfg.promotion_potential_weight)==(0,0,0)
    profiles={};evaluators={}
    for name,cfg in (("static",static_cfg),("default",default_cfg)):
        profiles[name]=build_ruleset_profile(c,cfg);evaluators[name]=Evaluator(c,profiles[name],cfg)
    # Independent set algebra, using actual compiled tables and owner frames.
    def targets(tid,owner,source):
        return {square_to_index(sq,c.board_size) for sq in c.empty_mobility[tid][owner][source]}
    def coverage(position,owner):
        out=set()
        for i,p in enumerate(position.board):
            if p is not None and p.owner==owner:out.update(targets(p.current_type_id,owner,i))
        return out
    pos=root.state.position;owner=pos.side_to_move;anchor=next(i for i,p in enumerate(pos.board) if p and p.owner==owner and c.types_by_id[p.current_type_id].is_anchor)
    target=set()
    for i,p in enumerate(pos.board):
        if p is not None and p.owner!=owner:
            for d in targets(p.current_type_id,p.owner,i):
                if anchor in targets(p.current_type_id,p.owner,d):target.add(d)
    assert sum(1<<i for i in target)==get("summary.json")["target_mask"]
    arms={enc(get("arm-"+str(i)+".json")["action"]):get("arm-"+str(i)+".json") for i in range(2)}
    prefix_submits=0;edge_submits=0;leaf_rows=[]
    for action in root.legal_actions():
        child=GameSession.replay(c,root_record);child.submit(action);edge_submits+=1
        replies=child.legal_actions();wins=0
        saved=arms.get(enc(record_value(action)))
        if saved:
            assert record_value(child.state.terminal_status)==saved["after_quiet"]
            assert Counter(enc(record_value(a)) for a in replies)==Counter(enc(x["reply"]) for x in saved["replies"])
        for reply in replies:
            s=GameSession.replay(c,child.to_record());prefix_submits+=len(child.to_record().actions)
            s.submit(reply);edge_submits+=1
            if saved:
                obs=next(x for x in saved["replies"] if enc(x["reply"])==enc(record_value(reply)))
                assert record_value(s.state.terminal_status)==obs["terminal"]
                assert record_value(s.to_record())==obs["record"]
            wins+=s.state.terminal_status.is_terminal and s.state.terminal_status.winner==1
        after=coverage(child.state.position,owner);before=coverage(pos,owner)
        row=dict(action=record_value(action),raw_static_root_view=-evaluators["static"].evaluate(child.state),
            raw_default_root_view=-evaluators["default"].evaluate(child.state),
            opponent_reply_count=len(replies),immediate_opponent_wins=wins,
            threat_coverage_delta=len(after&target)-len(before&target),
            global_coverage_delta=len(after)-len(before),child_record=record_value(child.to_record()))
        if saved:
            assert row["threat_coverage_delta"]==saved["threat_delta"] and row["global_coverage_delta"]==saved["global_delta"]
            assert wins==get("summary.json")["arms"][0 if saved["threat_delta"]==0 else 1]["immediate_opponent_wins"]
        leaf_rows.append(row)
    assert len(leaf_rows)==3
    decisions=[];pv_submits=0
    old_reader={x["file"]:x for x in json.loads(m["mechanism-original-reader.json"])["records"]}
    for mode,prefix in (("static","search-"),("default","default-search-")):
        freeze=get("four-search-freeze.json" if mode=="static" else "default-control-freeze.json")
        summaries=get("four-search-summary.json")["rows"] if mode=="static" else get("default-control.json")
        for index,(depth,on) in enumerate(freeze["slots"]):
            name=prefix+str(index)+".json";raw=m["mechanism-witness/"+name];x=json.loads(raw);d=x["decision"]
            assert old_reader[name]["sha256"]==sha(raw)
            assert x["depth"]==depth and type(x["on"])is bool and x["on"]==on
            a=diagnostic_action(d["action"],c.ruleset_fingerprint);assert a in root.legal_actions()
            assert d["completed_depth"]==depth and d["termination_reason"]=="completed_depth"
            assert d["result_source"]=="main_iteration" and d["runtime_depth_balanced"]
            assert d["runtime_pushes"]==d["runtime_pops"]
            assert d["result_ordinary_qdepth"]==(4 if mode=="default" and depth==2 else 0)
            s=GameSession.replay(c,root_record)
            pv=d["principal_variation"];assert pv and enc(pv[0])==enc(d["action"])
            for record in pv:
                s.submit(diagnostic_action(record,c.ruleset_fingerprint));pv_submits+=1
            if mode=="static":
                z=summaries[index]
                assert all(enc(z[k])==enc(x[k] if k in ("depth","on") else d[k]) for k in ("depth","on","score","action","completed_depth"))
            else:assert enc(x)==enc(summaries[index])
            leaf=next(z for z in leaf_rows if enc(z["action"])==enc(d["action"]))
            score=((-1)**len(pv))*evaluators[mode].evaluate(s.state)
            if d["result_ordinary_qdepth"]==0:assert score==d["score"]
            decisions.append(dict(file=name,depth=depth,on=on,selected=record_value(a),score=d["score"],
                result_q=d["result_ordinary_qdepth"],qnodes=d["qnodes"],
                pv_plies=len(pv),direct_PV_leaf_value_in_root_view=score,
                numeric_leaf_equal=(score==d["score"]),
                immediate_reply_wins=leaf["immediate_opponent_wins"],
                result_source=d["result_source"],
                source_gap="Original per-call executed source-byte/binary identities absent; no engine/hardware rerun.",
                child_entry_activity="UNKNOWN: saved feature/yield records are not post-budget child-entry events."))
    assert [x["immediate_reply_wins"] for x in decisions]==[1,0,0,0,0,0,0,0]
    default_values=[x["raw_default_root_view"] for x in leaf_rows]
    assert len([x for x in default_values if x==max(default_values)])==1
    result=dict(binding=binding,input_fingerprint=c.ruleset_fingerprint,config_hashes={k:v.config_hash for k,v in profiles.items()},
        independent_root_target_indices=sorted(target),all_root_children=leaf_rows,decisions=decisions,
        actual_consumer_submissions=dict(root_and_reply_edges=edge_submits,prefix_replays=prefix_submits,pv_edges=pv_submits,total=edge_submits+prefix_submits+pv_submits),
        interpretation="StaticD1 changes a tie; defaultD1 already has a unique highest static child and resultQ0. Therefore default correction here cannot be credited to retainedQ4. D2defaultQ4 score need not equal PV leaf. None establishes WDL quality, causal observedchildentry or transferable strength.",
        limits="All3actualrootactions and their legal replies checked; no new labels beyond actual two-ply terminals. Surviving branches UNKNOWN. Eight historical returns source-bound/PV-replayed, not recreated. No new root search, Player or timing; producer's elapsed values not validated.")
    output.parent.mkdir(parents=True,exist_ok=True);output.write_bytes((json.dumps(result,indent=2)+"\n").encode())
    return result
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--output",type=Path,required=True);a=p.parse_args();r=run(a.output)
    print(json.dumps(dict(submissions=r["actual_consumer_submissions"],children=[{k:v for k,v in x.items()if k not in ("child_record","action")} for x in r["all_root_children"]],returns=[{k:v for k,v in x.items()if k not in ("selected","source_gap","child_entry_activity")}for x in r["decisions"]]),indent=2))
