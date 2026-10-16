"""Closed73 records/certificates and336node-only checks; no study producers."""
from pathlib import Path
import json,time,sys
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.session.result import SessionStatus
from scripts.generic_session_win_proof import SessionWinCertificate,SessionStrategyCursor,verify_session_certificate
from results.dev_aux.task2048.portable_certificate import decode
OUT=Path('.replay_output73')
def run():
 OUT.mkdir(exist_ok=False);start=time.perf_counter();summary={}
 from results.dev_aux.task2140 import audit as first
 first.OUT=OUT/'first';first.OUT.mkdir();first.audit(2139);summary['2139_actual_records']='544logical496physical146certificates'
 from results.dev_aux.task2150 import audit as second
 second.OUT=OUT/'second';second.OUT.mkdir();second.audit(2149);summary['2149_actual_records']='928logical848physical159certificates'
 from results.dev_aux.task2144 import audit_journal as journal
 journal.OUT=OUT/'journal';journal.OUT.mkdir();journal.run();summary['all6045_precommit_decisions']='PASS'
 from results.dev_aux.task2151 import audit_panel as panel
 panel.OUT=OUT/'panel';panel.OUT.mkdir();panel.run();summary['puregeneric_saved_queries']='576rows65certificates'
 from results.dev_aux.task2154 import attribute
 attribute.OUT=OUT/'attribute';attribute.OUT.mkdir();attribute.run();summary['paired_actual_price_attribution']='PASS'
 from results.dev_aux.task2159 import audit as enriched
 enriched.OUT=OUT/'enriched';enriched.OUT.mkdir();enriched.audit(2158);summary['2158_conditional_price_active_actual_records']='PASS_actualrecords_and_savedcertificates_nullDEVskip_checked'
 from results.dev_aux.task2160 import audit_decisions as latejournal
 latejournal.OUT=OUT/'latejournal';latejournal.OUT.mkdir();latejournal.run();summary['all15179_late_precommit_decisions_and_actual_fallback']='PASS'
 from results.dev_aux.task2156 import audit_inputs as inputs
 inputs.OUT=OUT/'inputs';inputs.OUT.mkdir();deadline=time.perf_counter()+180;inputs.audit(cancel=lambda:time.perf_counter()>=deadline);summary['price_active_inputs']='140candidates1992nodes336normalnode-onlyqueries'
 count=moves=0
 for r in json.loads(Path('results/dev_aux/task2143/certificates.json').read_text(encoding='utf-8')):
  c=compile_ruleset_for_execution(deserialize_ruleset(Path(r['rules']).read_text(encoding='utf-8')));s=GameSession.replay(c,deserialize_game_record(json.dumps(r['root_record'])));cert=SessionWinCertificate(c.ruleset_fingerprint,s.to_record(),s.state,r['target'],decode(r['tree'],c.ruleset_fingerprint));cursor=SessionStrategyCursor(s,cert,max_nodes=131072,seconds=4.)
  while s.result.status is SessionStatus.ONGOING:
   choice=cursor.choose(s)if s.state.position.side_to_move==r['target']else max(cursor.node.edges,key=lambda e:e[1].rank)[0];cursor.commit(s,choice);moves+=1
  assert s.result.winner==r['target'];count+=1
 summary.update(min_rank_tree_saved_certificates=count,min_rank_tree_actual_cursor_moves=moves,status='PASS_CLOSED73_SOURCE_AND_EVIDENCE_CONSUMERS',seconds=time.perf_counter()-start,scope='No studyprover/fit/gameproducer orcapreset; closedrecords/savedcertificates+336normalalgorithmchecks. Separatepytestfixturesinvokeonlytheirboundedtinyprovers. CurrenthostPython/OSunbundled. No liveSlack/accountreads or externalprivatebridgeimport.')
 assert 'generic_chess.learning.alphasho_bridge'not in sys.modules
 (OUT/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8');print(json.dumps(summary),flush=True)
if __name__=='__main__':run()
