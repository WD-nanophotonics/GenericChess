"""Same fixed goal and seeds, isolate ordinal random-stream coupling after all endpoints freeze."""
import json,time,sys,os,math,importlib.util,inspect
from pathlib import Path
R=Path.cwd();sp=importlib.util.spec_from_file_location('g328',R/'results/dev_aux/task320/run.py');G=importlib.util.module_from_spec(sp);sp.loader.exec_module(G);Q=G.Q;O=R/'results/dev_aux/task328'
def execute():
 O.mkdir(exist_ok=False);Q.P.stop();E=json.loads((R/'results/dev_aux/task322/endpoints.json').read_bytes());assert E['complete'];D0=json.loads((R/'results/dev_aux/task322/declaration.json').read_bytes());profiles={**{f'initial-{k}':w for k,w in D0['initials'].items()},**{f'endpoint-{k}':v['weights'] for k,v in E['endpoints'].items()}};unique={};aliases={}
 for name,w in profiles.items():
  kk=tuple(w[k] for k in 'PNBRQK')
  if kk not in unique:unique[kk]=name
  aliases[name]=unique[kk]
 # A new private per-opponent-turn generator prevents n-dependent rejection consuming futureturns' stream.
 src=inspect.getsource(G.run_game).replace('rng=random.Random(seed);actions=[]','random_turn=0;actions=[]').replace('ix=rng.randrange(len(legal));m=legal[ix];','rng=random.Random(str(seed)+":"+str(random_turn));ix=rng.randrange(len(legal));random_turn+=1;m=legal[ix];');assert src!=inspect.getsource(G.run_game);(O/'ordinal_run_game.py').write_text(src,encoding='utf-8');env=dict(G.__dict__);exec(compile(src,'ordinal_run_game','exec'),env);game=env['run_game']
 D=dict(task_id='328',question='Does frozenprice gain survive a different fixedcoupling of sameuniformlegalrandom opponent?',roots=D0['roots'],profiles=profiles,unique_profiles=list(unique.values()),aliases=aliases,seeds=D0['random_seeds'][:4],colors=[True,False],node_limit=1024,cap=48,random_coupling='Foropponentturn j, Random(str(seed)+":"+str(j)).randrange(len(sortedlegalUCI)); indexeddrawstreams local toturn, rejectiondoesn't consume laterturnstreams. Each action uniform under PRNGmodel; finitefixed16cells notconfidence/IID guarantee. Historical320/322coupling remainsunaltered.',reference='322sameprices/root/color/first4seeds exactsamegoal, alreadyobserved trajectories. Onlycouplingchanges, noextra seeds/fit/horizon. Allendpoints frozen before counterfactualgoals, notselection.',endpoint_sha256=Q.sha(R/'results/dev_aux/task322/endpoints.json'),whole_fuse_seconds=600,scope='Goalstillrandommate-speed, same marginaluniformlegalpolicy butdifferentcoupledfinite-realizations; sensitivitydoesnotitselfprovecausallegalsetbias/generalpriceimpossibility. No sameopponentactionsafterdifferent boards.')
 Q.write(O/'declaration.json',D);start=time.monotonic();deadline=start+600;configure_env=dict(P=Q.P,O=O,deadline=deadline,math=math);exec(compile((R/'results/dev_aux/task272/configure.py').read_text(),'configure272','exec'),configure_env);configure=configure_env['configure'];rows=[];out=dict(complete=False,calls=rows)
 try:
  with (O/'queries.jsonl').open('x',encoding='utf-8') as journal:
   for name in unique.values():
    w=profiles[name];e=Q.P.M.start(R/'.local_agent/alignment-order/fairy-order-toggle.exe',3,deadline,Q.P.stop)
    try:
     for ri,f in enumerate(D['roots']):
      for color in D['colors']:
       for seed in D['seeds']:
        journal.write(json.dumps(dict(event='game_start',profile=name,root=ri,color=color,seed=seed,weights=w),separators=(',',':'))+'\n');journal.flush();row=dict(profile=name,root=ri,**game(e,w,f,color,seed,1024,deadline,configure,journal=journal));rows.append(row)
    finally:e.close()
    print(name,len(rows),round(time.monotonic()-start,3),flush=True)
  out['complete']=True
 except BaseException as ex:out['failure']=dict(type=type(ex).__name__,message=str(ex));raise
 finally:out['seconds']=time.monotonic()-start;Q.write(O/'result.json',out)
if __name__=='__main__':execute()