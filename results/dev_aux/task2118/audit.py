from pathlib import Path
from collections import defaultdict,Counter
import json,time,hashlib,math
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record,serialize_game_record
from generic_chess.core.actions import action_to_dict
from scripts.generic_proof_rnb_bridge import actor_state,uci
from scripts.generic_royal_actor import RoyalActor
from results.dev_aux.task2068.teacher import CanonicalTeacher
OUT=Path('results/dev_aux/task2118')
def run():
 start=time.perf_counter();deadline=start+180;old=Path('results/dev_aux/task2100');inputs=json.loads((old/'inputs.json').read_text())['roots'];g=json.loads((old/'games.jsonl').read_text().splitlines()[0]);c=compile_ruleset_for_execution(deserialize_ruleset(Path(inputs[g['family']]['rules']).read_text(encoding='utf-8')));record=deserialize_game_record(json.dumps(g['record']));s=GameSession(c);teacher=CanonicalTeacher('results/dev_aux/task2097','results/dev_aux/task2098','results/dev_aux/task2099');actor=RoyalActor(4);queries=[json.loads(x)for x in Path('results/dev_aux/task2116/queries.jsonl').read_text().splitlines()];assert len(queries)==16;paired=[]
 for ply in range(8):
  rs=[r for r in queries if r['ply']==ply];assert [r['provider']for r in rs]==(['PN','NEGATIVE_FILTER']if ply%2==0 else['NEGATIVE_FILTER','PN']);by={r['provider']:r for r in rs};assert all(r['full_record']==json.loads(serialize_game_record(s.to_record()))for r in rs);row=teacher.rows[teacher.key(actor_state(s.state))];assert row['label']=='DRAW';legal={json.dumps(action_to_dict(a),sort_keys=True)for a in s.legal_actions()};assert set(dict(actor.moves(actor_state(s.state))))=={uci(a)for a in s.legal_actions()}
  for r in rs:
   assert r['logical_status']=='UNKNOWN'and r['source']=='MATERIAL_SEARCH'and json.dumps(r['choice'],sort_keys=True)in legal and r['normal_depth']==2 and r['proof_nodes']<=1024 and r['normal_nodes']<=4096
   assert r['limits']['normal_seconds']==.1 and r['limits']['normal_nodes']==4096 and r['limits']['proof_seconds']==1.5
  assert by['NEGATIVE_FILTER']['proof_reason']=='certified_complete_graph_no_win'and by['NEGATIVE_FILTER']['proof_nodes']==0;paired.append(dict(ply=ply,same_choice=by['PN']['choice']==by['NEGATIVE_FILTER']['choice'],same_completed_depth=by['PN']['normal_depth']==by['NEGATIVE_FILTER']['normal_depth'],saved_proof_seconds=by['PN']['proof_seconds']-by['NEGATIVE_FILTER']['proof_seconds']));s.submit(record.actions[ply])
 games=[json.loads(x)for x in(old/'games.jsonl').read_text().splitlines()if json.loads(x)['reused_from']is None];steps=defaultdict(list)
 for line in(old/'moves.jsonl').read_text().splitlines():
  m=json.loads(line);steps[m['physical_id']].append(m)
 compiled={};groups=defaultdict(Counter);seen=0
 for g in games:
  if time.perf_counter()>=deadline:raise TimeoutError('original180cap')
  if g['family']not in compiled:compiled[g['family']]=compile_ruleset_for_execution(deserialize_ruleset(Path(inputs[g['family']]['rules']).read_text(encoding='utf-8')))
  s=GameSession(compiled[g['family']]);rec=deserialize_game_record(json.dumps(g['record']))
  for m,a in zip(steps[g['physical_id']],rec.actions):
   row=teacher.rows[teacher.key(actor_state(s.state))];kind='NONWIN'if row['label']in('DRAW','LOSS')else'POSITIONAL_WIN';counts=groups[kind];counts['calls']+=1;counts['proof_nodes']+=m['proof_nodes'];counts['proof_seconds']+=m['proof_seconds'];counts['normal_seconds']+=m['normal_seconds'];counts['moves_above4']+=sum(p is not None for p in s.state.position.board)>4;assert hashlib.sha256(repr(s.state).encode()).hexdigest()==m['before_state_sha'];s.submit(a);seen+=1
 per=sum(r['saved_proof_seconds']for r in paired)/8;result=dict(status='PASS_FROZEN_PAIRED_RECEIPT_AND_CLOSED_TRACE_AUDIT',paired=paired,closed2100_groups={k:dict(v)for k,v in groups.items()},closed_physical=len(games),closed_moves=seen,estimated_queries_to_amortize_teacher_build_and_current_load=math.ceil((593.562+10.0420562)/per),seconds=time.perf_counter()-start,scope='CostattributiononfixedOLDtraces, not counterfactual fullgame saving: filtering may change wallcompletion/actions and future histories. PositionalWINneverimplieshistoryWIN; NONWINskip suppliesUNKNOWN only. No originalcaprestart or missingtrialcompletion.')
 (OUT/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result))
if __name__=='__main__':run()
