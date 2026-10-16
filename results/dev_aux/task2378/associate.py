"""Post-fit reference association for BOTH first-LOW entries of the sole TRAIN gain."""
from pathlib import Path
import json,time,hashlib
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from scripts.generic_proof_rnb_bridge import actor_state
from results.dev_aux.task2153.stop_evidence import EvidenceStopReader
OUT=Path('results/dev_aux/task2378')
def key(raw):return ''.join(raw[:-1])+str(raw[-1])
def run():
 t=time.perf_counter();stop=EvidenceStopReader(Path.cwd());stop();f=Path('results/dev_aux/task2358');p=json.loads((f/'plan.json').read_text());roots={r['index']:r for r in json.loads(Path(p['input']).read_text())};games=[json.loads(x)for x in(f/'games.jsonl').read_text().splitlines()];ds=[json.loads(x)for x in(f/'decisions.jsonl').read_text().splitlines()];wanted=[]
 for price in(1.,1.5):
  g=next(g for g in games if(g['root'],g['opponent'],g['candidate_color'],g['ratio'])==(4,0,0,price));d=next(d for d in ds if d['slot']==g['slot']and d['is_candidate']and d['new_proof_attempt']);s=GameSession.replay(compile_ruleset_for_execution(deserialize_ruleset(Path(roots[4]['rules']).read_text())),deserialize_game_record(json.dumps(d['root_record'])));assert hashlib.sha256(repr(s.state).encode()).hexdigest()==d['root_state_sha'];wanted.append(dict(price=price,source_task=g['source_task'],source_slot=g['source_slot'],ply=d['ply'],root_state_sha=d['root_state_sha'],token=key(actor_state(s.state)),candidate_color=g['candidate_color'],side=s.state.position.side_to_move,actual_status=s.result.status.value,actual_attempt_source=d['source'],actual_proof_reason=d['proof_reason'],actual_game_outcome=g['outcome'],inventory=[dict(current=x.current_type_id,owner=x.owner)for x in s.state.position.board if x is not None]))
 labels={};needed={w['token']for w in wanted}
 for n,line in enumerate(Path('results/dev_aux/task2249/labels.jsonl').open(encoding='utf-8')):
  if n%1024==0:stop()
  row=json.loads(line);token=key(row['board'])
  if token in needed:labels[token]=row
 assert set(labels)==needed
 for row in wanted:
  label=labels[row['token']];row.update(canonical_next_mover_label=label['label'],canonical_rank=label['rank'],scope='CanonicalPositionreference descriptor, NOTactualhistorycertificate orreward')
 result=dict(status='PASS_BOTH_FIRST_LOW_CANONICAL_DESCRIPTORS',rows=wanted,seconds=time.perf_counter()-t,scope='Postfitdiagnosis/ALLtwofirstLOWentries ofsingleknownTRAINgain, no success/labelscreening ornewsearch. Wholeprepaidreferencealreadyexposed; actualhistoryWINrequiresoriginalindependentcertificate, unknownbaseline notrelabelledLOSS/DRAW. Doesnotestablishcausalstrategicvalue orstableprice. No reservedperformance read/priceupdate.')
 with(OUT/'association.json').open('x')as fp:json.dump(result,fp,indent=2)
 print(json.dumps(result))
if __name__=='__main__':run()
