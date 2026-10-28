"""Two frozen public Player calls testing a literal-action metamorphic gate.

A deliberately tied D1 control, not quality, speed, a new family or a rollout.
"""
from __future__ import annotations
from dataclasses import replace
from pathlib import Path
from collections import Counter
from time import perf_counter,process_time
import argparse,json,hashlib
from scripts.aux_representation_history import definitions as history_definitions
from scripts.research_record import record_value
from generic_chess.rules.schema import ruleset_to_dict,ruleset_from_dict
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution as compile_rule
from generic_chess.core.identity import repetition_identity_key
from generic_chess.session.session import GameSession
from generic_chess.ai.evaluation.config import EvaluationConfig
from generic_chess.ai.evaluation.profile import build_ruleset_profile
from generic_chess.ai.evaluation.evaluator import Evaluator
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.ai.limits import SearchLimits
from generic_chess.ai.alphabeta import search as actual_search
NAMES={"K":"K","A":"Z","B":"A"}
def enc(v):return json.dumps(record_value(v),sort_keys=True,separators=(",",":")).encode()
def sha(b):return hashlib.sha256(b).hexdigest()
def definitions():
    _,a,_=history_definitions()
    assert not(a.semantic_actions or a.declarations or a.promotion_allowed or a.initial_setup_options)
    b=replace(a,
        piece_types=tuple(replace(t,type_id=NAMES[t.type_id],name=NAMES[t.type_id])for t in a.piece_types),
        initial_position=tuple(tuple(None if p is None else replace(p,base_type_id=NAMES[p.base_type_id],current_type_id=NAMES[p.current_type_id])for p in row)for row in a.initial_position),
        drop_allowed={NAMES[t]:v for t,v in a.drop_allowed.items()})
    return a,b
def freeze(path):
    a,b=definitions();v=dict(source="48749ec334c9eb42955a844f06e1d101bb2a02e2",
        literal_rules=[ruleset_to_dict(a),ruleset_to_dict(b)],bijective_type_map=NAMES,
        slots=["original","globally-renamed"],lifetime_Player_call_cap=2,
        per_call=dict(max_depth=1,max_nodes=10000,Q=0,hardQ=0,whole_service_seconds=3,
            TT=False,ordering=True,root_tactical=False,Native_legality=False,disk_cache=False),
        whole_experiment_seconds=120,
        evaluation=dict(dynamic_mobility_weight=0,anchor_escape_weight=0,promotion_potential_weight=0),
        endpoint="Do literal actions fail to map although BOTH are in the same mapped completeD1 argmax set?",
        stop="Any failed preflight, incomplete result, deadline/exception stops remaining calls. No replacement, repeats, games, training, default edit or speed claim.",
        forecast="Source/preflight+2calls, approximately10researchminutes, additional root service<=6seconds, within existing110minsegment cap; prior costs retained.",
        exposure="Known engineered typed6x6 input from priorhistorycontrol, not new/holdout/crossfamilybenchmark.")
    b=enc(v);path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():assert path.read_bytes()==b
    else:
        with path.open("xb")as f:f.write(b)
    return sha(b)
def rename_values(v):
    if isinstance(v,dict):return{k:rename_values(x)for k,x in v.items()}
    if isinstance(v,list):return[rename_values(x)for x in v]
    return NAMES.get(v,v)if isinstance(v,str)else v
def preflight(f):
    a,b=map(ruleset_from_dict,f["literal_rules"]);ca,cb=compile_rule(a),compile_rule(b)
    cfg=EvaluationConfig(**f["evaluation"]);ea,eb=(Evaluator(c,build_ruleset_profile(c,cfg),cfg)for c in(ca,cb))
    for old,new in NAMES.items():
        for owner in(0,1):assert ca.empty_mobility[old][owner]==cb.empty_mobility[new][owner]
    def signature(p,c,rename):
        x=record_value(p);x.pop("pattern_id");x.pop("name");gids=x.pop("geometry_ids")
        geometries=[]
        for g in gids:
            z=record_value(c.ir.geometry[g]);z.pop("geometry_id");geometries.append(z)
        x["geometry_bodies"]=geometries
        return enc(rename_values(x)if rename else x)
    ap={signature(p,ca,True):p for p in ca.ir.patterns if ca.ir.geometry[p.geometry_ids[0]].kind!="drop"}
    bp={signature(p,cb,False):p for p in cb.ir.patterns if cb.ir.geometry[p.geometry_ids[0]].kind!="drop"}
    assert len(ap)==len(bp)==48 and set(ap)==set(bp)
    pm={p.pattern_id:bp[key].pattern_id for key,p in ap.items()};gm={}
    for key,p in ap.items():
        for ga,gb in zip(p.geometry_ids,bp[key].geometry_ids):gm[ga]=gb
    def mapped(action):return replace(action,actor_type_id=NAMES[action.actor_type_id],pattern_id=pm[action.pattern_id],geometry_id=gm[action.geometry_id])
    sa,sb=GameSession(ca),GameSession(cb);aa,bb=sa.legal_actions(),sb.legal_actions()
    assert Counter(enc(mapped(x))for x in aa)==Counter(enc(x)for x in bb)
    keys={};raw=[];edges=0;replays=0;nodes=0
    def walk(x,y,depth):
        nonlocal edges,replays,nodes
        nodes+=1
        mapped_board=tuple(None if p is None else replace(p,base_type_id=NAMES[p.base_type_id],current_type_id=NAMES[p.current_type_id])for p in x.state.position.board)
        assert mapped_board==y.state.position.board and x.state.position.side_to_move==y.state.position.side_to_move
        assert x.state.terminal_status==y.state.terminal_status
        kx,ky=repetition_identity_key(x.state.position,ca),repetition_identity_key(y.state.position,cb)
        assert keys.setdefault(kx,ky)==ky and len(set(keys.values()))==len(keys)
        assert {keys[k]:v for k,v in x.state.repetition_counts}==dict(y.state.repetition_counts)
        xx,yy=x.legal_actions(),y.legal_actions()
        assert Counter(enc(mapped(z))for z in xx)==Counter(enc(z)for z in yy)
        if depth==1:
            va=-ea.evaluate(x.state);vb=-eb.evaluate(y.state)
            assert not x.state.terminal_status.is_terminal and va==vb==2000
            raw.append(dict(action=record_value(x.to_record().actions[-1]),mapped_action=record_value(y.to_record().actions[-1]),raw_root_view=va))
        if depth==2:return
        for act in xx:
            xr,yr=x.to_record(),y.to_record()
            u,v=GameSession.replay(ca,xr),GameSession.replay(cb,yr);replays+=len(xr.actions)+len(yr.actions)
            u.submit(act);v.submit(mapped(act));edges+=1;walk(u,v,depth+1)
    walk(sa,sb,0)
    return dict(root_actions=len(aa),all_D1_values=[x["raw_root_view"]for x in raw],argmax_rows=raw,
        two_ply_prefixes=nodes,paired_edges=edges,actual_Session_submit_calls=2*edges+replays,
        pattern_map=pm,geometry_map=gm,full_count_bijection_size=len(keys)),mapped
def run(frozen,output):
    origin=perf_counter();cpu=process_time();f=json.loads(frozen.read_bytes())
    dispatch=output.with_suffix(".dispatch.json")
    if dispatch.exists()or output.exists():raise RuntimeError("closed/previous dispatch exists; no automatic rerun")
    dispatch.parent.mkdir(parents=True,exist_ok=True)
    with dispatch.open("xb")as h:h.write(enc(dict(frozen_sha256=sha(frozen.read_bytes()),slots=2,status="DISPATCHED_ONCE",source=f["source"])))
    v=dict(source=f["source"],frozen_sha256=sha(frozen.read_bytes()),calls=[],remaining_slots="NOT_RUN",status="PREFLIGHT")
    try:
        pf,mapped=preflight(f);v["preflight"]=pf
        for slot,definition in zip(f["slots"],f["literal_rules"]):
            assert perf_counter()-origin<f["whole_experiment_seconds"]
            start=perf_counter();pc=process_time()
            c=compile_rule(ruleset_from_dict(definition))
            p=AlphaBetaPlayer(c,evaluation_config=EvaluationConfig(**f["evaluation"]),
                use_disk_cache=False,use_native_semantic_legality=False,use_tt=False,use_ordering=True,tuning=SearchTuning(use_root_tactical=False))
            s=GameSession(c);remaining=f["per_call"]["whole_service_seconds"]-(perf_counter()-start)
            assert remaining>0
            d=p.choose_action(s,SearchLimits(max_depth=1,max_nodes=10000,max_time_seconds=remaining,quiescence_max_depth=0,quiescence_hard_max_depth=0))
            packed=record_value(d)
            call=dict(slot=slot,fingerprint=c.ruleset_fingerprint,decision=packed,
                whole_compile_constructor_choose_pack_wall=perf_counter()-start,
                whole_compile_constructor_choose_pack_CPU=process_time()-pc)
            v["calls"].append(call)
            assert d.result_source=="main_iteration"and d.completed_depth==1 and d.result_ordinary_qdepth==0 and d.score==2000
            assert d.runtime_depth_balanced and d.runtime_pushes==d.runtime_pops
            assert d.action in s.legal_actions()
            s.submit(d.action)
            assert len(d.principal_variation)==1 and d.principal_variation[0]==d.action
        actual=v["calls"];old_action=actual[0]["decision"]["action"];new_action=actual[1]["decision"]["action"]
        expected=next(x["mapped_action"]for x in pf["argmax_rows"]if enc(x["action"])==enc(old_action))
        assert any(enc(x["mapped_action"])==enc(new_action)for x in pf["argmax_rows"])
        v.update(status="COMPLETE",literal_selected_action_maps=(enc(expected)==enc(new_action)),
            expected_mapped_old_action=expected,
            interpretation="Different literal choices inside an exactly mappedD1 tie set are not a failedgame/evaluator-equivalence contract or quality gain. If no difference is observed, retain thatnegative result; do not alter input or repeat.")
    except Exception as exc:
        v.update(status="FAIL_STOP_NO_REFILL",failure_type=type(exc).__name__,failure=str(exc))
    v.update(actual_Player_calls=len(v["calls"]),post_decision_PV_submit_calls=len(v["calls"]),whole_experiment_wall=perf_counter()-origin,whole_experiment_CPU=process_time()-cpu,
        actual_executed_search_source_sha256=sha(Path(actual_search.__file__).read_bytes()),
        actual_executed_search_source_LF_sha256=sha(Path(actual_search.__file__).read_bytes().replace(b"\r\n",b"\n")),
        limits="Two cold semantic publicPlayercalls maximum,Pythonlegality,TT/Q/root tacticsOFF; no extra call for tests/reproduction. No speed estimate or fullWDL/actual game quality label. Wholecall includescompile/constructor/choose/recordpacking,excludesinputdiskload/preflight/replay/filepersistence;all experimentcost separately retained.")
    output.write_bytes((json.dumps(v,indent=2)+"\n").encode());return v
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("phase",choices=("freeze","preflight","run"));p.add_argument("--frozen",type=Path,required=True);p.add_argument("--output",type=Path);a=p.parse_args()
    if a.phase=="freeze":print(freeze(a.frozen))
    elif a.phase=="preflight":
        v,_=preflight(json.loads(a.frozen.read_bytes()));print(json.dumps({k:v for k,v in v.items()if k not in("argmax_rows","pattern_map","geometry_map")},indent=2))
    else:
        v=run(a.frozen,a.output);print(json.dumps(dict(status=v["status"],actual_Player_calls=v["actual_Player_calls"],literal_selected_action_maps=v.get("literal_selected_action_maps"),failure=v.get("failure")),indent=2))
