"""Consume saved PN/graph certificates and actual records; no producer rerun."""
from pathlib import Path
from dataclasses import replace
from collections import Counter
import json,time,hashlib
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.core.pieces import Piece
from generic_chess.core.actions import action_from_dict
from generic_chess.session.session import GameSession
from generic_chess.session.result import SessionResult,SessionStatus
from generic_chess.session.serialization import deserialize_game_record
from scripts.generic_session_win_proof import SessionChoice,SessionWinCertificate,verify_session_certificate
from scripts.generic_proof_rnb_bridge import actor_state,uci
from scripts.generic_royal_actor import RoyalActor
from scripts.generic_win_proof import _same_state
from results.dev_aux.task2048.portable_certificate import decode
from results.dev_aux.task2179.graph import GraphCertificate,GraphNode,verify_graph
from results.dev_aux.task2153.stop_evidence import EvidenceStopReader
OUT=Path('results/dev_aux/task2182')
def root_session(root):
 c=compile_ruleset_for_execution(deserialize_ruleset(Path(root['rules']).read_text(encoding='utf-8')));board=tuple(None if ch=='.'else Piece(int(ch.islower()),ch.upper(),ch.upper())for ch in root['root'][:-1]);c=replace(c,initial_position=replace(c.initial_position,board=board,side_to_move=0),initial_setup_positions={});s=GameSession(c);assert s.result.status is SessionStatus.ONGOING and actor_state(s.state)==tuple(root['root'])and hashlib.sha256(repr(s.state).encode()).hexdigest()==root['root_state_sha'];return s

def graph_decode(raw,s):
 nodes=[]
 for n in raw['nodes']:
  terminal=None if n['terminal']is None else SessionResult(SessionStatus(n['terminal']['status']),n['terminal']['winner']);edges=tuple((SessionChoice('ACTION',action=action_from_dict(e['action'])),e['child'])for e in n['edges']);nodes.append(GraphNode(n['rank'],edges,terminal))
 return GraphCertificate(s.compiled.ruleset_fingerprint,s.to_record(),s.state,raw['target'],tuple(nodes))

def audit(cancel=None):
 start=time.perf_counter();deadline=start+180;stop=EvidenceStopReader(Path.cwd())if cancel is None else None
 def check():
  if stop:stop()
  if time.perf_counter()>=deadline or(cancel is not None and cancel()):raise TimeoutError('180consumer cap')
 roots=json.loads(Path('results/dev_aux/task2177/inputs.json').read_text(encoding='utf-8'))['roots'];actor=RoyalActor(4);counts=Counter();summaries={}
 for task in(2177,2181):
  folder=Path(f'results/dev_aux/task{task}');rows=list(map(json.loads,(folder/'queries.jsonl').read_text(encoding='utf-8').splitlines()));completion=json.loads((folder/'completion.json').read_text(encoding='utf-8'));certs=list(map(json.loads,(folder/'certificates.jsonl').read_text(encoding='utf-8').splitlines()));assert len(rows)==completion['queries'];by={(r['query']if task==2177 else r['family']):r for r in certs};order=[]
  for root in roots:
   if task==2177:
    p=json.loads((folder/'plan.json').read_text(encoding='utf-8'));off=(root['family']+root['target'])%4;order.extend((root['family'],e)for e in(p['envelopes'][off:]+p['envelopes'][:off]))
   else:order.append((root['family'],None))
  for i,row in enumerate(rows):
   check();root=roots[row['family']];assert row['family']==order[i][0]and row['target']==root['target'];s=root_session(root)
   if task==2177:assert row['envelope']==order[i][1]and row['nodes']<=row['envelope']['nodes']
   else:assert row['positions']<=8192 and row['expanded']<=8192 and row['transitions']<=65536
   key=i if task==2177 else row['family'];raw=by.get(key)
   if raw is not None:
    assert _same_state(deserialize_game_record(json.dumps(raw['root_record'])),s.to_record())
    if task==2177:
     cert=SessionWinCertificate(s.compiled.ruleset_fingerprint,s.to_record(),s.state,root['target'],decode(raw['tree'],s.compiled.ruleset_fingerprint));vr=verify_session_certificate(s,cert,max_nodes=131072,seconds=4.)
    else:vr=verify_graph(s,graph_decode(raw['certificate'],s),max_nodes=65536,seconds=4.)
    assert vr['verified'];assert root['label']!='DRAW';counts[str(task)+'_certificates']+=1;counts[str(task)+'_offline_verify_nodes']+=vr['nodes']
   actual=row.get('actual_mate')
   if actual is not None:
    assert raw is not None;rec=deserialize_game_record(json.dumps(actual['record']))
    for a in rec.actions:
     legal={uci(x):x for x in s.legal_actions()};literal=dict(actor.moves(actor_state(s.state)));assert set(legal)==set(literal)and uci(a)in legal;s.submit(a);assert actor_state(s.state)==literal[uci(a)];counts['actual_moves']+=1
    assert s.result.status is not SessionStatus.ONGOING and s.result.winner==root['target']==actual['winner']and len(rec.actions)==actual['moves'];replayed=GameSession.replay(s.compiled,rec);assert _same_state(replayed.state,s.state)and replayed.result==s.result;counts[str(task)+'_actual_mates']+=1
  assert len(certs)==counts[str(task)+'_certificates'];summaries[str(task)]=dict(queries=len(rows),missing=(248 if task==2177 else 62)-len(rows),actual_mates=counts[str(task)+'_actual_mates'])
 result=dict(status='PASS_ALL_SAVED_CERTIFICATES_CANONICAL_CONTEXTS_AND_ACTUAL_RECORDS',counts=dict(counts),studies=summaries,seconds=time.perf_counter()-start,new_proof_queries_or_training_or_games=0,scope='Independent savedartifact consumer. Verifiers execute bounded rules; no producer/proofsearch rerun or capreset. Graph rootadmissionfix doesnotchange ongoingcanonical benchmark contexts. Timingnotreproduced.');(OUT/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result),flush=True)
if __name__=='__main__':audit()
