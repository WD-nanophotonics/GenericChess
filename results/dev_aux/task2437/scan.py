"""Freeze earliest existing dual capture roots, without price/outcome selection."""
from pathlib import Path
import json,time,datetime,hashlib
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.core.actions import action_to_dict
from results.dev_aux.task2392.reader import SharedDeleteStopReader
OUT=Path('results/dev_aux/task2437')
def run():
 assert not(OUT/'started.json').exists();t=time.perf_counter();stop=SharedDeleteStopReader(Path.cwd());p=json.loads((OUT/'plan.json').read_text());out=[];examined=0;seen=set();compiled={}
 (OUT/'started.json').write_text(json.dumps(dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),cap=p['cap_seconds'])));
 for task in p['task_order']:
  f=Path(f'results/dev_aux/task{task}');plan=json.loads((f/'plan.json').read_text());roots={r['index']:r for r in json.loads(Path(plan['input']).read_text())};games={g['slot']:g for g in map(json.loads,(f/'games.jsonl').read_text().splitlines())}
  for d in map(json.loads,(f/'decisions.jsonl').read_text().splitlines()):
   stop()
   if len(out)>=p['max_roots']or time.perf_counter()-t>=p['cap_seconds']:break
   examined+=1;rule=roots[games[d['slot']]['root']]['rules'];c=compiled.setdefault(rule,compile_ruleset_for_execution(deserialize_ruleset(Path(rule).read_text())));s=GameSession.replay(c,deserialize_game_record(json.dumps(d['root_record'])));side=s.state.position.side_to_move;legal=s.legal_actions();captures={k:[]for k in('R','N')}
   for a in legal:
    if not hasattr(a,'from_square'):continue
    victim=s.state.position.board[a.to_square.rank*4+a.to_square.file]
    if victim is not None and victim.owner!=side and victim.current_type_id==victim.base_type_id and victim.current_type_id in captures:captures[victim.current_type_id].append(action_to_dict(a))
   if not all(captures.values()):continue
   key=repr((s.state.position.board,s.state.position.hands,side,s.state.position.aux_state))
   if key in seen:continue
   seen.add(key);out.append(dict(index=len(out),family=len(out),source_task=task,source_slot=d['slot'],source_ply=d['ply'],rules=rule,record=d['root_record'],state_sha=d['root_state_sha'],captures=captures,all_legal_actions=[action_to_dict(a)for a in legal]))
  if len(out)>=p['max_roots']or time.perf_counter()-t>=p['cap_seconds']:break
 (OUT/'inputs.json').write_text(json.dumps(out,indent=2));result=dict(status='CLOSED_STRUCTURAL_SCAN',roots=len(out),examined=examined,seconds=time.perf_counter()-t,scope=p['scope']);(OUT/'result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
if __name__=='__main__':run()
