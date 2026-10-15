"""Outcome-selected integration diagnostic, never new independent WDL evidence."""
from pathlib import Path
import json,hashlib,time
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.session.serialization import deserialize_game_record,serialize_game_record
from generic_chess.session.session import GameSession
from generic_chess.session.result import SessionStatus
from scripts.generic_session_win_proof_batch_pn import prove_session_win_batch_pn
from scripts.generic_session_win_proof import SessionStrategyCursor
from scripts.generic_session_proof_bank import SessionLogicalProofBank
OUT=Path('results/dev_aux/task1857')
def run():
 calls=[json.loads(x) for x in Path('results/dev_aux/task1856/calls.jsonl').read_text().splitlines()];chosen=[x['query'] for x in calls if x['method']=='COLD' and x['adoptable_win']][:4];assert len(chosen)==4
 allqueries=[json.loads(x) for x in Path('results/dev_aux/task1848/moves.jsonl').read_text().splitlines() if json.loads(x)['proof_reason'] not in ('disabled','verified_strategy','new_proof_disabled')];games={g['slot']:g for g in (json.loads(x) for x in Path('results/dev_aux/task1848/games.jsonl').read_text().splitlines())};c=compile_ruleset_for_execution(deserialize_ruleset(Path('results/dev_aux/task1846/rules.json').read_text()));rows=[];beg=time.perf_counter()
 for qi in chosen:
  m=allqueries[qi];raw=dict(games[m['slot']]['record']);raw['actions']=raw['actions'][:m['ply']];s=GameSession.replay(c,deserialize_game_record(json.dumps(raw)));caps=m['phase_limits'];before=s.to_record();bank=SessionLogicalProofBank(prove_session_win_batch_pn)
  kw=dict(target=m['side'],max_nodes=caps['proof_nodes'],seconds=caps['proof_seconds'],max_depth=64)
  cold=prove_session_win_batch_pn(s,**kw);miss=bank.query(s,**kw,verification_max_nodes=caps['verification_nodes'],verification_seconds=caps['verification_seconds']);hit=bank.query(s,**kw,verification_max_nodes=caps['verification_nodes'],verification_seconds=caps['verification_seconds'])
  assert cold.certificate==miss.logical_result.certificate==hit.logical_result.certificate and hit.hit and hit.actual_proof_nodes==0 and hit.verification_scope=='HISTORICAL_SAME_LIMITS'
  a=SessionStrategyCursor(s,cold.certificate,max_nodes=16384,seconds=.5);b=SessionStrategyCursor(s,hit.logical_result.certificate,max_nodes=16384,seconds=.5);assert a.choose(s)==b.choose(s) and s.to_record()==before
  steps=0;rank=b.node.rank
  while s.result.status is SessionStatus.ONGOING:
   assert steps<64
   choice=b.choose(s) if s.state.position.side_to_move==b.certificate.target else b.node.edges[0][0]
   old=b.node.rank;b.commit(s,choice);assert b.node.rank<old;steps+=1
  assert s.result.winner==m['side']
  rows.append(dict(query=qi,slot=m['slot'],ply=m['ply'],target=m['side'],root_sha=hashlib.sha256(repr(before).encode()).hexdigest(),certificate_sha=hashlib.sha256(repr(cold.certificate).encode()).hexdigest(),miss_proof_nodes=miss.actual_proof_nodes,hit_proof_nodes=hit.actual_proof_nodes,consumer_nodes=b.receipt['nodes'],rank=rank,physical_steps=steps,winner=s.result.winner,record=json.loads(serialize_game_record(s.to_record()))))
 result=dict(status='PASS_ACTUAL_BANK_CONSUMER_BINDING_AND_EXECUTION',cases=len(rows),unique_records=len({x['root_sha'] for x in rows}),physical_steps=sum(x['physical_steps'] for x in rows),seconds=time.perf_counter()-beg,rows=rows,scope='4EXPOSED winning requests chosen for integration mechanism only, some duplicate records;0Native, no learning/game reward changes. Cold/miss/hit certificates and first actions match, currentconsumer verification paid, knownstrategy branch physicallywins. Not4independent statistical games or a cache-enabled price trial.')
 with (OUT/'result.json').open('x',encoding='utf-8') as f:json.dump(result,f,indent=2)
 print(json.dumps({k:v for k,v in result.items() if k!='rows'}))
if __name__=='__main__':run()
