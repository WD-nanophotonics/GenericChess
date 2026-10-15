"""Bounded cold mature-material consumer for sized royal actor controls.

No unused tablebase/stock-draw dependency. Actual Core rules own every outcome.
No cache, worker or background process; one thread and explicit cold profile ACK.
"""
import datetime,json,time
from pathlib import Path
from scripts.generic_proof_native_study import mod,sha
from scripts.generic_royal_actor import RoyalActor


class SizedNativeDriver:
    def __init__(self,plan,out):
        self.plan=plan;self.O=Path(out);self.O.mkdir(exist_ok=False)
        self.T=RoyalActor(plan['width']);self.P=mod('SIZED_STOP55','results/dev_aux/task166/run.py')
        self.start=time.perf_counter();self.deadline=time.monotonic()+plan['seconds_cap']
        self.queries=0;self.newnodes=0;self.current=None;self.e=None
        for a,b in [('binary','binary_sha256'),('variant_ini','variant_sha256'),('actor_source','actor_sha256')]:assert sha(plan[a])==plan[b],a
        self.files={name:(self.O/f'{name}.jsonl').open('x',encoding='utf-8') for name in ('choices','games','acks','go_journal')}
        (self.O/'start.json').write_text(json.dumps(dict(at=datetime.datetime.now(datetime.timezone.utc).isoformat(),session_id=json.loads(Path('.local_agent/session.json').read_bytes())['id'],driver_sha256=sha(__file__),plan=plan),indent=2),encoding='utf-8')

    def log(self,name,value):
        self.files[name].write(json.dumps(value)+'\n');self.files[name].flush()

    def guard(self):
        self.P.stop()
        if time.monotonic()>=self.deadline:raise RuntimeError('wallcap')
        if self.queries>=self.plan['max_go']:raise RuntimeError('gocap')

    def start_engine(self):
        self.guard();self.e=self.P.M.start(Path(self.plan['binary']).resolve(),3,self.deadline,self.P.stop)
        for name,value in [('Threads',1),('Hash',16),('Use NNUE','false'),('SyzygyPath','<empty>'),('VariantPath',str(Path(self.plan['variant_ini']).resolve()))]:
            self.e.send(f'setoption name {name} value {value}');self.e.ready()

    def choose_timed(self,state,price,nodes,seconds):
        self.guard();e=self.e;price=tuple(price);beg=time.perf_counter();va=[]
        if self.current!=price:
            vn=self.plan['variant_names'][str(price)];e.send('setoption name UCI_Variant value '+vn);va=e.ready()
            assert any(z.startswith(f'info string variant {vn} files {self.T.width} ranks {self.T.width} ') for z in va)
            e.send('devauxleafrnbp '+' '.join(map(str,price)));ack=e.ready();self.current=price
            expected='info string DEV_AUX leafRNBP '+' '.join(map(str,price))+f' nativeP {price[3]} nativeR {price[0]} nativeN {price[1]} nativeB {price[2]} captureP {price[3]} captureR {price[0]} captureN {price[1]} captureB {price[2]}'
            assert expected in ack
        else:e.send('ucinewgame');ack=e.ready()
        self.log('acks',dict(state=state,price=price,ack=ack,variant_ack=va,explicit_clear_commands=1))
        milliseconds=max(1,int((seconds-(time.perf_counter()-beg))*1000));command=f'go nodes {nodes} movetime {milliseconds}'
        e.send('position fen '+self.T.fen(state));self.log('go_journal',dict(event='INTENT',state=state,price=price,command=command))
        e.send(command);self.queries+=1;self.log('go_journal',dict(event='SENT',state=state,price=price,command=command))
        raw=e.until(lambda z:z.startswith('bestmove '));e.ready();move=raw[-1].split()[1]
        assert move in dict(self.T.moves(state));used=0
        for line in raw:
            tokens=line.split()
            if 'nodes' in tokens:used=max(used,int(tokens[tokens.index('nodes')+1]))
        self.newnodes+=used
        self.log('choices',dict(state=state,price=price,requested_nodes=nodes,reported_nodes=used,command=command,raw=raw,seconds=time.perf_counter()-beg))
        return move,used

    def close(self):
        for file in self.files.values():file.close()
        if self.e:self.e.close()
