from pathlib import Path
from copy import copy
import json,time
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record,serialize_game_record
from generic_chess.session.result import SessionStatus
from scripts.generic_session_win_proof import SessionWinCertificate,SessionStrategyCursor,SessionChoice
from scripts.generic_session_phase_player import PhaseLimits
from scripts.generic_session_proof_player import commit_session_decision
from scripts.generic_win_proof import _same_state
from results.dev_aux.task2048.portable_certificate import decode
from results.dev_aux.task2136.legal_fallback import LegalFallbackPhasePlayer
from results.dev_aux.task2131.stop_reader import ParsedStopReader
from results.dev_aux.task2100.campaign import evaluate
OUT=Path('results/dev_aux/task2137')
def run():
 if(OUT/'result.json').exists():raise RuntimeError('one diagnostic only')
 start=time.perf_counter();deadline=start+60;stop=ParsedStopReader(Path.cwd())
 def cancelled():stop();return time.perf_counter()>=deadline
 root=Path('results/dev_aux/task2134');g=json.loads((root/'games.jsonl').read_text().splitlines()[-1]);assert g['physical_id']==340 and g['outcome']=='UNKNOWN';r=json.loads((root/'inputs.json').read_text())['roots'][g['family']];c=compile_ruleset_for_execution(deserialize_ruleset(Path(r['rules']).read_text(encoding='utf-8')));failed=GameSession.replay(c,deserialize_game_record(json.dumps(g['record'])));data=[json.loads(x)for x in(root/'certificates.jsonl').read_text().splitlines()if json.loads(x)['physical_id']==340][-1];s=GameSession.replay(c,deserialize_game_record(json.dumps(data['root_record'])));cert=SessionWinCertificate(c.ruleset_fingerprint,s.to_record(),s.state,data['target'],decode(data['tree'],c.ruleset_fingerprint));cursor=SessionStrategyCursor(s,cert,max_nodes=65536,seconds=2.,cancel=cancelled)
 for a in failed.to_record().actions[len(s.to_record().actions):]:cursor.commit(s,SessionChoice('ACTION',action=a))
 assert _same_state(s.state,failed.state)and _same_state(s.to_record(),failed.to_record());rank_before=cursor.node.rank;player=LegalFallbackPhasePlayer(c,evaluate(1.),proof_enabled=False,max_depth=2,limits=PhaseLimits(normal_seconds=0.));steps=[]
 while s.result.status is SessionStatus.ONGOING:
  if cancelled():raise TimeoutError('new60cap')
  if s.state.position.side_to_move==data['target']:
   choice=cursor.choose(s);cursor.commit(s,choice);steps.append(dict(source='EXISTING_CERTIFICATE_CONTINUATION',rank=cursor.node.rank))
  else:
   before=copy(s);d=player.choose(s,max_nodes=64,seconds=.75,cancel=cancelled);assert d.choice is not None and d.source=='PRECOMPUTED_LEGAL_FALLBACK';commit_session_decision(s,d,cancel=cancelled);cursor.observe(before,d.choice,s);steps.append(dict(source=d.source,seconds=d.seconds,normal_seconds=d.normal_seconds,completed_depth=None if d.normal_receipt is None else d.normal_receipt.completed_depth,rank=cursor.node.rank))
 assert s.result.winner==data['target'];result=dict(status='PASS_SEPARATE_DIAGNOSTIC_ACTUAL_MATE_AFTER_ZERO_NORMAL_FALLBACK',original2134_outcome='UNKNOWN_RETAINED',original2134_selector=None,original2134_DEV=0,new_diagnostic_moves=len(steps),target=data['target'],actual_result=dict(status=s.result.status.value,winner=s.result.winner),remaining_certificate_rank_before=rank_before,original_certification_receipt=cursor.receipt,steps=steps,seconds=time.perf_counter()-start,new_PN_or_pricefit=0,scope='Changedpolicy diagnosticbranchfromclosedpartialprefix, notoldexperimentcompletion/fitness/sample. Oldrecord/cap/UNKNOWN unchanged. Existingproofcursorobservesrealpubliclegalopponentfallback, realmateonly.')
 (OUT/'actual-record.json').write_text(serialize_game_record(s.to_record()),encoding='utf-8');(OUT/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result))
if __name__=='__main__':run()
