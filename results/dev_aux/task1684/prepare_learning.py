from pathlib import Path
import ast
R=Path.cwd();O=R/'results/dev_aux/task1684'
s=(R/'results/dev_aux/task1675/learn.py').read_text(encoding='utf-8-sig').replace('task1678','task1686').replace('task1677/plan.json','task1685/plan.json')
s=s.replace("  if f['phase']!=phase:continue","  if (phase=='TRAIN' and f['phase']=='DEV') or (phase=='DEV' and f['phase']!='DEV'):continue")
s=s.replace("BASE=tuple(plan['baseline'])","""BASE=tuple(plan['baseline'])
for x in (R/'results/dev_aux/task1678/choices.jsonl').open():
 old=json.loads(x);s0=tuple(old['state']);p0=tuple(old['price']);assert old['fen']==T.fen(s0) and old['move'] in dict(T.moves(s0));cache[p0,s0]=old['move']
paths=[];evaluations={}
def neighbors(p):
 out=set()
 for i,bounds in [(0,plan['pricebox_R']),(3,plan['pricebox_P'])]:
  for multiplier in (.5,2):
   q=list(p);q[i]=max(bounds[0],min(bounds[1],18*round(p[i]*multiplier/18)));q=tuple(q)
   if q!=p:out.add(q)
 return sorted(out)
def score(p):
 if p not in evaluations:
  z=evaluate(p,'TRAIN');TRAIN.append(z);evaluations[p]=z['finite_net']
 return evaluations[p]
""")
a=s.index(" for phase in ['TRAIN1','TRAIN2']:");b=s.index('except BaseException',a)
s=s[:a]+""" for number,initial in enumerate(plan['initials']):
  p=tuple(initial);score(p);steps=[];accepted=[p];ending='ROUND_CAP'
  for round_index in range(plan['round_cap']):
   direct=neighbors(p)
   for q in direct:score(q)
   best=min(direct+[p],key=lambda q:(-score(q),q));examined=list(direct);bridge=None
   if score(best)<=score(p):
    neutral=[q for q in direct if score(q)==score(p)]
    frontier_candidates=[]
    for mid in neutral[:plan['plateau_frontiers']]:
     for q in neighbors(mid):score(q);examined.append(q);frontier_candidates.append((q,mid))
    if frontier_candidates:
     q,mid=min(frontier_candidates,key=lambda z:(-score(z[0]),z[0],z[1]))
     if score(q)>score(p):best=q;bridge=mid
   steps.append({'round':round_index,'current':p,'score':score(p),'examined':sorted(set(examined)),'best':best,'best_score':score(best),'neutral_bridge':bridge})
   (O/f'path{number}_partial.json').write_text(json.dumps({'initial':initial,'steps':steps,'accepted':accepted},indent=2))
   if score(best)<=score(p):ending='NO_IMPROVEMENT_AFTER_BOUNDED_NEUTRAL_FRONTIERS';break
   if bridge is not None:accepted.append(bridge)
   p=best;accepted.append(p)
  paths.append({'initial':initial,'endpoint':p,'initial_score':score(tuple(initial)),'endpoint_score':score(p),'steps':steps,'accepted':accepted,'ending':ending})
 selected={f'PATH{i}':tuple(x['endpoint']) for i,x in enumerate(paths)};selected['PRIMARY']=min(selected.values(),key=lambda q:(-score(q),q));(O/'selection.json').write_text(json.dumps({'selected':selected,'paths':paths,'evaluations':{str(k):v for k,v in evaluations.items()}},indent=2))
 for price in sorted(set(selected.values())|{BASE}|set(map(tuple,plan['initials']))):DEV.append(evaluate(price,'DEV'))
"""+s[b:]
s=s.replace("'selected':selected,'TRAIN':TRAIN","'selected':selected,'paths':paths,'TRAIN':TRAIN");(O/'learn.py').write_text(s,encoding='utf8');ast.parse(s)
