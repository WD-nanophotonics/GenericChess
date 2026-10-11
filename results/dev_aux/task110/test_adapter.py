"""Fault injection into actual adapter/game integration; no engine or learning claim."""
import importlib.util, json, sys, tempfile, time, queue, hashlib
from pathlib import Path
import chess
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/"results/dev_aux/task109"))
import adapter
import run as runner
checks=[]
def check(name,value):
    if not value:raise AssertionError(name)
    checks.append(name)
def raises(name,kind,call):
    try:call()
    except kind:checks.append(name);return
    raise AssertionError(name+" did not fail")
class MockEngine:
    def __init__(self,mode="lexical",missing=None):
        self.backend="MOCK_UCI_ORCHESTRATION_ONLY";self.mode=mode;self.commands=[];self.closed=False;self.board=chess.Board();self.config_weights=None
        names=["Threads","Hash","Use NNUE","SyzygyPath","VariantPath","UCI_Variant"]
        self.handshake=["option name "+n+" type string" for n in names if n!=missing]+["uciok"]
    def send(self,line):
        self.commands.append(line)
        if line.startswith("setoption name VariantPath value "):
            config=Path(line.split(" value ",1)[1]).read_text()
            values=config.split("pieceValueMg = ",1)[1].splitlines()[0]
            self.config_weights={k.upper():int(v) for k,v in (field.split(":") for field in values.split())}
        if line.startswith("position fen "):self.board=chess.Board(line.split("position fen ",1)[1])
        if line.startswith("position startpos"):
            self.board=chess.Board()
            for move in line.split()[3:]:self.board.push_uci(move)
    def ready(self):
        last=self.commands[-1];self.commands.append("isready")
        if last=="setoption name UCI_Variant value aux_short" and self.mode!="ignored_variant":
            return ["info string variant aux_short files 8 ranks 8 pocket 0 template chess startpos "+chess.Board().fen(),"readyok"]
        if last=="eval":
            kind=next(p.symbol().upper() for p in self.board.piece_map().values() if p.piece_type!=chess.KING)
            value=1 if self.mode=="ignored_weights" else self.config_weights[kind]/208
            return ["Final evaluation       "+format(value,".2f")+" (white side)","readyok"]
        return ["readyok"]
    def until(self,predicate):
        if self.mode=="illegal":return ["bestmove a1a8"]
        if self.mode=="eof":raise RuntimeError("mock EOF")
        move=sorted(self.board.legal_moves,key=lambda x:x.uci())[0]
        return ["info nodes 1024","bestmove "+move.uci()]
    def close(self):self.closed=True
w=runner.PROFILES[0]
ctx=dict(opening_seed=41001,random_seed=42001,agent_color=True,phase="pilot",name="finite")
with tempfile.TemporaryDirectory(dir=ROOT/".local_agent") as temporary:
    base=Path(temporary)
    j=adapter.Journal(base/"legal.jsonl");engine=MockEngine()
    g=adapter.play_game(engine,w,ctx,1000,base/"legal.ini",j,runner.GAME.opening,runner.GAME.score,lambda:None,clock=lambda:0)
    j.close()
    check("64ply cap",len(g["actions"])<=64)
    check("mock backend stays explicit",all(r["backend"]=="MOCK_UCI_ORCHESTRATION_ONLY" for r in g["search_records"]))
    check("no human/learned reward",g["reward"]==g["score"]["terminal_component"]+g["score"]["mate_speed_component"]+g["score"]["cutoff_quantity_component"])
    board=chess.Board()
    for move in g["opening"]:board.push_uci(move)
    index=0
    for move in g["actions"]:
        if board.turn==ctx["agent_color"]:
            record=g["search_records"][index];index+=1
            check("complete search history "+str(index),record["full_history"]==[m.uci() for m in board.move_stack])
        check("legal replay "+str(len(board.move_stack)),chess.Move.from_uci(move) in board.legal_moves)
        board.push_uci(move)
    check("final fen matches replay",g["final_fen"]==board.fen())
    check("only1024nodes",all(c=="go nodes 1024" for c in engine.commands if c.startswith("go ")))
    check("candidate five leaf probes",len(g["candidate_leaf_probes"])==5)
    check("royal value omitted","k:" not in (base/"legal.ini").read_text())
    check("single thread/hash/NNUE/tablebase fixed",all(c in engine.commands for c in ("setoption name Threads value 1","setoption name Hash value 16","setoption name Use NNUE value false","setoption name SyzygyPath value <empty>")))
    check("readiness fenced search",engine.commands[-1]=="isready")
    events=[json.loads(x) for x in (base/"legal.jsonl").read_text().splitlines()]
    check("journal completed game",events[-1]["kind"]=="game_complete")
    check("all moves journaled",sum(x["kind"]=="move" for x in events)==len(g["actions"]))
    for mode in ("illegal","eof"):
        j=adapter.Journal(base/(mode+".jsonl"));engine=MockEngine(mode)
        raises(mode+" search fails",ValueError if mode=="illegal" else RuntimeError,
               lambda:adapter.play_game(engine,w,ctx,1000,base/(mode+".ini"),j,runner.GAME.opening,runner.GAME.score,lambda:None,clock=lambda:0))
        j.close()
        events=[json.loads(x) for x in (base/(mode+".jsonl")).read_text().splitlines()]
        check(mode+" unfinished board retained",events[-1]["kind"]=="before_move" and not any(x["kind"]=="game_complete" for x in events))
    raises("missing option",RuntimeError,lambda:adapter.configure(MockEngine(missing="VariantPath"),w,base/"missing.ini",1000,lambda:None,lambda:0))
    for mode in ("ignored_variant","ignored_weights"):
        raises("reject "+mode,RuntimeError,lambda:adapter.configure(MockEngine(mode),w,base/(mode+".ini"),1000,lambda:None,lambda:0))
    for wrong in ({**w,"K":1},{**w,"N":0},{**w,"N":True},{**w,"P":209}):
        raises("invalid learned weights",ValueError,lambda:adapter.validate_weights(wrong))
    # Exercise real UCI wait loop with an injected queue; do not invoke Popen.
    u=adapter.UCI.__new__(adapter.UCI)
    u.deadline=100;u.stop=lambda:None;u.response_seconds=10;u.q=queue.Queue()
    clock_values=iter([0,0,0,11]);u.clock=lambda:next(clock_values)
    raises("response deadline",TimeoutError,lambda:u.until(lambda x:x=="uciok"))
    u.clock=lambda:0;u.q.put(None)
    raises("EOF wait",RuntimeError,lambda:u.until(lambda x:x=="uciok"))
    u.q=queue.Queue()
    for i in range(100):u.q.put("info "+str(i))
    u.q.put("uciok")
    lines=u.until(lambda x:x=="uciok")
    check("bounded info retention",len(lines)==64 and lines[-1]=="uciok")
    u.stop=lambda:(_ for _ in ()).throw(adapter.PersistentStop("mock user stop"))
    raises("stop during wait",adapter.PersistentStop,lambda:u.until(lambda x:x=="uciok"))
    # Full four-game pipeline, using actual PythonChess legality/rewards and only lexical mock moves.
    made=[]
    def factory(deadline):
        engine=MockEngine();made.append(engine);return engine
    result=runner.execute(factory,base/"tie",lambda:None,clock=lambda:0,scope="MOCK_UCI_ORCHESTRATION_ONLY")
    check("paired mock pilot no training",result["status"]=="NO_PAIRED_PILOT_SIGNAL" and result["pilot_games_completed"]==4 and result["training_games_completed"]==0)
    check("fresh owned engine each pilot",len(made)==4 and all(e.closed for e in made))
    pilot=json.loads((base/"tie/pilot.json").read_bytes())["rows"]
    check("colors paired",[(r["profile"],r["context"]["agent_color"]) for r in pilot]==[(0,True),(0,False),(1,True),(1,False)])
    check("seed pairs exact",len({(r["context"]["opening_seed"],r["context"]["random_seed"]) for r in pilot})==1)
    raises("no overwrite rerun evidence",FileExistsError,lambda:runner.execute(factory,base/"tie",lambda:None,clock=lambda:0,scope="MOCK"))
    result=runner.execute(lambda d:MockEngine("illegal"),base/"fail",lambda:None,clock=lambda:0,scope="MOCK")
    check("batch partial fail retained",result["status"]=="INTERRUPTED" and result["pilot_games_completed"]==0 and (base/"fail/events.jsonl").is_file())
    # Existing4551 record rejects before production creates any transport.
    raises("blocked runtime rejects",RuntimeError,lambda:adapter.validated_entry(ROOT/".local_agent/material-selfplay/fairy-material.exe",ROOT/"results/dev_aux/task091/qualification.json"))
# Additional finite integration controls isolate transport ownership and stage acceptance.
with tempfile.TemporaryDirectory(dir=ROOT/".local_agent") as temporary:
    base=Path(temporary);timer=[0.0];made=[];original=runner.play_game
    def factory(deadline):
        engine=MockEngine();made.append(engine);return engine
    def synthetic_game(engine,weights,context,deadline,config,journal,opening,score,stop,clock):
        timer[0]+=3
        result=dict(reward=weights["N"]/208,scope="SYNTHETIC_FAULT_TEST")
        journal.record("game_complete",weights=weights,context=context,result=result)
        return result
    runner.play_game=synthetic_game
    try:
        r=runner.execute(factory,base/"cost",lambda:None,clock=lambda:timer[0],scope="MOCK_COST_CONTROL")
        check("expensive pilot rejects training",r["status"]=="PROJECTED_COST_EXCEEDS_FROZEN_BUDGET" and r["training_games_completed"]==0 and r["projected_480_game_seconds"]==1440)
        check("cost includes all four games",r["pilot_seconds"]==12 and len(made)==4 and all(e.closed for e in made))
        timer[0]=0;made.clear()
        def overrun(engine,weights,context,deadline,config,journal,opening,score,stop,clock):
            timer[0]+=.1 if context["phase"]=="pilot" else 901
            result=dict(reward=weights["N"]/208,scope="SYNTHETIC_FAULT_TEST")
            journal.record("game_complete",weights=weights,context=context,result=result)
            return result
        runner.play_game=overrun
        r=runner.execute(factory,base/"fuse",lambda:None,clock=lambda:timer[0],scope="MOCK_FUSE_CONTROL")
        check("late callback not accepted",r["status"]=="INTERRUPTED" and r["training_callbacks_accepted"]==0 and r["training_games_completed"]==1)
        partial=json.loads((base/"fuse/controller_partial.json").read_bytes())
        check("partial controller has unfinished generation",not partial["completed"] and len(partial["runs"])==1 and not partial["runs"][0]["iterations"])
        check("overrun closes only owned transports",len(made)==5 and all(e.closed for e in made))
        timer[0]=0;made.clear();runner.play_game=synthetic_game
        # Zero-duration oracle checks all callback/journal phase connections; not gameplay.
        r=runner.execute(factory,base/"full",lambda:None,clock=lambda:0,scope="SYNTHETIC_FULL_SCHEDULER")
        check("full callback pipeline exact484",r["status"]=="COMPLETE" and len(made)==484 and r["completed_games_by_phase"]=={"pilot":4,"train":432,"heldout":48})
        check("all pipeline transports closed",all(e.closed for e in made))
        controller=json.loads((base/"full/controller.json").read_bytes())
        check("full final file three frozen runs",controller["completed"] and len(controller["runs"])==3 and len(controller["calls"])==480)
        events=[json.loads(line) for line in (base/"full/events.jsonl").read_text().splitlines()]
        check("all synthetic completion records journaled",len(events)==484 and all(e["kind"]=="game_complete" for e in events))
    finally:runner.play_game=original
    # A complete synthetic twenty-probe record tests evidence validation, never execution.
    binary=base/"not-an-executable.dat";binary.write_bytes(b"mock qualification bytes")
    qualification=dict(complete=True,binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),weights=[{k.lower():v for k,v in w.items() if k!="K"} for w in runner.PROFILES],rows=[])
    for profile,weights in enumerate(runner.PROFILES):
        for kind in "pnbrq":
            for side in ("w","b"):
                fen="7k/8/8/3"+kind.upper()+"4/8/8/8/K7 "+side+" - - 0 1"
                board=chess.Board(fen)
                qualification["rows"].append(dict(variant=profile,type=kind,side=side,fen=fen,bestmove=sorted(board.legal_moves,key=lambda m:m.uci())[0].uci(),final_eval_pawns=weights[kind.upper()]/208))
    qfile=base/"synthetic-qualification.json";adapter.atomic_json(qfile,qualification)
    check("twenty probe evidence format",adapter.validated_entry(binary,qfile)[1]==qualification["binary_sha256"])
    for name,modify in (("missing probe",lambda q:q["rows"].pop()),("wrong side",lambda q:q["rows"][0].update(side="b")),("wrong leaf",lambda q:q["rows"][0].update(final_eval_pawns=99)),("nonfinite leaf",lambda q:q["rows"][0].update(final_eval_pawns=float("nan")))):
        import copy
        q=copy.deepcopy(qualification);modify(q)
        # Deliberately malformed input may contain NaN; output writer never emits it.
        qfile.write_text(json.dumps(q))
        raises("reject "+name,ValueError,lambda:adapter.validated_entry(binary,qfile))
    adapter.atomic_json(qfile,qualification);binary.write_bytes(b"replaced mock bytes")
    raises("reject binary replacement",RuntimeError,lambda:adapter.validated_entry(binary,qfile))
    # Same full-history replay includes a repeated initial board; board FEN alone loses it.
    board=chess.Board()
    for move in ("g1f3","g8f6","f3g1","f6g8")*2:board.push_uci(move)
    engine=MockEngine();_,record=adapter.search(engine,board,1000,lambda:None,lambda:0)
    check("repetition prefix preserved",len(record["full_history"])==8 and engine.board.can_claim_threefold_repetition())
    check("reported nodes separate from limit",record["reported_nodes"]==1024 and record["nodes_limit"]==1024)
    u=adapter.UCI.__new__(adapter.UCI);u.deadline=100;u.stop=lambda:None;u.response_seconds=10;u.clock=lambda:0;u.q=queue.Queue()
    for i in range(100):u.q.put("option name option"+str(i)+" type string")
    u.q.put("uciok")
    check("large handshake retains earlier options",len(u.until(lambda x:x=="uciok",max_lines=512))==101)

output=dict(complete=True,checks=checks,check_count=len(checks),scope="MOCK_UCI_ORCHESTRATION_ONLY",mature_games_executed=0)
Path(__file__).with_name("test_result.json").write_bytes((json.dumps(output,indent=2)+"\n").encode())
print(json.dumps(output))
