from pathlib import Path
from fractions import Fraction as F
import json,collections
R=Path.cwd();O=R/'results/dev_aux/task1300';O.mkdir(exist_ok=False)
D=json.loads((R/'results/dev_aux/task1299/plan.json').read_bytes());specs=json.loads((R/'results/dev_aux/task1251/plan.json').read_bytes())['roots']
mat=json.loads((R/'results/dev_aux/task1275/result.json').read_bytes());ora=json.loads((R/'results/dev_aux/task1266/result.json').read_bytes())
key=lambda g:(g['root']['seed'],g['root']['variant'],g['color']);mk={(v['seed'],v['variant']):v for v in mat['rows']};ok={(v['seed'],v['variant']):v for v in ora['rows']}
def value(q,r):return F(q['terminal']*1000000) if 'terminal' in q else q['R']*r+q['N']
gs={}
for n in [1243,1253,1269]:
 pp=R/f'results/dev_aux/task{n}/result.json';assert json.loads(pp.read_bytes())['complete']
 gs[n]=[json.loads(v) for v in pp.with_name('games.jsonl').read_text().splitlines()]
rows=[];tot=collections.Counter()
for sp in specs:
 root=sp['root'];k=(root['seed'],root['variant']);mm=mk[k];oo=ok[k];assert oo['root']['fen8']==root['fen8'] and oo['color']==sp['color']
 aff=set()
 for ls in mm['tree'].values():
  for q in ls:
   if 'terminal' not in q:aff.add((q['R'],q['N']))
   elif q['terminal']==0:aff.add((0,0))
 low,high=map(F,D['ratio_domain']);cuts={low,high}
 for a,b in aff:
  for c,e in aff:
   if a!=c:
    t=F(e-b,a-c)
    if low<t<high:cuts.add(t)
 cuts=sorted(cuts);samples=[dict(kind='point',at=x,domain=[str(x),str(x)]) for x in cuts]
 samples +=[dict(kind='open_interval',at=(a+b)/2,domain=[str(a),str(b)]) for a,b in zip(cuts,cuts[1:])]
 cells=[]
 for cell in samples:
  x=cell['at'];scores={u:min(value(q,x) for q in ls) for u,ls in mm['tree'].items()};mx=max(scores.values());best=sorted(u for u,v in scores.items() if v==mx);lex=best[0]
  cells.append(dict(kind=cell['kind'],domain=cell['domain'],sample=str(x),optimal_actions=best,lexical_choice=lex,H4_values={u:oo['scores'][u] for u in best},any_optimal_H4win=any(oo['scores'][u]==1 for u in best),lexical_H4value=oo['scores'][lex]))
 points=[]
 for x in map(F,D['points']):
  scores={u:min(value(q,x) for q in ls) for u,ls in mm['tree'].items()};mx=max(scores.values());best=sorted(u for u,z in scores.items() if z==mx)
  points.append(dict(ratio=str(x),optimal_actions=best,lexical_choice=best[0],H4_values={u:oo['scores'][u] for u in best}))
 actions=collections.defaultdict(list);observations=[]
 for n,zs in gs.items():
  for g in zs:
   if key(g)!=(root['seed'],root['variant'],sp['color']):continue
   assert g['root']['fen8']==root['fen8']
   u=g['actions'][0]['move'];ratio=F(g.get('ratio',str(F(g['price'],720))));tag=dict(source=n,arm=g['arm'],N=g.get('N',720),ratio=str(ratio),opponent=g['opponent'],first=u,H4_value=oo['scores'][u],actualH24=g['label'])
   actions[u].append(tag);observations.append(tag)
 witnesses=[c['first'] for c in oo['certificates'] if c['value']==1]
 for u in witnesses:actions[u].append(dict(source='independent_H4_all_defense_witness'))
 labels={u:'CERTIFIED_WIN_BY_H4' if oo['scores'][u]==1 else 'CERTIFIED_FORCED_LOSS_BY_H4' if oo['scores'][u]==-1 else 'NO_FORCED_H4_TERMINAL_LONGER_UNKNOWN' for u in actions}
 tot['roots']+=1;tot['H4_winning_root']+=oo['best_value']==1;tot['selected_action_union']+=len(actions)
 tot['selected_union_has_H4_value_difference']+=len({oo['scores'][u] for u in actions})>1
 tot['same_ratio_scale_changes_rootchoice']+=any(len({z['first'] for z in observations if z['source']==1269 and z['ratio']==str(q) and z['opponent']=='unit_search'})>1 for q in [F(1),F(2),F(12,5)])
 rows.append(dict(seed=root['seed'],variant=root['variant'],color=sp['color'],fen=root['fen8'],H4_root_value=oo['best_value'],known_winning_witnesses=witnesses,selected_union={u:dict(label=labels[u],observed_by=vv) for u,vv in actions.items()},full_D2_cells=cells,explicit_points=points))
out=dict(status='EXACT_IDENTICAL_ROOT_ACTION_LABEL_PRICE_CELL_JOIN',rows=rows,counts=dict(tot),new_go=0,scope=D)
(O/'result.json').write_text(json.dumps(out,indent=2));print(dict(tot))
