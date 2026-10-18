"""Saved TRAIN loss/cost and common first-candidate-root residuals, no refit."""
from pathlib import Path
from collections import defaultdict
from math import tanh
import json,sys
import chess
D=Path('results/dev_aux/task2571');T=Path('results/dev_aux/task2568')
def run():
 models=json.loads((D/'binding-audit.json').read_text())['checks'];train=[json.loads(l)for l in(T/'games.jsonl').open()];saved=[]
 for m in models:
  method=m['method'].split('@')[0];gs=[g for g in train if g['seed']==m['seed']and g['method']==method and g['total_nodes']<=m['actual_nodes']];terms=sum(g['stats']['samples']for g in gs);loss=sum(g['stats']['samples']*g['stats']['loss']for g in gs if g['stats']['samples']and g['stats']['loss']is not None)
  saved.append(dict(seed=m['seed'],method=method,nominal_nodes=m['nominal'],actual_nodes=m['actual_nodes'],closed_episodes=len(gs),td_terms=terms,weighted_changing_data_loss=None if not terms else loss/terms,actual_terminal=sum(g['outcome']is not None for g in gs),unknown=sum(g['outcome']is None for g in gs)))
 first={};shared={};rows=[]
 for q in map(json.loads,(D/'eval-queries.jsonl').open()):
  slot=tuple(q['slot']);color=slot[3]
  if q['actor']!=color or slot in first:continue
  first[slot]=q;key=(slot[1],slot[2],color,slot[5]);record=q['record_before']
  if key in shared:assert shared[key]==record
  else:shared[key]=record
  board=chess.Board(record['initial'])
  for u in record['moves']:board.push_uci(u)
  phi=[len(board.pieces(t,chess.WHITE))-len(board.pieces(t,chess.BLACK))for t in(1,2,3,4,5)];static=sum(w*x for w,x in zip(q['weights'],phi));residual=None if not q['complete']else(tanh(q['value']/10)-tanh(static/10))**2/2
  rows.append(dict(slot=list(slot),phi=phi,complete=q['complete'],static=static,search_value=q['value'],half_squared_root_bootstrap_residual=residual,root_material_zero=all(x==0 for x in phi),pv_terminal=q['pv_terminal']))
 out=dict(status='PASS_COMMON_FIRST_CANDIDATE_ROOT_BINDING',training_loss_cost_curves=saved,first_candidate_rows=rows,shared_roots=len(shared),first_queries=len(first),scope='TRAIN loss uses savedchangingtrajectories, notheldoutloss andnot evidenceofstrength. EVALfirstcandidate root isidenticalacrossmodels foreachseed/family/role/foe, checkedfullhistory. Rootbootstrap residual isdiagnostic only, notactualWLD/probabilitycalibration orsearch-targetaccuracy. UNKNOWNqueries keptwithouttargets, no newsearch/train/refit.')
 (D/'loss-diagnostics.json').write_text(json.dumps(out,indent=2));print(json.dumps(dict(status=out['status'],train_cost_points=len(saved),shared_roots=len(shared),first_queries=len(first),zero_material_first_roots=sum(x['root_material_zero']for x in rows))))
if __name__=='__main__':run()
