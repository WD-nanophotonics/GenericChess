import json,sys,time,collections,hashlib
from pathlib import Path
from fractions import Fraction
R=Path.cwd();O=R/'results/dev_aux/task463';O.mkdir(exist_ok=True);tasks=[int(x) for x in sys.argv[1:]] or [432,433,439,440,449,450];groups={};t0=time.perf_counter();games=0
for task in tasks:
 ep=json.loads((R/f'results/dev_aux/task{task}/endpoints.json').read_text(encoding='utf-8'));arm=ep['arm']
 for line in (R/f'results/dev_aux/task{task}/games.jsonl').open(encoding='utf-8'):
  g=json.loads(line);assert g['root']['phase']=='train';games+=1;qs=g['queries'];budget=qs[0]['nodes_limit'] if qs else 1024
  key=(task,g['root']['seed'],g['color'],budget);r=groups.setdefault(key,dict(task=task,arm=arm,root_seed=g['root']['seed'],color=g['color'],nodes=budget,first_input=None,first_moves=set(),weights=set(),goals=set(),terminals=set(),win_terminal_plies=set(),trajectories=set(),actual_go=0,games=0))
  if qs:
   q=qs[0];assert q['player']=='candidate';inp=(q['initial_sfen'],tuple(q['history']),q['nodes_limit'])
   if r['first_input'] is None:r['first_input']=inp
   else:assert r['first_input']==inp,(key,inp,r['first_input'])
   r['first_moves'].add(q['bestmove'])
  r['weights'].add(tuple(g['weights']));r['goals'].add(g['goal']);term=g['termination'];state='cap' if term['kind']=='cap24' else 'draw' if term['winner'] is None else 'win' if term['winner']==g['color'] else 'loss';r['terminals'].add(state)
  if state=='win':r['win_terminal_plies'].add(len(g['actions']))
  r['trajectories'].add(tuple(a['move'] for a in g['actions']));r['actual_go']+=len(qs);r['games']+=1
rows=[]
for r in groups.values():
 row={k:v for k,v in r.items() if k not in ['first_input','first_moves','weights','goals','terminals','win_terminal_plies','trajectories']};row.update(distinct_actual_prices=len(r['weights']),distinct_first_candidate_moves=len(r['first_moves']),first_candidate_input_equal_across_prices=True,distinct_original_goals=len(r['goals']),original_goals=sorted(r['goals'],key=Fraction),observed_terminal_states=sorted(r['terminals']),all_tested_prices_win=r['terminals']=={'win'},distinct_win_terminal_plies=sorted(r['win_terminal_plies']),distinct_full_action_trajectories=len(r['trajectories']),all_observed_game_goals_invariant=len(r['goals'])==1)
 if r['first_input'] is not None:row['first_input_sha256']=hashlib.sha256(json.dumps(r['first_input']).encode()).hexdigest()
 rows.append(row)
summaries=[]
for task in tasks:
 rr=[r for r in rows if r['task']==task];summaries.append(dict(task=task,root_color_cells=len(rr),goalinvariant_cells=sum(r['all_observed_game_goals_invariant'] for r in rr),allpricewin_cells=sum(r['all_tested_prices_win'] for r in rr),first_move_invariant_cells=sum(r['distinct_first_candidate_moves']<=1 for r in rr),price_sensitive_first_move_but_goal_invariant=sum(r['distinct_first_candidate_moves']>1 and r['all_observed_game_goals_invariant'] for r in rr),allpricewin_with_speed_response=sum(r['all_tested_prices_win'] and len(r['distinct_win_terminal_plies'])>1 for r in rr)))
out=dict(status='PASS_DERIVATION',summaries=summaries,rows=rows,existing_fitgames=games,new_go=0,seconds=time.perf_counter()-t0,scope='ALLactuallytestedpriceprobes, firstcandidate input provenfixed withinroot/color/budget under indexedrandom. Differentfirstmove is searchresponse notgain; invariantfirstmove doesnotprove laterinvariance. Flatobservedgoal orallwin cells are finitediscrimination/saturation evidence, notglobalparameteridentifiability orhumanvalue/expectedrandomWDL proof.');(O/('result_'+('_'.join(map(str,tasks)))+'.json')).write_text(json.dumps(out,indent=2),encoding='utf-8');print({k:v for k,v in out.items() if k!='rows'})
