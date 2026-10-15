"""Actual-WL learning audit, family uncertainty and offline optimizer-cost replay."""
from pathlib import Path
from collections import Counter
import json,random,time
from results.dev_aux.task1928.audit import audit,lines,read
from results.dev_aux.task1931.audit import profile
O=Path('results/dev_aux/task1945')
def effect(rows,selected,opp=None,phase='DEV'):
 gs=[g for g in rows if g['phase']==phase and (opp is None or g.get('opponent_nodes')==opp)];ids=sorted({g['family'] for g in gs});ix={(g['family'],g['candidate_side'],g['ratio']):g for g in gs};deltas=[];bounds=[];roles=Counter();trans=Counter()
 for family in ids:
  ds=[]
  for role in (0,1):
   a,b=ix[family,role,1.],ix[family,role,selected];d=b['finite_event_score']-a['finite_event_score'];ds.append(d);roles[role]+=d;trans[a['outcome']+'->'+b['outcome']]+=1
   if a['slot']==b['slot']:bounds.append((0,0))
   else:bounds.append(((b['finite_event_score'] if b['outcome']!='UNKNOWN' else -1)-(a['finite_event_score'] if a['outcome']!='UNKNOWN' else 1),(b['finite_event_score'] if b['outcome']!='UNKNOWN' else 1)-(a['finite_event_score'] if a['outcome']!='UNKNOWN' else -1)))
  deltas.append(sum(ds)/2)
 rng=random.Random(20261016641945);n=len(ids);boots=sorted(sum(rng.choices(deltas,k=n))/n for _ in range(20000))
 return dict(mean=sum(deltas)/n,families=n,family_deltas=deltas,family95=[boots[500],boots[19499]],nonzero_families=sum(d!=0 for d in deltas),role_means={s:v/n for s,v in roles.items()},transitions=dict(trans),unknown_ultimate_extreme_bounds=[sum(v[j] for v in bounds)/(2*n) for j in (0,1)],scope='FiniteactualW-L budgetedpolicy; UNKNOWN separate, not infiniteWDL. Sharedfamilies, unadjusteddescriptivefamilybootstrap, no price choice fromtheseeffects.')
def run():
 beg=time.perf_counter();folder=Path('results/dev_aux/task1939');plan=read(folder/'run-plan.json');sel=read(folder/'selection-before-dev.json');rows=lines(folder/'games.jsonl');base=audit(folder);pr=profile(folder);chosen=sel['selected'];grid=plan['prices'];scores={r:sum(g['finite_event_score'] for g in rows if g['phase']=='TRAIN' and g['ratio']==r) for r in grid};assert chosen==min(scores,key=lambda r:(-scores[r],r)) and {float(k):v for k,v in sel['scores'].items()}==scores
 cells=[]
 for phase in ('TRAIN','DEV'):
  for ratio in grid:
   gs=[g for g in rows if g['phase']==phase and g['ratio']==ratio];assert len(gs)==32;cells.append(dict(phase=phase,ratio=ratio,outcomes=dict(Counter(g['outcome'] for g in gs)),net=sum(g['finite_event_score'] for g in gs),seconds=sum(g['seconds'] for g in gs)))
 # Descriptive TRAIN-only stability, no new selected price or games.
 train=[g for g in rows if g['phase']=='TRAIN'];family_values={f:{r:sum(g['finite_event_score'] for g in train if g['family']==f and g['ratio']==r) for r in grid} for f in range(16)}
 rng=random.Random(20261016641945);bootstrap_select=Counter()
 for _ in range(10000):
  draw=rng.choices(range(16),k=16);ss={r:sum(family_values[f][r] for f in draw) for r in grid};bootstrap_select[min(ss,key=lambda r:(-ss[r],r))]+=1
 lofo={f:min(grid,key=lambda r:(-(scores[r]-family_values[f][r]),r)) for f in range(16)}
 # Offline exact strict-adjacent optimizer replay on paid TRAIN fitness table.
 optimizers=[];costs={r:sum(g['seconds'] for g in train if g['ratio']==r) for r in grid}
 for initial in grid:
  current=initial;path=[current];queried=set()
  while True:
   j=grid.index(current);neighbors=grid[max(0,j-1):min(len(grid),j+2)];queried.update(neighbors);better=[r for r in neighbors if scores[r]>scores[current]]
   if not better:break
   current=min(better,key=lambda r:(-scores[r],r));path.append(current)
  assert sel['strict_adjacent_paths'][str(initial)]==path
  optimizers.append(dict(initial=initial,path=path,endpoint=current,train_regret_net=max(scores.values())-scores[current],distinct_fitness_queries=len(queried),paid_game_equivalents=len(queried)*32,paid_cell_seconds=sum(costs[r] for r in queried),scope='Offline table replay only; not new independent training, adaptive execution/runtime or general speedup estimate. Plateau-stopping can miss strictglobalbest.'))
 out=dict(status='PASS_832_PHYSICAL_GAMES_AND_TRAIN_LOCK',audit=base,profiles=pr,selected=chosen,cells=cells,dev_selected_minus_unit=effect(rows,chosen),train_global_optima=[r for r in grid if scores[r]==max(scores.values())],train_nonflat_families=sum(len(set(x.values()))>1 for x in family_values.values()),train_family_vectors=family_values,train_bootstrap_selection_counts=dict(bootstrap_select),train_lofo_selected=lofo,offline_adjacent_optimizers=optimizers,scope='Fresh1938law first16TRAIN/last16DEV, not DESIGNroots1933. ActualW-L alone. Common13starts share samefitnesssurface; bootstrap/LOFO reuseTRAIN, notfreshreplicates or selectors. No humanfit/DEVchoice.',seconds=time.perf_counter()-beg)
 (O/'result.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps({k:out[k] for k in ['status','selected','dev_selected_minus_unit','train_nonflat_families','train_bootstrap_selection_counts','train_lofo_selected','seconds']}))
if __name__=='__main__':run()
