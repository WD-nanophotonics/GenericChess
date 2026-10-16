"""Consume ALL first actual divergences; canonical quality is descriptive, not reward."""
from pathlib import Path
from collections import Counter
import json,time,hashlib
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.session.result import SessionStatus
from scripts.generic_proof_rnb_bridge import actor_state
from results.dev_aux.task2153.stop_evidence import EvidenceStopReader
OUT=Path('results/dev_aux/task2374')
def key(raw):return ''.join(raw[:-1])+str(raw[-1])
def run(task=2358):
 t=time.perf_counter();stop=EvidenceStopReader(Path.cwd());read=lambda p:json.loads(Path(p).read_text());analysis=read(f'results/dev_aux/task2373/task{task}-mechanism.json');folder=Path(f'results/dev_aux/task{task}');p=read(folder/'plan.json');roots={r['index']:r for r in read(p['input'])};games={(g['root'],g['opponent'],g['candidate_color'],g['ratio']):g for g in map(json.loads,(folder/'games.jsonl').read_text().splitlines())};prices=(1.,float(read('results/dev_aux/task2357/selection.json')['selected_price']));pending=[];needed=set()
 for original in analysis['first_differences']:
  if original['prices']!=list(prices):continue
  row=dict(original,is_candidate=original['kind']=='candidate_first')
  stop();c=compile_ruleset_for_execution(deserialize_ruleset(Path(roots[row['family']]['rules']).read_text()));record=deserialize_game_record(json.dumps(row['root_record']));parent=GameSession.replay(c,record);actual=[]
  for price in prices:
   g=games[(row['family'],row['opponent'],row['color'],price)];final=deserialize_game_record(json.dumps(g['record']));assert final.actions[:len(record.actions)]==record.actions;s=GameSession.replay(c,record);s.submit(final.actions[len(record.actions)]);pos=s.state.position;assert not pos.aux_state and not any(h.total()for h in pos.hands)and all(pc is None or(pc.base_type_id==pc.current_type_id and not pc.promoted)for pc in pos.board);token=key(actor_state(s.state));needed.add(token);actual.append(dict(token=token,side=s.state.position.side_to_move,actual_child_status=s.result.status.value,actual_child_winner=s.result.winner,price=price))
  pending.append(dict(first=row,children=actual))
 labels={}
 if needed:
  for n,line in enumerate(Path('results/dev_aux/task2249/labels.jsonl').open(encoding='utf-8')):
   if n%1024==0:stop()
   r=json.loads(line);token=key(r['board'])
   if token in needed:labels[token]=r
 assert set(labels)==needed;rows=[]
 for item in pending:
  row=item['first'];utilities=[]
  for child in item['children']:
   label=labels[child['token']]['label'];v={'WIN':1,'DRAW':0,'LOSS':-1}[label];utility=v if child['side']==row['color']else-v;child.update(canonical_next_mover_label=label,canonical_candidate_utility=utility);utilities.append(utility)
  rows.append(dict(family=row['family'],opponent=row['opponent'],color=row['color'],is_candidate=row['is_candidate'],sources=row['sources'],ply=row['ply'],canonical_candidate_delta=utilities[1]-utilities[0],actual_game_delta=row['delta'],children=item['children']))
 result=dict(status='PASS_ALL_CLOSED_FIRST_DIFFERENCES_CANONICAL_ASSOCIATION',task=task,first_actual_differences=len(rows),candidate_first=sum(r['is_candidate']for r in rows),foe_first=sum(not r['is_candidate']for r in rows),canonical_quality_changed=sum(r['canonical_candidate_delta']!=0 for r in rows),positive_game_delta_with_same_first_quality=sum(r['actual_game_delta']is not None and r['actual_game_delta']>0 and r['canonical_candidate_delta']==0 for r in rows),rows=rows,seconds=time.perf_counter()-t,scope='ALLfirstcommittedactiondifferences forPOST-TRAINselected1.5vs1contrast, notpre-registeredconfirmation. CanonicalWDLreadfromexplicitfullyexposed2249teacher isassociationonly, NOTactualfiniteSessionvalue/fixedfoeW-L/reward/causalmediation orpricefit. Actualchildterminals reportedseparately. No extra games/search/teacherconstruction orbestprice/defaultadoption.')
 with(OUT/f'task{task}-result.json').open('x')as f:json.dump(result,f,indent=2)
 print(json.dumps({k:v for k,v in result.items()if k!='rows'}))
if __name__=='__main__':
 import sys
 run(int(sys.argv[1]) if len(sys.argv)>1 else 2358)
