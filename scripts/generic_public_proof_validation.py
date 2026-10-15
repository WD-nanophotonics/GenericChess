"""Bounded complete finite public-game reference for no-progress proof fallback.

Only the reference sees its exact outcome; the solver receives rules/state.
All roots are declared initial setups, so no-progress replay is authoritative.
No board-only memo: histories remain distinct even on the same board.
"""
import collections,json,random,time
from dataclasses import replace
from pathlib import Path
from generic_chess.core.pieces import Piece
from generic_chess.core.transition import initial_state,apply_action
from generic_chess.core.movegen import legal_actions
from generic_chess.rules.schema import RuleNoProgressDraw
from generic_chess.rules.compiler import compile_ruleset
from scripts.generic_royal_actor import RoyalActor
from scripts.generic_proof_fixtures import krk_ruleset
from scripts.generic_proof_native_study import sha,mod
from scripts.generic_public_win_proof import prove_win_public,verify_public_certificate,PublicStrategyCursor
from scripts.generic_win_proof import PROVEN_WIN


def freeze(folder):
    out=Path(folder);out.mkdir(exist_ok=False);rng=random.Random(20261015565);model=RoyalActor(4);roots=[];seen=set()
    while len(roots)<24:
        k,b,r=rng.sample(range(16),3);board=["."]*16;board[k]="K";board[b]="k";board[r]="R";raw=tuple(board)+(0,)
        if raw in seen or not model.valid(raw) or len(model.moves(raw))<2:continue
        seen.add(raw);roots.append(dict(k=k,b=b,r=r))
    sources=["scripts/generic_public_win_proof.py","scripts/generic_proof_public_path.py","scripts/generic_public_proof_validation.py"]
    plan=dict(seed=20261015565,roots=roots,thresholds=[1,2,4],max_ply=4,targets=[0,1],max_nodes=16384,seconds_per_call=.5,verification_nodes=65536,verification_seconds=1.,total_seconds=600,expected_seconds=180,max_reference_nodes=2000000,source_sha256={x:sha(x) for x in sources},purpose="Actual finite maxply4 rule WDL including no-progress threshold/capture reset; no price learning or infinite-WDL inference. Root selection before labels, all planned roots/targets retained, no cap extension.")
    (out/"plan.json").write_text(json.dumps(plan,indent=2),encoding="utf-8")
    (out/"source").mkdir()
    for x in sources:(out/"source"/Path(x).name).write_bytes(Path(x).read_bytes())
    print("PUBLIC_REFERENCE_FROZEN",len(roots)*len(plan["thresholds"]),flush=True)


def run(folder):
    out=Path(folder);p=json.loads((out/"plan.json").read_text())
    assert all(sha(x)==h for x,h in p["source_sha256"].items())
    stop=mod("PUBLIC_VALIDATION_STOP56","results/dev_aux/task166/run.py").stop
    started=time.perf_counter();deadline=started+p["total_seconds"];nodes=edges=0;counts=collections.Counter();done=0;proofs=0;error=None;active={}
    def guard():
        if time.perf_counter()>=deadline:raise RuntimeError("frozen_wallcap")
        if nodes>=p["max_reference_nodes"]:raise RuntimeError("frozen_reference_nodecap")
        if nodes%64==0:stop()
    def exact(state,c):
        nonlocal nodes,edges
        guard();nodes+=1;t=state.terminal_status
        if t.is_terminal:
            counts["reference_terminal_"+t.status.value]+=1
            return 0 if t.winner is None else 1 if t.winner==0 else -1
        children=[]
        for action in legal_actions(state,c):
            guard();edges+=1;children.append(exact(apply_action(state,action,c),c))
        assert children,"unreported public terminal"
        return max(children) if state.position.side_to_move==0 else min(children)
    with (out/"calls.jsonl").open("x",encoding="utf-8") as log:
        try:
            for i,root in enumerate(p["roots"]):
                for threshold in p["thresholds"]:
                    stop();guard();active=dict(root=i,threshold=threshold,phase="REFERENCE")
                    rs=krk_ruleset(4);board=[None]*16
                    for sq,piece in [(root["k"],Piece(0,"K","K")),(root["b"],Piece(1,"K","K")),(root["r"],Piece(0,"R","R"))]:board[sq]=piece
                    rs=replace(rs,initial_position=tuple(tuple(board[k:k+4]) for k in range(0,16,4)),max_ply=p["max_ply"],no_progress_draw=RuleNoProgressDraw(threshold,True))
                    c=compile_ruleset(rs);s=initial_state(c);before=nodes;beg=time.perf_counter();label=exact(s,c);reference_seconds=time.perf_counter()-beg
                    for target in p["targets"]:
                        stop();guard();active.update(phase="PROOF",target=target)
                        r=prove_win_public(c,s,target=target,max_nodes=p["max_nodes"],seconds=p["seconds_per_call"],max_depth=p["max_ply"],cancel=lambda:time.perf_counter()>=deadline)
                        receipt=None;physical=[]
                        if r.status==PROVEN_WIN:
                            assert label==(1 if target==0 else -1)
                            receipt=verify_public_certificate(c,s,r.certificate,max_nodes=p["verification_nodes"],seconds=p["verification_seconds"],cancel=lambda:time.perf_counter()>=deadline)
                            assert receipt["verified"],receipt
                            cursor=PublicStrategyCursor(c,r.certificate,max_nodes=p["verification_nodes"],seconds=p["verification_seconds"])
                            while cursor.node.edges:
                                action=cursor.node.edges[0][0];physical.append(dict(rank=cursor.node.rank,actor=cursor.state.position.side_to_move,action=str(action)))
                                cursor.advance(cursor.state,action)
                            assert cursor.state.terminal_status.winner==target;proofs+=1
                        assert r.pushes==r.pops and r.nodes<=p["max_nodes"]
                        record=dict(root=i,input=root,threshold=threshold,target=target,rule_fingerprint=c.ruleset_fingerprint,exact_for_player0=label,reference_nodes=nodes-before,reference_seconds=reference_seconds,status=r.status,reason=r.reason,proof_nodes=r.nodes,proof_seconds=r.seconds,rank=r.certificate.tree.rank if r.certificate else None,verification=receipt,actual_physical_path=physical)
                        log.write(json.dumps(record)+"\n");log.flush();done+=1;counts[str((threshold,label,target,r.status))]+=1
                    print("PUBLIC_REFERENCE_ROOT",i,threshold,"label",label,"nodes",nodes,flush=True)
        except BaseException as exc:error=type(exc).__name__+":"+str(exc)
    result=dict(status="COMPLETE_FINITE_REFERENCE_PASS" if error is None else "PARTIAL_PRESERVED",error=error,calls=done,planned_calls=len(p["roots"])*len(p["thresholds"])*len(p["targets"]),proved_and_physically_won=proofs,reference_nodes=nodes,reference_edges=edges,counts=dict(counts),active_if_interrupted=active if error else None,seconds=time.perf_counter()-started,native_go=0,limits="Only declared4x4KRK maxply4 initial setups. Unknown is not refutation. Public-rule oracle validates proof search, not independently reimplements rule semantics. Executed one defense path per certificate; verifier enumerates all defenses.")
    (out/"result.json").write_text(json.dumps(result,indent=2),encoding="utf-8");print(json.dumps(result))


if __name__=="__main__":
    import argparse
    a=argparse.ArgumentParser();a.add_argument("mode",choices=["freeze","run"]);a.add_argument("folder");args=a.parse_args();(freeze if args.mode=="freeze" else run)(args.folder)
