"""Exact complete-D1 linear-material sensitivity over an integer price box.

A baseline argmax is invariant iff every competitor fails to beat it anywhere
in the box, accounting for lexical ties. Maximize each affine score difference
at its analytic box corner: O(actions * parameters), no LP or training.
"""
from dataclasses import replace
import json,time
from pathlib import Path
import numpy as np

from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.alphabeta.search import terminal_score
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.ai.evaluation.evaluator import Evaluator
from generic_chess.ai.evaluation.semantic import build_semantic_opportunity_profile
from generic_chess.ai.limits import SearchLimits
from generic_chess.core.transition import legal_successors
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record,serialize_game_record
from scripts.price_regions import CONFIG
from scripts.research_record import write_record,record_value


def vector(state,owner,features):
    index={f:i for i,f in enumerate(features)};v=np.zeros(len(features),dtype=np.int64)
    for p in state.position.board:
        if p is not None and ('board',p.current_type_id) in index:
            v[index['board',p.current_type_id]]+=1 if p.owner==owner else -1
    for side,h in enumerate(state.position.hands):
        for tid,n in h.counts:
            if ('hand',tid) in index:v[index['hand',tid]]+=n*(1 if side==owner else -1)
    return v


def certificate(vectors,constants,baseline,lo,hi):
    scores=vectors@baseline+constants;k=int(np.argmax(scores))
    best_witness=None
    for j in range(len(vectors)):
        if j==k:continue
        delta=vectors[j]-vectors[k];corner=np.where(delta>0,hi,np.where(delta<0,lo,baseline))
        maximum=int(delta@corner+constants[j]-constants[k])
        if maximum>0 or maximum==0 and j<k:
            winner=int(np.argmax(vectors@corner+constants))
            assert winner!=k
            # An interior integer witness distinguishes robust movement from a
            # box-face tie when one step away from every bound still changes it.
            inside=np.minimum(hi-1,np.maximum(lo+1,corner))
            inside=np.where(hi==lo,lo,inside)
            interior=int(np.argmax(vectors@inside+constants))
            candidate=dict(weights=corner.tolist(),selected=winner,competitor=j,
                margin_over_baseline=maximum,interior_selected=interior,
                interior_weights=inside.tolist(),interior_changed=interior!=k)
            if best_witness is None or maximum>best_witness['margin_over_baseline']:best_witness=candidate
    return dict(invariant=best_witness is None,baseline_selected=k,
                baseline_score=int(scores[k]),witness=best_witness)


def run(source,output):
    if output.exists():raise FileExistsError(output)
    output.parent.mkdir(parents=True,exist_ok=True)
    data=json.loads(source.read_text());start=time.perf_counter();children=0
    plan=dict(question='Does nonzero root material predict actual complete-D1 price sensitivity?',
        source=str(source).replace('\\','/'),prefixes=[0,9,18,27],planned_slots=96,seconds=90,max_children=10000,
        features='All declared nonanchor board CURRENT types and hand BASE types; anchor coefficients0.',
        box='board125..4000, hand0..4000, independently; integer coefficients; no median renormalization.',
        baseline='Unit board1000/hand900; no dynamic/promotion bonus,q,TT,ordering.',
        scope='Exposed six cannon-recombined rules/24saved full histories; D1 only, no WDL, fit or strength claim; no frozen games rerun.')
    report=dict(plan=plan,rows=[],public_checks=[])
    write_record(output,report)
    for rule in data['rules']:
        compiled=compile_ruleset_for_execution(ruleset_from_dict(rule['definition']))
        assert not compiled.ir.declarations,'Declarations require a separately defined decision box'
        types=tuple(sorted(t for t,p in compiled.support.type_metadata.items() if not p.is_anchor))
        features=tuple((kind,t) for kind in ('board','hand') for t in types)
        n=len(types);baseline=np.array([1000]*n+[900]*n,dtype=np.int64)
        lows=np.array([125]*n+[0]*n,dtype=np.int64);highs=np.array([4000]*(2*n),dtype=np.int64)
        profile,_=build_semantic_opportunity_profile(compiled,CONFIG)
        verified=False
        for slot in [x for x in data['slots'] if x['seed']==rule['seed']]:
            session=GameSession(compiled);rec=deserialize_game_record(json.dumps(slot['record']))
            for ply in range(len(rec.actions)+1):
                if time.perf_counter()-start>=90 or children>=10000:
                    report['incomplete']='global cost fuse';write_record(output,report);return report
                if ply in plan['prefixes']:
                    row=dict(seed=rule['seed'],policy=slot['policy'],ply=ply,owner=session.state.position.side_to_move,
                        record=json.loads(serialize_game_record(session.to_record())),features=features)
                    report['rows'].append(row)
                    if session.state.terminal_status.is_terminal:
                        row.update(status='terminal_at_prefix',terminal=record_value(session.state.terminal_status))
                    else:
                        pairs=sorted(legal_successors(session.state,compiled),key=lambda z:str(z[0]))
                        children+=len(pairs)
                        vectors=[];constants=[]
                        for a,c in pairs:
                            if c.terminal_status.is_terminal:
                                vectors.append(np.zeros(2*n,dtype=np.int64))
                                constants.append(-terminal_score(c.terminal_status,c.position.side_to_move,1))
                            else:vectors.append(vector(c,session.state.position.side_to_move,features));constants.append(0)
                        vs=np.array(vectors,dtype=np.int64);cs=np.array(constants,dtype=np.int64)
                        assert max(abs(vs@highs+cs))<1000000001
                        row.update(status='ongoing',root_vector=vector(session.state,session.state.position.side_to_move,features).tolist(),
                            actions=[str(a) for a,_ in pairs],child_vectors=vs.tolist(),constants=cs.tolist(),
                            all_material_children_identical=bool(np.all(vs==vs[0])),certificates={})
                        for label in ('full','board_only','hand_only'):
                            lo=lows.copy();hi=highs.copy()
                            if label=='board_only':lo[n:]=hi[n:]=baseline[n:]
                            if label=='hand_only':lo[:n]=hi[:n]=baseline[:n]
                            row['certificates'][label]=certificate(vs,cs,baseline,lo,hi)
                        full=row['certificates']['full']
                        if not verified and not full['invariant']:
                            for weights in (baseline,np.array(full['witness']['weights'],dtype=np.int64)):
                                board={t:0 for t in compiled.support.type_metadata};hand=board.copy()
                                for (kind,t),w in zip(features,weights):(board if kind=='board' else hand)[t]=int(w)
                                p=replace(profile,board_value_by_type=board,hand_value_by_base_type=hand,
                                    promotion_gain_by_type={t:0 for t in board})
                                player=AlphaBetaPlayer(compiled,evaluator_override=Evaluator(compiled,p,CONFIG),
                                    use_disk_cache=False,use_tt=False,use_ordering=False,use_native_semantic_legality=False,
                                    tuning=SearchTuning(use_root_tactical=False))
                                before=session.state
                                d=player.choose_action(session,SearchLimits(max_depth=1,max_nodes=100000,max_time_seconds=3,
                                    quiescence_max_depth=0,quiescence_hard_max_depth=0))
                                ix=int(np.argmax(vs@weights+cs))
                                assert d.completed_depth==1 and d.score==int(vs[ix]@weights+cs[ix]) and d.action==pairs[ix][0]
                                assert session.state==before
                                report['public_checks'].append(dict(seed=rule['seed'],policy=slot['policy'],ply=ply,
                                    weights=weights.tolist(),expected_action=str(pairs[ix][0]),decision=record_value(d)))
                            verified=True
                if ply<len(rec.actions):session.submit(rec.actions[ply])
            assert session.state==GameSession.replay(compiled,rec).state
            for missing in [p for p in plan['prefixes'] if p>len(rec.actions)]:
                report['rows'].append(dict(seed=rule['seed'],policy=slot['policy'],ply=missing,status='ended_before_prefix',
                    terminal=record_value(session.state.terminal_status)))
        write_record(output,report)
    report.update(wall_seconds=time.perf_counter()-start,children=children,observed_slots=len(report['rows']))
    write_record(output,report)
    return report


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('source',type=Path);p.add_argument('output',type=Path)
    a=p.parse_args();r=run(a.source,a.output)
    print({k:r.get(k) for k in ('observed_slots','children','wall_seconds','incomplete')})
