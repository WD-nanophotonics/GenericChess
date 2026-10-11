import json,hashlib,collections,time
from pathlib import Path
import chess
from short_game import score,play,opening
ROOT=Path.cwd();OUT=Path(__file__).resolve().parent;start=time.perf_counter()
checks=[]
def check(name,condition):
    if not condition:raise AssertionError(name)
    checks.append(name)
# Real terminal authorities and cap rewards cannot masquerade as one another.
mate=chess.Board("7k/6Q1/5K2/8/8/8/8/8 b - - 0 1")
check("valid mate",mate.is_valid() and mate.is_checkmate())
check("faster mate preferred",score(mate,True,8)["reward"]>score(mate,True,32)["reward"])
check("later loss preferred",score(mate,False,32)["reward"]>score(mate,False,8)["reward"])
stale=chess.Board("7k/5Q2/6K1/8/8/8/8/8 b - - 0 1")
check("stalemate is actual zero draw",stale.is_stalemate() and score(stale,True,20)["reward"]==0)
root=chess.Board();r=score(root,True,64)
check("cap tie remains ongoing",not r["terminal"] and r["proxy_result"]==0 and r["termination"]=="cutoff")
queen=chess.Board("7k/8/8/8/8/8/4Q3/K7 w - - 0 1")
pawn=chess.Board("7k/8/8/8/8/8/4P3/K7 w - - 0 1")
check("unit reward independent of piece type",queen.is_valid() and pawn.is_valid() and score(queen,True,64)["reward"]==score(pawn,True,64)["reward"])
check("color reversal",score(queen,True,64)["reward"]==-score(queen,False,64)["reward"])
check("mate dominates largest count",score(mate,True,64)["reward"]>1)
# Callback deliberately destroys its private board; live game must retain history.
def fake(board):
    move=sorted(board.legal_moves,key=lambda x:x.uci())[0];board.clear();return move,{"backend":"FAKE_ORCHESTRATION_ONLY"}
g=play(fake,True,opening(51001),52001,cap=8)
check("fixed cap and isolated callback",len(g["actions"])==8 and len(g["search_records"])==4)
# Independent full replay expands Task097 coverage; inspect the first64 ply objective.
rows=[];failures=[];sources={}
for task in ("task093","task096"):
    for path in sorted((ROOT/"results/dev_aux"/task).glob("*.json")):
        d=json.loads(path.read_bytes())
        if not all(k in d for k in ("actions","metrics","final_state","opening")):continue
        sources[path.relative_to(ROOT).as_posix()]=hashlib.sha256(path.read_bytes()).hexdigest()
        try:
            board=chess.Board();cut=None;oplen=len(d["opening"]["actions"])
            for ply,a in enumerate(d["opening"]["actions"]+d["actions"]):
                f,t=a["from"],a["to"];uci=chess.square_name(chess.square(*f))+chess.square_name(chess.square(*t))+(a.get("promotion_target_id") or "").lower()
                move=chess.Move.from_uci(uci);check_legal=move in board.legal_moves
                if not check_legal:raise AssertionError((ply,uci))
                board.push(move)
                if ply+1-oplen==64:cut=score(board,True,64)
            final=d["final_state"]["position"]
            expected=[None if x is None else (x["owner"],x["current_type_id"]) for x in final["board"]]
            actual=[None if board.piece_at(j) is None else (0 if board.piece_at(j).color else 1,board.piece_at(j).symbol().upper()) for j in range(64)]
            if expected!=actual or final["side_to_move"]!=(0 if board.turn else 1):raise AssertionError("final board/turn mismatch")
            if d["status"]=="checkmate" and not board.is_checkmate():raise AssertionError("mate mismatch")
            if d["status"]=="stalemate" and not board.is_stalemate():raise AssertionError("stalemate mismatch")
            if cut is None:cut=score(board,True,len(d["actions"]))
            rows.append(dict(task=task,game=path.stem,full_replay_plies=len(d["actions"]),project_status=d["status"],short_score=cut))
        except Exception as ex:failures.append(dict(task=task,game=path.stem,error=str(ex)))
counts=collections.Counter(x["short_score"]["quantity_difference"] for x in rows if not x["short_score"]["terminal"])
result=dict(complete=not failures,checks=checks,fake_game=g,rows=rows,failures=failures,source_hashes=sources,
            completed_records=len(rows),short_cut_quantity_histogram=dict(sorted(counts.items())),
            short_terminal=collections.Counter(x["short_score"]["termination"] for x in rows),
            wall_seconds=time.perf_counter()-start,
            scope="Exposed Native trajectories only; objective qualification/replay, no learning/no mature/no random-opponent claim. Equal unit reward for pawn and queen is deliberate cutoff-objective bias, not universal price evidence.")
(OUT/"audit.json").write_bytes((json.dumps(result,indent=2)+"\n").encode())
print(json.dumps({k:v for k,v in result.items() if k not in ("rows","source_hashes","fake_game")}))
assert result["complete"]
