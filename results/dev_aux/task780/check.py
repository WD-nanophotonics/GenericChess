import json,hashlib
from pathlib import Path
from fractions import Fraction as F
R=Path.cwd();O=R/'results/dev_aux';load=lambda p:json.loads((O/p).read_bytes());p=O/'task780';p.mkdir(exist_ok=True);rows=[]
for n,label in [(743,'A'),(749,'B'),(763,'C')]:
 for u in load(f'task{n}/endpoints.json')['updates']:
  triples=[]
  for c in u['candidates']:
   wins=sum(not t['kind'].startswith('cap') and t['winner']==i%2 for i,t in enumerate(c['terminations']));losses=sum(not t['kind'].startswith('cap') and t['winner'] is not None and t['winner']!=i%2 for i,t in enumerate(c['terminations']));triples.append((-losses,wins,F(c['mean_goal'])))
  chosen=max(range(len(triples)),key=lambda j:triples[j]);rows.append(dict(method=label,start=u['start'],axis=u['axis'],original_index=u['selected_index'],lexicographic_index=chosen,terminal_pairs=len(set(x[:2] for x in triples)),choices_disagree=chosen!=u['selected_index'],values=[dict(losses=-x[0],wins=x[1],feedback=str(x[2])) for x in triples]))
(p/'result.json').write_text(json.dumps(dict(status='ALL72_VISITED_GRID_OBSERVATIONAL_TERMINAL_DISCRIMINATION',rows=rows,new_go=0,changed_choices=sum(x['choices_disagree'] for x in rows),terminal_flat_grids=sum(x['terminal_pairs']==1 for x in rows),scope='Posthoc actualvisitedgrids only; notnewendpoints/offpolicy rollforward. Lexicographic losses,wins,feedback discrimination isnotusefulness/generalization.'),indent=2),encoding='utf-8');print(json.dumps(dict(changed_choices=sum(x['choices_disagree'] for x in rows),terminal_flat_grids=sum(x['terminal_pairs']==1 for x in rows))))
