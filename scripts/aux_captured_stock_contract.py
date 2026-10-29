"""One full-history captured-stock/learner-gradient boundary; no training."""
from __future__ import annotations
from pathlib import Path
from dataclasses import replace
from collections import Counter
import argparse,json,hashlib
from scripts.aux_representation_contract import definitions,encode
from scripts.research_record import record_value
from generic_chess.rules.schema import ruleset_to_dict,ruleset_from_dict
from generic_chess.rules.compiler import compile_ruleset,compile_legacy_ruleset_for_semantic_execution
from generic_chess.core.identity import repetition_identity_key
from generic_chess.session.session import GameSession
from generic_chess.learning.incremental import FixedScaleSessionEnv,Model
def definitions_pair():
    a,_,_=definitions()
    b=replace(a,capture_disposition="capture_to_hand")
    capture=[((0,0),(1,0)),((0,3),(1,2)),((1,0),(0,0)),((1,2),(2,2))]
    cycle=[((0,0),(1,0)),((2,2),(2,3)),((1,0),(0,0)),((2,3),(2,2))]
    return a,b,capture+cycle*3
def freeze(path):
    a,b,trace=definitions_pair()
    v=dict(source="48749ec334c9eb42955a844f06e1d101bb2a02e2",
        literal_rules=[ruleset_to_dict(a),ruleset_to_dict(b)],coordinate_trace=trace,
        intended_relation="Same reachableboard; target owner1 handP=1-boardowner0P,owner0handempty. This relation is injective over reachablepositions, not arbitrarycaller states.",
        expected="Fourfoldoutcome and fullcountmap should agree. FixedPunit learner predicts same atzero freeweights but targethand gradient may become nonzero aftercapture.",
        cost=dict(max_trace_plies_per_rule_route=16,Player=0,search=0,train=0))
    raw=encode(v);path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():assert path.read_bytes()==raw
    else:
        with path.open("xb")as f:f.write(raw)
    return hashlib.sha256(raw).hexdigest()
def physical(a):
    return (a.from_square.file,a.from_square.rank,a.to_square.file,a.to_square.rank,a.promotion_target_id)
def promotion_boundary():
    """A four-ply actual Core witness: CURRENT != BASE inventory."""
    from scripts.aux_promotion_frame_contract import definitions as promotion_definitions
    r,_=promotion_definitions()
    r=replace(r,capture_disposition="capture_to_hand")
    rows={}
    for name,C in (("legacy",compile_ruleset),("semantic",compile_legacy_ruleset_for_semantic_execution)):
        session=GameSession(C(r));trace=[]
        def row():
            pos=session.state.position
            base=sum((1 if p.owner==0 else -1) for p in pos.board if p and p.base_type_id=="P")
            current=sum((1 if p.owner==0 else -1) for p in pos.board if p and p.current_type_id=="P")
            hand=pos.hands[0].count("P")-pos.hands[1].count("P")
            assert hand==base-1
            trace.append(dict(ply=session.state.ply_count,base_P=base,current_P=current,hand_P=hand,
                              features=FixedScaleSessionEnv(session,unit_type="P").features()))
        row()
        for fr,to,prom in [((1,1),(1,2),"G"),((3,3),(3,2),None),
                           ((1,2),(2,2),None),((3,2),(2,2),None)]:
            action=next(a for a in session.legal_actions() if
                (a.from_square.file,a.from_square.rank)==fr and
                (a.to_square.file,a.to_square.rank)==to and a.promotion_target_id==prom)
            session.submit(action);row()
        assert trace[1]["current_P"]==0 and trace[1]["base_P"]==1 and trace[1]["hand_P"]==0
        assert trace[4]["hand_P"]==-1 and session.state.position.hands[1].count("G")==0
        rows[name]=dict(trace=trace,actual_Session_submit_calls=4,record=record_value(session.to_record()))
    return dict(literal_rule=ruleset_to_dict(r),routes=rows,actual_Session_submit_calls=8,
                scope="One promotion/current-versus-base boundary, not new Player, solver, game campaign or learning.")

def admit_inert_pair(a,b):
    """Reject configurations not covered by this exact stock/board proof."""
    assert a.capture_disposition=="remove_from_game" and b.capture_disposition=="capture_to_hand"
    expected,_,_=definitions()
    assert a==expected, "This reader admits only the literal one-P proof input"
    assert replace(a,capture_disposition="capture_to_hand")==b
    for r in(a,b):
        assert not(r.semantic_actions or r.declarations or r.promotion_allowed or r.initial_setup_options)
        assert all(not any(mask)for masks in r.drop_allowed.values()for mask in masks)

def run(frozen,output):
    f=json.loads(frozen.read_bytes());a,b=map(ruleset_from_dict,f["literal_rules"])
    admit_inert_pair(a,b)
    out={}
    for route,C in(("legacy",compile_ruleset),("semantic",compile_legacy_ruleset_for_semantic_execution)):
        ca,cb=C(a),C(b);sa,sb=GameSession(ca),GameSession(cb)
        models=[Model([0.,0.],fixed=0,scale=10.)for _ in range(2)]
        keys={};trace=[]
        def observe():
            x,y=sa.state,sb.state
            assert x.position.board==y.position.board and x.position.side_to_move==y.position.side_to_move and x.ply_count==y.ply_count
            assert x.terminal_status==y.terminal_status
            p=sum(q is not None and q.owner==0 and q.current_type_id=="P"for q in x.position.board)
            assert p in(0,1)and not any(h.counts for h in x.position.hands)
            assert not y.position.hands[0].counts and y.position.hands[1].count("P")==1-p
            assert all(t=="P"and n==1-p for t,n in y.position.hands[1].counts)
            kx,ky=repetition_identity_key(x.position,ca),repetition_identity_key(y.position,cb)
            assert keys.setdefault(kx,ky)==ky and len(set(keys.values()))==len(keys)
            assert {keys[k]:v for k,v in x.repetition_counts}==dict(y.repetition_counts)
            aa,bb=sa.legal_actions(),sb.legal_actions()
            assert len({physical(q)for q in aa})==len(aa)and len({physical(q)for q in bb})==len(bb)
            assert Counter(physical(q)for q in aa)==Counter(physical(q)for q in bb)
            observations=[]
            for s,m in zip((sa,sb),models):
                env=FixedScaleSessionEnv(s,unit_type="P");phi=env.features()
                assert env.names==(("board","P"),("hand","P"))
                terminal=env.terminal()
                observations.append(dict(features=phi,raw=m.raw(phi),prediction=m.prediction(phi),
                    raw_model_gradient=m.gradient(phi),
                    actual_terminal_leaf_gradient=([0.,0.]if terminal is not None else None),
                    actual_terminal_WLD=terminal))
            assert observations[0]["features"]==(p,0)and observations[1]["features"]==(p,p-1)
            assert observations[0]["raw"]==observations[1]["raw"]==p
            if p==0 and not x.terminal_status.is_terminal:
                assert observations[0]["raw_model_gradient"]==(0.,0.)
                assert observations[1]["raw_model_gradient"]==(0.,-.1)
            trace.append(dict(ply=x.ply_count,P_on_board=p,source_current_count=dict(x.repetition_counts)[kx],
                target_current_count=dict(y.repetition_counts)[ky],source_counts=record_value(x.repetition_counts),
                target_counts=record_value(y.repetition_counts),terminal=record_value(x.terminal_status),learner=record_value(observations)))
        observe()
        for start,end in f["coordinate_trace"]:
            for s in(sa,sb):
                q=next(q for q in s.legal_actions()if(q.from_square.file,q.from_square.rank)==tuple(start)and(q.to_square.file,q.to_square.rank)==tuple(end))
                s.submit(q)
            observe()
        assert sa.state.ply_count==16 and sa.state.terminal_status.is_terminal
        assert sa.state.terminal_status.winner is None and str(sa.state.terminal_status.status.value)=="repetition"
        assert all(m.weights==[1.,0.]for m in models)
        out[route]=dict(trace=trace,source_record=record_value(sa.to_record()),target_record=record_value(sb.to_record()),
            repetition_identity_bijection_size=len(keys),actual_Session_submit_calls=32,model_updates=0)
    v=dict(source=f["source"],frozen_input_sha256=hashlib.sha256(frozen.read_bytes()).hexdigest(),routes=out,
        actual_Session_submit_calls=64,
        interpretation="On this exact reachableinventory,hand stock is determinedbyboard and cannotbeused/readbyrules beyondtypedidentity. Fullhistoryrelationpreserves4fold. Nevertheless reallearnerhandfeature=boardP-1 becomesnonzero,withfreegradient-.1 atzero handweight. No-drop doesnotimplyzerogradient. Nonzero gradient alone doesnot imply nonzeroTDerrors, identifiability ofindependentstockvalue, usefullearning or a traininggain.",
        scope="A controlled existingcapture-disposition variant,not a general state quotient. Arbitraryinitialstock,drop,creation,promotion,ownerchange,hand-consuming/readingDSL/declarations or otherhistorypolicies invalidate this proof unless separately mapped. No state/TTkey was replaced. No Player/search/train/modelapply/observe/finish was called. Actual terminaldraw is one16plytrace,not a solvedgameWDL label.")
    output.parent.mkdir(parents=True,exist_ok=True);output.write_bytes((json.dumps(v,indent=2)+"\n").encode());return v
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("phase",choices=("freeze","run"));p.add_argument("--frozen",type=Path,required=True);p.add_argument("--output",type=Path);a=p.parse_args()
    if a.phase=="freeze":print(freeze(a.frozen))
    else:
        v=run(a.frozen,a.output)
        print(json.dumps({r:dict(prefix4=d["trace"][4],final=d["trace"][-1],submits=d["actual_Session_submit_calls"])for r,d in v["routes"].items()},indent=2))
