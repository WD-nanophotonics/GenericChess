"""Freshpaireddeployment of ALLsixfrozenends; notraining/selection extension."""
import json,time,hashlib,sys,importlib.util,random,statistics
from pathlib import Path
R=Path.cwd();O=R/'results/dev_aux/task150';O.mkdir(exist_ok=True)
s=importlib.util.spec_from_file_location('toggle139for150',R/'results/dev_aux/task139/run.py');M=importlib.util.module_from_spec(s);s.loader.exec_module(M);A=M.A;G=M.M.G;BASE=A.configure
def prepare(e,w,config,deadline,stop,clock=time.monotonic):
 probes=BASE(e,w,config,deadline,stop,clock)
 e.send('setoption name UCI_Variant value aux_short');reply=e.ready();acks=[x for x in reply if x.startswith('info string DEV_AUX alignment ')]
 assert len(acks)==1;parts=acks[0].split();assert int(parts[4])==e.alignment
 measured={int(x.split(':')[0]):tuple(map(int,x.split(':')[1:])) for x in parts[5:]};assert measured=={i+1:(w[k],w[k]) for i,k in enumerate('PNBRQ')}
 e.last_table_ack=acks[0];e.send('ucinewgame');e.ready();return probes
A.configure=prepare
def freeze():
 if (O/'declaration.json').exists():raise FileExistsError('frozen')
 C=json.loads((R/'results/dev_aux/task142/controller.json').read_bytes());assert C['completed'];build=json.loads((R/'results/dev_aux/task147/build.json').read_bytes());assert build['status']=='COMPLETE';qualified=json.loads((R/'results/dev_aux/task149/result.json').read_bytes());assert qualified['complete'] and len(qualified['rows'])==96
 roots={str(1011000+i):G.opening(1011000+i,plies=24) for i in range(8)}
 profiles=[dict(seed=x['seed'],training_alignment=x['alignment'],weights=x['final_weights']) for x in C['runs']]
 d=dict(task_id='150',question='Do SEErecaptureconstant+priceordering repairschange deployedproxyreturn of everyfrozenendpoint atsameleafandnewseeds?',profiles=profiles,roots=roots,random_seeds=[1111000+i for i in range(8)],modes=[1,3],games=192,cap=16,nodes_limit=1024,deadline_seconds=180,binary_relative=build['binary_relative'],binary_sha256=build['binary_sha256'],source_controller_sha256=hashlib.sha256((R/'results/dev_aux/task142/controller.json').read_bytes()).hexdigest(),scope='Bothmodes samecandidateleaf ANDsearchPieceValueMG/EG; mode3addsrecaptureconstants+priceorderedattackerclass. Fixedmargins/SEEgeometryapproxremain. Allsixends included, nohumanselection. Freshpaireddeployment, notnewtraining/humanvalue recovery.',cost='192shortgamesestimated20-30s,180sfuse; no newworkers, longer games,oroldtestrerun.',decision='Consistentreturnimprovement wouldjustify nextboundedlearning comparisonwithnewprice-consistententry; mixed/negativeeffects warnthatparameterconsistencyrepairalone doesnotensureproxybenefit.')
 (O/'declaration.json').write_text(json.dumps(d,indent=2),encoding='utf-8');print(json.dumps(dict(frozen=True,games=192,ends=len(profiles))))
def execute():
 d=json.loads((O/'declaration.json').read_bytes());binary=R/d['binary_relative'];assert hashlib.sha256(binary.read_bytes()).hexdigest()==d['binary_sha256'];started=time.monotonic();deadline=started+d['deadline_seconds'];stop=lambda:A.stop_check(R);stop()
 if (O/'events.jsonl').exists():raise FileExistsError('frozenexecution')
 j=A.Journal(O/'events.jsonl');calls=[];complete=False
 try:
  for pi,profile in enumerate(d['profiles']):
   for mode in ((1,3) if pi%2==0 else (3,1)):
    e=M.start(binary,mode,deadline,stop);w=profile['weights']
    try:
     for oi in range(8):
      for color in (True,False):
       x=dict(opening_seed=1011000+oi,random_seed=1111000+oi,agent_color=color,phase='paireddeployment',name=f'p{pi}-mode{mode}-o{oi}-c{int(color)}',profile_index=pi,mode=mode)
       r=A.play_game(e,w,x,deadline,O/'variant.ini',j,lambda seed:d['roots'][str(seed)],G.score,stop,cap=16);r['search_table_ack']=e.last_table_ack;calls.append(dict(context=x,weights=w,result=r))
    finally:e.close()
  complete=True
 except BaseException as ex:error=type(ex).__name__+': '+str(ex)
 finally:j.close()
 out=dict(complete=complete,calls=calls,wall_seconds=time.monotonic()-started,declaration_sha256=hashlib.sha256((O/'declaration.json').read_bytes()).hexdigest(),binary_sha256=d['binary_sha256'])
 if not complete:out['error']=error
 A.atomic_json(O/'games.json',out);summary=dict(complete=complete,games=len(calls),wall_seconds=out['wall_seconds'],profiles=[])
 if complete:
  for pi,profile in enumerate(d['profiles']):
   pairs=[];mates={};means={}
   for oi in range(8):
    for color in (True,False):
     pair=[next(c['result'] for c in calls if c['context']['name']==f'p{pi}-mode{mode}-o{oi}-c{int(color)}') for mode in (1,3)]
     bounded=[(0 if r['score']['winner'] is None else (1 if r['score']['winner']==color else -1)) if r['score']['terminal'] else r['score']['quantity_difference']/15 for r in pair]
     pairs.append(dict(opening=oi,color=color,original_delta=pair[1]['reward']-pair[0]['reward'],bounded_delta=bounded[1]-bounded[0]))
   for mode in (1,3):
    rows=[c['result'] for c in calls if c['context']['profile_index']==pi and c['context']['mode']==mode];mates[str(mode)]=sum(r['score']['termination']=='CHECKMATE' and r['score']['winner']==r['score']['agent_color'] for r in []) if False else sum(r['score']['termination']=='CHECKMATE' and r['score']['winner']==c['context']['agent_color'] for c in calls if c['context']['profile_index']==pi and c['context']['mode']==mode for r in [c['result']]);means[str(mode)]=statistics.mean(r['reward'] for r in rows)
   summary['profiles'].append(dict(**profile,mate_wins=mates,mean_original_reward=means,paired_original_mean=statistics.mean(p['original_delta'] for p in pairs),paired_bounded_mean=statistics.mean(p['bounded_delta'] for p in pairs),pairs=pairs))
 A.atomic_json(O/'summary.json',summary);print(json.dumps({k:v for k,v in summary.items() if k!='profiles'}));return 0 if complete else 3
if __name__=='__main__':
 if sys.argv[1:]==['freeze']:freeze()
 else:sys.exit(execute())
