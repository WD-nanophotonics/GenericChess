"""Check all retained ordinary-q0 PV-gap witnesses; no Native execution."""
from pathlib import Path
import sys,json,time,os
sys.path.insert(0,str(Path.cwd()))
from tools.local_agent.common import write_json
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution
from generic_chess.session.session import GameSession
from generic_chess.core.actions import SemanticBoardMove,SemanticDropMove
from generic_chess.core.coordinates import Square
from generic_chess.core.semantic_executor import semantic_engine_for
D=Path(__file__).resolve().parent;S=Path.cwd()/'.local_agent/root-window-q4-20261019';start=time.monotonic();allrows=json.loads((D/'result.json').read_bytes())['rows'];chosen=[r for r in allrows if r['returned_qdepth']==0];assert len(chosen)==39
mismatches=json.loads((S/'reader-result.json').read_bytes())['score_leaf_mismatches'];qs={(q['slot'],q['relative_ply']):q for q in map(json.loads,(S/'queries.jsonl').read_bytes().splitlines())};compiled={g['rule']:compile_legacy_ruleset_for_semantic_execution(ruleset_from_dict(g['rules']))for g in map(json.loads,(S/'generation.jsonl').read_bytes().splitlines())if 'rules'in g};rows=[]
for r in chosen:
 assert time.monotonic()-start<60
 for name in ('rollout','advisor','slack'):
  f=json.loads((Path(os.environ.get('GC_REPLAY_STOP_ROOT',Path.cwd()))/'.local_agent'/(name+'.json')).read_bytes());assert not(f.get('stopped')or f.get('user_paused'))
 m=mismatches[r['mismatch_index']];q=qs[r['slot'],r['relative_ply']];c=compiled[r['rule']];s=GameSession(c)
 for a in m['leaf_record']['actions']:
  kw=dict(a);kw['to_square']=Square(**kw['to_square'])
  if 'from_square'in kw:kw['from_square']=Square(**kw['from_square']);action=SemanticBoardMove(**kw)
  else:action=SemanticDropMove(**kw)
  s.submit(action)
 rows.append(dict(mismatch_index=r['mismatch_index'],rule=r['rule'],slot=r['slot'],relative_ply=r['relative_ply'],completed_depth=q['completed_depth'],ordinary_qdepth=q['result_ordinary_qdepth'],check_hard_qdepth=q['result_check_hard_qdepth'],PV_leaf_in_check=bool(semantic_engine_for(c).in_check(s.state.position,s.state.position.side_to_move)),root_score=q['score'],integer_leaf=m['expected'],cause=q['cause']))
write_json(D/'reserve-witness-result.json',dict(status='CHECKED_ALL_39_RETAINED_ORDINARY_Q0_GAPS',rows=rows,leaf_in_check=sum(r['PV_leaf_in_check']for r in rows),counts=39,seconds=time.monotonic()-start,scope='Ordinaryqdepth0 inside requestedq4 retains hardcheck depth8; not equivalentto explicitlyrequestedq0. Source andactualPV-leaf checks separate retainedtargetpolicy from paidabortedqwork. No q4training/bug orall-domainclaim.'))
print('RESERVE_WITNESSES',len(rows),sum(r['PV_leaf_in_check']for r in rows),time.monotonic()-start)
