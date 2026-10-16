"""Concrete risk control: Session-only declaration vs board sibling isolation."""
from pathlib import Path
from dataclasses import replace
from copy import copy
import sys,importlib.util
sys.path.insert(0,str(Path('tests').resolve()))
sys.path.insert(0,str(Path('tests/development').resolve()))
from test_generic_session_win_proof import session,claim
from generic_chess.session.session import GameSession
from scripts.generic_session_win_proof import prove_session_win,replay_bound,execute,verify_session_certificate
from scripts.generic_win_proof import _same_state
from results.dev_aux.task2145.verify import verify_prefix_session_certificate

def snapshot(s):return(s.state,s.to_record(),s.result,s._search_witnesses)
def same(s,v):assert all(_same_state(a,b)for a,b in zip(snapshot(s),v))

def test_declaration_board_siblings_keep_full_record_result_and_witnesses_in_both_orders():
 caller=session(claim(1,'LOSS'),k=0,b=2,r=10,turn=1);original=snapshot(caller)
 cert=prove_session_win(caller,target=0,max_nodes=65536,max_depth=8,seconds=3.).certificate
 assert cert is not None and len(cert.tree.edges)>=2
 declaration=next(c for c,n in cert.tree.edges if c.kind=='DECLARATION')
 board=next(c for c,n in cert.tree.edges if c.kind=='ACTION')
 for order in((declaration,board),(board,declaration)):
  parent=replay_bound(caller);assert parent is not caller;bound=snapshot(parent);prior=[]
  for choice in order:
   child=copy(parent);execute(child,choice)
   independent=GameSession.replay(caller.compiled,parent.to_record());execute(independent,choice)
   assert all(_same_state(a,b)for a,b in zip(snapshot(child),snapshot(independent)))
   same(parent,bound);same(caller,original)
   for earlier,v in prior:same(earlier,v)
   if choice.kind=='DECLARATION':
    assert _same_state(child.state,parent.state)and child.to_record()!=parent.to_record()and child.result!=parent.result
   prior.append((child,snapshot(child)))
  variant=replace(cert,tree=replace(cert.tree,edges=tuple(reversed(cert.tree.edges))))if order[0]is board else cert
  for fn in(verify_session_certificate,verify_prefix_session_certificate):
   r=fn(caller,variant,max_nodes=65536,seconds=3.);assert r['verified'];same(caller,original)

def test_prefix_verifier_never_copies_the_callers_session(monkeypatch):
 import results.dev_aux.task2145.verify as verifier
 caller=session(claim(1,'LOSS'),k=0,b=2,r=10,turn=1);cert=prove_session_win(caller,target=0,max_nodes=65536,max_depth=8,seconds=3.).certificate
 assert cert is not None
 copied=[];realcopy=verifier.copy
 def tracked(source):
  assert source is not caller
  copied.append(source)
  return realcopy(source)
 monkeypatch.setattr(verifier,'copy',tracked)
 r=verifier.verify_prefix_session_certificate(caller,cert,max_nodes=65536,seconds=3.)
 assert r['verified']and len(copied)==r['session_transitions']and copied
