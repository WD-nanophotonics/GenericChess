"""Experimental full-rule PN ordering only: claims stream first, actor-winning
terminal board choices then checks then other moves. No price input or action
filter. Existing PN and independent actual-Session certificate verifier retain
all authority. Not adopted into live players or product defaults.
"""
from generic_chess.session.result import SessionStatus
from generic_chess.core.attacks import is_in_check
from scripts.generic_session_win_proof_batch_pn import _children,prove_session_win_batch_pn

def ordered_children(current,b,cost):
 board=[]
 for choice,child in _children(current,b,cost):
  if choice.kind=='DECLARATION':yield choice,child
  else:board.append((choice,child))
 decorated=[]
 for ordinal,(choice,child) in enumerate(board):
  b.poll();terminal=child.result
  if terminal.status is not SessionStatus.ONGOING:
   key=0 if terminal.winner==current.state.position.side_to_move else 3
  else:key=1 if is_in_check(child.state.position,child.state.position.side_to_move,current.compiled) else 2
  b.poll();decorated.append((key,ordinal,choice,child))
 for _,_,choice,child in sorted(decorated,key=lambda r:r[:2]):
  b.poll();yield choice,child

def prove_check_first(session,**kwargs):
 if '_children_factory' in kwargs:raise ValueError('factory owned by this experimental wrapper')
 return prove_session_win_batch_pn(session,_children_factory=ordered_children,**kwargs)
