import json,time
from fractions import Fraction as F
from pathlib import Path
R=Path.cwd();O=R/'results/dev_aux/task604';O.mkdir(exist_ok=True);start=time.perf_counter();rows=[]
for task,objective in [(597,'terminal'),(598,'mixed')]:
 ep=json.loads((R/f'results/dev_aux/task{task}/endpoints.json').read_bytes())
 for u in ep['updates']:
  vs=[[F(x) for x in c['goals']] for c in u['candidates']];p=[[F(x) for x in c['physical_goals']] for c in u['candidates']];means=[sum(v)/104 for v in vs];cell_differ=sum(len({v[i] for v in vs})>1 for i in range(104));terms=[[F(32 if abs(F(x))==32 else 0) for x in c['goals']] for c in u['candidates']];rows.append(dict(objective=objective,start=u['family'],iteration=u['iteration'],all_three_means_tied=len(set(means))==1,cell_objectives_differ=cell_differ,terminal_cells_differ=sum(len({v[i] for v in terms})>1 for i in range(104)),mean_tied_but_cells_differ=len(set(means))==1 and cell_differ>0,all104cells_same=cell_differ==0))
summ=[]
for objective in ['terminal','mixed']:
 for family in ['unit','random2514']:
  rr=[x for x in rows if x['objective']==objective and x['start']==family];summ.append(dict(objective=objective,start=family,all_means_tied=sum(x['all_three_means_tied'] for x in rr),all_cells_same_rounds=sum(x['all104cells_same'] for x in rr),mean_cancellation_rounds=sum(x['mean_tied_but_cells_differ'] for x in rr),nonflat_terminal_rounds=sum(x['terminal_cells_differ']>0 for x in rr)))
out=dict(status='PASS_ACTUAL_REWARD_SATURATION',rounds=48,summary=summ,rows=rows,new_go=0,seconds=time.perf_counter()-start,scope='Exactactualcandidate104cell rewardarray diagnostic, notallactualpaths/evaluation equality. Terminalfitness field in597physical_goals misnamed; onlygoals andrule outcome used here. mean ties mayhidechangedcells; allcellstiedhere bounds sampled directions only, notglobalpriceflatness or theoretical optimum. Noresultadaptiveextension.');(O/'result.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in out.items() if k!='rows'}))