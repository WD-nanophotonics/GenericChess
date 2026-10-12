from pathlib import Path
from fractions import Fraction
import json,collections
R=Path.cwd();O=R/'results/dev_aux/task414';O.mkdir(exist_ok=True);out={}
for task in (411,412):
 r=json.loads((R/f'results/dev_aux/task{task}/result.json').read_text(encoding='utf-8'));gs=[json.loads(x) for x in (R/f'results/dev_aux/task{task}/games.jsonl').read_text(encoding='utf-8').splitlines()];cells=[]
 for root in range(4):
  for c in (0,1):
   rows=[x for x in r['rows'] if x['root_index']==root and x['color']==c];assert len(rows)==6;trip=[]
   for row,g in zip(rows,[g for g in gs if g['root']['index']==root and g['color']==c]):
    term=g['termination'];winner=term['winner'];outcome='unfinished' if term['kind']=='cap24' else ('draw' if winner is None else 'win' if winner==c else 'loss');trip.append(dict(names=row['names'],outcome=outcome,terminal_ply=None if outcome=='unfinished' else row['plies'],unfinished_quantity=g['raw_quantity'] if outcome=='unfinished' else None,goal=row['goal'],speed_goal=row['speed_goal']))
   outcomes={x['outcome'] for x in trip};speeds={x['terminal_ply'] for x in trip if x['outcome']=='win'};classification='allwins-sameply-saturated' if outcomes=={'win'} and len(speeds)==1 else 'allwins-speed-response' if outcomes=={'win'} else 'terminal-response' if len(outcomes)>1 and outcomes!={'unfinished'} else 'quantity-response-only' if outcomes=={'unfinished'} and len({x['unfinished_quantity'] for x in trip})>1 else 'invariant';cells.append(dict(root=root,color=c,classification=classification,profiles=trip))
 out[r['arm']]=dict(seconds=r['seconds'],games=48,actual_go=r['actual_go'],actual_plies=sum(x['plies'] for x in r['rows']),true_terminal_count=sum(g['termination']['kind']!='cap24' for g in gs),classification_counts=dict(collections.Counter(x['classification'] for x in cells)),goal_response_cells=sum(len({p['goal'] for p in x['profiles']})>1 for x in cells),speed_goal_response_cells=sum(len({p['speed_goal'] for p in x['profiles']})>1 for x in cells),cells=cells)
(O/'result.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print({k:{a:b for a,b in v.items() if a!='cells'} for k,v in out.items()})
