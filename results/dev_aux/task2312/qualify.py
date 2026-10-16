"""Postfreeze reference strata ONLY; never policy reward or runtime skipping."""
from pathlib import Path
from collections import Counter
import json,time,hashlib
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from scripts.generic_proof_rnb_bridge import actor_state
from scripts.generic_inventory_proof_transport import execution_differences
from results.dev_aux.task2251.study import Guide,key
from results.dev_aux.task2153.stop_evidence import EvidenceStopReader
OUT=Path('results/dev_aux/task2312')
def run():
 t=time.perf_counter();stop=EvidenceStopReader(Path.cwd());data=json.loads(Path('results/dev_aux/task2311/inputs.json').read_text());guide=Guide();rows=[]
 for row in data['contexts']:
  stop();c=compile_ruleset_for_execution(deserialize_ruleset(Path(row['rules']).read_text()));s=GameSession.replay(c,deserialize_game_record(json.dumps(row['root_record'])));assert not execution_differences(guide.reference,c);assert row['root_state_sha']==hashlib.sha256(repr(s.state).encode()).hexdigest()
  q=guide.rows[key(actor_state(s.state))];rows.append(dict(context=row['context'],canonical_mover_label=q['label'],canonical_rank=q['rank'],actual_status=s.result.status.value,side=s.state.position.side_to_move,occurrences=len(row['occurrences']),remaining_horizon=min(x['remaining_horizon']for x in row['occurrences'])))
 r=dict(status='PASS_POSTFREEZE_REFERENCE_STRATA_ONLY',contexts=len(rows),occurrences=len(data['occurrences']),labels=dict(Counter(q['canonical_mover_label']for q in rows)),weighted_labels={k:sum(q['occurrences']for q in rows if q['canonical_mover_label']==k)for k in('WIN','DRAW','LOSS')},rows=rows,seconds=time.perf_counter()-t,scope='ALL14frozenactualhistorycontexts from27candidateLOWattempts. Canonicalreference notactualhistoryWDLproof; no state/turn substitution, nocandidatesfiltered, nofreepolicylabels/rewards/skipgate. Frozenfullhistories/remainingHauthorityretained.')
 with(OUT/'result.json').open('x')as f:json.dump(r,f,indent=2)
 print(json.dumps(r))
if __name__=='__main__':run()
