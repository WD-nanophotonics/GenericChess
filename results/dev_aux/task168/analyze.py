"""Recover only pilot summaries from saved actual games; never rerun games."""
import json,statistics,hashlib
from pathlib import Path
R=Path.cwd();P=R/'results/dev_aux/task166';O=R/'results/dev_aux/task168';O.mkdir(exist_ok=True)
D=json.loads((P/'declaration.json').read_bytes());X=json.loads((P/'games.json').read_bytes());assert X['complete'] and len(X['calls'])==D['games'];C=X['calls']
summary=dict(complete=True,games=len(C),seconds=X['wall_seconds'],groups=[],profile_pairs=[])
for opponent in D['opponents']:
 for profile in D['profiles']:
  rows=[c for c in C if c['profile']==profile and c['opponent']==opponent];assert len(rows)==2*len(D['roots'])
  summary['groups'].append(dict(profile=profile,opponent=opponent,games=len(rows),mate_wins=sum(c['result']['score']['termination']=='CHECKMATE' and c['result']['score']['winner']==c['result']['agent_color'] for c in rows),mate_losses=sum(c['result']['score']['termination']=='CHECKMATE' and c['result']['score']['winner']!=c['result']['agent_color'] for c in rows),cutoffs=sum(not c['result']['score']['terminal'] for c in rows),original_reward_mean=statistics.mean(c['result']['reward'] for c in rows),cutoff_quantity_mean=statistics.mean(c['result']['score']['cutoff_quantity_component'] for c in rows),opponent_leaf_nodes=sum(r['leaf_nodes'] for c in rows for r in c['result']['opponent_records'])))
 for profile in ('learned','reversed'):
  for oi in range(len(D['roots'])):
   for color in (True,False):
    pair=[next(c['result'] for c in C if c['name']==f'{p}-{opponent}-o{oi}-c{int(color)}') for p in ('unit',profile)]
    summary['profile_pairs'].append(dict(profile=profile,opponent=opponent,opening=oi,color=color,reward_delta=pair[1]['reward']-pair[0]['reward'],same_actions=pair[0]['actions']==pair[1]['actions'],terminal=[r['score']['termination'] for r in pair]))
summary['recovery']='All84physicalgames completed14.547s; postprocessor retained hardcodedrange8 despite7validfrozenroots causedStopIteration aftergames.json saved. Summary only regenerated usingdeclaredrootcount, originaldriver unchanged; no game rerun orclockreset.'
summary['source_games_sha256']=hashlib.sha256((P/'games.json').read_bytes()).hexdigest()
(O/'analysis.json').write_text(json.dumps(summary,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in summary.items() if k!='profile_pairs'},indent=2))
