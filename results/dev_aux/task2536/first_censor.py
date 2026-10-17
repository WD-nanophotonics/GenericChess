from pathlib import Path
from collections import Counter
import json,hashlib
from generic_chess.rules.compiler import compile_ruleset
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from results.dev_aux.task2529.training_audit import terminal
T=Path('results/dev_aux/task2534');O=Path('results/dev_aux/task2536')
def run():
 rows=T.joinpath('episodes.jsonl').read_bytes().rsplit(b'\n',1)[0].splitlines();e=next(json.loads(x)for x in rows if json.loads(x)['ending']=='HORIZON_UNKNOWN');raw=json.loads(Path(f"results/dev_aux/task2525/rules-{e['generator_seed']}.json").read_text());cc=compile_ruleset(ruleset_from_dict(raw));record=deserialize_game_record(json.dumps(e['record']));s=GameSession(cc);seen=Counter([repr(s.state.position)]);terminal_ply=None
 for ply,a in enumerate(record.actions,1):
  s.submit(a);seen[repr(s.state.position)]+=1
  if terminal(s)is not None:terminal_ply=ply
 assert s.to_record()==record and terminal(s)is None and terminal_ply is None
 out=dict(status='PASS_FIRST_ACTUAL_H128_RECORD_DIAGNOSIS',rule=e['generator_seed'],method=e['method'],seed=e['seed'],game=e['game'],source_record_sha=hashlib.sha256(json.dumps(e['record'],sort_keys=True).encode()).hexdigest(),prefix_plies=len(e['initial_record']['actions']),actual_play_plies=len(record.actions)-len(e['initial_record']['actions']),observed_positions=len(record.actions)+1,distinct_full_Position_repr=len(seen),maximum_equal_Position_repr_occurrences=max(seen.values()),repeated_Position_occurrences=sum(n-1 for n in seen.values()),actual_terminal_at_horizon=False,declared_repetition_limit=raw['repetition_limit'],declared_max_ply=raw['max_ply'],rule_top_keys=list(raw),scope='FIRSTreturnedHORIZON_UNKNOWN exposedTRAINrecord; fullpublicsubmit/replay, noquery orcontinuation/relabelling/filtering. Positionrepr includesPosition fields but NOT completeSessionhistory; equality here is a repetitiondiagnostic NOTstatequotient/drawproof orallfuturecycleproof. OriginalH128U andrulecap remainunchanged.')
 (O/'first-censor-diagnosis.json').write_text(json.dumps(out,indent=2));print(json.dumps(out))

if __name__=='__main__':run()
