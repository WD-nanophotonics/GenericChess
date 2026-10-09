"""Changed premise: count-to-any saturation under the SAME default source law.
Rule-only diagnostic statistic, not a price/profile change. Fixed default density
points/weights; all owners/sources/types,128 independent full layouts per density
in each of two fixed RNG replicates. Share layouts across types, force source
occupied by self. Actual supported projected path predicates, not legality,
promotion, hand service or WDL. No sample-label fitting; old routes are exposed.
Question: does saturation alone remove fixed-ranking loss on the old complete
immediate task, or does default source law still dominate? Compare both replicate
orders without selecting the favorable one. Max60seconds per rule, no autoextend.
"""
from pathlib import Path
import json,sys,hashlib,random,time,datetime
from fractions import Fraction as F
root=Path.cwd();sys.path[:0]=[str(root),str(root/'.local_agent/finite-law-20261009')]
from finite_law import collect
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.ai.evaluation.config import EvaluationConfig
from scripts.research_record import write_record
p=Path(__file__).parent;out=p/'any-capture-probe.json';assert not out.exists()
declaration=dict(scope=__doc__,at=datetime.datetime.now(datetime.timezone.utc).isoformat(),producer_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),replicate_seeds=[20261009,20261010],layouts_per_density=128,comparison='all8existing immediate task rules, no subset or retuning')
write_record(p/'any-capture-declaration.json',declaration)
report=dict(scope=__doc__,declaration_sha256=hashlib.sha256((p/'any-capture-declaration.json').read_bytes()).hexdigest(),rules=[],complete=False)
task=json.loads((p/'pair-audit.json').read_bytes())
def mask(values):return sum(1<<i for i in values)
for source in ('.local_agent/generated6-20261008/coverage.json','.local_agent/generated8-20261008/transfer.json'):
 for old in json.loads(Path(source).read_bytes())['cases']:
  start=time.monotonic();c=compile_ruleset_for_execution(ruleset_from_dict(old['rules']));cfg=EvaluationConfig();area=c.board_size**2;types=sorted(t.type_id for t in c.piece_types if not t.is_anchor)
  edges={t:[[(target,[(mask(cl),mask(cells),k) for cl,cells,k in events]) for target,events in bucket.items()] for bucket in collect(c,c.ir,t,cfg)[0]['target_enemy']] for t in types}
  row=dict(seed=old['seed'],replicates=[],complete=False);report['rules'].append(row)
  try:
   for rngseed in declaration['replicate_seeds']:
    rng=random.Random(rngseed);curves=[]
    for rho in cfg.density_points:
     sums={t:dict(count=0,any=0) for t in types}
     for sample in range(128):
      occupied=0;enemy=[0,0]
      for i in range(area):
       if rng.random()<rho:
        occupied|=1<<i;owner=rng.randrange(2);enemy[1-owner]|=1<<i
      for index in range(2*area):
       owner,src=divmod(index,area);occ=occupied&~(1<<src);foes=enemy[owner]&~(1<<src)
       for t in types:
        count=sum(bool(foes&(1<<target)) and any(not occ&cl and (k is None or (occ&cells).bit_count()==k) for cl,cells,k in events) for target,events in edges[t][index])
        sums[t]['count']+=count;sums[t]['any']+=bool(count)
      if time.monotonic()-start>60:raise RuntimeError('declared60sec rule checkpoint')
     curves.append(dict(density=rho,mean={t:{k:F(v,128*2*area) for k,v in vals.items()} for t,vals in sums.items()}))
    values={t:sum((F(str(w))*v['mean'][t]['any'] for w,v in zip(cfg.density_weights,curves)),F()) for t in types}
    original=next(x for x in task['rules'] if x['seed']==old['seed']);loss=F()
    for pair in original['pairs']:
     a,b=pair['pair'];bg=pair['backgrounds'];ma=sum((F(x['mean_a']) for x in bg),F())/17;mb=sum((F(x['mean_b']) for x in bg),F())/17;oracle=sum((F(x['oracle']) for x in bg),F())/17
     loss+=oracle-(ma if values[a]>values[b] else mb if values[b]>values[a] else (ma+mb)/2)
    fixed=sum((F(x['losses']['semantic_v3']) for x in original['pairs']),F())/len(original['pairs'])
    row['replicates'].append(dict(rng_seed=rngseed,values=values,order=sorted(types,key=lambda t:(-values[t],t)),curves=curves,mean_pair_loss=loss/len(original['pairs']),loss_minus_current=loss/len(original['pairs'])-fixed))
   row['complete']=True
  except Exception as exc:row['failure']=dict(kind=type(exc).__name__,message=str(exc))
  row['seconds']=time.monotonic()-start;write_record(out,report);print(old['seed'],row['complete'],[(r['order'],str(r['loss_minus_current'])) for r in row['replicates']],row['seconds'],flush=True)
report['complete']=all(r['complete'] for r in report['rules']);write_record(out,report)
