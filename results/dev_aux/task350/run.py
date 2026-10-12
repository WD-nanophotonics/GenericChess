"""Bounded TD-directed root-material prototype under same finite338 objective."""
import json,time,math,random,importlib.util,os
from pathlib import Path
from fractions import Fraction as F
import chess
R=Path.cwd();sp=importlib.util.spec_from_file_location('g350',R/'results/dev_aux/task335/run.py');G=importlib.util.module_from_spec(sp);sp.loader.exec_module(G);Q=G.Q;O=R/'results/dev_aux/task350';assert not (O/'declaration.json').exists();D0=json.loads((R/'results/dev_aux/task338/declaration.json').read_bytes());cells=[(ri,color) for ri in range(8) for color in (True,False)];orders=[]
for epoch in range(2):
 cc=cells.copy();random.Random(2026102450+epoch).shuffle(cc);orders.append([dict(root=ri,color=color) for ri,color in cc])
D=dict(task_id='350',question='Can cheaper ROOT-TD ratherthan9-policycoordinate proposals optimize SAMEfinitequantity/mate target with maturesearch?',initials=D0['initials'],unit=D0['unit'],roots=D0['roots'],orders=orders,epochs=2,games=96,node_limit=1024,cap=24,alpha=.05,lam=.7,beta=.25,whole_fuse_seconds=600,estimated_seconds=40,goal='338CHECKMATE±32/ruleDRAW0/nonterminalquantity/15; normalizeby32 ONLYforboundedTDtarget; samepolicyrankingobjective, notultimateWDL. No speedterm/quantityhumanweights.',model='tanh(beta*sum(normalizedlatentweights[k]*candidateviewnonkingcountdifference[k])); P=1K0, updatesNBRQonly. Candidatechoice remainspurematerial maturemode3 using nearestinteger208*latentweights, clip32..8192. Floatlatent model/roundedsearchpolicy distinction explicit; noPV/UCI-scoregradient assumption.',update='Weights heldpergame; observations beforeeachcandidatemove; fixedRootTD(lambda) batchepisode usingeligibilitytrace. Delta=nextrootprediction-current, final normalizedactualfinitegoal-current. Sumalpha*trace*delta; clip latent tosame32..8192 afterepisode, recordUNCLIPPEDvalues andboundhits. No claimtruepolicygradient/convergence orsemanticgenerality.',scope='Changedoptimizer versus338 butsame roots/opponent/goals/1024/cap24. Only2epochs32gamesperinitial, allthreeendpointsfrozen beforedevelopment; no human-fit/hyperparameterselection, epochgrowth ordiscardingfailedstarts. RootTD usesactualboard smoothmodel, not minmaxPV gradient. Ordersfixedalgorithmicshared acrossinitials. Boundhit countsandrounding disclosed; clippedresults notproof ofnaturalpositiveprices.',literature='TD-directed variant in https://arxiv.org/pdf/cs/9901001; source distinguishes rootprediction fromleafprediction. Thesearbitrarysmallprototypealpha/lambda/beta arepredeclared, notclaimedreplication ofunreadBeal1997/Smiththesis.',decision='This96gameproxy testsoptimizer/samplecost separatelyfrommorecoordinate generations. If modeldoesnotlearn/gain oronlyfitsfiniteproxy, retainnegative; no longgames, no rescue/extraepochs. Directusercostexperimentalreadyworks, notanentryblocksubstitute.')
Q.write(O/'declaration.json',D);start=time.monotonic();deadline=start+600;env=dict(P=Q.P,O=O,deadline=deadline,math=math);exec(compile((R/'results/dev_aux/task272/configure.py').read_text(encoding='utf-8'),'configure272','exec'),env);configure=env['configure'];rows=[];endpoints={};actual_queries=0;status=dict(complete=False);eu=None
try:
 eu=Q.P.M.start(R/'.local_agent/alignment-order/fairy-order-toggle.exe',3,deadline,Q.P.stop)
 with (O/'games.jsonl').open('x',encoding='utf-8') as games,(O/'queries.jsonl').open('x',encoding='utf-8') as journal:
  for family,initial in D['initials'].items():
   latent={k:initial[k]/208 for k in 'PNBRQ'};bounds=0
   for epoch,order in enumerate(orders):
    for ci,cell in enumerate(order):
     ww={k:max(32,min(8192,math.floor(latent[k]*208+.5))) for k in 'PNBRQ'};ww['K']=0;ec=Q.P.M.start(R/'.local_agent/alignment-order/fairy-order-toggle.exe',3,deadline,Q.P.stop);f=D['roots'][cell['root']];color=cell['color'];journal.write(json.dumps(dict(event='game_start',family=family,epoch=epoch,cell=ci,**cell,weights=ww),separators=(',',':'))+'\n');journal.flush()
     try:z=G.run_game(ec,eu,ww,D['unit'],f,color,deadline,configure,journal)
     finally:ec.close()
     if z['termination']not in ('CHECKMATE','UNKNOWN_CUTOFF'):z['fitness']='0'
     b=Q.P.board(f);observations=[]
     for u in z['actions']:
      if b.turn==color:
       x={k:len(b.pieces(i+1,color))-len(b.pieces(i+1,not color)) for i,k in enumerate('PNBRQ')};pred=math.tanh(D['beta']*sum(latent[k]*x[k] for k in 'PNBRQ'));grad={k:D['beta']*(1-pred*pred)*x[k] for k in 'NBRQ'};observations.append(dict(x=x,prediction=pred,gradient=grad))
      b.push_uci(u)
     assert b.fen()==z['final_fen'];target=float(F(z['fitness'])/32);trace={k:0. for k in 'NBRQ'};update={k:0. for k in 'NBRQ'};deltas=[]
     for i,obs in enumerate(observations):
      nxt=observations[i+1]['prediction'] if i+1<len(observations) else target;delta=nxt-obs['prediction'];deltas.append(delta)
      for k in 'NBRQ':trace[k]=D['lam']*trace[k]+obs['gradient'][k];update[k]+=D['alpha']*trace[k]*delta
     unclip={k:latent[k]+update.get(k,0.) for k in 'PNBRQ'};after={k:max(32/208,min(8192/208,unclip[k])) for k in 'PNBRQ'};after['P']=1.;hits=[k for k in 'NBRQ' if unclip[k]!=after[k]];bounds+=len(hits);row=dict(family=family,epoch=epoch,cell=ci,root=cell['root'],color=color,latent_before=latent,latent_unclipped=unclip,latent_after=after,bound_hits=hits,target=target,observations=observations,deltas=deltas,update=update,**{k:v for k,v in z.items() if k!='color'});rows.append({k:v for k,v in row.items() if k!='search_records'});games.write(json.dumps(row,separators=(',',':'))+'\n');games.flush();os.fsync(games.fileno());actual_queries+=len(z['search_records']);latent=after
    print(family,epoch,latent,len(rows),actual_queries,round(time.monotonic()-start,3),flush=True)
   final={k:max(32,min(8192,math.floor(latent[k]*208+.5))) for k in 'PNBRQ'};final['K']=0;endpoints[family]=dict(weights=final,latent=latent,bound_hits=bounds,episodes=32)
  Q.write(O/'endpoints.json',dict(complete=True,endpoints=endpoints,frozen_at=time.time(),actual_games=len(rows),actual_queries=actual_queries,seconds=time.monotonic()-start));status['complete']=True
except BaseException as ex:status['failure']=dict(type=type(ex).__name__,message=str(ex));raise
finally:
 if eu:eu.close()
 Q.write(O/'result.json',dict(status=status,actual_games=len(rows),actual_queries=actual_queries,rows=rows,endpoints=endpoints,seconds=time.monotonic()-start))
print('COMPLETE',len(rows),actual_queries,round(time.monotonic()-start,3),endpoints)