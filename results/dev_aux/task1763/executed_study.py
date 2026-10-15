"""Frozen small mature-material/Generic-proof four-cell study. No WDL surrogate."""
import argparse,collections,hashlib,importlib.util,json,random,time
from dataclasses import asdict,replace
from pathlib import Path
from generic_chess.core.movegen import legal_actions
from generic_chess.core.transition import apply_action
from scripts.generic_proof_rnb_bridge import compile_rnb,from_actor,actor_state,uci,orbit
from scripts.generic_proof_player import ProofMaterialPlayer


def mod(name,path):
    sp=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);return m


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def freeze(folder):
    out=Path(folder);out.mkdir(exist_ok=False)
    T=mod('RNB54','results/dev_aux/task1675/rules.py');rng=random.Random(20261015541)
    excluded=set();sources=[]
    for path in sorted(Path('results/dev_aux').glob('task*/plan.json')):
        if path.stat().st_size>5_000_000:continue
        p=json.loads(path.read_text(encoding='utf-8-sig'))
        rows=p.get('families',[]) if isinstance(p,dict) else []
        if not isinstance(rows,list):continue
        matched=0
        for f in rows:
            if not isinstance(f,dict):continue
            for raw in f.get('roots',[]):
                if isinstance(raw,list) and len(raw)==17 and set(raw[:-1])<=set('.KRNBkrnb'):
                    excluded.update(orbit(tuple(raw)));matched+=1
        if matched:sources.append(dict(path=str(path),sha256=sha(path),roots=matched))
    fs=[];attempts=0
    while len(fs)<16 and attempts<100000:
        attempts+=1;places=rng.sample(range(16),8);board=['.']*16
        for sq,piece in zip(places,'KkRNBrnb'):board[sq]=piece
        s=tuple(board)+(0,)
        if not T.valid(s) or T.attacked(s,T.king(s,0),1):continue
        ll=T.moves(s)
        if len(ll)<4:continue
        capture=any(s[ord(u[2])-97+4*(int(u[3])-1)]!='.' for u,_ in ll)
        quiet=any(s[ord(u[2])-97+4*(int(u[3])-1)]=='.' for u,_ in ll)
        if not(capture and quiet) or orbit(s)&excluded:continue
        if any(not T.moves(t) for _,t in ll):continue
        flipped=tuple(x.swapcase() for x in s[:-1])+(1,)
        fs.append(dict(family=len(fs),phase='DEV',roots=[s,flipped]));excluded.update(orbit(s))
    assert len(fs)==16
    prices=[[720,720,720,720],[720,720,360,720]]
    names={str(tuple(p)):'aux54_'+ '_'.join(map(str,p)) for p in prices}
    ini='[aux54base:chess]\nmaxFile = 4\nmaxRank = 4\ncastling = false\ndoubleStep = false\npromotionRank = 4\npromotionPieceTypes = rnb\nnMoveRule = 0\nnFoldRule = 0\nstartFen = k3/4/4/3K w - - 0 1\n'
    for p in prices:
        ini+='\n['+names[str(tuple(p))]+':aux54base]\n'+''.join(f'pieceValue{x} = p:{p[3]} n:{p[1]} b:{p[2]} r:{p[0]} q:1664\n' for x in ['Mg','Eg'])
    (out/'variant.ini').write_text(ini)
    plan=dict(families=fs,seed=20261015541,attempts=attempts,prices=prices,variant_names=names,
              model='results/dev_aux/task1675/rules.py',model_sha256=sha('results/dev_aux/task1675/rules.py'),
              binary='.local_agent/leaf-rnbp-46/fairy-leaf-rnb.exe',binary_sha256=sha('.local_agent/leaf-rnbp-46/fairy-leaf-rnb.exe'),
              variant_ini=str(out/'variant.ini'),variant_sha256=sha(out/'variant.ini'),
              stockproof='results/dev_aux/task1706/proof4.json',stockproof_sha256=sha('results/dev_aux/task1706/proof4.json'),
              candidate_nodes=256,opponents=[dict(id='UNIT64',nodes=64),dict(id='UNIT256',nodes=256)],
              H=16,seconds_cap=600,max_go=10000,step_seconds=.25,
              allocation='Proof at most1/4 visits and time; validation at most1/4; actual Native receives remainder. Actual reported node overrun retained. Visits across engines are not equal primitive cost.',
              trigger='Every ongoing state for both colors, fixed depth64; continue verified original tree after BOTH moves.',
              outcome='Actual Core checkmate/stalemate/repetition/maxply only. H16 unresolved retained with[-1,+1], no quantity reward or policy-cycle shortcut.',
              rootlaw='Fresh4x4 closed8actor KkRNBrnb, uncheck,>=4choices,capture+quiet,no immediate terminal; fullD4/color exclusion. No price/WDL filter.',
              exclusion_sources=sources,
              solver_sha256=sha('scripts/generic_win_proof.py'),player_sha256=sha('scripts/generic_proof_player.py'))
    (out/'plan.json').write_text(json.dumps(plan,indent=2));print('FROZEN',len(fs),'families',len(sources),'oldcohorts')


def run(folder):
    folder=Path(folder);p=json.loads((folder/'plan.json').read_text())
    assert sha('scripts/generic_win_proof.py')==p['solver_sha256'] and sha('scripts/generic_proof_player.py')==p['player_sha256']
    D=mod('DRIVER54','results/dev_aux/task1720/driver.py')
    class TimedDriver(D.Driver):
        def choose_timed(self,s,price,nodes,seconds):
            self.guard();e=self.e;price=tuple(price);beg=time.perf_counter();va=[]
            if self.current!=price:
                vn=self.plan['variant_names'][str(price)];e.send('setoption name UCI_Variant value '+vn);va=e.ready()
                assert any(z.startswith(f'info string variant {vn} files 4 ranks 4 ') for z in va)
                e.send('devauxleafrnbp '+' '.join(map(str,price)));ack=e.ready();self.current=price
                expected='info string DEV_AUX leafRNBP '+' '.join(map(str,price))+f' nativeP {price[3]} nativeR {price[0]} nativeN {price[1]} nativeB {price[2]} captureP {price[3]} captureR {price[0]} captureN {price[1]} captureB {price[2]}'
                assert expected in ack
            else:e.send('ucinewgame');ack=e.ready()
            self.log('acks',dict(state=s,price=price,ack=ack,variant_ack=va,explicit_clear_commands=1))
            milliseconds=max(1,int((seconds-(time.perf_counter()-beg))*1000))
            cmd=f'go nodes {nodes} movetime {milliseconds}'
            e.send('position fen '+self.T.fen(s));self.log('go_journal',dict(event='INTENT',state=s,price=price,command=cmd))
            e.send(cmd);self.queries+=1;self.log('go_journal',dict(event='SENT',state=s,price=price,command=cmd))
            raw=e.until(lambda z:z.startswith('bestmove '));e.ready();move=raw[-1].split()[1]
            assert move in dict(self.T.moves(s));used=0
            for line in raw:
                a=line.split()
                if 'nodes' in a:used=max(used,int(a[a.index('nodes')+1]))
            self.newnodes+=used
            self.log('choices',dict(state=s,price=price,requested_nodes=nodes,reported_nodes=used,command=cmd,raw=raw,seconds=time.perf_counter()-beg))
            return move,used
    d=TimedDriver(p,folder/'run');c=compile_rnb();rows=[];error=None;start=time.perf_counter()
    def check_frontier(s):
        raw=actor_state(s);expected=dict(d.T.moves(raw));actual={uci(a):a for a in legal_actions(s,c)}
        assert set(actual)==set(expected)
        for u,a in actual.items():assert actor_state(apply_action(s,a,c))==expected[u]
        return actual
    try:
        # All roots and all one-ply public frontiers before any WDL measurement.
        for f in p['families']:
            for raw in f['roots']:
                s=from_actor(c,raw);ll=check_frontier(s)
                for a in ll.values():check_frontier(apply_action(s,a,c))
        (folder/'qualification.json').write_text(json.dumps(dict(status='PASS_ALL_ROOTS_AND_CHILDREN_CORE_ACTOR_EQUIVALENCE',roots=32)))
        d.start_engine()
        for f in p['families']:
            # Paired and counterbalanced arm order, frozen family parity.
            cells=[(False,0),(True,0),(False,1),(True,1)]
            if f['family']%2:cells.reverse()
            for enabled,price_index in cells:
                price=p['prices'][price_index]
                for color in (0,1):
                    for opponent in p['opponents']:
                        d.guard();s=from_actor(c,f['roots'][color]);target=s.position.side_to_move
                        path=[];players={};pay=None
                        for side in (0,1):
                            pp=price if side==target else p['prices'][0]
                            def external(state,nodes,seconds,cancel,pp=pp):
                                raw=actor_state(state);move,used=d.choose_timed(raw,pp,nodes,seconds)
                                return check_frontier(state)[move],used
                            players[side]=ProofMaterialPlayer(c,None,proof_enabled=enabled,normal_search=external)
                        for ply in range(p['H']+1):
                            d.guard()
                            if s.terminal_status.is_terminal:
                                pay=0 if s.terminal_status.winner is None else (1 if s.terminal_status.winner==target else -1);break
                            if ply==p['H']:break
                            cap=p['candidate_nodes'] if s.position.side_to_move==target else opponent['nodes']
                            z=players[s.position.side_to_move].choose(s,max_nodes=cap,seconds=p['step_seconds'],cancel=lambda:time.monotonic()>=d.deadline)
                            if z.action is None:break
                            a=z.action;path.append(dict(actor=actor_state(s),decision={**asdict(z),'action':uci(a)}))
                            for player in players.values():player.observe(s,a)
                            s=apply_action(s,a,c)
                        row=dict(family=f['family'],color=color,opponent=opponent['id'],proof=enabled,price_index=price_index,price=price,
                                 payoff=pay,lower=-1 if pay is None else pay,upper=1 if pay is None else pay,
                                 terminal=s.terminal_status.status.value,end=actor_state(s),trajectory=path)
                        rows.append(row);d.log('games',row)
            print('FAMILY',f['family'],len(rows),flush=True)
    except BaseException as e:error=type(e).__name__+':'+str(e)
    finally:d.close()
    out=dict(status='COMPLETE' if error is None and len(rows)==256 else 'PARTIAL_PRESERVED',error=error,games=len(rows),
             actual_native_go=d.queries,actual_native_reported_nodes=d.newnodes,seconds=time.perf_counter()-start,
             cells=[dict(proof=q,price_index=j,games=len([r for r in rows if r['proof']==q and r['price_index']==j]),
                         known_net=sum(r['payoff'] or 0 for r in rows if r['proof']==q and r['price_index']==j),
                         unknown=sum(r['payoff'] is None for r in rows if r['proof']==q and r['price_index']==j)) for q in [False,True] for j in [0,1]])
    (folder/'result.json').write_text(json.dumps(out,indent=2));print(out)


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('mode',choices=['freeze','run']);ap.add_argument('folder');a=ap.parse_args()
    (freeze if a.mode=='freeze' else run)(a.folder)
