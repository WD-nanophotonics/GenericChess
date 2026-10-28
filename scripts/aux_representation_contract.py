"""Finite research controls for representation invariance; no default patch.

Uses existing published builders and actual Core, not a replacement normalizer.
No Player, engine root search, WDL solver or gameplay campaign.
"""
from __future__ import annotations
import argparse, json, hashlib
from collections import Counter
from dataclasses import replace
from pathlib import Path
from generic_chess.core.coordinates import Square
from generic_chess.core.movement import LeapAtom
from generic_chess.core.pieces import Piece, PieceType
from generic_chess.rules.schema import RuleSet, RuleInitialSetupOption, ruleset_to_dict
from generic_chess.rules.compiler import compile_ruleset, compile_legacy_ruleset_for_semantic_execution
from generic_chess.ai.evaluation.profile import build_ruleset_profile, _initially_reachable_type_ids
from generic_chess.ai.evaluation.evaluator import Evaluator
from generic_chess.ai.evaluation.config import EvaluationConfig
from generic_chess.session.session import GameSession
from generic_chess.core.identity import repetition_identity_key
from scripts.research_record import record_value

SOURCE="d91928c548d3a69c83260adfd4198447c69125a4"
def encode(v): return json.dumps(record_value(v),sort_keys=True,separators=(",",":")).encode()
def digest(v): return hashlib.sha256(encode(v)).hexdigest()
def definitions():
    """All literal choices fixed before evaluation. No result-dependent slots."""
    n=4
    K=PieceType("K","K",tuple(LeapAtom((x,y)) for x in (-1,0,1) for y in (-1,0,1) if (x,y)!=(0,0)),is_anchor=True)
    P=PieceType("P","P",(LeapAtom((1,1)),))
    X=PieceType("X","X",(LeapAtom((1,0)),LeapAtom((0,1))))
    rows=[[None]*n for _ in range(n)]
    rows[0][0]=Piece(0,"K","K",False)
    rows[3][0]=Piece(1,"K","K",False)
    rows[2][2]=Piece(0,"P","P",False)
    off=(False,)*(n*n)
    base=RuleSet(board_size=n,piece_types=(K,P),initial_position=tuple(map(tuple,rows)),
        drop_allowed={"P":(off,off)},promotion_allowed={},promotion_forced={},
        capture_disposition="remove_from_game",repetition_limit=4,max_ply=32,stalemate_result="draw")
    # The only extra promotion destinations are outside X's forward mobility.
    decorated=replace(base,piece_types=(K,replace(P,is_promotable=True,promotion_target_ids=("X",)),X),
        drop_allowed={"P":(off,off),"X":(off,off)},
        promotion_allowed={"P":(frozenset({(Square(2,2),Square(3,3))}),
                                frozenset({(Square(1,1),Square(0,0))}))},
        promotion_forced={"P":(frozenset(),frozenset())})
    alt=[list(r) for r in rows];alt[1][1]=Piece(0,"X","X",False)
    alternative=replace(decorated,initial_setup_options=(RuleInitialSetupOption("X-start",tuple(map(tuple,alt))),))
    return base,decorated,alternative

def freeze(path):
    rules=definitions()
    payload=dict(source=SOURCE,question="Does conservative legacy closure imply invariance under a promotion option that Core suppresses everywhere?",
        literal_rules={k:ruleset_to_dict(r) for k,r in zip(("base","dead-promotion","alternate-setup"),rules)},
        expected_before_execution=dict(base_vs_dead="same legal histories, no X creation, maybe different profile median; no numeric outcome frozen",
            alternate_setup="not globally equivalent; X-start includes X and must not be filtered by base-root inventory"),
        protocol=dict(board_size=4,root_transition_depth=2,max_transition_edges=2000,
            no_new_player=True,no_engine_root_search=True,no_WDL=True,
            paired_history="complete repetition key map and count equality at every prefix; fingerprints remain distinct",
            interpretation="source/contract control, deliberately motivated by existing dead-promotion regression, not holdout or game strength"))
    path.parent.mkdir(parents=True,exist_ok=True)
    b=encode(payload)
    if path.exists(): assert path.read_bytes()==b
    else:
        with path.open("xb") as f:f.write(b)
    return digest(payload)

def physical_action(a):
    d=record_value(a)
    # Legacy BoardMove already has no representation identity.
    # Semantic comparison needs its actual mapped pattern separately.
    return d
def paired_legacy(left,right,depth=2,edge_cap=2000,semantic=False):
    compiler=compile_legacy_ruleset_for_semantic_execution if semantic else compile_ruleset
    ca,cb=compiler(left),compiler(right)
    pattern_map={}
    if semantic:
        ap={p.name:p for p in ca.ir.patterns if ca.ir.geometry[p.geometry_ids[0]].kind!="drop"}
        bp={p.name:p for p in cb.ir.patterns if cb.ir.geometry[p.geometry_ids[0]].kind!="drop" and "X" not in p.type_ids}
        assert set(ap)==set(bp)
        for name,p in ap.items():
            x,y=record_value(p),record_value(bp[name]);x.pop("pattern_id");y.pop("pattern_id");assert x==y
            assert all(record_value(ca.ir.geometry[g])==record_value(cb.ir.geometry[g]) for g in p.geometry_ids)
            pattern_map[p.pattern_id]=bp[name].pattern_id
    def mapped(action):return replace(action,pattern_id=pattern_map[action.pattern_id]) if semantic else action
    sa,sb=GameSession(ca),GameSession(cb)
    mapping={};edges=0;nodes=0;replay_submissions=0;terminals=Counter();witness=[]
    def replay(c,record):
        nonlocal replay_submissions
        replay_submissions+=len(record.actions)
        return GameSession.replay(c,record)
    def check(a,b,path):
        nonlocal nodes,edges
        nodes+=1
        x,y=a.state,b.state
        assert x.position.board==y.position.board and x.position.hands==y.position.hands
        assert x.position.side_to_move==y.position.side_to_move and x.ply_count==y.ply_count
        assert x.terminal_status==y.terminal_status
        for z in (x,y):assert not any(p and (p.current_type_id=="X" or p.base_type_id=="X") for p in z.position.board)
        kx,ky=repetition_identity_key(x.position,ca),repetition_identity_key(y.position,cb)
        assert mapping.setdefault(kx,ky)==ky and len(set(mapping.values()))==len(mapping)
        assert {mapping[k]:v for k,v in x.repetition_counts}==dict(y.repetition_counts)
        aa,bb=a.legal_actions(),b.legal_actions()
        assert Counter(encode(physical_action(mapped(z))) for z in aa)==Counter(encode(physical_action(z)) for z in bb)
        terminals[str(record_value(x.terminal_status))]+=1
        if not path or (path and not witness):
            witness.append(dict(path=path,base_record=record_value(a.to_record()),decorated_record=record_value(b.to_record())))
        if len(path)>=depth:return
        for act in aa:
            assert edges<edge_cap,"bounded control exceeded; no silent partial PASS"
            xa=replay(ca,a.to_record());xb=replay(cb,b.to_record())
            xa.submit(act);xb.submit(mapped(act));edges+=1;check(xa,xb,path+[record_value(act)])
    check(sa,sb,[])
    return dict(route="semantic" if semantic else "legacy",pattern_id_mapping=pattern_map,nodes=nodes,paired_edges=edges,direct_paired_edge_submissions=2*edges,prefix_replay_submissions=replay_submissions,total_session_submit_calls=2*edges+replay_submissions,
        repetition_key_bijection_size=len(mapping),terminal_counts=dict(terminals),
        max_depth=depth,complete_to_depth=True,witness=witness,
        scope="Finite history-prefix replay only; global no-X proof uses all promotion destination viability and no other creation source. Not exhaustive game solution.")

def run(frozen,output):
    from generic_chess.rules.schema import ruleset_from_dict
    f=json.loads(frozen.read_bytes())
    a,b,alt=(ruleset_from_dict(f["literal_rules"][k]) for k in ("base","dead-promotion","alternate-setup"))
    rows={}
    for route,compiler in (("legacy",compile_ruleset),("semantic",compile_legacy_ruleset_for_semantic_execution)):
        cases={}
        for key,r in (("base",a),("dead-promotion",b),("alternate-setup",alt)):
            try:
                c=compiler(r)
            except ValueError as exc:
                if key!="alternate-setup":raise
                assert "INITIAL_SETUP_INVENTORY_MISMATCH" in str(exc)
                cases[key]=dict(status="REJECTED_INVALID_LITERAL_INPUT",error=str(exc),
                    correction="Initial planning expected this alternate setup to be valid; actual compiler requires same inventory. Frozen input preserved; no new replacement.")
                continue
            cfg=EvaluationConfig();p=build_ruleset_profile(c,cfg);e=Evaluator(c,p,cfg);s=GameSession(c)
            cases[key]=dict(fingerprint=c.ruleset_fingerprint,reachable_closure=sorted(_initially_reachable_type_ids(c)),
                board_values=dict(p.board_value_by_type),hand_values=dict(p.hand_value_by_base_type),
                raw={t:v.raw_capability_score for t,v in p.piece_profiles.items()},root_value=e.evaluate(s.state),
                root_legal_count=len(s.legal_actions()),root_terminal=record_value(s.state.terminal_status),
                promotion_gain=dict(p.promotion_gain_by_type),promotion_zones={str(k):sorted(v) for k,v in e._zones.items()},
                initial_record=record_value(s.to_record()))
            if key=="dead-promotion":
                # Check EVERY allowed owner/from/to pair, not just current root.
                viability=[dict(owner=owner,origin=record_value(fr),destination=record_value(to),
                    targets={t:len(c.empty_mobility[t][owner][to.rank*4+to.file]) for t in c.types_by_id["P"].promotion_target_ids})
                    for owner in (0,1) for fr,to in c.promotion_allowed["P"][owner]]
                assert all(not any(x["targets"].values()) for x in viability)
                cases[key]["every_declared_promotion_destination_viability"]=viability
            if key=="alternate-setup":
                other=GameSession(c,"X-start")
                cases[key]["alternate_record"]=record_value(other.to_record())
                cases[key]["alternate_X_count"]=sum(p is not None and p.current_type_id=="X" for p in other.state.position.board)
                assert cases[key]["alternate_X_count"]==1
        rows[route]=cases
    paired={route:paired_legacy(a,b,f["protocol"]["root_transition_depth"],f["protocol"]["max_transition_edges"],route=="semantic") for route in ("legacy","semantic")}
    result=dict(source=SOURCE,frozen_input_sha256=hashlib.sha256(frozen.read_bytes()).hexdigest(),
        profiles=rows,paired_Core=paired,
        structural_no_X="Initial and every allowed setup have X inventory zero; no drops/hands/semantic create/transform. All declared P promotion destinations have zero X empty mobility in each owner frame; Core suppresses every such promotion. Move/capture-removal induction keeps all histories X-free; unchanged old movement and adjudication transport full histories.",
        limits="No new normalizer, product patch, full minimax labels, timing, search or playing-strength experiment. Legacy closure deliberately overapproximates promotion reachability; report actual numeric outcome, not an asserted bug.")
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_bytes((json.dumps(result,indent=2)+"\n").encode())
    return result
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("phase",choices=("freeze","run"));p.add_argument("--frozen",required=True,type=Path);p.add_argument("--output",type=Path);a=p.parse_args()
    if a.phase=="freeze":print(freeze(a.frozen))
    else:
        r=run(a.frozen,a.output)
        print(json.dumps(dict(profiles=r["profiles"],paired={route:{k:v for k,v in d.items() if k!="witness"} for route,d in r["paired_Core"].items()}),indent=2))
