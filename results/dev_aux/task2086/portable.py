"""Portable export and independent existing-verifier/cursor consumption."""
from pathlib import Path
from dataclasses import replace
import json,hashlib,time,sys
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.session.result import SessionStatus
from scripts.generic_session_win_proof import SessionWinCertificate,verify_session_certificate,SessionStrategyCursor
from results.dev_aux.task2048.portable_certificate import encode,decode
from results.dev_aux.task2068.teacher import CanonicalTeacher
from results.dev_aux.task2086.rank_certificate import RankCertificateProvider
OUT=Path('results/dev_aux/task2086')
def build():
 start=time.perf_counter();teacher=CanonicalTeacher('results/dev_aux/task2056','results/dev_aux/task2058','results/dev_aux/task2059');provider=RankCertificateProvider(teacher);cases=json.loads(Path('results/dev_aux/task2084/cases.json').read_text());plan=json.loads(Path('results/dev_aux/task2063/run-plan.json').read_text());games=[json.loads(x)for x in Path('results/dev_aux/task2063/games.jsonl').read_text().splitlines()];data=[]
 for case in cases:
  rules=plan['roots'][games[case['source_slot']]['family']]['rules'];c=compile_ruleset_for_execution(deserialize_ruleset(Path(rules).read_text()));s=GameSession.replay(c,deserialize_game_record(json.dumps(case['root_record'])));r=provider(s,target=case['target'],max_nodes=1024,seconds=1.5,max_depth=64);assert r.status=='PROVEN_WIN'and r.nodes<=1024
  data.append(dict(rules=rules,target=r.certificate.target,root_record=case['root_record'],tree=encode(r.certificate.tree),certificate_sha=hashlib.sha256(repr(r.certificate).encode()).hexdigest(),build_nodes=r.nodes,build_seconds=r.seconds,source_slot=case['source_slot'],source_ply=case['source_ply']))
 (OUT/'certificates.json').write_text(json.dumps(data,indent=2));(OUT/'build.json').write_text(json.dumps(dict(status='COMPLETE_EXISTING_TYPED_CERTIFICATE_EXPORT',cases=len(data),nodes=sum(x['build_nodes']for x in data),query_seconds=sum(x['build_seconds']for x in data),total_with_teacher_load_seconds=time.perf_counter()-start,scope='8EXPOSEDfailureexamples, unchanged1024/1.5squerycap; tablebuildpreviouslypaid50.27s, notfree. Noactivepolicy/default/NN changes; notgeneralrulecoverage.'),indent=2));verify()
def verify():
 data=json.loads((OUT/'certificates.json').read_text());receipts=[];moves=0;bad_rejected=False
 for row in data:
  c=compile_ruleset_for_execution(deserialize_ruleset(Path(row['rules']).read_text()));s=GameSession.replay(c,deserialize_game_record(json.dumps(row['root_record'])));cert=SessionWinCertificate(c.ruleset_fingerprint,s.to_record(),s.state,row['target'],decode(row['tree'],c.ruleset_fingerprint));assert hashlib.sha256(repr(cert).encode()).hexdigest()==row['certificate_sha'];cursor=SessionStrategyCursor(s,cert,max_nodes=16384,seconds=.5);receipts.append(cursor.receipt)
  while s.result.status is SessionStatus.ONGOING:
   choice=cursor.choose(s)if s.state.position.side_to_move==cert.target else max(cursor.node.edges,key=lambda e:e[1].rank)[0];cursor.commit(s,choice);moves+=1;replay=GameSession.replay(c,s.to_record());assert replay.state==s.state and replay.result==s.result
  assert s.result.winner==cert.target
  wrong=replace(cert,root_record=s.to_record());rejection=verify_session_certificate(GameSession.replay(c,deserialize_game_record(json.dumps(row['root_record']))),wrong,max_nodes=16384,seconds=.5);assert not rejection['verified'];bad_rejected=True
 result=dict(status='PASS_PORTABLE_EXISTING_VERIFIER_AND_CURSOR',certificates=len(data),verification_nodes=sum(r['nodes']for r in receipts),verification_seconds=sum(r['seconds']for r in receipts),actual_cursor_moves=moves,actual_checkmates=len(data),wrong_root_record_rejected=bad_rejected,new_PN_or_Native_calls=0,scope='ExistingtypedSessionWinCertificate plusindependentSessionverifier andSessionStrategyCursor, fullhistoricalrecord binding andalllegaldefenses. 8scopedpositiveexamples; no96gamequalityclaim/generalMateSolvercompletion. Source-onlyconsumerdoesnot regeneratecertificates.')
 (OUT/'replay.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
if __name__=='__main__':{'build':build,'verify':verify}[sys.argv[1]]()
