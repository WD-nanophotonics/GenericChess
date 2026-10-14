"""Scoped research KRN runner: one manifest owns all executed resource settings."""
import ast,json,hashlib,importlib.util,time,os,random,chess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def scoped(path):
 p=(ROOT/path).resolve()
 if not p.is_relative_to(ROOT):raise ValueError('path outside own clone')
 return p
def validate(plan):
 # Actual observed legacy failure: max_train_seconds changed while max_seconds did not.
 for old in ('max_train_seconds','max_dev_seconds','prices_by_arm','arms','pilot_games'):
  if old in plan:raise ValueError('ambiguous legacy field:'+old)
 if plan['H']<1 or plan['nodes']<1 or plan['max_seconds']<=0:raise ValueError('positive executed budget required')
 if not plan['profiles'] or set(plan['opponents'])!={'unit_search','uniform_random'}:raise ValueError('frozen profiles/opponents')
 if plan['opponents']['unit_search']!=720:raise ValueError('teacher scope720')
 if digest(scoped(plan['root_file']))!=plan['root_sha256']:raise ValueError('root input changed')
 roots=json.loads(scoped(plan['root_file']).read_bytes())['roots'][slice(*plan['root_range'])]
 if len(roots)!=plan['root_count']:raise ValueError('root slice/count mismatch')
 for root in roots:
  b=chess.Board(root['fen8'])
  if not b.is_valid() or b.castling_rights or b.ep_square is not None or b.halfmove_clock!=0:raise ValueError('unsupported root')
  if len(b.piece_map())>10 or any(p.piece_type not in [2,4,6] for p in b.piece_map().values()):raise ValueError('KRN10 scope')
  if sorted(m.uci() for m in b.legal_moves)!=root['legal']:raise ValueError('frozen legal list')
 for name,p in plan['profiles'].items():
  if not 1<=p['leafR']<=4096 or not 1<=p['nativeR']<=4096:raise ValueError('qualified leaf/native range')
 n=len(roots)*2*len(plan['opponents'])*len(plan['profiles'])
 if n!=plan['expected_games']:raise ValueError('case matrix/count mismatch')
 if digest(scoped(plan['binary']))!=plan['binary_sha256']:raise ValueError('binary changed')
 return roots
def runtime():
 s=importlib.util.spec_from_file_location('owned166',ROOT/'results/dev_aux/task166/run.py')
 p=importlib.util.module_from_spec(s);s.loader.exec_module(p)
 return p
def emit(f,value):
 f.write(json.dumps(value)+'\n');f.flush();os.fsync(f.fileno())
def search(e,b,nodes):
 e.send('position fen '+b.root().fen()+' moves '+' '.join(m.uci() for m in b.move_stack))
 cmd='go nodes '+str(nodes);e.send(cmd);lines=e.until(lambda x:x.startswith('bestmove '))
 move=lines[-1].split()[1]
 if move not in legal5(b):raise ValueError('illegal bestmove')
 e.ready()
 return move,dict(root_fen5=b.root().fen(),root_fen8=b.root().fen(),full_history=[m.uci() for m in b.move_stack],command=cmd,uci_info=lines[:-1],backend=e.backend)
def close_all(engines):
 failures=[]
 for e in engines:
  try:e.close()
  except BaseException as ex:failures.append(type(ex).__name__+':'+str(ex))
 if failures:raise RuntimeError('cleanup failed:'+repr(failures))

def inside(s):
    return chess.square_file(s) < 8 and chess.square_rank(s) < 8

def legal5(b):
    return sorted((m.uci() for m in b.legal_moves if inside(m.from_square) and inside(m.to_square)))

def fen5(b):
    return b.fen()

def term5(b):
    legal = legal5(b)
    if not legal:
        return dict(kind='CHECKMATE' if b.is_check() else 'STALEMATE', winner=not b.turn if b.is_check() else None)
    if b.is_insufficient_material():
        return dict(kind='SUFFICIENT_MATERIAL_INSUFF_DRAW', winner=None)
    if b.is_repetition(3):
        return dict(kind='THREEFOLD_AUTO', winner=None)
    if b.halfmove_clock >= 100:
        return dict(kind='FIFTY_MOVE_AUTO', winner=None)
    return None

def config5(e, w, out):
    line = ' '.join((k.lower() + ':' + str(w[k]) for k in 'PNBRQ'))
    config = out / 'variant.ini'
    config.write_text('[aux_full:chess]\npieceValueMg = ' + line + '\npieceValueEg = ' + line + '\n', encoding='utf-8')
    for name, value in [('Threads', 1), ('Hash', 16), ('Use NNUE', 'false'), ('SyzygyPath', '<empty>'), ('VariantPath', str(config)), ('UCI_Variant', 'aux_full')]:
        e.send('setoption name ' + name + ' value ' + str(value))
        reply = e.ready()
        if name == 'UCI_Variant':
            assert any((x.startswith('info string variant aux_full files 8 ranks 8 ') for x in reply))
            ack = [x for x in reply if x.startswith('info string DEV_AUX alignment ')]
            assert len(ack) == 1
    f = ack[0].split()
    assert int(f[4]) == 3
    assert {int(x.split(':')[0]): list(map(int, x.split(':')[1:])) for x in f[5:]} == {i + 1: [w[k], w[k]] for i, k in enumerate('PNBRQ')}
    probes = []
    for piece in 'NR':
        e.send('position fen 4k3/8/8/8/2' + piece + '5/8/8/K7 w - - 0 1')
        e.send('eval')
        r = e.ready()
        v = [x for x in r if x.startswith('Final evaluation')]
        assert len(v) == 1
        measured = float(v[0].split()[2])
        assert abs(measured - w[piece] / 208) <= 0.011
        probes.append(dict(piece=piece, measured=measured, expected=w[piece] / 208, raw=r))
    return dict(raw=ack[0], probes=probes, weights=w)

def execute(plan_path,output):
 plan_path=scoped(plan_path);D=json.loads(plan_path.read_bytes());roots=validate(D)
 O=scoped(output);O.mkdir(exist_ok=False)
 P=runtime();P.stop();start=time.monotonic();deadline=start+D['max_seconds']
 engines=[];closed=go=0;acks=[];error=None;complete=False
 w0=dict(P=1664,N=720,B=1664,R=720,Q=1664,K=0)
 def start_engine():
  e=P.M.start(scoped(D['binary']),3,deadline,P.stop);engines.append(e);return e
 with (O/'queries.jsonl').open('x',encoding='utf-8') as qj,(O/'games.jsonl').open('x',encoding='utf-8') as gj:
  try:
   for arm,profile in D['profiles'].items():
    leafR=profile['leafR'];nativeR=profile['nativeR'];w=dict(w0,R=leafR);nw=dict(w0,R=nativeR)
    for opp in D['opponents']:
     e=eu=None
     try:
      e=start_engine();ack=config5(e,nw,O);e.send('devauxleafr '+str(leafR));read=e.ready()
      leafack=next(x for x in read if x.startswith('info string DEV_AUX leafR '))
      if leafack!=f'info string DEV_AUX leafR {leafR} nativeR {nativeR} captureR {nativeR}':raise ValueError('leaf/native/capture ack')
      probes=[]
      for piece,expect in [('N',720),('R',leafR)]:
       e.send('position fen 4k3/8/8/8/2'+piece+'5/8/8/K7 w - - 0 1');e.send('eval');raw=e.ready()
       measured=float(next(x for x in raw if x.startswith('Final evaluation')).split()[2])
       if abs(measured-expect/208)>.011:raise ValueError('leaf probe mismatch')
       probes.append(dict(piece=piece,expected=expect/208,measured=measured,raw=raw))
      acks.append(dict(profile=arm,opponent=opp,native=ack,leafack=leafack,leafprobes=probes,backend=e.backend))
      if opp=='unit_search':eu=start_engine();acks.append(dict(profile=arm,opponent=opp,unit=config5(eu,w0,O),backend=eu.backend))
      for root in roots:
       for color in [False,True]:
        for eng in [e,eu]:
         if eng:eng.send('ucinewgame');eng.ready()
        b=chess.Board(root['fen8']);name=f'{arm}-{leafR}-{opp}-{root["seed"]}-{root["variant"]}-{int(color)}';acts=[];queries=[];rt=0
        for ply in range(D['H']):
         P.A.guard(deadline,P.stop)
         if term5(b):break
         actor=b.turn;before=b.fen();draw=None
         if actor==color or eu is not None:
          move,meta=search(e if actor==color else eu,b.copy(stack=True),D['nodes'])
          q=dict(game=name,ply=ply,player='candidate' if actor==color else 'unit',weights=w if actor==color else w0,native_weights=nw if actor==color else w0,move=move,metadata=meta)
          emit(qj,q);queries.append(q);go+=1
         else:
          legal=legal5(b);seed=(D['random_seed_base']+2*root['seed']+int(color))*100+rt;idx=random.Random(seed).randrange(len(legal));move=legal[idx];draw=dict(seed=seed,index=idx,legal=legal,opponent_turn=rt);rt+=1
         if move not in legal5(b):raise ValueError('illegal action')
         b.push_uci(move);acts.append(dict(actor=actor,move=move,before=before,after=b.fen(),draw=draw))
        t=term5(b);label='C' if t is None else 'D' if t['winner'] is None else 'W' if t['winner']==color else 'L'
        emit(gj,dict(game=name,root=root,arm=arm,profile=arm,nativeR=nativeR,leafR=leafR,price=leafR,opponent=opp,color=color,weights=w,actions=acts,queries=queries,termination=t or dict(kind='cap'+str(D['H']),winner=None),label=label,final_fen=b.fen()));closed+=1
     finally:
      # This is inside finally: a producer exception must also close the teacher.
      close_all([eng for eng in [e,eu] if eng is not None])
   complete=True
  except BaseException as ex:error=type(ex).__name__+': '+str(ex)
  finally:
   try:close_all(engines)
   except BaseException as ex:error=(error or '')+'; '+str(ex);complete=False
 all_closed=all(e.closed and e.p.poll() is not None for e in engines)
 if not all_closed:complete=False;error=(error or '')+'; owned process cleanup not confirmed'
 out=dict(complete=complete,error=error,closed_games=closed,actual_go=go,seconds=time.monotonic()-start,executed=dict(H=D['H'],nodes=D['nodes'],max_seconds=D['max_seconds'],random_seed_base=D['random_seed_base'],expected_games=D['expected_games']),plan_sha256=digest(plan_path),root_sha256=digest(scoped(D['root_file'])),binary_sha256=D['binary_sha256'],source_sha256=digest(__file__),owned_engine_exit_codes=[e.p.poll() for e in engines],all_owned_engines_closed=all_closed)
 (O/'price_acks.json').write_text(json.dumps(acks,indent=2));(O/'result.json').write_text(json.dumps(out,indent=2));print(out)
 return out
if __name__=='__main__':
 import sys
 execute(sys.argv[1],sys.argv[2])
