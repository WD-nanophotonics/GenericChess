"""Independent saved-record/certificate consumers; no player/fit producers."""
from pathlib import Path
from collections import Counter,defaultdict
from copy import copy
import json,hashlib,time
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record,serialize_game_record
from generic_chess.session.result import SessionStatus
from scripts.generic_session_win_proof import SessionChoice,SessionWinCertificate,verify_session_certificate,execute
from results.dev_aux.task2205.consume import decode_graph
from results.dev_aux.task2048.portable_certificate import decode as decode_tree
from results.dev_aux.task2199.semantic_graph import verify_graph,GraphStrategyCursor
from results.dev_aux.task2175.receipt import choice_value
from results.dev_aux.task2153.stop_evidence import EvidenceStopReader
OUT=Path('results/dev_aux/task2252')
def read(p):return json.loads(Path(p).read_text())
def run():
 assert not(OUT/'result.json').exists();start=time.perf_counter();stop=EvidenceStopReader(Path.cwd());deadline=start+300
 def cancel():stop();return time.perf_counter()>=deadline
 folder=Path('results/dev_aux/task2247');plan=read(folder/'plan.json');done=read(folder/'completion.json');roots={r['index']:r for r in read(plan['input'])};games=[json.loads(l)for l in(folder/'games.jsonl').read_text().splitlines()];decisions=[json.loads(l)for l in(folder/'decisions.jsonl').read_text().splitlines()];certs=[json.loads(l)for l in(folder/'certificates.jsonl').read_text().splitlines()];by=defaultdict(list)
 assert done['status']=='COMPLETE'and len(games)==16 and len(decisions)==done['decisions']and len(certs)==done['certificates'];normal=Counter();sources=Counter();steps=0
 for d in decisions:by[d['slot']].append(d)
 for g in games:
  cancel();root=roots[g['root']];c=compile_ruleset_for_execution(deserialize_ruleset(Path(root['rules']).read_text()));s=GameSession.replay(c,deserialize_game_record(json.dumps(root['record'])));actions=deserialize_game_record(json.dumps(g['record'])).actions;assert len(actions)==g['plies']==len(by[g['slot']])
  for i,(a,d)in enumerate(zip(actions,by[g['slot']])):
   assert d['ply']==i and d['root_record']==json.loads(serialize_game_record(s.to_record()))and d['root_state_sha']==hashlib.sha256(repr(s.state).encode()).hexdigest();assert d['choice']==choice_value(SessionChoice('ACTION',action=a));assert d['side']==s.state.position.side_to_move and d['is_candidate']==(d['side']==g['candidate_color']);assert d['normal_visits']<=512 and d['graph_positions']<=4096
   if d['source']in('VERIFIED_GRAPH_STRATEGY','VERIFIED_FULL_HISTORY_STRATEGY'):
    receipts=d['verification_receipts'];assert any(r[1]=='INDEPENDENT'and r[2]['verified']for r in receipts)and any(r[1]=='CURRENT_CURSOR'and r[2]['verified']for r in receipts)
   if d['normal_receipt']is not None:normal[d['normal_receipt']['completed_depth']]+=1
   sources[d['source']]+=1;s.submit(a);steps+=1
  assert json.loads(serialize_game_record(s.to_record()))==g['record']and s.result.status.value==g['actual_status']and s.result.winner==g['winner'];assert g['reward']==(0 if s.result.winner is None else 1 if s.result.winner==g['candidate_color']else-1)and s.result.status is not SessionStatus.ONGOING
 pilot_certificates=[]
 for row in certs:
  g=games[row['slot']];root=roots[g['root']];c=compile_ruleset_for_execution(deserialize_ruleset(Path(root['rules']).read_text()));s=GameSession.replay(c,deserialize_game_record(json.dumps(row['root_record'])))
  if row['kind']=='GRAPH':
   cert=decode_graph(s,row['certificate']);v=verify_graph(s,cert,max_nodes=65536,seconds=5.,cancel=cancel);assert v['verified'];cursor=GraphStrategyCursor(s,cert,max_nodes=65536,seconds=5.,cancel=cancel)
   for a in deserialize_game_record(json.dumps(g['record'])).actions[row['ply']:]:
    before=copy(s);choice=SessionChoice('ACTION',action=a)
    if s.state.position.side_to_move==cert.target:assert cursor.choose(s)==choice
    execute(s,choice);cursor.observe(before,choice,s)
  else:
   cert=SessionWinCertificate(c.ruleset_fingerprint,s.to_record(),s.state,row['side'],decode_tree(row['certificate'],c.ruleset_fingerprint));v=verify_session_certificate(s,cert,max_nodes=65536,seconds=5.,cancel=cancel);assert v['verified'];s=GameSession.replay(c,deserialize_game_record(json.dumps(g['record'])))
  assert s.result.status is not SessionStatus.ONGOING and s.result.winner==row['side'];pilot_certificates.append(dict(slot=row['slot'],ply=row['ply'],kind=row['kind'],verification=v,actual_converted=True))
 # All posthoc first-entry records/certificates, with actual prehistory intact.
 folder=Path('results/dev_aux/task2246');entries=[json.loads(l)for l in(folder/'queries.jsonl').read_text().splitlines()];saved={r['slot']:r for r in map(json.loads,(folder/'certificates.jsonl').read_text().splitlines())};source_games={g['slot']:g for g in map(json.loads,Path('results/dev_aux/task2230/games.jsonl').read_text().splitlines())if g['context']==2228};entryroots={r['family']:r for r in read('results/dev_aux/task2228/inputs.json')['roots']};entrychecks=[]
 assert len(entries)==128
 for row in entries:
  cancel();g=source_games[row['slot']]
  if not row['positive_entry_verified']:continue
  root=entryroots[g['family']];c=compile_ruleset_for_execution(deserialize_ruleset(Path(root['rules']).read_text()));s=GameSession.replay(c,deserialize_game_record(json.dumps(row['root_record'])));assert hashlib.sha256(repr(s.state).encode()).hexdigest()==row['root_state_sha'];cert=decode_graph(s,saved[row['slot']]['certificate']);assert cert.target==g['candidate_color'];v=verify_graph(s,cert,max_nodes=65536,seconds=5.,cancel=cancel);assert v['verified'];cursor=GraphStrategyCursor(s,cert,max_nodes=65536,seconds=5.,cancel=cancel)
  for a in deserialize_game_record(json.dumps(g['record'])).actions[row['first_entry_ply']:]:
   before=copy(s);choice=SessionChoice('ACTION',action=a)
   if s.state.position.side_to_move==cert.target:assert cursor.choose(s)==choice
   execute(s,choice);cursor.observe(before,choice,s)
  assert s.result.status is not SessionStatus.ONGOING and s.result.winner==g['candidate_color']and g['outcome']=='W'and row['actual_cursor_converted'];entrychecks.append(dict(slot=row['slot'],verification=v,actual_cursor_converted=True))
 result=dict(status='PASS_CLOSED_GENERIC_POLICY_AND_ACTUAL_ENTRY_PROOFS',pilot_actual_games=len(games),pilot_actual_moves=steps,pilot_sources=dict(sources),pilot_normal_completed_depths=dict(normal),pilot_certificates=pilot_certificates,pilot_price_outcomes={str(x):dict(WLD=dict(Counter(g['outcome']for g in games if g['ratio']==x)),mean_W_minus_L=sum(g['reward']for g in games if g['ratio']==x)/sum(g['ratio']==x for g in games))for x in(1.,2.)},posthoc_entry_rows=len(entries),posthoc_entry_proofs=len(entrychecks),posthoc_entry_checks=entrychecks,seconds=time.perf_counter()-start,scope='ClosedactualrecordreplayandgenericfullPosition/historyboundverifiers+executablecursor. No playerproducers/fit/newstatisticalgames; posthocentrytableguidedconstructionnotonlinegenericdiscovery.16smallpilotpolicytransfer,notlearnedgeneralratio; guideandgenericprotocolsnotpooled.')
 (OUT/'result.json').write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items()if k not in('pilot_certificates','posthoc_entry_checks')}))
if __name__=='__main__':run()
