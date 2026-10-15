"""Independent no-search exact record/state matching of all exported proofs."""
from pathlib import Path
import json,hashlib
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record

def run():
 old=json.loads(Path('results/dev_aux/task1880/plan.json').read_text());slot=old['case']['slots'][1];game=next(json.loads(x) for x in Path('results/dev_aux/task1877/games.jsonl').read_text().splitlines() if json.loads(x)['slot']==slot);c=compile_ruleset_for_execution(deserialize_ruleset(Path('results/dev_aux/task1872/rules.json').read_text()));reports=[]
 for task in (1886,1893):
  d=json.loads(Path('results/dev_aux/task'+str(task)+'/result.json').read_text());total=matches=0
  for row in d['rows']:
   for e in row['exports']:
    assert e['verification']['verified'];total+=1;prefix=row['ply']+e['relative_ply'];record=dict(game['record']);record['actions']=record['actions'][:prefix]
    if record==e['root_record']:
     assert hashlib.sha256(repr(GameSession.replay(c,deserialize_game_record(json.dumps(record))).state).encode()).hexdigest()==e['state_sha'];matches+=1
  previous=json.loads(Path('results/dev_aux/task'+('1892' if task==1886 else '1893')+'/matching.json').read_text());assert previous['actual_matches']==matches
  reports.append(dict(task=task,verified_exports=total,actual_full_record_and_state_matches=matches))
 out=dict(status='PASS_ALL_SAVED_EXPORTS_EXACT_MATCH_RECHECK',reports=reports,new_proof_or_native_calls=0)
 with Path('results/dev_aux/task1892/recheck.json').open('x') as f:json.dump(out,f,indent=2)
 print(json.dumps(out))
if __name__=='__main__':run()
