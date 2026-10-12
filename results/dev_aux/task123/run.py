"""Fresh versus profile-owned reuse; no engine weights, search or reward changes."""
import json,time,sys,statistics,hashlib,importlib.util
from pathlib import Path
ROOT=Path.cwd();OUT=ROOT/'results/dev_aux/task123';sys.path.insert(0,str(ROOT/'results/dev_aux/task109'));import adapter
sp=importlib.util.spec_from_file_location('game123',ROOT/'results/dev_aux/task104/short_game.py');G=importlib.util.module_from_spec(sp);sp.loader.exec_module(G)
original_configure=adapter.configure
phase_records=[]
def instrument_configure(e,w,config,deadline,stop,clock=time.monotonic):
 started=clock();reused=getattr(e,'same_profile',None)==w
 if not reused:
  probes=original_configure(e,w,config,deadline,stop,clock);e.same_profile=dict(w)
 else:
  # Verify actual values each game. Only startup/option/profile setup is reused.
  probes=[]
  for kind in 'PNBRQ':
   adapter.guard(deadline,stop,clock);fen='7k/8/8/3'+kind+'4/8/8/8/K7 w - - 0 1'
   e.send('position fen '+fen);e.send('eval');reply=e.ready();final=[x for x in reply if x.startswith('Final evaluation')]
   if len(final)!=1:raise RuntimeError('missing reuse leaf')
   measured=float(final[0].split()[2]);expected=w[kind]/208
   if abs(measured-expected)>.011:raise RuntimeError('reuse wrong material')
   probes.append(dict(type=kind,fen=fen,measured_white_pawns=measured,expected_white_pawns=expected))
  e.send('ucinewgame');e.ready()
 phase_records.append(dict(config_seconds=clock()-started,reused_same_profile=reused))
 return probes
adapter.configure=instrument_configure

def run():
 stop=lambda:adapter.stop_check(ROOT);stop();deadline=time.monotonic()+180
 if (OUT/'events.jsonl').exists():raise FileExistsError('Frozen new control cannot rerun')
 binary,digest,q=adapter.validated_entry(ROOT/'.local_agent/material-selfplay/fairy-material.exe',ROOT/'results/dev_aux/task120/qualification.json')
 old=json.loads((ROOT/'results/dev_aux/task121/controller.json').read_bytes());journ=adapter.Journal(OUT/'events.jsonl');rows=[];started=time.monotonic()
 try:
  for run in old['runs']:
   for arm in ('initial','final'):
    weights=run[arm+'_weights'];contexts=[]
    for oi in range(4):
     for color in (True,False):contexts.append(dict(opening_seed=82000+oi,random_seed=92000+oi,agent_color=color,phase='control',name=f"s{run['seed']}-{arm}-o{oi}-c{int(color)}"))
    # Alternating mode order over profiles; within a mode complete8declared games.
    modes=('fresh','reuse') if (run['seed']+int(arm=='final'))%2 else ('reuse','fresh')
    for mode in modes:
     engine=None;blockstart=time.monotonic()
     try:
      for context in contexts:
       adapter.guard(deadline,stop);initstart=time.monotonic();new=(mode=='fresh' or engine is None)
       if new:
        engine=adapter.UCI(binary,ROOT,deadline,stop);engine.backend='QUALIFIED_FAIRY_MATERIAL:'+digest
       initcost=time.monotonic()-initstart
       gamestart=time.monotonic();result=adapter.play_game(engine,weights,context,deadline,OUT/'variant.ini',journ,G.opening,G.score,stop,cap=16)
       cleanup=time.monotonic()
       if mode=='fresh':engine.close();engine=None
       rows.append(dict(seed=run['seed'],arm=arm,mode=mode,context=context,weights=weights,result=result,init_seconds=initcost,config=phase_records[-1],game_inclusive_seconds=time.monotonic()-gamestart,cleanup_seconds=time.monotonic()-cleanup))
     finally:
      if engine:engine.close()
     rows[-1]['block_inclusive_seconds']=time.monotonic()-blockstart
 finally:journ.close()
 comparisons=[]
 for r in old['runs']:
  for arm in ('initial','final'):
   block=[z for z in rows if z['seed']==r['seed'] and z['arm']==arm];f=[z for z in block if z['mode']=='fresh'];u=[z for z in block if z['mode']=='reuse'];pairs=[]
   for a,b in zip(f,u):
    ar,br=a['result'],b['result'];eq=ar['actions']==br['actions'] and ar['score']==br['score'] and ar['final_fen']==br['final_fen']
    eqnodes=[z['reported_nodes'] for z in ar['search_records']]==[z['reported_nodes'] for z in br['search_records']]
    pairs.append(dict(name=a['context']['name'],actions_score_fen_equal=eq,nodes_equal=eqnodes))
   comparisons.append(dict(seed=r['seed'],arm=arm,pairs=pairs,fresh_seconds=f[-1]['block_inclusive_seconds'],reuse_seconds=u[-1]['block_inclusive_seconds'],ratio=u[-1]['block_inclusive_seconds']/f[-1]['block_inclusive_seconds']))
 result=dict(complete=True,scope='New exposed-profile execution control; not added Task121 heldout',physical_games=len(rows),profile_groups=6,comparisons=comparisons,all48paired_trajectories_equal=all(p['actions_score_fen_equal'] for z in comparisons for p in z['pairs']),all48paired_nodes_equal=all(p['nodes_equal'] for z in comparisons for p in z['pairs']),wall_seconds=time.monotonic()-started,rows=rows)
 adapter.atomic_json(OUT/'control.json',result);print(json.dumps({k:v for k,v in result.items() if k!='rows'},indent=2))
if __name__=='__main__':run()