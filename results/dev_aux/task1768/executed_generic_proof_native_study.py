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


def freeze(folder, *, learning=False, replication=False, krn=False):
    out=Path(folder);out.mkdir(exist_ok=False)
    T=mod('RNB54','results/dev_aux/task1675/rules.py');rng=random.Random(20261015544 if krn else 20261015543 if replication else 20261015542 if learning else 20261015541)
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
    fs=[];attempts=0;family_count=80 if krn else 128 if replication else 24 if learning else 16
    while len(fs)<family_count and attempts<100000:
        attempts+=1;places=rng.sample(range(16),6 if krn else 8);board=['.']*16
        for sq,piece in zip(places,'KkRNrn' if krn else 'KkRNBrnb'):board[sq]=piece
        s=tuple(board)+(0,)
        if not T.valid(s) or T.attacked(s,T.king(s,0),1):continue
        ll=T.moves(s)
        if len(ll)<4:continue
        capture=any(s[ord(u[2])-97+4*(int(u[3])-1)]!='.' for u,_ in ll)
        quiet=any(s[ord(u[2])-97+4*(int(u[3])-1)]=='.' for u,_ in ll)
        if not(capture and quiet) or orbit(s)&excluded:continue
        if any(not T.moves(t) for _,t in ll):continue
        flipped=tuple(x.swapcase() for x in s[:-1])+(1,)
        fs.append(dict(family=len(fs),phase=('TRAIN' if learning and len(fs)<(16 if krn else 8) else 'DEV'),roots=[s,flipped]));excluded.update(orbit(s))
    assert len(fs)==family_count
    prices=([[r,720,b,720] for r in (360,720,1440) for b in (360,720,1440)] if learning else [[720,720,720,720],[720,720,360,720]])
    if krn:prices=[[r,720,720,720] for r in (360,720,1440)]
    if replication:
        selection=json.loads(Path('results/dev_aux/task1765/selection.json').read_text())
        prices=[[720,720,720,720],selection['selected']]
    names={str(tuple(p)):'aux54_'+ '_'.join(map(str,p)) for p in prices}
    ini='[aux54base:chess]\nmaxFile = 4\nmaxRank = 4\ncastling = false\ndoubleStep = false\npromotionRank = 4\npromotionPieceTypes = rnb\nnMoveRule = 0\nnFoldRule = 0\nstartFen = k3/4/4/3K w - - 0 1\n'
    for p in prices:
        ini+='\n['+names[str(tuple(p))]+':aux54base]\n'+''.join(f'pieceValue{x} = p:{p[3]} n:{p[1]} b:{p[2]} r:{p[0]} q:1664\n' for x in ['Mg','Eg'])
    (out/'variant.ini').write_text(ini)
    plan=dict(families=fs,seed=(20261015544 if krn else 20261015543 if replication else 20261015542 if learning else 20261015541),attempts=attempts,study_kind=('LEARN' if learning else 'FOUR_CELL'),baseline_index=prices.index([720,720,720,720]),prices=prices,variant_names=names,
              model='results/dev_aux/task1675/rules.py',model_sha256=sha('results/dev_aux/task1675/rules.py'),
              binary='.local_agent/leaf-rnbp-46/fairy-leaf-rnb.exe',binary_sha256=sha('.local_agent/leaf-rnbp-46/fairy-leaf-rnb.exe'),
              variant_ini=str(out/'variant.ini'),variant_sha256=sha(out/'variant.ini'),
              stockproof='results/dev_aux/task1706/proof4.json',stockproof_sha256=sha('results/dev_aux/task1706/proof4.json'),
              candidate_nodes=(4096 if krn else 256),opponents=[dict(id='UNIT64',nodes=64),dict(id=('UNIT4096' if krn else 'UNIT256'),nodes=(4096 if krn else 256))],
              H=16,seconds_cap=(1200 if krn else 600),max_go=(40000 if krn else 10000),step_seconds=(1. if krn else .25),
              allocation='Proof at most1/4 visits and time; validation at most1/4; actual Native receives remainder. Actual reported node overrun retained. Visits across engines are not equal primitive cost.',
              trigger='Every ongoing state for both colors, fixed depth64; continue verified original tree after BOTH moves.',
              outcome='Actual Core checkmate/stalemate/repetition/maxply only. H16 unresolved retained with[-1,+1], no quantity reward or policy-cycle shortcut.',
              rootlaw=('Fresh4x4 closed6actor KkRNrn' if krn else 'Fresh4x4 closed8actor KkRNBrnb')+' , uncheck,>=4choices,capture+quiet,no immediate terminal; fullD4/color exclusion. No price/WDL filter.',
              exclusion_sources=sources,
              solver_sha256=sha('scripts/generic_win_proof.py'),player_sha256=sha('scripts/generic_proof_player.py'),study_sha256=sha(__file__),
              learning_objective='TRAIN finite-horizon actual win-event minus loss-event; unfinished stays UNKNOWN, contributes neither event, never relabeled draw.',
              initial_prices=[[360,720,1440,720],[720,720,720,720],[1440,720,360,720]],
              primary_selector='Full9grid TRAIN integerW-L,lex ties; three strict adjacent-coordinate paths descriptive, shared actual TRAIN games, no human-price fit.')
    plan['proof_algorithm']='PN' if krn else 'ANDOR'
    plan['pn_sha256']=sha('scripts/generic_win_proof_pn.py')
    plan['active_coordinates']=[0] if krn else [0,2]
    if krn:
        plan['initial_prices']=[[360,720,720,720],[720,720,720,720],[1440,720,720,720]]
        plan['incremental_cost_decision']='Newtwo-type game+PN, not rerun1766. 192TRAIN and<=1024DEV H16 means<=19456Nativecalls;40000cap covers bound,1200s stops independently. Can decide whether simple R/N relation generalizes under actual terminal feedback, no human fit.'
    plan['expected_DEV_games']=4*len([f for f in fs if f['phase']=='DEV'])*(4 if prices[-1]!=[720,720,720,720] else 2)
    if replication:
        plan['fixed_selection_source']='results/dev_aux/task1765/selection.json'
        plan['fixed_selection_sha256']=sha(plan['fixed_selection_source'])
        plan['status']='FROZEN_NEW128_FIXED_TRAIN_CANDIDATE_REPLICATION_NOT_EXTENSION_OF_OLD_DEV16'
    (out/'plan.json').write_text(json.dumps(plan,indent=2));print('FROZEN',len(fs),'families',len(sources),'oldcohorts')


def run(folder):
    folder=Path(folder);p=json.loads((folder/'plan.json').read_text())
    assert not p.get('study_sha256') or sha(__file__)==p['study_sha256']
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
    d=TimedDriver(p,folder/'run');d.files['game_events']=(d.O/'game_events.jsonl').open('w');c=compile_rnb();rows=[];error=None;start=time.perf_counter();active={}
    from scripts.generic_win_proof_pn import prove_win_pn
    from scripts.generic_win_proof import prove_win
    proof_function=prove_win_pn if p.get('proof_algorithm')=='PN' else prove_win
    assert p.get('proof_algorithm')!='PN' or sha('scripts/generic_win_proof_pn.py')==p['pn_sha256']
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
        def play(f,enabled,price_index,color,opponent):
            nonlocal active
            price=p['prices'][price_index];d.guard();s=from_actor(c,f['roots'][color]);target=s.position.side_to_move
            path=[];players={};pay=None
            active=dict(family=f['family'],phase=f['phase'],color=color,opponent=opponent['id'],proof=enabled,price_index=price_index,price=price,trajectory=path)
            d.log('game_events',dict(event='START',**active))
            for side in (0,1):
                pp=price if side==target else p['prices'][p.get('baseline_index',0)]
                def external(state,nodes,seconds,cancel,pp=pp):
                    raw=actor_state(state);move,used=d.choose_timed(raw,pp,nodes,seconds)
                    return check_frontier(state)[move],used
                players[side]=ProofMaterialPlayer(c,None,proof_enabled=enabled,normal_search=external,proof_search=proof_function)
            for ply in range(p['H']+1):
                if s.terminal_status.is_terminal:
                    pay=0 if s.terminal_status.winner is None else (1 if s.terminal_status.winner==target else -1);break
                if ply==p['H']:break
                d.guard()
                cap=p['candidate_nodes'] if s.position.side_to_move==target else opponent['nodes']
                z=players[s.position.side_to_move].choose(s,max_nodes=cap,seconds=p['step_seconds'],cancel=lambda:time.monotonic()>=d.deadline)
                if z.action is None:break
                a=z.action;step=dict(actor=actor_state(s),decision={**asdict(z),'action':uci(a)});path.append(step)
                d.log('game_events',dict(event='MOVE',family=f['family'],phase=f['phase'],color=color,opponent=opponent['id'],proof=enabled,price_index=price_index,ply=ply,**step))
                for player in players.values():player.observe(s,a)
                s=apply_action(s,a,c)
            row=dict(family=f['family'],phase=f['phase'],color=color,opponent=opponent['id'],proof=enabled,price_index=price_index,price=price,
                     payoff=pay,lower=-1 if pay is None else pay,upper=1 if pay is None else pay,
                     terminal=s.terminal_status.status.value,end=actor_state(s),trajectory=path)
            rows.append(row);d.log('games',row);d.log('game_events',dict(event='END',family=f['family'],phase=f['phase'],color=color,opponent=opponent['id'],proof=enabled,price_index=price_index,payoff=pay,terminal=row['terminal']));active={}
        selected=1
        baseline=p.get('baseline_index',0)
        if p.get('study_kind')=='LEARN':
            for f in p['families']:
                if f['phase']!='TRAIN':continue
                for index in range(len(p['prices'])):
                    for color in (0,1):
                        for op in p['opponents']:play(f,True,index,color,op)
                print('TRAIN_FAMILY',f['family'],len(rows),flush=True)
            score={i:sum(r['payoff'] or 0 for r in rows if r['price_index']==i) for i in range(len(p['prices']))}
            selected=min(score,key=lambda i:(-score[i],p['prices'][i]))
            paths=[]
            for initial in p['initial_prices']:
                current=p['prices'].index(initial);path=[current]
                for sweep in range(6):
                    changed=False
                    for coord in p.get('active_coordinates',[0,2]):
                        levels=[360,720,1440];level=levels.index(p['prices'][current][coord]);neighbors=[]
                        for j in (level-1,level+1):
                            if 0<=j<3:
                                value=list(p['prices'][current]);value[coord]=levels[j];neighbors.append(p['prices'].index(value))
                        eligible=[i for i in neighbors if score[i]>score[current]]
                        if eligible:
                            current=min(eligible,key=lambda i:(-score[i],p['prices'][i]));path.append(current);changed=True
                    if not changed:break
                paths.append(dict(initial=initial,path=[p['prices'][i] for i in path],endpoint=p['prices'][current]))
            (folder/'selection.json').write_text(json.dumps(dict(selected_index=selected,selected=p['prices'][selected],integer_scores=score,paths=paths,source='TRAIN only, before DEV'),indent=2))
        for f in p['families']:
            if f['phase']!='DEV':continue
            cells=[(False,baseline),(True,baseline)]
            if selected!=baseline:cells += [(False,selected),(True,selected)]
            if f['family']%2:cells.reverse()
            for enabled,index in cells:
                for color in (0,1):
                    for op in p['opponents']:play(f,enabled,index,color,op)
            print('DEV_FAMILY',f['family'],len(rows),flush=True)
    except BaseException as e:
        error=type(e).__name__+':'+str(e)
        if active:(folder/'partial_game.json').write_text(json.dumps(dict(**active,error=error,payoff=None,lower=-1,upper=1),indent=2))
    finally:d.close()
    out=dict(status='COMPLETE' if error is None else 'PARTIAL_PRESERVED',error=error,games=len(rows),
             actual_native_go=d.queries,actual_native_reported_nodes=d.newnodes,seconds=time.perf_counter()-start,
             cells=[dict(phase=phase,proof=q,price_index=j,
                         games=len([r for r in rows if r['phase']==phase and r['proof']==q and r['price_index']==j]),
                         known_net=sum(r['payoff'] or 0 for r in rows if r['phase']==phase and r['proof']==q and r['price_index']==j),
                         unknown=sum(r['payoff'] is None for r in rows if r['phase']==phase and r['proof']==q and r['price_index']==j))
                    for phase in sorted({r['phase'] for r in rows}) for q in [False,True] for j in sorted({r['price_index'] for r in rows})])
    (folder/'result.json').write_text(json.dumps(out,indent=2));print(out)


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('mode',choices=['freeze','freeze_learning','freeze_replication','freeze_krn','run']);ap.add_argument('folder');a=ap.parse_args()
    (freeze(a.folder,learning=a.mode in ('freeze_learning','freeze_krn'),replication=a.mode=='freeze_replication',krn=a.mode=='freeze_krn') if a.mode.startswith('freeze') else run(a.folder))
