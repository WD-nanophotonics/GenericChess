"""New frozen actual deployment control of the return-prediction coefficients."""
import importlib.util,json,math,sys,time,hashlib,statistics
from pathlib import Path
ROOT=Path.cwd();OUT=ROOT/'results/dev_aux/task127';sys.path.insert(0,str(ROOT/'results/dev_aux/task109'));import adapter
s=importlib.util.spec_from_file_location('score127',ROOT/'results/dev_aux/task104/short_game.py');G=importlib.util.module_from_spec(s);s.loader.exec_module(G)
original=adapter.configure

def cached(e,w,config,deadline,stop,clock=time.monotonic):
 adapter.guard(deadline,stop,clock)
 if not hasattr(e,'profile'):
  result=original(e,w,config,deadline,stop,clock);e.profile=dict(w);return result
 if e.profile!=w:raise ValueError('Profile changes require a new owned process')
 probes=[]
 for kind in 'PNBRQ':
  fen='7k/8/8/3'+kind+'4/8/8/8/K7 w - - 0 1';e.send('position fen '+fen);e.send('eval');reply=e.ready();v=[z for z in reply if z.startswith('Final evaluation')]
  if len(v)!=1:raise RuntimeError('Missing/ambiguous material readback')
  measured=float(v[0].split()[2]);expected=w[kind]/208
  if not math.isfinite(measured) or abs(measured-expected)>.011:raise RuntimeError('Wrong/nonfinite material readback')
  probes.append(dict(type=kind,fen=fen,measured_white_pawns=measured,expected_white_pawns=expected))
 e.send('ucinewgame');e.ready();return probes
adapter.configure=cached

def execute():
 stop=lambda:adapter.stop_check(ROOT);stop();started=time.monotonic();deadline=started+120
 decl=json.loads((OUT/'declaration.json').read_bytes());binary,digest,q=adapter.validated_entry(ROOT/'.local_agent/material-selfplay/fairy-material.exe',ROOT/'results/dev_aux/task120/qualification.json')
 if (OUT/'events.jsonl').exists():raise FileExistsError('Frozen control cannot rerun')
 calls=[];journal=adapter.Journal(OUT/'events.jsonl');state='COMPLETE';e=None
 try:
  for op in (6,24):
   # Counterbalance profile order across regimes.
   for arm in (('unit','learned') if op==6 else ('learned','unit')):
    w=decl['profiles'][arm];e=adapter.UCI(binary,ROOT,deadline,stop);e.backend='QUALIFIED_FAIRY_MATERIAL:'+digest
    try:
     for oi in range(8):
      for color in (True,False):
       x=dict(opening_seed=86000+oi,random_seed=96000+oi,agent_color=color,phase='new_deployment',name=f'p{op}-a{arm}-o{oi}-c{int(color)}')
       r=adapter.play_game(e,w,x,deadline,OUT/'variant.ini',journal,lambda seed:G.opening(seed,plies=op),G.score,stop,cap=16);adapter.guard(deadline,stop);calls.append(dict(context=x,weights=w,result=r))
    finally:e.close();e=None
 except BaseException as err:state='INTERRUPTED';error=type(err).__name__+': '+str(err)
 finally:
  if e:e.close()
  journal.close()
 result=dict(complete=state=='COMPLETE',calls=calls,scope='New declared64game learned-vs-unit deployment, no training or human-fit')
 if state!='COMPLETE':result['error']=error
 adapter.atomic_json(OUT/'games.json',result)
 status=dict(status=state,physical_games=len(calls),wall_seconds=time.monotonic()-started,cap=16,hard_seconds=120,model_frozen=True,intercept_not_deployed=True,scope='Actual material leaf effect, conditional mature priors')
 if state!='COMPLETE':status['error']=error
 adapter.atomic_json(OUT/'status.json',status);print(json.dumps(status));return 0 if state=='COMPLETE' else 3
if __name__=='__main__':sys.exit(execute())