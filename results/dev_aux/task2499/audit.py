"""Closed game/curve/source audit, no training or extra games."""
from pathlib import Path
from collections import Counter
import json,hashlib,math,chess
OUT=Path('results/dev_aux/task2499')
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def rows(p):return [json.loads(x)for x in Path(p).read_text(encoding='utf-8-sig').splitlines()]
def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def run():
 studies=[];all_plies=0
 for task in(2492,2495,2497):
  root=Path(f'results/dev_aux/task{task}');done=read(root/'result.json');curves=rows(root/'curves.jsonl');games=rows(root/'games.jsonl');summary=[]
  for g in games:
   b=chess.Board(g['record']['initial'])
   for u in g['record']['moves']:
    m=chess.Move.from_uci(u);assert m in b.legal_moves;b.push(m);all_plies+=1
   assert b.fen()==g['record']['fen'];o=b.outcome(claim_draw=True);v=None if o is None else 0 if o.winner is None else 1 if o.winner else-1;assert v==g['outcome']
  for arm in done['arms']:
   rr=[r for r in curves if r['seed']==arm['seed']and r['method']==arm['method']];gg=[g for g in games if g['seed']==arm['seed']and g['method']==arm['method']];w=arm['initial'];losses=[]
   for r in rr:
    if 'before'in r:assert r['before']==w
    w=r['weights'];assert w[0]==1 and all(map(math.isfinite,w))
    if r.get('loss')is not None:losses.append(r['loss']);assert r['loss']>=0 and math.isfinite(r['loss'])
   assert w==arm['weights'];assert sum(g['nodes']for g in gg)==arm['nodes']
   terminal_rows=[r for r in rr if r.get('event')=='terminal_or_censor'];summary.append(dict(seed=arm['seed'],method=arm['method'],initial=arm['initial'],final=w,games=len(gg),unique_full_records=len({json.dumps(g['record'],sort_keys=True)for g in gg}),outcomes=dict(Counter('U'if g['outcome']is None else'D'if g['outcome']==0 else'W'if g['outcome']==1 else'L'for g in gg)),searches=arm['search_updates'],samples=arm['training_samples'],nonzero_updates=arm['nonzero_update_steps'],nodes=arm['nodes'],seconds=arm['seconds'],final_terminal_credit_nonzero=sum(r.get('terminal_credit_l1',0)>0 for r in terminal_rows),curve_points=[dict(nodes=r['nodes'],weights=r['weights'],loss=r.get('loss'))for r in rr if 'event'in r]))
  studies.append(dict(task=task,arms=summary,games=len(games)))
 evaluations=[]
 for task in(2493,2496):
  root=Path(f'results/dev_aux/task{task}');rr=rows(root/'games.jsonl');done=read(root/'result.json');assert len(rr)==done['actual']==done['expected'];paired={}
  for g in rr:
   b=chess.Board(g['record']['initial'])
   for u in g['record']['moves']:
    m=chess.Move.from_uci(u);assert m in b.legal_moves;b.push(m);all_plies+=1
   assert b.fen()==g['record']['fen'];o=b.outcome(claim_draw=True);v=None if o is None else 0 if o.winner is None else 1 if o.winner else-1;assert g['reward']==(None if v is None else v*(1 if g['color']==0 else-1));key=(g['seed'],g['method'],g['prefix_seed'],g['color']);paired.setdefault(key,{})[g['treatment']]=g
  contrasts=[]
  for key,pair in paired.items():
   assert set(pair)=={'initial','learned'};a,b=pair['initial'],pair['learned'];assert a['initial_record']==b['initial_record'];av,bv=a['reward'],b['reward'];al,au=(-1,1)if av is None else(av,av);bl,bu=(-1,1)if bv is None else(bv,bv)
   contrasts.append(dict(key=key,baseline=av,learned=bv,difference=None if av is None or bv is None else bv-av,lower=bl-au,upper=bu-al,same_record=a['record']==b['record']))
  evaluations.append(dict(task=task,contrasts=contrasts,summary=done['results']))
 original=read('results/dev_aux/task2492/started.json')['sources'];overlays={}
 for name,h in original.items():
  p=Path(name);actual=p
  if digest(p)!=h:
   actual=p.with_name('executed_smoke_v1_'+p.name+'.txt');assert actual.exists()and digest(actual)==h;overlays[name]=str(actual).replace(chr(92),'/')
 for n,h in read('results/dev_aux/task2495/execution-dependencies.json')['files'].items():assert digest(n)==h
 for n,h in read('results/dev_aux/task2497/plan.json')['pins'].items():assert digest(n)==h
 output=dict(status='PASS_ALL_CLOSED_LEARNING_TRAJECTORIES_CURVES_AND_EXECUTION_VERSIONS',studies=studies,evaluations=evaluations,all_legal_plies=all_plies,original_execution_overlays=overlays,claims='Same library rules replay, NOT independent engine strength. U censored. No human prices, method/seed selection, or universal convergence claim. Episode final terminal residuals may be0 because full-depth search already predicted true mate/draw; retained eligibility verified by independent forward-sum and actual short-trajectory tests.')
 (OUT/'result.json').write_text(json.dumps(output,indent=2));print(json.dumps({k:v for k,v in output.items()if k not in('studies','evaluations')}))
if __name__=='__main__':run()
