from pathlib import Path
import json,collections
R=Path.cwd();O=R/'results/dev_aux/task1381';O.mkdir()
sources=[(1329,'B'),(1346,'B'),(1357,'P720'),(1361,'P720'),(1370,'P720')]
rows=[];total=0
for n,arm in sources:
 gs=[json.loads(v) for v in (R/f'results/dev_aux/task{n}/games.jsonl').read_text().splitlines() if json.loads(v)['arm']==arm and json.loads(v)['opponent']=='unit_search']
 seen={};pairs=[]
 for g in gs:seen.setdefault(g['root']['seed'],{})[g['color']]=g
 for seed,p in seen.items():
  a,b=p[False],p[True]
  assert a['actions']==b['actions'] and a['final_fen']==b['final_fen'] and a['termination']==b['termination']
  assert ((a['label']=='W')-(a['label']=='L'))+((b['label']=='W')-(b['label']=='L'))==0
  assert all(q['weights']==q['native_weights'] and q['weights']['R']==720 for g in p.values() for q in g['queries'])
  pairs.append(dict(seed=seed,labels=[a['label'],b['label']],plies=len(a['actions']),go_to_remove_if_future_single_physical_game=len(b['queries'])))
 total+=len(pairs);rows.append(dict(source=n,pairs=len(pairs),all_trajectories_exact=True,possible_saved_go=sum(p['go_to_remove_if_future_single_physical_game'] for p in pairs),cases=pairs))
out=dict(status='PASS_MATCHED_IDENTICAL_POLICY_SELFPLAY_COLORPAIR_SYMMETRY',pairs=total,rows=rows,new_go=0,scope='Existing physicaltwo games bothretained. Supports future predeclared onephysical selfplaybaseline with two perspective labels and explicit derived rows; not deletions or retrospectively loweredcost; randomopponent noteligible, nonuniform candidate noteligible. Exact cancellation of colorpair W-L not universal practicalskill.')
(O/'result.json').write_text(json.dumps(out,indent=2));print('SYMMETRY',total,'savedfuturego',sum(r['possible_saved_go'] for r in rows))
