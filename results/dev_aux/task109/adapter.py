"""Bounded Fairy UCI integration. This adapter does not establish engine qualification."""
import hashlib, json, math, queue, subprocess, threading, time
from pathlib import Path
import chess

class PersistentStop(RuntimeError):
    pass

def stop_check(root):
    for state in (Path(root)/".local_agent", Path(root).resolve().parent/"GenericChess 2"/".local_agent"):
        for name in ("rollout.json", "advisor.json", "slack.json"):
            value=json.loads((state/name).read_bytes())
            if value.get("user_paused") or value.get("stopped"):
                raise PersistentStop("persistent user stop")

def guard(deadline, stop, clock=time.monotonic):
    stop()
    if clock() >= deadline:
        raise TimeoutError("experiment wall fuse")

def atomic_json(path, value):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_suffix(path.suffix+".tmp")
    temporary.write_bytes((json.dumps(value,indent=2,allow_nan=False)+"\n").encode())
    temporary.replace(path)

class Journal:
    """One owned append-only event file; flush each event, no power-loss durability claim."""
    def __init__(self,path):
        self.path=Path(path);self.path.parent.mkdir(parents=True,exist_ok=True)
        self.file=self.path.open("x",encoding="utf-8",newline="\n")
    def record(self,kind,**value):
        self.file.write(json.dumps(dict(kind=kind,**value),allow_nan=False)+"\n")
        self.file.flush()
    def close(self):
        self.file.close()

class UCI:
    def __init__(self,binary,cwd,deadline,stop,clock=time.monotonic,response_seconds=10):
        self.backend="FAIRY_UCI_TRANSPORT_NOT_QUALIFICATION"
        self.deadline=deadline;self.stop=stop;self.clock=clock;self.response_seconds=response_seconds
        self.p=None;self.reader=None;self.closed=False;self.halt=threading.Event()
        guard(deadline,stop,clock)
        self.p=subprocess.Popen([str(binary)],cwd=str(cwd),stdin=subprocess.PIPE,stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,text=True,encoding="utf-8",errors="replace",
            creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
        self.q=queue.Queue(maxsize=256)
        def emit(item):
            while not self.halt.is_set():
                try:self.q.put(item,timeout=.1);return
                except queue.Full:pass
        def read():
            try:
                for line in self.p.stdout:
                    if self.halt.is_set():break
                    emit(line.rstrip())
            finally:emit(None)
        self.reader=threading.Thread(target=read,daemon=True);self.reader.start()
        try:
            self.send("uci");self.handshake=self.until(lambda x:x=="uciok",max_lines=512)
        except BaseException:
            self.close();raise
    def send(self,line):
        guard(self.deadline,self.stop,self.clock)
        self.p.stdin.write(line+"\n");self.p.stdin.flush()
    def until(self,predicate,max_lines=64):
        response_deadline=min(self.deadline,self.clock()+self.response_seconds);lines=[]
        while True:
            guard(response_deadline,self.stop,self.clock)
            try:line=self.q.get(timeout=min(.1,max(0,response_deadline-self.clock())))
            except queue.Empty:continue
            if line is None:raise RuntimeError("engine exited before required reply")
            lines.append(line)
            # Retain bounded recent information even when an engine is chatty.
            if len(lines)>max_lines:del lines[0]
            if predicate(line):return lines
    def ready(self):
        self.send("isready");return self.until(lambda x:x=="readyok")
    def close(self):
        if self.closed:return
        self.closed=True;self.halt.set()
        if self.p is None:return
        if self.p.poll() is None:
            try:
                # Cleanup must remain available after the search deadline/stop.
                self.p.stdin.write("stop\nquit\n");self.p.stdin.flush()
                self.p.wait(timeout=2)
            except (OSError,subprocess.TimeoutExpired):
                self.p.kill();self.p.wait(timeout=2)
        if self.reader:self.reader.join(timeout=1)
        self.p.stdin.close();self.p.stdout.close()

def validate_weights(weights):
    if set(weights)!={"P","N","B","R","Q","K"} or weights["P"]!=208 or weights["K"]!=0:
        raise ValueError("frozen weight identity/scale")
    if any(isinstance(weights[k],bool) or not isinstance(weights[k],int) or not 52<=weights[k]<=3328 for k in "NBRQ"):
        raise ValueError("frozen positive weight bounds")
    return dict(weights)

def configure(engine,weights,config,deadline,stop,clock=time.monotonic):
    guard(deadline,stop,clock);weights=validate_weights(weights)
    # Royal K is excluded rather than relying on zero-value override parsing.
    line=" ".join(k.lower()+":"+str(weights[k]) for k in "PNBRQ")
    Path(config).write_bytes(("[aux_short:chess]\npieceValueMg = "+line+"\npieceValueEg = "+line+"\n").encode())
    names={x.split("option name ",1)[1].split(" type ",1)[0] for x in engine.handshake if x.startswith("option name ")}
    for name,value in (("Threads",1),("Hash",16),("Use NNUE","false"),("SyzygyPath","<empty>"),
                       ("VariantPath",str(config)),("UCI_Variant","aux_short")):
        if name not in names:raise RuntimeError("missing required option: "+name)
        guard(deadline,stop,clock)
        engine.send("setoption name "+name+" value "+str(value));reply=engine.ready()
        if name=="UCI_Variant" and not any(x.startswith("info string variant aux_short files 8 ranks 8 ") for x in reply):
            raise RuntimeError("custom variant not acknowledged; readyok alone is insufficient")
    probes=[]
    for kind in "PNBRQ":
        guard(deadline,stop,clock)
        fen="7k/8/8/3"+kind+"4/8/8/8/K7 w - - 0 1"
        engine.send("position fen "+fen);engine.send("eval")
        reply=engine.ready()
        final=[x for x in reply if x.startswith("Final evaluation")]
        if len(final)!=1:raise RuntimeError("candidate leaf probe missing or ambiguous")
        value=float(final[0].split()[2]);expected=weights[kind]/208
        if not math.isfinite(value) or abs(value-expected)>.011:
            raise RuntimeError("candidate leaf value not applied: "+kind)
        probes.append(dict(type=kind,fen=fen,measured_white_pawns=value,expected_white_pawns=expected))
    engine.send("ucinewgame");engine.ready()
    return probes

def search(engine,board,deadline,stop,clock=time.monotonic):
    guard(deadline,stop,clock)
    if board.root().fen()!=chess.Board().fen():
        raise ValueError("initial-board complete history required")
    history=[m.uci() for m in board.move_stack]
    engine.send("position startpos"+(" moves "+" ".join(history) if history else ""))
    engine.send("go nodes 1024")
    lines=engine.until(lambda x:x.startswith("bestmove "))
    fields=lines[-1].split()
    if len(fields)<2:raise ValueError("malformed bestmove")
    move=chess.Move.from_uci(fields[1])
    if move not in board.legal_moves:raise ValueError("illegal mature bestmove")
    # Readiness fence prevents one move's late output from contaminating the next.
    engine.ready()
    guard(deadline,stop,clock)
    reported_nodes=None
    for text in lines[:-1]:
        fields=text.split()
        if fields and fields[0]=="info" and "nodes" in fields:
            try:
                value=int(fields[fields.index("nodes")+1])
                if value>=0:reported_nodes=value
            except (ValueError,IndexError):pass
    return move,dict(reported_nodes=reported_nodes,backend=engine.backend,nodes_limit=1024,
                     full_history=history,uci_info=lines[:-1])

def play_game(engine,weights,context,deadline,config,journal,opening,score,stop,clock=time.monotonic,cap=64):
    guard(deadline,stop,clock);weights=validate_weights(weights)
    probes=configure(engine,weights,config,deadline,stop,clock)
    import random
    initial=opening(context["opening_seed"]);board=chess.Board()
    for text in initial:
        move=chess.Move.from_uci(text)
        if move not in board.legal_moves:raise ValueError("illegal declared opening")
        board.push(move)
    rng=random.Random(context["random_seed"]);actions=[];records=[];started=clock()
    journal.record("game_start",weights=weights,context=context,opening=initial,candidate_leaf_probes=probes)
    for ply in range(cap):
        guard(deadline,stop,clock)
        if board.is_game_over(claim_draw=False):break
        journal.record("before_move",name=context["name"],ply=ply,fen=board.fen(),agent_turn=board.turn==context["agent_color"])
        if board.turn==context["agent_color"]:
            move,metadata=search(engine,board.copy(stack=True),deadline,stop,clock);records.append(metadata)
        else:
            move=rng.choice(sorted(board.legal_moves,key=lambda m:m.uci()))
        if move not in board.legal_moves:raise ValueError("illegal player move")
        board.push(move);actions.append(move.uci())
        journal.record("move",name=context["name"],ply=ply,action=move.uci())
    result=dict(reward=score(board,context["agent_color"],len(actions),cap)["reward"],
                score=score(board,context["agent_color"],len(actions),cap),candidate_leaf_probes=probes,opening=initial,actions=actions,
                search_records=records,final_fen=board.fen(),wall_seconds=clock()-started)
    journal.record("game_complete",weights=weights,context=context,result=result)
    return result

def validated_entry(binary,qualification):
    """Read complete actual probe evidence before launching; booleans alone are insufficient."""
    binary=Path(binary);q=json.loads(Path(qualification).read_bytes())
    digest=hashlib.sha256(binary.read_bytes()).hexdigest()
    if not q.get("complete"):
        raise RuntimeError("qualification failed: "+q.get("error","no actual completed probes"))
    if digest!=q.get("binary_sha256"):
        raise RuntimeError("qualification binary hash mismatch")
    expected={(profile,kind,side) for profile in range(2) for kind in "pnbrq" for side in ("w","b")}
    seen=set()
    for row in q.get("rows",[]):
        key=(row["variant"],row["type"],row["side"])
        if key not in expected or key in seen:raise ValueError("qualification probe coverage")
        seen.add(key)
        board=chess.Board(row["fen"])
        if not board.is_valid() or chess.Move.from_uci(row["bestmove"]) not in board.legal_moves:
            raise ValueError("qualification legality")
        expected_fen="7k/8/8/3"+key[1].upper()+"4/8/8/8/K7 "+key[2]+" - - 0 1"
        if board.fen()!=chess.Board(expected_fen).fen():
            raise ValueError("qualification probe position/type/side mismatch")
        expected_value=q["weights"][key[0]][key[1]]/208
        measured=row["final_eval_pawns"]
        if not isinstance(measured,(int,float)) or not math.isfinite(measured) or abs(measured-expected_value)>.011:
            raise ValueError("qualification material leaf effect")
    if seen!=expected:raise ValueError("qualification requires twenty actual probes")
    return binary,digest,q
