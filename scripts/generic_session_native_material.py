"""Scoped mature-material callback for actual public KRN sessions.

Modified Fairy/Stockfish-derived binary; not unmodified Stockfish or NNUE.
Only the declared closed K/R/N board fragment is admitted. Core/Session owns
all actual history and results; engine repetition and n-move rules are disabled
and its rollout is an approximation. Full root FEN + public action history is
sent nevertheless. Prices affect leaf/native/capture tables jointly.
One owned cold engine, one thread, explicit profile ACK and actual go receipts.
"""
from pathlib import Path
import hashlib,importlib.util,json,os,time
from scripts.generic_royal_actor import RoyalActor
from scripts.generic_proof_rnb_bridge import actor_state,uci
from scripts.generic_win_proof import _same_state,_Interrupted
from generic_chess.session.session import GameSession


def _load_transport():
    path=Path('results/dev_aux/task109/adapter.py')
    spec=importlib.util.spec_from_file_location('DEV_AUX_TRANSPORT109',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


class SessionKRNMaterialProvider:
    def __init__(self,plan,out,*,stop):
        self.plan=plan;self.out=Path(out);self.out.mkdir(exist_ok=False)
        self.transport=_load_transport();self.stop=stop;self.actor=RoyalActor(4)
        self.deadline=time.monotonic()+plan['seconds_cap'];self.e=None;self.current=None
        self.queries=0;self.reported_nodes=0
        self.journal=(self.out/'transport.jsonl').open('x',encoding='utf-8')
        for file,digest in plan['files'].items():
            if hashlib.sha256(Path(file).read_bytes()).hexdigest()!=digest:raise ValueError('source/binary hash mismatch')
    def log(self,event,**kw):
        self.journal.write(json.dumps(dict(event=event,**kw))+'\n');self.journal.flush()
    def guard(self):
        self.transport.guard(self.deadline,self.stop)
        if self.queries>=self.plan['max_go']:raise RuntimeError('go cap')
    def start(self):
        self.guard();key='GENERICCHESS_ALIGN_SEARCH_PRICES';old=os.environ.get(key);os.environ[key]='3'
        try:self.e=self.transport.UCI(Path(self.plan['binary']).resolve(),Path.cwd(),self.deadline,self.stop)
        finally:
            if old is None:os.environ.pop(key,None)
            else:os.environ[key]=old
        self.log('HANDSHAKE',raw=self.e.handshake)
        for name,value in [('Threads',1),('Hash',16),('Use NNUE','false'),('SyzygyPath','<empty>'),('VariantPath',str(Path(self.plan['variant_ini']).resolve()))]:
            self.e.send(f'setoption name {name} value {value}');self.log('OPTION',name=name,value=value if name!='VariantPath' else self.plan['variant_ini'],raw=self.e.ready())
    def profile(self,r):
        values=(r,720,720,720)
        if self.current!=values:
            name=self.plan['variant_names'][str(values)]
            self.e.send('setoption name UCI_Variant value '+name);raw=self.e.ready()
            assert any(x.startswith(f'info string variant {name} files 4 ranks 4 ') for x in raw)
            self.e.send('devauxleafrnbp '+' '.join(map(str,values)));ack=self.e.ready()
            expected=f'info string DEV_AUX leafRNBP {r} 720 720 720 nativeP 720 nativeR {r} nativeN 720 nativeB 720 captureP 720 captureR {r} captureN 720 captureB 720'
            assert expected in ack;self.log('PROFILE',R=r,raw=raw,ack=ack);self.current=values
        else:self.e.send('ucinewgame');self.log('CLEAR',R=r,raw=self.e.ready())
    def position_command(self,session,state):
        if not _same_state(session.state,state):raise ValueError('callback/session full state mismatch')
        c=session.compiled
        if (c.ruleset_fingerprint!=self.plan['fingerprint'] or c.board_size!=4 or c.declarations or c.no_progress_draw is not None
            or c.capture_disposition!='remove_from_game' or {p.type_id for p in c.piece_types}!={'K','R','N'}):
            raise ValueError('outside explicit KRN provider scope')
        raw=actor_state(state);actual={uci(a):a for a in session.legal_actions()}
        if set(actual)!=set(dict(self.actor.moves(raw))):raise ValueError('Core/actor legal frontier mismatch')
        record=session.to_record();root=GameSession(c,record.initial_setup_key)
        path=[uci(a) for a in record.actions]
        return 'position fen '+self.actor.fen(actor_state(root.state))+(' moves '+' '.join(path) if path else ''),actual
    def choose(self,session,state,r,nodes,seconds,cancel):
        self.guard()
        if cancel is not None and cancel():raise _Interrupted('cancelled')
        started=time.perf_counter();record=session.to_record();self.profile(r)
        command,actual=self.position_command(session,state)
        self.e.send(command);go=f'go nodes {nodes} movetime {max(1,int(max(0.,seconds-(time.perf_counter()-started))*1000))}'
        self.log('INTENT',query=self.queries,position=command,command=go,R=r,root_record=repr(record))
        self.e.send(go);self.log('SENT',query=self.queries);self.queries+=1
        raw=self.e.until(lambda line:line.startswith('bestmove '));self.e.ready();move=raw[-1].split()[1]
        if move not in actual:raise ValueError('illegal mature action')
        used=0
        for line in raw:
            fields=line.split()
            if 'nodes' in fields:used=max(used,int(fields[fields.index('nodes')+1]))
        self.reported_nodes+=used
        self.log('CHOICE',query=self.queries-1,move=move,R=r,requested_nodes=nodes,reported_nodes=used,raw=raw,seconds=time.perf_counter()-started)
        assert _same_state(session.state,state) and _same_state(session.to_record(),record)
        return actual[move],used
    def perft_one(self,session,r=720):
        self.guard();self.profile(r);command,actual=self.position_command(session,session.state)
        self.e.send(command);self.e.send('go perft 1')
        raw=self.e.until(lambda line:line.startswith('Nodes searched:'),max_lines=1024);self.e.ready()
        parsed={line.split(':')[0].strip():int(line.split(':')[1]) for line in raw if ':' in line and line.split(':')[0].strip() in actual}
        assert set(parsed)==set(actual) and all(n==1 for n in parsed.values())
        self.log('PERFT',position=command,moves=len(parsed),raw=raw)
        return len(parsed)
    def close(self):
        if self.e:self.e.close()
        self.journal.close()
