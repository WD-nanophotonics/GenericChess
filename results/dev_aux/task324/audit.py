"""Independent full-replay and exact candidate/endpoint selection audit of322."""
import json,time,random,hashlib,collections,math,statistics
from pathlib import Path
from fractions import Fraction as F
import chess
R=Path.cwd();O=R/'results/dev_aux/task324'
def execute():
 O.mkdir(exist_ok=True);assert not (O/'audit.json').exists();D=json.loads((R/'results/dev_aux/task322/declaration.json').read_bytes());E=json.loads((R/'results/dev_aux/task322/endpoints.json').read_bytes());P=json.loads((R/'results/dev_aux/task322/progress.json').read_bytes());assert E['complete'] and P['status']['complete'];start=time.monotonic();pilot=json.loads((R/'results/dev_aux/task320/result.json').read_bytes())['calls'];new=[json.loads(l) for l in (R/'results/dev_aux/task322/games.jsonl').read_bytes().splitlines()];assert len(new)==P['actual_games'];cache={};queries=0;matewins=matelosses=unknown=0;groups=[]
 def key(z):return tuple(z['weights'][k] for k in 'PNBRQK'),z['root'],z['color'],z['seed']
 for gi,z in enumerate(pilot+new):
  kk=key(z);assert kk not in cache;cache[kk]=z;f=D['roots'][z['root']];b=chess.Board(f['initial_fen'])
  for u in f['history']:b.push_uci(u)
  ss={r['ply']:r['record'] for r in z['search_records']};rs={r['ply']:r for r in z['random_choices']};rng=random.Random(z['seed'])
  for ply,u in enumerate(z['actions']):
   assert not b.is_game_over(claim_draw=False);m=chess.Move.from_uci(u);assert m in b.legal_moves
   if b.turn==z['color']:
    meta=ss[ply];assert meta['root_fen']==f['initial_fen'] and meta['full_history']==[m.uci() for m in b.move_stack];parts=[line.split() for line in meta['uci_info'] if ' pv ' in line];pv=parts[-1][parts[-1].index('pv')+1:];assert pv[0]==u;c=b.copy(stack=True)
    for t in pv:assert chess.Move.from_uci(t) in c.legal_moves;c.push_uci(t)
    assert meta['nodes_limit']==1024 and meta['reported_nodes']>=0;queries+=1
   else:
    legal=sorted(b.legal_moves,key=lambda m:m.uci());ix=rng.randrange(len(legal));assert rs[ply]==dict(ply=ply,index=ix,legal_count=len(legal),move=legal[ix].uci()) and legal[ix]==m
   b.push(m)
  assert b.fen()==z['final_fen'];oo=b.outcome(claim_draw=False);kind='UNKNOWN_CUTOFF' if oo is None else oo.termination.name;sign=0 if oo is None or oo.winner is None else 1 if oo.winner==z['color'] else -1;fitness=F(49-len(z['actions']),48) if kind=='CHECKMATE' and sign==1 else F(-1) if kind=='CHECKMATE' and sign==-1 else F(0);assert kind==z['termination'] and sign==z['finite_mate_sign'] and str(fitness)==z['fitness'];assert z['table_ack']['prices']=={str(i+1):[z['weights'][k]]*2 for i,k in enumerate('PNBRQ')}
  for pr in z['leaf_probes']:assert abs(pr['measured_white_pawns']-z['weights'][pr['type']]/208)<.011
  matewins+=sign==1;matelosses+=sign==-1;unknown+=kind=='UNKNOWN_CUTOFF'
  if gi%256==0:print('Replay',gi,queries,round(time.monotonic()-start,2),flush=True)
 assert len(cache)==P['unique_cases'] and sum(len(z['search_records']) for z in new)==P['actual_queries'];journalqueries=sum(json.loads(line).get('event')=='query' for line in (R/'results/dev_aux/task322/queries.jsonl').read_bytes().splitlines());assert journalqueries==P['actual_queries']
 def records(w):return [cache[(tuple(w[k] for k in 'PNBRQK'),ri,color,seed)] for ri in range(2) for color in D['colors'] for seed in D['random_seeds']]
 def mean(zz):return sum(F(z['fitness']) for z in zz)/len(zz)
 roundchecks=[]
 for row in P['rounds']:
  allscores=[]
  for cand in row['candidates']:
   zz=records(cand['weights']);v=mean(zz);assert str(v)==cand['fitness'];allscores.append(v)
  ix=max(range(len(allscores)),key=lambda i:allscores[i]);assert row['selected']==row['candidates'][ix]['variant'] and row['weights']==row['candidates'][ix]['weights'];assert row['strict_gain']==(allscores[ix]>allscores[0]);a=records(row['starting']);b=records(row['weights']);delta=[F(bb['fitness'])-F(aa['fitness']) for aa,bb in zip(a,b)];seed_delta=[sum(delta[i] for i,z in enumerate(a) if z['seed']==seed)/4 for seed in D['random_seeds']];root_delta=[sum(delta[i] for i,z in enumerate(a) if z['root']==ri)/32 for ri in range(2)];color_delta=[sum(delta[i] for i,z in enumerate(a) if z['color']==color)/32 for color in D['colors']];roundchecks.append(dict(family=row['family'],generation=row['generation'],chosen=row['selected'],delta=str(allscores[ix]-allscores[0]),root_deltas=list(map(str,root_delta)),color_deltas=list(map(str,color_delta)),seed_deltas=list(map(str,seed_delta)),negative_seeds=sum(v<0 for v in seed_delta),positive_seeds=sum(v>0 for v in seed_delta),net_sign_delta=str(F(sum(z['finite_mate_sign'] for z in b)-sum(z['finite_mate_sign'] for z in a),64))))
 for name,v in E['endpoints'].items():
  rr=[r for r in P['rounds'] if r['family']==name];assert len(rr)==v['rounds'] and rr[-1]['weights']==v['weights'] and (not rr[-1]['strict_gain'] or len(rr)==6);zz=records(v['weights']);init=records(D['initials'][name]);groups.append(dict(family=name,initial_weights=D['initials'][name],endpoint=v,initial_speed=str(mean(init)),endpoint_speed=str(mean(zz)),initial_wins=sum(z['finite_mate_sign']==1 for z in init),endpoint_wins=sum(z['finite_mate_sign']==1 for z in zz),initial_losses=sum(z['finite_mate_sign']==-1 for z in init),endpoint_losses=sum(z['finite_mate_sign']==-1 for z in zz),initial_unknown=sum(z['termination']=='UNKNOWN_CUTOFF' for z in init),endpoint_unknown=sum(z['termination']=='UNKNOWN_CUTOFF' for z in zz)))
 # Descriptive reference is read only AFTER fixed endpoint file, never into selection.
 human=(1,3,3,5,9);descriptive=[]
 for name,v in E['endpoints'].items():
  init=D['initials'][name];w=v['weights'];error=lambda a:sum(math.log((a[k]/a['P'])/h)**2 for k,h in zip('PNBRQ',human))/5;descriptive.append(dict(family=name,initial_log_MSE=error(init),endpoint_log_MSE=error(w),endpoint_ratios={k:w[k]/w['P'] for k in 'PNBRQ'},closer=error(w)<error(init)))
 out=dict(complete=True,new_games_audited=len(new),prior_pilot_games_rechecked=len(pilot),actual_new_queries_audited=P['actual_queries'],prior_pilot_queries=queries-P['actual_queries'],total_query_history_PV_checks=queries,all_price_legal_random_history_terminal_checks=True,rounds=len(P['rounds']),groups=groups,round_checks=roundchecks,descriptive_human_reference=descriptive,aggregate_complete_games=len(new)+24,aggregate_wins=matewins,aggregate_losses=matelosses,aggregate_unknown=unknown,seconds=time.monotonic()-start,producer_seconds=P['seconds'],scope='Cachedexactsameinputs reusednotphysicalqueries. Neighbor fitness optimization is empiricalpolicysearch underfixed64cells, not confidence/causaluniversalpricelearning. Humanreference strictlypostendpoint; no negativeclipping/fitafterexposure. Seedcoupling exact Pythonrandrange legaluniformpermove; rejectionmayconsumevariablebits andshiftsfuturewithin-game RNGcoupling, independentnewseedpergameprevents crossgamestreamshift. Dotrequestedturn-indexedstreamcounterfactual isseparatefuturecontrol, historicaldataunchanged.')
 (O/'audit.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in out.items() if k not in ('round_checks','scope')},indent=2))
if __name__=='__main__':execute()