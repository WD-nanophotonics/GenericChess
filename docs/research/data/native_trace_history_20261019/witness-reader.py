"""Canonical record/full witness verification independent of Native."""
from pathlib import Path
import os,sys,json,time,hashlib
from collections import Counter
sys.path.insert(0,str(Path.cwd()))
from tools.local_agent.common import write_json
from scripts.research_record import record_value
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.core.transition import apply_action
from generic_chess.learning.material import LearnableMaterialCheckpoint
D=Path(__file__).resolve().parent;start=time.perf_counter();i=json.loads((D/'witness-inputs.json').read_bytes());qs=list(map(json.loads,(D/'witness-queries.jsonl').read_bytes().splitlines()));c=compile_legacy_ruleset_for_semantic_execution(ruleset_from_dict(i['rule']));cp=LearnableMaterialCheckpoint.from_dict(i['checkpoint']);scale=cp.semantic_native_scale;counts=Counter();sessions={}
for p in i['parents']:
 for name in ('rollout','advisor','slack'):
  f=json.loads((Path(os.environ.get('GC_REPLAY_STOP_ROOT',Path.cwd()))/'.local_agent'/(name+'.json')).read_bytes());assert not(f.get('stopped')or f.get('user_paused'))
 s=GameSession.replay(c,deserialize_game_record(json.dumps(p['record'])));assert record_value(s.state)==p['state']and record_value(s.history)==p['history']
 values=[]
 for action in s.legal_actions():
  child=apply_action(s.state,action,c);counts['Core_children']+=1
  assert child.terminal_status.winner is None
  value=0 if child.terminal_status.is_terminal else sum((1 if pc.owner==0 else -1)*round(cp.board_weights[pc.current_type_id]*scale)for pc in child.position.board if pc)
  values.append(value)
 expected=(max if s.state.position.side_to_move==0 else min)(values)*(1 if s.state.position.side_to_move==0 else -1);assert expected==p['expected_score_native'];sessions[p['witness']]=(s,expected)
a,b=(sessions[n][0]for n in (0,1));assert a.state.position==b.state.position and a.state.ply_count==b.state.ply_count==7 and a.state.history!=b.state.history and a.state.repetition_counts!=b.state.repetition_counts
keys={}
for q in qs:
 s,value=sessions[q['witness']];r=q['result'];assert q['parent_unchanged']and r['completed_depth']==1 and not r['used_fallback'];assert r['score']*scale==value
 row=next(x for x in r['training_trace']if x['search_ply']==0 and x['remaining_depth']==1);assert row['bound_class']=='EXACT'and row['score_native']==value
 key=tuple(row[k]for k in ('position_identity','side_to_move','remaining_depth','search_ply','ruleset_fingerprint'));keys.setdefault(str(q['mode']),[]).append((key,value))
 counts['queries']+=1
for rows in keys.values():assert rows[0][0]==rows[1][0]and rows[0][1]!=rows[1][1]
write_json(D/'witness-reader-result.json',dict(status='PASS_SAME_PLY_REACHABLE_HISTORY_ALIAS',counts=dict(counts),native_scores=[sessions[n][1]for n in (0,1)],same_ply=7,scale=scale,seconds=time.perf_counter()-start,scope='Canonical full public Session records and Core child values; sameboard/sameply DIFFERENTcompletehistories. All four actual Native roots correct; identical tracekeys cannot identify a unique historytarget. No Native rerun, training or proof of a wrong Native execution path.'))
print(dict(counts),[sessions[n][1]for n in (0,1)],time.perf_counter()-start)
