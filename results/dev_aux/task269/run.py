import json,time,math,hashlib,importlib.util,datetime
from pathlib import Path
from fractions import Fraction
import chess
R=Path.cwd();O=R/'results/dev_aux/task269';D=json.loads((O/'declaration.json').read_bytes());assert not (O/'result.json').exists();s=importlib.util.spec_from_file_location('p',R/'results/dev_aux/task166/run.py');P=importlib.util.module_from_spec(s);s.loader.exec_module(P);P.stop();binary=R/D['binary_relative'];assert hashlib.sha256(binary.read_bytes()).hexdigest()==D['binary_sha256'];start=time.monotonic();deadline=start+600;env=dict(P=P,O=O,deadline=deadline,math=math);exec(compile((O/'configure.py').read_text(),str(O/'configure.py'),'exec'),env);configure=env['configure'];calls=[];out=dict(complete=False,calls=calls);unit=P.M.start(binary,3,deadline,P.stop)
def save():out['seconds']=time.monotonic()-start;P.A.atomic_json(O/'result.json',out)
def block(name,w,phase):
 e=P.M.start(binary,3,deadline,P.stop)
 try:
  roots=D['train_roots' if phase=='train' else 'development_roots']
  for oi,f in enumerate(roots):
   for color in (True,False):
    P.A.guard(deadline,P.stop);probes,ack=configure(e,w);oprobes,oack=configure(unit,D['opponent_weights']);b=P.board(f);actor=color;actions=[];searches=[];ts=time.monotonic()
    for ply in range(48):
     P.A.guard(deadline,P.stop)
     if b.is_game_over(claim_draw=False):break
     side='agent' if b.turn==actor else 'unit';m,v=P.M.M.search(e if side=='agent' else unit,b.copy(stack=True),deadline,P.stop,limit=1024);searches.append(dict(ply=ply,player=side,record=v));assert m in b.legal_moves;b.push(m);actions.append(m.uci())
    outcome=b.outcome(claim_draw=False);kind='UNKNOWN_CUTOFF' if outcome is None else outcome.termination.name;sign=0 if outcome is None or outcome.winner is None else 1 if outcome.winner==actor else -1;fitness=Fraction(sign)*(1+Fraction(48-len(actions),4800)) if kind=='CHECKMATE' else Fraction(0);calls.append(dict(name=name,phase=phase,weights=w,root=oi,color=color,actions=actions,search_records=searches,final_fen=b.fen(),termination=kind,terminal=outcome is not None,actual_terminal_result=None if outcome is None else sign,finite_mate_goal=sign if kind=='CHECKMATE' else 0,fitness=str(fitness),quantity_at_cap=sum(len(b.pieces(t,actor))-len(b.pieces(t,not actor)) for t in range(1,6)),seconds=time.monotonic()-ts,leaf_probes=probes,opponent_leaf_probes=oprobes,table_ack=ack,opponent_table_ack=oack));save()
 finally:e.close()
 print(phase,name,len(calls),round(time.monotonic()-start,3),flush=True)
try:
 for name,w in D['profiles'].items():block(name,w,'train')
 means={name:sum(Fraction(z['fitness']) for z in calls if z['phase']=='train' and z['name']==name)/4 for name in D['profiles']};chosen={name:max(family,key=lambda nm:means[nm]) for name,family in D['families'].items()};endpoints=dict(complete=True,chosen=chosen,weights={name:D['profiles'][nm] for name,nm in chosen.items()},train_means={name:str(v) for name,v in means.items()},training_games=len(calls),frozen_at=datetime.datetime.now(datetime.timezone.utc).isoformat());P.A.atomic_json(O/'endpoints.json',endpoints);out['endpoints']=endpoints;save();held={'unit':D['opponent_weights'],**{f'initial-{k}':w for k,w in D['initials'].items()},**{f'selected-{k}':w for k,w in endpoints['weights'].items()}};alias={};unique={}
 for name,w in held.items():
  key=tuple(w[k] for k in 'PNBRQK')
  if key in unique:alias[name]=unique[key]
  else:unique[key]=name;alias[name]=name;block(name,w,'development')
 out['development_aliases']=alias;out['complete']=True;save();print('COMPLETE',len(calls),out['seconds'],chosen)
except BaseException as ex:out['failure']=dict(type=type(ex).__name__,message=str(ex));save();raise
finally:unit.close()
