"""Independent raw UCI parsing, complete history/PV/readbacks, finite-response diagnostics."""
import json,hashlib,collections,time,math
from pathlib import Path
import chess,numpy as np
R=Path.cwd();O=R/'results/dev_aux/task318';O.mkdir(exist_ok=False);start=time.monotonic();D=json.loads((R/'results/dev_aux/task317/declaration.json').read_bytes());A=json.loads((R/'results/dev_aux/task313/result.json').read_bytes());B=json.loads((R/'results/dev_aux/task317/result.json').read_bytes());assert A['complete'] and B['complete'];rows=[dict(z,variant='base') for z in A['rows']]+B['rows'];checks=[];by={}
for z in rows:
 f=next(f for f in D['roots'] if f['id']==z['root']);b=chess.Board(f['initial_fen'])
 for u in f['history']:assert chess.Move.from_uci(u) in b.legal_moves;b.push_uci(u)
 assert b.fen()==f['fen'] and z['metadata']['root_fen']==f['initial_fen'] and z['metadata']['full_history']==f['history'];actor=b.turn
 # Separate parser uses protocol positions, retaining every bounds tag rather than trusting producer score.
 lines=[s.split() for s in z['metadata']['uci_info'] if s.startswith('info depth ') and ' score ' in s and ' pv ' in s];last=lines[-1];i=last.index('score');kind=last[i+1];val=int(last[i+2]);bounds=[s for s in last if s in ('lowerbound','upperbound')];assert len(bounds)<=1;bound=bounds[0] if bounds else 'exact_report';pv=last[last.index('pv')+1:];assert z['score']['kind']==kind and z['score']['value']==val and z['score']['bound']==bound and z['score']['pv']==pv and pv[0]==z['move']
 for u in pv:assert chess.Move.from_uci(u) in b.legal_moves;b.push_uci(u)
 vec=[len(b.pieces(i+1,actor))-len(b.pieces(i+1,not actor)) for i in range(5)];ack=z['table_ack'];assert ack['alignment']==3 and ack['prices']=={str(i+1):[z['weights'][k]]*2 for i,k in enumerate('PNBRQ')}
 assert len(z['leaf_probes'])==5
 for pr in z['leaf_probes']:assert abs(pr['measured_white_pawns']-z['weights'][pr['type']]/208)<.011
 assert z['metadata']['reported_nodes']>=z['nodes_limit'];key=(z['root'],z['profile'],z['nodes_limit'],z['variant']);assert key not in by;by[key]=dict(row=z,kind=kind,val=val,bound=bound,vector=vec);checks.append(dict(root=z['root'],profile=z['profile'],limit=z['nodes_limit'],variant=z['variant'],kind=kind,bound=bound,score=val,PV_leaf_raw=sum(z['weights'][k]*v for k,v in zip('PNBRQ',vec)),PV_vector=vec,depth=z['metadata']['reported_depth'],reported_nodes=z['metadata']['reported_nodes']))
axes=[]
for f in D['roots']:
 for name in D['profiles']:
  for limit in D['node_limits']:
   base=by[f['id'],name,limit,'base']
   for ki,k in enumerate('PNBRQ'):
    minus=by[f['id'],name,limit,k+'-'];plus=by[f['id'],name,limit,k+'+'];exact=all(z['kind']=='cp' and z['bound']=='exact_report' for z in (base,minus,plus));a=dict(root=f['id'],profile=name,limit=limit,piece=k,all_cp_unbounded=exact,raw_values=[z['val'] for z in (minus,base,plus)],bounds=[z['bound'] for z in (minus,base,plus)],actions=[z['row']['move'] for z in (minus,base,plus)],depths=[z['row']['metadata']['reported_depth'] for z in (minus,base,plus)],PV_branch_prediction_cp_per_raw=base['vector'][ki]*100/208)
    if exact:a.update(positive_finite_cp_per_raw=(plus['val']-base['val'])/8,negative_finite_cp_per_raw=(base['val']-minus['val'])/8,central_cp_per_raw=(plus['val']-minus['val'])/16)
    axes.append(a)
response=[]
for name in D['profiles']:
 for limit in D['node_limits']:
  aa=[a for a in axes if a['profile']==name and a['limit']==limit];usable=[a for a in aa if a['all_cp_unbounded']];response.append(dict(profile=name,limit=limit,axes=len(aa),usable_unbounded=len(usable),bounded_axes=len(aa)-len(usable),nonzero_response=sum(a['positive_finite_cp_per_raw']!=0 or a['negative_finite_cp_per_raw']!=0 for a in usable),asymmetric_axes=sum(a['positive_finite_cp_per_raw']!=a['negative_finite_cp_per_raw'] for a in usable),action_changes=sum(len(set(a['actions']))>1 for a in aa),depth_changes=sum(len(set(a['depths']))>1 for a in aa),max_cp_step=max((max(abs(a['raw_values'][0]-a['raw_values'][1]),abs(a['raw_values'][2]-a['raw_values'][1])) for a in usable),default=None)))
pairs=[]
for f in D['roots']:
 for name in D['profiles']:
  for k in 'PNBRQ':
   aa=[next(a for a in axes if (a['root'],a['profile'],a['piece'],a['limit'])==(f['id'],name,k,l)) for l in D['node_limits']];good=all(a['all_cp_unbounded'] for a in aa);pairs.append(dict(root=f['id'],profile=name,piece=k,usable=good,central_signs=[int(np.sign(a['central_cp_per_raw'])) for a in aa] if good else None))
out=dict(complete=True,actual_new_queries=176,reused_between_tasks=18,physical_query_accounting={'313':16,'314':0,'315':2,'317':158},full_queries_checked=len(checks),bound_counts=dict(collections.Counter(z['bound'] for z in checks)),kind_counts=dict(collections.Counter(z['kind'] for z in checks)),groups=response,usable_budget_pairs=sum(x['usable'] for x in pairs),opposite_budget_response_signs=sum(x['usable'] and x['central_signs'][0]*x['central_signs'][1]<0 for x in pairs),axes=axes,budget_pairs=pairs,checks=checks,seconds=time.monotonic()-start,source_price_lifecycle='267oneprocessperprofile/opponent;269blockcreatesfreshprocessperweight, reusedunitprocessalwayssameunit208. Existingactualallpriceacks passed;315firsttimechangesweightswithinsameprocess andwascaughtbeforego. Priorclaimsnotretractedforunobservedcachebug.',scope='Finite selective search response; unbounded protocol report is NOT complete minimax certificate. Bounds excluded from numericaldifferences, no training/fit/continuousgradientclaim. Step8 priorchoice retained; nochangedroots/seeds/horizons. Fixeddenominator208/integercp quantization retainsup to~2.08rawprecisionloss; no grain16assumption since custompurematerialreturnsbeforeclassical path.')
(O/'audit.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in out.items() if k not in ('axes','budget_pairs','checks')},indent=2))