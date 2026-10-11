"""Qualification-gated short mature pilot; never retries a rejected executable."""
import hashlib,json,sys,time
from pathlib import Path
import chess, queue, subprocess, threading
from contextlib import contextmanager
from short_game import opening,play
ROOT=Path.cwd(); OUT=Path(__file__).resolve().parent

def stop_check():
    roots=(ROOT/".local_agent",Path(r"C:\Users\wdai\Documents\ChatGPT\GenericChess 2\.local_agent"))
    for root in roots:
        for name in ("rollout.json","advisor.json","slack.json"):
            d=json.loads((root/name).read_bytes())
            if d.get("user_paused") or d.get("stopped"):
                raise RuntimeError("persistent stop")

class UCI:
    def __init__(self,binary):
        self.p=subprocess.Popen([str(binary)],cwd=binary.parent,stdin=subprocess.PIPE,stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT,text=True,encoding="utf-8",errors="replace",
                                creationflags=subprocess.CREATE_NO_WINDOW)
        self.q=queue.Queue()
        def read():
            for line in self.p.stdout:self.q.put(line.rstrip())
            self.q.put(None)
        self.reader=threading.Thread(target=read,daemon=True);self.reader.start()
        try:
            self.send("uci");self.handshake=self.until(lambda x:x=="uciok")
        except BaseException:
            self.close();raise
    def send(self,line):
        self.p.stdin.write(line+"\n");self.p.stdin.flush()
    def until(self,predicate):
        deadline=time.monotonic()+10;lines=[]
        while True:
            left=deadline-time.monotonic()
            if left<=0:raise TimeoutError("bounded UCI response timeout")
            line=self.q.get(timeout=left)
            if line is None:raise RuntimeError("engine exited")
            lines.append(line)
            if predicate(line):return lines
    def ready(self):
        self.send("isready");self.until(lambda x:x=="readyok")
    def close(self):
        if self.p.poll() is None:
            try:self.send("quit");self.p.wait(timeout=2)
            except (OSError,subprocess.TimeoutExpired):self.p.kill();self.p.wait(timeout=2)
        self.reader.join(timeout=1)
        self.p.stdin.close();self.p.stdout.close()

@contextmanager
def engine_context(binary):
    engine=UCI(binary)
    try:yield engine
    finally:engine.close()

def main():
    stop_check()
    q=json.loads((ROOT/"results/dev_aux/task091/qualification.json").read_bytes())
    binary=ROOT/".local_agent/material-selfplay/fairy-material.exe"
    digest=hashlib.sha256(binary.read_bytes()).hexdigest()
    if not q.get("complete") or q.get("binary_sha256") != digest:
        result=dict(status="BLOCKED_BEFORE_LAUNCH",mature_games_executed=0,
                    cause=q.get("error","qualification missing/hash mismatch"),binary_sha256=digest,
                    learning_failure=False,scope="No retry, security change or project Native substitute.")
        (OUT/"pilot.json").write_bytes((json.dumps(result,indent=2)+"\n").encode())
        print(json.dumps(result));return 3
    # Two deliberately contrasting profiles qualify short signal/cost only, not training.
    weights=({"p":208,"n":73,"b":901,"r":149,"q":397},
             {"p":208,"n":701,"b":89,"r":997,"q":131})
    rows=[];started=time.perf_counter()
    for profile,w in enumerate(weights):
        cfg=ROOT/".local_agent/material-selfplay/short-pilot.ini"
        line=" ".join(f"{k}:{v}" for k,v in w.items())
        cfg.write_bytes((f"[aux_short:chess]\npieceValueMg = {line}\npieceValueEg = {line}\n").encode())
        for color in (chess.WHITE,chess.BLACK):
            stop_check()
            with engine_context(binary) as engine:
                names={x.split("option name ",1)[1].split(" type ",1)[0] for x in engine.handshake if x.startswith("option name ")}
                for name,value in (("Threads",1),("Hash",16),("Use NNUE","false"),("SyzygyPath","<empty>"),("VariantPath",str(cfg)),("UCI_Variant","aux_short")):
                    if name not in names:raise RuntimeError("missing required mature option:"+name)
                    engine.send(f"setoption name {name} value {value}")
                    engine.ready()
                engine.send("ucinewgame");engine.ready()
                def search(board):
                    if board.root().fen() != chess.Board().fen():raise ValueError("pilot requires initial-board full history")
                    engine.send("position startpos moves "+" ".join(m.uci() for m in board.move_stack))
                    engine.send("go nodes 1024")
                    lines=engine.until(lambda x:x.startswith("bestmove "))
                    return chess.Move.from_uci(lines[-1].split()[1]),{"uci_info":lines[:-1]}
                game=play(search,color,opening(41001),42001,check_stop=stop_check)
                game["profile"]=profile;game["weights"]=w;rows.append(game)
    result=dict(status="PILOT_COMPLETE",rows=rows,binary_sha256=digest,wall_seconds=time.perf_counter()-started,
                scope="Four mature short games for cost/signal; no trained vector or human-value recovery claim.")
    (OUT/"pilot.json").write_bytes((json.dumps(result,indent=2)+"\n").encode())
    print(json.dumps({k:v for k,v in result.items() if k!="rows"}));return 0
if __name__=="__main__":sys.exit(main())
