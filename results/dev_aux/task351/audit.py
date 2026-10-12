"""Independent RootTD backward-return update andallmaturequeries replay."""
import json,time,math,hashlib
from pathlib import Path
from fractions import Fraction as F
import chess
R=Path.cwd();O=R/'results/dev_aux/task351';assert not (O/'audit.json').exists();start=time.monotonic();D=json.loads((R/'results/dev_aux/task350/declaration.json').read_bytes());X=json.loads((R/'results/dev_aux/task350/result.json').read_bytes());E=json.loads((R/'results/dev_aux/task350/endpoints.json').read_bytes());assert X['status']['complete'] and E['complete'];rows=[json.loads(l) for l in (R/'results/dev_aux/task350/games.jsonl').read_bytes().splitlines()];latent={k:{p:w[p]/208 for p in 'PNBRQ'} for k,w in D['initials'].items()};nq=hits=0;maxerr=0.;near=lambda a,b:abs(a-b)<1e-12
for z in rows:
 family=z['family'];before=latent[family];assert z['latent_before']==before;ww={k:max(32,min(8192,math.floor(before[k]*208+.5))) for k in 'PNBRQ'};ww['K']=0;assert z['weights']==ww;cell=D['orders'][z['epoch']][z['cell']];assert (z['root'],z['color'])==(cell['root'],cell['color']);f=D['roots'][z['root']];b=chess.Board(f['initial_fen'])
 for u in f['history']:b.push_uci(u)
 ss={p['ply']:p for p in z['search_records']};assert len(ss)==len(z['actions'])<=24;observations=[]
 for ply,u in enumerate(z['actions']):
  assert not b.is_game_over(claim_draw=False);qr=ss[ply];who='candidate' if b.turn==z['color'] else 'unit';assert qr['player']==who;meta=qr['record'];assert meta['root_fen']==f['initial_fen'] and meta['full_history']==[m.uci() for m in b.move_stack] and meta['nodes_limit']==1024 and meta['reported_nodes']>=0;parts=[s.split() for s in meta['uci_info'] if ' pv ' in s];pv=parts[-1][parts[-1].index('pv')+1:];assert pv[0]==u;c=b.copy(stack=True)
  for t in pv:assert chess.Move.from_uci(t) in c.legal_moves;c.push_uci(t)
  if who=='candidate':
   v={k:len(b.pieces(i+1,z['color']))-len(b.pieces(i+1,not z['color'])) for i,k in enumerate('PNBRQ')};pred=math.tanh(D['beta']*sum(before[k]*v[k] for k in 'PNBRQ'));grad={k:D['beta']*(1-pred**2)*v[k] for k in 'NBRQ'};observations.append((v,pred,grad))
  assert chess.Move.from_uci(u) in b.legal_moves;b.push_uci(u);nq+=1
 oo=b.outcome(claim_draw=False);kind='UNKNOWN_CUTOFF' if oo is None else oo.termination.name;sign=0 if kind!='CHECKMATE' else 1 if oo.winner==z['color'] else -1;count=lambda co:sum(len(b.pieces(k,co)) for k in range(1,6));quantity=count(z['color'])-count(not z['color']);goal=F(32*sign) if sign else F(quantity,15) if oo is None else F(0);target=float(goal/32);assert (str(goal),quantity,sign,kind,b.fen())==(z['fitness'],z['quantity_difference'],z['finite_mate_sign'],z['termination'],z['final_fen']);assert near(target,z['target']) and len(observations)==len(z['observations']);delta=[]
 for i,(v,p,g) in enumerate(observations):
  raw=z['observations'][i];assert raw['x']==v and near(raw['prediction'],p) and all(near(raw['gradient'][k],g[k]) for k in 'NBRQ');nxt=observations[i+1][1] if i+1<len(observations) else target;delta.append(nxt-p)
 assert all(near(a,b) for a,b in zip(delta,z['deltas']));update={k:0. for k in 'NBRQ'};future=0.
 for i in reversed(range(len(delta))):
  future=delta[i]+D['lam']*future
  for k in 'NBRQ':update[k]+=D['alpha']*observations[i][2][k]*future
 for k in 'NBRQ':maxerr=max(maxerr,abs(update[k]-z['update'][k]));assert near(update[k],z['update'][k])
 unclip={k:before[k]+update.get(k,0) for k in 'PNBRQ'};after={k:max(32/208,min(8192/208,unclip[k])) for k in 'PNBRQ'};after['P']=1.;assert all(near(unclip[k],z['latent_unclipped'][k]) and near(after[k],z['latent_after'][k]) for k in 'PNBRQ');bh=[k for k in 'NBRQ' if unclip[k]!=after[k]];assert bh==z['bound_hits'];hits+=len(bh);latent[family]=z['latent_after']
 for field,w in [('table_ack',ww),('opponent_table_ack',D['unit'])]:assert z[field]['prices']=={str(i+1):[w[k]]*2 for i,k in enumerate('PNBRQ')}
 for field,w in [('leaf_probes',ww),('opponent_leaf_probes',D['unit'])]:
  for p in z[field]:assert abs(p['measured_white_pawns']-w[p['type']]/208)<.011
assert len(rows)==96 and nq==X['actual_queries']==sum(json.loads(l).get('event')=='query' for l in (R/'results/dev_aux/task350/queries.jsonl').read_bytes().splitlines());summary=[];human=(1,3,3,5,9)
for name,ep in E['endpoints'].items():
 assert ep['latent']==latent[name] and ep['weights']=={**{k:max(32,min(8192,math.floor(latent[name][k]*208+.5))) for k in 'PNBRQ'},'K':0};err=lambda w:sum(math.log((w[k]/w['P'])/h)**2 for k,h in zip('PNBRQ',human))/5;summary.append(dict(family=name,weights=ep['weights'],ratios={k:ep['weights'][k]/208 for k in 'PNBRQ'},initial_human_logMSE=err(D['initials'][name]),endpoint_human_logMSE=err(ep['weights']),bound_hits=ep['bound_hits']))
out=dict(complete=True,games=96,queries=nq,allprice_history_PV_legal_goalchecks=True,all96backwardeligibility_updates_pass=True,max_forward_backward_float_error=maxerr,total_bound_hits=hits,endpoints=summary,seconds=time.monotonic()-start,producer_seconds=X['seconds'],scope='ROOT-TD uses exactsmoothroot-modelgradient underfloatlatentparameters; roundedmaturesearchpolicy differs andisnotdifferentiated. Fixedfinitequantity/mate goal normalizedby32, notWDLprobability. All48PVleafgradientcounterexamples separatefromthisRootvariant. Humanreferenceafterallendpointsfreeze only; no selection orclippinghidden. Short96samplenegative cannotrefuteallTD/learning.')
(O/'audit.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps(out,indent=2))