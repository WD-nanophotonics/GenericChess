from pathlib import Path
import json,collections
from fractions import Fraction as F
R=Path.cwd();O=R/'results/dev_aux/task1096';O.mkdir(exist_ok=False)
a=[json.loads(x) for x in (R/'results/dev_aux/task1094/games.jsonl').read_text().splitlines()];old={g['game']:g for g in map(json.loads,(R/'results/dev_aux/task1081/games.jsonl').read_text().splitlines())};rows=[];first=[];nodecounts=[]
for g in a:
 o=old[g['game']];q=next(q for q in g['queries'] if q['player']=='candidate');z=next(q for q in o['queries'] if q['player']=='candidate');assert q['metadata']['full_history']==z['metadata']['full_history'];first.append(dict(game=g['game'],same_first_candidate_position=True,ab=q['move'],mature=z['move'],different=q['move']!=z['move']))
 for q in g['queries']:
  if q['player']=='unit':
   line=next(line for line in reversed(q['metadata']['uci_info']) if ' nodes ' in line);f=line.split();nodecounts.append(int(f[f.index('nodes')+1]))
for backend,gg in [('complete2ply',a),('mature64',[old[g['game']] for g in a])]:
 for p in [64,90,671]:
  for opp in ['unit_search','uniform_random']:
   xx=[g for g in gg if g['price']==p and g['opponent']==opp];cc=collections.Counter(g['label'] for g in xx);rows.append(dict(backend=backend,price=p,opponent=opp,N=len(xx),counts=dict(cc),J16=str(F(cc['W']-cc['L'],len(xx)))))
(O/'result.json').write_text(json.dumps(dict(status='PASS_MATCHED16_EXPOSED_FAMILY_CONSUMER_DIAGNOSTIC',rows=rows,firstcandidate_changes=sum(x['different'] for x in first),firstcandidate_total=len(first),firstcandidate_records=first,AB_counts=json.loads((R/'results/dev_aux/task1095/result.json').read_bytes())['counts'],native_opponent_reported_nodes=dict(sum=sum(nodecounts),N=len(nodecounts),min=min(nodecounts),max=max(nodecounts)),scope='NOTequalbudget/equaltime searchcomparison; complete2plydifferenttree/tiepolicyfrommature64node selective search. RealWLconsumerconditional, notuniversalrulesvalue/humanfitness.',new_go=0),indent=2),encoding='utf-8');print(rows);print('firstcandidate_changes',sum(x['different'] for x in first),len(first))
