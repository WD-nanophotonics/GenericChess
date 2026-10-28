"""Actual legal-prefix witness to non-invariance of heuristic expectations.

No learning update, trained model, engine search or terminal-reward claim.
"""
from __future__ import annotations
from pathlib import Path
from fractions import Fraction
from math import tanh
from dataclasses import replace
import argparse,json,hashlib
from scripts.aux_representation_contract import definitions,encode
from generic_chess.rules.compiler import compile_ruleset,compile_legacy_ruleset_for_semantic_execution
from generic_chess.session.session import GameSession
from generic_chess.ai.evaluation.config import EvaluationConfig
from generic_chess.ai.evaluation.profile import build_ruleset_profile
from generic_chess.ai.evaluation.evaluator import Evaluator
from generic_chess.core.identity import repetition_identity_key
from scripts.research_record import record_value
from generic_chess.learning.incremental import FixedScaleSessionEnv,Model

PATHS={
 "comparison":(((0,0),(0,1)),((0,3),(1,3)),((0,1),(1,0)),((1,3),(2,2))),
 "mixture-common":(((0,0),(1,0)),((0,3),(1,2)),((1,0),(0,0)),((1,2),(2,2))),
 "mixture-rare":(((0,0),(1,0)),((0,3),(1,2)),((1,0),(0,0)),((1,2),(0,3))),
}
def freeze(path):
    a,b,_=definitions()
    v=dict(source="d91928c548d3a69c83260adfd4198447c69125a4",
        paired_fingerprints=[compile_ruleset(r).ruleset_fingerprint for r in(a,b)],
        coordinate_paths=PATHS,mixture_probability={"rare":[1,48],"common":[47,48]},
        illustrative_tanh_scale=1000,
        purpose="Constructive exact comparator for mean heuristic scores, NOT an observed random-policy frequency, actual target dataset, or new terminal objective.",
        predicted="All3four-ply paths legal/ongoing; compare deterministic policy score with specified rare/common mixture. Strictly increasing leaf embedding need not commute with expectation.")
    raw=encode(v);path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():assert path.read_bytes()==raw
    else:
        with path.open("xb")as f:f.write(raw)
    return hashlib.sha256(raw).hexdigest()
def run(frozen,output):
    f=json.loads(frozen.read_bytes());a,b,_=definitions();cfg=EvaluationConfig();out={}
    assert [compile_ruleset(r).ruleset_fingerprint for r in(a,b)]==f["paired_fingerprints"]
    for route,C in(("legacy",compile_ruleset),("semantic",compile_legacy_ruleset_for_semantic_execution)):
        ca,cb=C(a),C(b);ea=Evaluator(ca,build_ruleset_profile(ca,cfg),cfg);eb=Evaluator(cb,build_ruleset_profile(cb,cfg),cfg)
        rows={}
        for name,path in f["coordinate_paths"].items():
            sa,sb=GameSession(ca),GameSession(cb);mapping={};prefix=[]
            def check():
                x,y=sa.state,sb.state
                assert x.position.board==y.position.board and x.position.hands==y.position.hands and x.ply_count==y.ply_count
                assert x.terminal_status==y.terminal_status and not x.terminal_status.is_terminal
                ka,kb=repetition_identity_key(x.position,ca),repetition_identity_key(y.position,cb)
                assert mapping.setdefault(ka,kb)==kb and len(set(mapping.values()))==len(mapping)
                assert {mapping[k]:v for k,v in x.repetition_counts}==dict(y.repetition_counts)
                prefix.append(dict(ply=x.ply_count,old_current_count=dict(x.repetition_counts)[ka],new_current_count=dict(y.repetition_counts)[kb]))
            check()
            for start,end in path:
                for s in(sa,sb):
                    act=next(z for z in s.legal_actions() if (z.from_square.file,z.from_square.rank)==tuple(start) and (z.to_square.file,z.to_square.rank)==tuple(end))
                    s.submit(act)
                check()
            assert sa.state.position.side_to_move==0
            learner=[]
            for s in (sa,sb):
                env=FixedScaleSessionEnv(s,unit_type="P")
                model=Model([0.0]*len(env.names),fixed=0,scale=10.0)
                phi=env.features()
                assert all(value==0 for i,value in enumerate(phi) if i!=model.fixed)
                assert all(g==0 for g in model.gradient(phi))
                learner.append(dict(names=record_value(env.names),features=list(phi),
                    material_raw=model.raw(phi),prediction=model.prediction(phi),
                    gradient=list(model.gradient(phi))))
            assert learner[0]["material_raw"]==learner[1]["material_raw"]
            assert learner[0]["prediction"]==learner[1]["prediction"]
            rows[name]=dict(old=ea.evaluate(sa.state),new=eb.evaluate(sb.state),learner_readonly=learner,
                final_ply=sa.state.ply_count,terminal=record_value(sa.state.terminal_status),
                old_record=record_value(sa.to_record()),new_record=record_value(sb.to_record()),prefix_counts=prefix)
        p=Fraction(*f["mixture_probability"]["rare"]);expected={}
        for representation in("old","new"):
            comparator=Fraction(rows["comparison"][representation])
            mixed=p*rows["mixture-rare"][representation]+(1-p)*rows["mixture-common"][representation]
            scale=f["illustrative_tanh_scale"]
            bounded_mixed=float(p)*tanh(rows["mixture-rare"][representation]/scale)+float(1-p)*tanh(rows["mixture-common"][representation]/scale)
            expected[representation]=dict(raw_comparator=str(comparator),raw_mixture=str(mixed),raw_difference=str(mixed-comparator),
                illustrative_tanh_comparator=tanh(float(comparator)/scale),illustrative_tanh_mixture=bounded_mixed)
        assert Fraction(expected["old"]["raw_difference"])>0 and Fraction(expected["new"]["raw_difference"])<0
        assert expected["old"]["illustrative_tanh_mixture"]>expected["old"]["illustrative_tanh_comparator"]
        assert expected["new"]["illustrative_tanh_mixture"]<expected["new"]["illustrative_tanh_comparator"]
        out[route]=dict(legal_prefixes=rows,expectations=expected,actual_Session_submit_calls=24)
    v=dict(source=f["source"],frozen_input_sha256=hashlib.sha256(frozen.read_bytes()).hexdigest(),routes=out,
        actual_Session_submit_calls=48,
        interpretation="Actual4ply/Core-compatible conditional continuation policies, all leavesongoing andfullWDLUNKNOWN. Probability1/48 is deliberately specified, not estimated, uniform-opponent or optimal-play claim. Heuristic-mean comparator reverses despite identical ordinal leaf relation. Illustrativetanh1000 is not maintainedlearner's configuredscale.",
        actual_learner_scope="Existingincremental.Model usesfixedunit weight/scale anditsownMaterialoverride, notgeneric-v5defaultprofile. TDLeafEpisode freezesepisode,transformednonterminalvalues/gradients andactualterminalWLD; arbitrarymonotonevaluemappingdoesnotguaranteeupdateequivariance. No observation/update/training function was called here.")
    output.write_bytes((json.dumps(v,indent=2)+"\n").encode());return v
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("phase",choices=("freeze","run"));p.add_argument("--frozen",type=Path,required=True);p.add_argument("--output",type=Path);a=p.parse_args()
    if a.phase=="freeze":print(freeze(a.frozen))
    else:
        r=run(a.frozen,a.output);print(json.dumps({k:dict(scores={n:{f:x[f]for f in("old","new","final_ply")}for n,x in v["legal_prefixes"].items()},expectations=v["expectations"])for k,v in r["routes"].items()},indent=2))
