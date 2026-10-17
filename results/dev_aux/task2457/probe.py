"""Fixed N-hand coefficient is a modeling restriction, not a second scale gauge."""
from pathlib import Path
from fractions import Fraction as F
from dataclasses import fields
from math import inf
from itertools import combinations
import json,time,hashlib,datetime
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from results.dev_aux.task2397.material import channels,material
from results.dev_aux.task2148.normal import SessionCompleteMaterialSearch
from results.dev_aux.task2175.receipt import choice_value
from results.dev_aux.task2392.reader import SharedDeleteStopReader
OUT=Path('results/dev_aux/task2457')
def run():
 assert not(OUT/'started.json').exists();p=json.loads((OUT/'plan.json').read_text());stop=SharedDeleteStopReader(Path.cwd());t=time.perf_counter();folder=Path(p['tree']);nodes=[json.loads(x)for x in(folder/'nodes.jsonl').read_text().splitlines()];root=json.loads((folder/'root.json').read_text());c=compile_ruleset_for_execution(deserialize_ruleset(Path(root['rules']).read_text()));target=nodes[0]['side'];vectors={};states={};(OUT/'started.json').write_text(json.dumps(dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),cap=p['cap_seconds'])));
 def cancel():stop();return time.perf_counter()-t>=p['cap_seconds']
 for n in nodes:
  if cancel():raise TimeoutError('original_nuisance_channel_cap')
  ss=GameSession.replay(c,deserialize_game_record(json.dumps(n['record'])));fs=channels(ss.state.position,target,excluded_type_ids={'K'});vectors[n['index']]=[fs['board'].get('R',0),fs['hand'].get('R',0),fs['hand'].get('N',0),fs['board'].get('N',0)];states[n['index']]=ss
 def fold(point):
  vals={};leaf={}
  for n in reversed(nodes):
   i=n['index']
   if n['status']!='ongoing':vals[i]=F(0)if n['winner']is None else inf if n['winner']==target else-inf;leaf[i]=i
   elif n['depth_remaining']==0:vals[i]=sum(F(x)*y for x,y in zip(vectors[i],(*point,F(1))));leaf[i]=i
   else:
    best=(max if n['side']==target else min)(vals[j]for ch,j in n['children']);j=next(j for ch,j in n['children']if vals[j]==best);vals[i]=best;leaf[i]=leaf[j]
  score=max(vals[j]for ch,j in nodes[0]['children']);choice,j=next((ch,j)for ch,j in nodes[0]['children']if vals[j]==score);return dict(point=list(point),choice=choice,score=float(score),leaf_features=vectors[leaf[j]],all_choices=[dict(choice=ch,score=float(vals[j]),features=vectors[leaf[j]])for ch,j in nodes[0]['children']])
 rows=[fold(tuple(map(F,(a,b,eta))))for a,b in p['R_grid']for eta in p['held_N_values']];actual=[]
 for eta in p['actual_normal_N_hand']:
  if cancel():break
  a=b=.75;ss=states[0];normal=SessionCompleteMaterialSearch(c,lambda pos,tar:material(pos,tar,{'R':a,'N':1.,'B':1.},{'R':b,'N':eta,'B':1.},excluded_type_ids={'K'}),max_depth=3);r=normal.choose(ss,max_nodes=8192,seconds=min(3.,p['cap_seconds']-(time.perf_counter()-t)),cancel=cancel);expected=next(row for row in rows if row['point']==[F(a),F(b),F(eta)]);assert r.completed_depth==3 and choice_value(r.choice)==expected['choice']and r.score==expected['score'];actual.append(dict(N_hand=eta,choice=choice_value(r.choice),score=r.score,nodes=r.nodes,completed_depth=r.completed_depth,seconds=r.seconds))
 for r in rows:r['point']=list(map(str,r['point']))
 (OUT/'rows.json').write_text(json.dumps(rows,indent=2));(OUT/'features.json').write_text(json.dumps(vectors,indent=2));result=dict(status='CLOSED_N_HAND_MODELING_CONSTRAINT_DIAGNOSTIC',nodes=len(nodes),folds=len(rows),actual_normal_queries=actual,seconds=time.perf_counter()-t,scope=p['scope']);(OUT/'result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
if __name__=='__main__':run()
