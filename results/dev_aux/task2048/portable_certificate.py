"""One portable typed proof tree and independent all-defense consumer replay."""
from pathlib import Path
from dataclasses import asdict,replace
import json,hashlib,sys
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record,serialize_game_record
from generic_chess.session.result import SessionResult,SessionStatus
from generic_chess.core.actions import action_to_dict
from scripts.generic_session_win_proof import SessionChoice,SessionProofNode,SessionWinCertificate,verify_session_certificate,execute
from scripts.generic_session_win_proof_batch_pn import prove_session_win_batch_pn
OUT=Path('results/dev_aux/task2048')
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def save(name,v):
 with(OUT/name).open('x',encoding='utf-8')as f:json.dump(v,f,indent=2)
def session():
 plan=read('results/dev_aux/task2020/run-plan.json');c=compile_ruleset_for_execution(deserialize_ruleset(Path(plan['rules']).read_text(encoding='utf-8')));sample=read('results/dev_aux/task2046/result.json')['positive_control'];return GameSession.replay(c,deserialize_game_record(json.dumps(sample['record'])))
def encode(node):
 terminal=None if node.terminal is None else asdict(node.terminal)
 if terminal is not None:terminal['status']=node.terminal.status.value
 return dict(rank=node.rank,terminal=terminal,edges=[dict(choice=dict(kind=c.kind,action=action_to_dict(c.action)if c.action is not None else None,declaration_id=c.declaration_id),child=encode(n))for c,n in node.edges])
def decode(node,fp):
 edges=[]
 for edge in node['edges']:
  c=edge['choice'];action=None
  if c['action']is not None:action=deserialize_game_record(json.dumps(dict(schema_version=1,ruleset_fingerprint=fp,actions=[c['action']],resigned_by=None))).actions[0]
  edges.append((SessionChoice(c['kind'],action,c['declaration_id']),decode(edge['child'],fp)))
 terminal=None if node['terminal']is None else SessionResult(**{**node['terminal'],'status':SessionStatus(node['terminal']['status'])})
 return SessionProofNode(node['rank'],tuple(edges),terminal)
def build():
 s=session();r=prove_session_win_batch_pn(s,max_nodes=1024,seconds=1.5,max_depth=64);assert r.status=='PROVEN_WIN'
 old=read('results/dev_aux/task2046/result.json')['positive_control'];digest=hashlib.sha256(repr(r.certificate).encode()).hexdigest();assert digest==old['certificate_sha']
 save('certificate.json',dict(ruleset_fingerprint=r.certificate.ruleset_fingerprint,target=r.certificate.target,root_record=json.loads(serialize_game_record(r.certificate.root_record)),tree=encode(r.certificate.tree),original_certificate_sha=digest,scope='Reconstructed once from fixed existing2046 positive control, same1024budget/exact certificate SHA; not a newly selected game or reward. Typed public proof tree, no private state pickle.'))
 save('build.json',dict(status='EXACT_CERTIFICATE_RECONSTRUCTED',PN_nodes=r.nodes,PN_seconds=r.seconds,new_PN_calls=1,new_Native_calls=0))
 verify()
def verify():
 s=session();data=read('results/dev_aux/task2048/certificate.json');assert data['root_record']==json.loads(serialize_game_record(s.to_record()))and data['ruleset_fingerprint']==s.compiled.ruleset_fingerprint
 cert=SessionWinCertificate(s.compiled.ruleset_fingerprint,s.to_record(),s.state,data['target'],decode(data['tree'],s.compiled.ruleset_fingerprint));assert hashlib.sha256(repr(cert).encode()).hexdigest()==data['original_certificate_sha']
 receipt=verify_session_certificate(s,cert,max_nodes=16384,seconds=2.);assert receipt['verified']
 leaves=[];edges=0
 def walk(current,node,path):
  nonlocal edges
  if current.result.status is not SessionStatus.ONGOING:
   assert current.result.winner==cert.target and node.rank==0;leaves.append(dict(winner=current.result.winner,status=current.result.status.value,plies=len(path),record=json.loads(serialize_game_record(current.to_record()))));return
  if current.state.position.side_to_move!=cert.target:assert {x.action for x,_ in node.edges}==set(current.legal_actions())
  else:assert len(node.edges)==1
  for choice,child in node.edges:
   assert child.rank<node.rank;next_session=GameSession.replay(current.compiled,current.to_record());execute(next_session,choice);edges+=1;walk(next_session,child,path+[choice])
 walk(s,cert.tree,[])
 def omit(node):
  if len(node.edges)>1:return replace(node,edges=node.edges[:-1]),True
  changed=[];done=False
  for choice,child in node.edges:
   new,hit=omit(child)if not done else(child,False);changed.append((choice,new));done|=hit
  return replace(node,edges=tuple(changed)),done
 bad,changed=omit(cert.tree);assert changed
 rejection=verify_session_certificate(s,replace(cert,tree=bad),max_nodes=16384,seconds=2.);assert not rejection['verified']
 save('replay.json',dict(status='PASS_PORTABLE_FULL_RULE_ALL_DEFENSE_EXECUTION',verification=receipt,independent_transition_count=edges,actual_winning_leaves=leaves,omitted_defense_rejected=rejection,new_PN_or_Native_calls=0,scope='Consumer reconstructs typed certificate from JSON plus actual public root record; replays every defender response to actual win. One scoped positive tree, not a general generated-domain coverage claim or new WDL trial.'))
 print(json.dumps(dict(status='PASS_PORTABLE_FULL_RULE_ALL_DEFENSE_EXECUTION',edges=edges,winning_leaves=len(leaves),omitted_defense_rejected=True,new_PN_or_Native_calls=0)))
if __name__=='__main__':{'build':build,'verify':verify}[sys.argv[1]]()
