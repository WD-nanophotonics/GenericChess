"""All mature developmental replay and fixed endpoint resource contrasts."""
import json,time,math,hashlib,collections
from pathlib import Path
from fractions import Fraction as F
import chess
R=Path.cwd();O=R/'results/dev_aux/task344';O.mkdir(exist_ok=False);start=time.monotonic();datasets={};newq=0;games=0
for task in (342,345):
 D=json.loads((R/f'results/dev_aux/task{task}/declaration.json').read_bytes());X=json.loads((R/f'results/dev_aux/task{task}/result.json').read_bytes());assert X['complete'];EX=json.loads((R/'results/dev_aux/task342/execution.json').read_bytes());q=0
 for z in X['calls']:
  f=D['roots'][z['root']];b=chess.Board(f['initial_fen'])
  for u in f['history']:b.push_uci(u)
  ss={p['ply']:p for p in z['search_records']};assert len(ss)==len(z['actions'])<=24
  for ply,u in enumerate(z['actions']):
   assert not b.is_game_over(claim_draw=False);qr=ss[ply];assert qr['player']==('candidate' if b.turn==z['color'] else 'unit');meta=qr['record'];assert meta['root_fen']==f['initial_fen'] and meta['full_history']==[m.uci() for m in b.move_stack] and meta['nodes_limit']==D['node_limit'] and meta['reported_nodes']>=0;parts=[s.split() for s in meta['uci_info'] if ' pv ' in s];pv=parts[-1][parts[-1].index('pv')+1:];assert pv[0]==u;c=b.copy(stack=True)
   for t in pv:assert chess.Move.from_uci(t) in c.legal_moves;c.push_uci(t)
   assert chess.Move.from_uci(u) in b.legal_moves;b.push_uci(u);q+=1
  oo=b.outcome(claim_draw=False);kind='UNKNOWN_CUTOFF' if oo is None else oo.termination.name;sign=0 if kind!='CHECKMATE' else 1 if oo.winner==z['color'] else -1;count=lambda co:sum(len(b.pieces(k,co)) for k in range(1,6));quantity=count(z['color'])-count(not z['color']);goal=F(32*sign) if sign else F(quantity,15) if oo is None else F(0);assert (kind,sign,quantity,str(goal),b.fen())==(z['termination'],z['finite_mate_sign'],z['quantity_difference'],z['fitness'],z['final_fen'])
  for field,w in [('table_ack',z['weights']),('opponent_table_ack',EX['unit'])]:assert z[field]['prices']=={str(i+1):[w[k]]*2 for i,k in enumerate('PNBRQ')}
  for field,w in [('leaf_probes',z['weights']),('opponent_leaf_probes',EX['unit'])]:
   for p in z[field]:assert abs(p['measured_white_pawns']-w[p['type']]/208)<.011
  games+=1
 assert q==sum(json.loads(s).get('event')=='query' for s in (R/f'results/dev_aux/task{task}/queries.jsonl').read_bytes().splitlines());newq+=q;datasets['mature_'+str(D['node_limit'])]=X['calls']
N=json.loads((R/'results/dev_aux/task340/result.json').read_bytes());assert N['complete'];datasets['Native_D3']=N['rows'];D0=json.loads((R/'results/dev_aux/task338/declaration.json').read_bytes());E=json.loads((R/'results/dev_aux/task338/endpoints.json').read_bytes());summary=[];contrasts=[]
for name,rows in datasets.items():
 getname=lambda z:z.get('name',z.get('profile'))
 for profile in EX['unique_profiles']:
  rr=[z for z in rows if getname(z)==profile];assert len(rr)==16;summary.append(dict(dataset=name,profile=profile,fitness=str(sum(F(z['fitness']) for z in rr)/16),wins=sum(z['finite_mate_sign']==1 for z in rr),losses=sum(z['finite_mate_sign']==-1 for z in rr),quantity_mean=str(F(sum(z['quantity_difference'] for z in rr),16)),mate_contribution=str(F(sum(z['finite_mate_sign'] for z in rr)*32,16)),quantity_contribution=str(sum(F(z['fitness']) if z['finite_mate_sign']==0 else F(0) for z in rr)/16)))
 for family in D0['initials']:
  a={(z['root'],z['color']):z for z in rows if getname(z)==EX['aliases']['initial-'+family]};b={(z['root'],z['color']):z for z in rows if getname(z)==EX['aliases']['endpoint-'+family]};assert set(a)==set(b) and len(a)==16;delta={k:F(b[k]['fitness'])-F(a[k]['fitness']) for k in a};drops=[sum(v for k,v in delta.items() if k[0]!=ri)/14 for ri in range(8)];contrasts.append(dict(dataset=name,family=family,fitness_delta=str(sum(delta.values())/16),net_mate_delta=str(F(sum(b[k]['finite_mate_sign']-a[k]['finite_mate_sign'] for k in a),16)),rawquantity_delta=str(F(sum(b[k]['quantity_difference']-a[k]['quantity_difference'] for k in a),16)),positive_cells=sum(v>0 for v in delta.values()),negative_cells=sum(v<0 for v in delta.values()),same_trajectories=sum(a[k]['actions']==b[k]['actions'] for k in a),root_delta=[str(sum(v for k,v in delta.items() if k[0]==ri)/2) for ri in range(8)],leave_one_root_delta=list(map(str,drops)),negative_leave_one_root=sum(v<0 for v in drops),scope='Fixedallendpoints, no development/human modelselection orconfidence; singlemate±32 dominatesquantity; Nativeallqueryoracle343 separate qualification.'))
out=dict(complete=True,mature_games_checked=games,mature_queries_checked=newq,Native_games=N['actual_games'],Native_queries=N['actual_queries'],Native_value_receipt='343 independentwholeD3oracle mustpass beforeclaim exactvalues',summary=summary,contrasts=contrasts,seconds=time.monotonic()-start,scope='Samefrozen24cap/root/color/goal at1024/8192bothplayers givesresource/usefulness curve; NativeD3bothactors hasdifferentalgorithm/work/internalterminalclamp, overalldeploymentreference only, no isolatedpruningcausalclaim. Rootswerefixedbeforetraining; after342areexposeddevelopment and345cannotrestoreunexposed status. Trainingendpoints andoldfailures retained.')
(O/'audit.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps(dict(complete=True,games=games,queries=newq,contrasts=contrasts),indent=2))