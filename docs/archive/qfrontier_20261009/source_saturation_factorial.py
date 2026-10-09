"""Adaptive diagnostic separating source weights from capture saturation.
Four statistics: uniform source count/any and initial ordinary-slot source
count/any, same default density law and shared128layouts per density in two
fixed RNG replicates. No task labels define a coefficient or source weight.
All8old rules/routes/all pair losses/zeros retained. Source-template assumption
is an explicit diagnostic, not uniquely rule-given context law or replacement.
Old rare-bridge and template-source failures remain valid. No product changes.
Predeclared question: does the previous saturation failure chiefly remain when
source weights change, or is this a useful concrete assumption to investigate?
Cost60seconds/rule; no new trajectories/actions/fit or automatic extension.
"""
from pathlib import Path
import json,sys,hashlib,random,time,datetime
from fractions import Fraction as F
root=Path.cwd();sys.path[:0]=[str(root),str(root/'.local_agent/finite-law-20261009')]
from finite_law import collect
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.session.session import GameSession
from generic_chess.ai.evaluation.config import EvaluationConfig
from scripts.research_record import write_record
p=Path(__file__).parent;out=p/'source-saturation-factorial.json';assert not out.exists()
decl=dict(scope=__doc__,producer_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),at=datetime.datetime.now(datetime.timezone.utc).isoformat(),rng_seeds=[20261009,20261010],layouts_per_density=128,inputs={n:hashlib.sha256(Path(n).read_bytes()).hexdigest() for n in ('.local_agent/generated6-20261008/coverage.json','.local_agent/generated8-20261008/transfer.json',str(p/'pair-audit.json'))})
write_record(p/'source-saturation-declaration.json',decl)
report=dict(scope=__doc__,declaration_sha256=hashlib.sha256((p/'source-saturation-declaration.json').read_bytes()).hexdigest(),rules=[],complete=False)
task=json.loads((p/'pair-audit.json').read_bytes());prior=json.loads((p/'any-capture-probe.json').read_bytes())
def mask(xs):return sum(1<<x for x in xs)
for filename in ('.local_agent/generated6-20261008/coverage.json','.local_agent/generated8-20261008/transfer.json'):
 for case in json.loads(Path(filename).read_bytes())['cases']:
  start=time.monotonic();c=compile_ruleset_for_execution(ruleset_from_dict(case['rules']));cfg=EvaluationConfig();area=c.board_size**2;types=sorted(t.type_id for t in c.piece_types if not t.is_anchor)
  board=GameSession(c).state.position.board;tpl={piece.owner*area+i for i,piece in enumerate(board) if piece and piece.current_type_id in types};assert tpl
  edges={t:[[(target,[(mask(cl),mask(cells),k) for cl,cells,k in events]) for target,events in bucket.items()] for bucket in collect(c,c.ir,t,cfg)[0]['target_enemy']] for t in types}
  row=dict(seed=case['seed'],template_sources=sorted(tpl),replicates=[],complete=False);report['rules'].append(row)
  try:
   for seed in decl['rng_seeds']:
    rng=random.Random(seed);curves=[]
    for rho in cfg.density_points:
     sums={t:{k:0 for k in ('uniform_count','uniform_any','template_count','template_any')} for t in types}
     for sample in range(128):
      occupied=0;enemy=[0,0]
      for i in range(area):
       if rng.random()<rho:occupied|=1<<i;owner=rng.randrange(2);enemy[1-owner]|=1<<i
      for index in range(2*area):
       owner,src=divmod(index,area);occ=occupied&~(1<<src);foes=enemy[owner]&~(1<<src)
       for t in types:
        count=sum(bool(foes&(1<<target)) and any(not occ&cl and (k is None or (occ&cells).bit_count()==k) for cl,cells,k in events) for target,events in edges[t][index])
        sums[t]['uniform_count']+=count;sums[t]['uniform_any']+=bool(count)
        if index in tpl:sums[t]['template_count']+=count;sums[t]['template_any']+=bool(count)
      if time.monotonic()-start>60:raise RuntimeError('declared60second rule checkpoint')
     curves.append(dict(density=rho,values={t:{k:F(v,128*(len(tpl) if k.startswith('template') else 2*area)) for k,v in vals.items()} for t,vals in sums.items()}))
    original=next(r for r in task['rules'] if r['seed']==case['seed']);methods={}
    for method in ('uniform_count','uniform_any','template_count','template_any'):
     values={t:sum((F(str(w))*r['values'][t][method] for w,r in zip(cfg.density_weights,curves)),F()) for t in types};loss=F()
     for pair in original['pairs']:
      a,b=pair['pair'];bg=pair['backgrounds'];means={t:sum((F(x[k]) for x in bg),F())/17 for t,k in ((a,'mean_a'),(b,'mean_b'))};oracle=sum((F(x['oracle']) for x in bg),F())/17
      loss+=oracle-(means[a] if values[a]>values[b] else means[b] if values[b]>values[a] else (means[a]+means[b])/2)
     fixed=sum((F(r['losses']['semantic_v3']) for r in original['pairs']),F())/len(original['pairs'])
     methods[method]=dict(values=values,order=sorted(types,key=lambda t:(-values[t],t)),loss_minus_current=loss/len(original['pairs'])-fixed)
    old=next(r for r in prior['rules'] if r['seed']==case['seed'])['replicates'][decl['rng_seeds'].index(seed)]
    assert methods['uniform_any']['values']=={t:F(v) for t,v in old['values'].items()}
    row['replicates'].append(dict(seed=seed,methods=methods,curves=curves))
   row['complete']=True
  except Exception as exc:row['failure']=dict(kind=type(exc).__name__,message=str(exc))
  row['seconds']=time.monotonic()-start;write_record(out,report);print(case['seed'],row['complete'],[{n:str(v['loss_minus_current']) for n,v in r['methods'].items()} for r in row['replicates']],flush=True)
report['complete']=all(r['complete'] for r in report['rules']);write_record(out,report)
