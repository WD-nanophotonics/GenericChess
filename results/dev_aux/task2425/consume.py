from pathlib import Path
from copy import copy
from collections import Counter,defaultdict
import json,time
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record,serialize_game_record
from generic_chess.session.result import SessionStatus
from scripts.generic_session_win_proof import execute,SessionChoice
from results.dev_aux.task2199.semantic_graph import verify_graph,GraphStrategyCursor
from results.dev_aux.task2205.consume import decode_graph
from results.dev_aux.task2392.reader import SharedDeleteStopReader
OUT=Path('results/dev_aux/task2425')
def run():
 tick=time.perf_counter();stop=SharedDeleteStopReader(Path.cwd());folder=Path('results/dev_aux/task2424');p=json.loads((folder/'plan.json').read_text());slots=json.loads((folder/'inputs.json').read_text());done=json.loads((folder/'completion.json').read_text());rows=list(map(json.loads,(folder/'queries.jsonl').read_text().splitlines()));certs={r['slot']:r for r in map(json.loads,(folder/'certificates.jsonl').read_text().splitlines())};assert len(rows)==done['rows']and done['unstarted']==32-len(rows);verified=[]
 original=Path('results/dev_aux/task2402');source_games={g['slot']:g for g in map(json.loads,(original/'games.jsonl').read_text().splitlines())};source_ds=list(map(json.loads,(original/'decisions.jsonl').read_text().splitlines()))
 for item in slots:
  game=source_games[item['source_game']];assert game['root']==item['family']and game['candidate_color']==item['role']and[game['ratio'],game['hand_ratio']]==[1.5,1.5]
  lows=[d for d in source_ds if d['slot']==game['slot']and d['is_candidate']and d['regime']=='LOW'];expected=lows[item['low_index']]['root_record']if len(lows)>item['low_index']else None;assert expected==item['record']
 for row,slot in zip(rows,slots):
  stop();assert all(row[k]==v for k,v in slot.items())
  if slot['record']is None:assert not row['queried']and not row['verified']and not row['actual_mate'];continue
  assert row['queried'];c=compile_ruleset_for_execution(deserialize_ruleset(Path(slot['rules']).read_text()));s=GameSession.replay(c,deserialize_game_record(json.dumps(slot['record'])));assert s.result.status is SessionStatus.ONGOING and s.state.position.side_to_move==slot['role'];assert row['query_seconds_allocated']<=2.1 and sum(x is not None for x in s.state.position.board)<=4;assert sum(x is not None for x in s.state.position.board)+sum(h.total()for h in s.state.position.hands)<=8
  if row['verified']:
   cert=decode_graph(s,certs[row['slot']]['certificate']);v=verify_graph(s,cert,max_nodes=65536,seconds=5.,cancel=lambda:stop()or False);assert v['verified'];cur=GraphStrategyCursor(s,cert,max_nodes=65536,seconds=5.,cancel=lambda:stop()or False);record=deserialize_game_record(json.dumps(row['actual_record']))
   for a in record.actions[len(s.to_record().actions):]:
    stop();before=copy(s);choice=SessionChoice('ACTION',action=a)
    if s.state.position.side_to_move==cert.target:assert cur.choose(s)==choice
    execute(s,choice);cur.observe(before,choice,s)
   assert s.result.status.value==row['actual_status'];assert row['actual_mate']==(s.result.status is not SessionStatus.ONGOING and s.result.winner==slot['role']);verified.append(dict(slot=row['slot'],stage=row['stage'],actual_mate=row['actual_mate'],moves=row.get('actual_conversion_moves',0)))
 bystage=[]
 for stage in('FIRST_LOW','FIFTH_LOW'):
  part=[r for r in rows if r['stage']==stage];bystage.append(dict(stage=stage,planned=16,available=sum(s['record']is not None for s in slots if s['stage']==stage),returned=len(part),queried=sum(r['queried']for r in part),verified=sum(r['verified']for r in part),actual_mates=sum(r['actual_mate']for r in part),not_reached=sum(not r['queried']for r in part),shortened_allocations=sum(r['queried']and r['query_seconds_allocated']<2.1 for r in part)))
 paired=[]
 for family in range(8):
  for role in(0,1):
   rr={r['stage']:r for r in rows if r['family']==family and r['role']==role}
   if len(rr)==2 and all(r['queried']for r in rr.values()):paired.append(dict(family=family,role=role,first_verified=rr['FIRST_LOW']['verified'],later_verified=rr['FIFTH_LOW']['verified'],first_actual_mate=rr['FIRST_LOW']['actual_mate'],later_actual_mate=rr['FIFTH_LOW']['actual_mate']))
 out=dict(status='PASS_ACTUAL_TIMING_CONTEXTS_CERTIFICATES_AND_CONVERSIONS',planned=32,rows=len(rows),queried=done['queried'],stages=bystage,paired_available=paired,verified_paths=verified,seconds=time.perf_counter()-tick,scope='ALL16baselinehistories, fifthLOWavailability/survivalbias explicit. Existinggames unchanged, new2.1s early/laterqueries only. No unavailablecontext asUNKNOWNgame/draw, no capextension/policyadoption. IndependentpublicGraphverifier/cursor plus actualCorepaths; notexternalengine. Descriptiveproofavailability, notcausalnewgameW-Lbenefit.')
 (OUT/'result.json').write_text(json.dumps(out,indent=2));print(json.dumps(out))
if __name__=='__main__':run()
