"""Late consumer: execute the already-issued10 full-history certificates."""
from pathlib import Path
import json
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.session.result import SessionStatus
from scripts.generic_session_win_proof import SessionWinCertificate,SessionStrategyCursor
from results.dev_aux.task2048.portable_certificate import decode
OUT=Path('results/dev_aux/task2114')
def run():
 rows=json.loads(Path('results/dev_aux/task2091/certificates.json').read_text(encoding='utf-8'));moves=0;receipts=[]
 for r in rows:
  c=compile_ruleset_for_execution(deserialize_ruleset(Path(r['rules']).read_text(encoding='utf-8')));s=GameSession.replay(c,deserialize_game_record(json.dumps(r['root_record'])));assert max(n for _,n in s.state.repetition_counts)==2;cert=SessionWinCertificate(c.ruleset_fingerprint,s.to_record(),s.state,r['target'],decode(r['tree'],c.ruleset_fingerprint));cursor=SessionStrategyCursor(s,cert,max_nodes=16384,seconds=.5);receipts.append(cursor.receipt)
  while s.result.status is SessionStatus.ONGOING:
   a=cursor.choose(s)if s.state.position.side_to_move==r['target']else max(cursor.node.edges,key=lambda e:e[1].rank)[0];before=cursor.node.rank;cursor.commit(s,a);assert cursor.node.rank<before;replayed=GameSession.replay(c,s.to_record());assert replayed.state==s.state and replayed.result==s.result;moves+=1
  assert s.result.winner==r['target']
 result=dict(status='PASS_EXISTING_FULL_HISTORY_CURSOR_EXECUTION',certificates=len(rows),actual_checkmates=len(rows),actual_moves=moves,verification_nodes=sum(r['nodes']for r in receipts),new_PN_or_certificate_construction=0,scope='LateconsumerafterSource/Evidence71sealed; directGitandLATEarchive. Alreadyissued2091certs, genuinepriorrepeat2history, existingindependentverifierandcursor/longest-rankdefenses, no newfitnessgames/oldcapchange.')
 (OUT/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result))
if __name__=='__main__':run()
