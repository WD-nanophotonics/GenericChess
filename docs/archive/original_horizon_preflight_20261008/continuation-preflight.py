"""Recover all frozen frontiers and validate finite-horizon sampling inputs."""
import sys,json,hashlib,time,collections
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.core.transition import initial_state,apply_action
from generic_chess.core.movegen import legal_actions
from scripts.research_record import write_record,record_value
p=Path(__file__).parent; prior=ROOT/'.local_agent/custody-kernel-20261008'
raw=(prior/'pretransfer-coupling.json').read_bytes(); frozen=json.loads(raw)
defs=(prior/'kernel-completed.json').read_bytes(); cases=json.loads(defs)['cases']
out=p/'continuation-preflight.json';assert not out.exists();start=time.perf_counter()
compiled=[compile_ruleset_for_execution(ruleset_from_dict(x['definition'])) for x in cases]
trajectories={t['seed']:t for t in frozen['trajectories']};assert len(trajectories)==64
rows=[];transitions=0
for f in frozen['frontiers']:
 assert not json.loads((ROOT/'.local_agent/rollout.json').read_bytes()).get('user_paused')
 t=trajectories[f['seed']];assert t['first_transfer'] and t['plies']==f['ply']
 row=dict(seed=f['seed'],consumed=f['ply'],remaining=32-f['ply'],cases=[])
 for case,c,actions,saved in zip(cases,compiled,f['paired_actions'],f['paired_states']):
  state=initial_state(c);assert len(actions)==f['ply']
  for v in actions:
   state=apply_action(state,next(a for a in legal_actions(state,c) if record_value(a)==v),c);transitions+=1
  assert record_value(state)==saved
  # The saved first transfer is an enemy capture of the owner0 tag.
  owner=1-state.position.side_to_move;count=state.position.hands[owner].count(case['base']);assert owner==1 and count>=1
  row['cases'].append(dict(base=case['base'],tag_hand_owner=owner,same_base_count=count,terminal=record_value(state.terminal_status)))
 rows.append(row)
assert len(rows)==13 and all(r['remaining']>=0 for r in rows)
r=dict(complete=True,question='Can the frozen original population support a remaining-horizon custody estimate?',source_sha256=hashlib.sha256(raw).hexdigest(),definition_sha256=hashlib.sha256(defs).hexdigest(),producer_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),original_samples=64,nontransfer_samples=51,total_horizon=32,frontiers=rows,replay_transitions=transitions,continuation_max_transitions_per_repeat=2*sum(x['remaining'] for x in rows),seconds=time.perf_counter()-start,decision='All saved histories and hand tags recover; estimate continuation per frontier with remaining horizon, then average over64, not13. A zero nontransfer contrast is specific to matched pre-transfer service, not general whole-state utility. No post-transfer result has been estimated here.')
write_record(out,r);print(json.dumps({k:r[k] for k in ('replay_transitions','continuation_max_transitions_per_repeat','seconds')}))
