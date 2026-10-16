"""ALL12 closed transfer divergences: capture/formation timing, no new search."""
from pathlib import Path
from collections import Counter
from copy import copy
import json,time
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from results.dev_aux.task2153.stop_evidence import EvidenceStopReader
OUT=Path('results/dev_aux/task2349')
def inventory(s):
 return Counter((pc.owner,pc.current_type_id)for pc in s.state.position.board if pc is not None and pc.current_type_id!='K')
def run():
 t=time.perf_counter();stop=EvidenceStopReader(Path.cwd());read=lambda p:json.loads(Path(p).read_text());analysis=read('results/dev_aux/task2337/task2331-result.json');p=read('results/dev_aux/task2331/plan.json');roots={r['index']:r for r in read(p['input'])};games={(g['root'],g['opponent'],g['candidate_color'],g['ratio']):g for g in map(json.loads,Path('results/dev_aux/task2331/games.jsonl').read_text().splitlines())};ds={}
 for d in map(json.loads,Path('results/dev_aux/task2331/decisions.jsonl').read_text().splitlines()):ds.setdefault(d['slot'],[]).append(d)
 rows=[]
 for row in analysis['first_actual_divergences']:
  stop();root=roots[row['family']];c=compile_ruleset_for_execution(deserialize_ruleset(Path(root['rules']).read_text()));base=GameSession.replay(c,deserialize_game_record(json.dumps(root['record'])));parent=GameSession.replay(c,deserialize_game_record(json.dumps(row['root_record'])));actions=[]
  for price in(1.,2.):
   g=games[(row['family'],row['opponent'],row['color'],price)];record=deserialize_game_record(json.dumps(g['record']));a=record.actions[len(parent.to_record().actions)];child=copy(parent);child.submit(a);before=inventory(parent);after=inventory(child);actions.append(dict(price=price,total_nonanchor_delta=sum(after.values())-sum(before.values()),removed=[dict(owner=k[0],type=k[1],count=n)for k,n in(before-after).items()],ordinary_material_decisions_before=sum(d['is_candidate']and d['source']=='FULL_SESSION_MATERIAL_SEARCH'for d in ds[g['slot']][:row['ply']])))
  initial_capture_choices=0
  for a in base.legal_actions():
   child=copy(base);child.submit(a);initial_capture_choices+=sum(inventory(child).values())<sum(inventory(base).values())
  rows.append(dict(family=row['family'],opponent=row['opponent'],color=row['color'],first_difference_ply=row['ply'],candidate_first=row['is_candidate'],actual_delta=row['delta'],initial_legal_capture_choices=initial_capture_choices,actions=actions))
 result=dict(status='PASS_ALL_CLOSED_DIVERGENCES_CAPTURE_AND_FORMATION_ACCOUNTING',contexts=len(rows),positive_delta_pairs=sum(r['actual_delta']is not None and r['actual_delta']>0 for r in rows),first_own_decision_pairs=sum(all(a['ordinary_material_decisions_before']==0 for a in r['actions'])for r in rows),pairs_with_any_immediate_capture=sum(any(a['total_nonanchor_delta']<0 for a in r['actions'])for r in rows),positive_pairs_with_any_immediate_capture=sum(r['actual_delta']is not None and r['actual_delta']>0 and any(a['total_nonanchor_delta']<0 for a in r['actions'])for r in rows),rows=rows,seconds=time.perf_counter()-t,scope='ALL12actualfirstdifferences/basiccapture-removaldomain only; publicCorechildexecution andactualmaterialinventories. Initialmuallowscapturesat targetroots despiteNONcaptureparentprefix. No newgame/search/W-Lreward/referencefitting. Timeorder/captureassociationnotcausalmediation orlongtermadvantageformationproof; initialfamilyholdoutnotallsearchstateholdout.')
 with(OUT/'result.json').open('x')as f:json.dump(result,f,indent=2)
 print(json.dumps({k:v for k,v in result.items()if k!='rows'}))
if __name__=='__main__':run()
