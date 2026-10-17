"""Rule authorities/adapters only. No material search or engine priors imported."""
from copy import copy
import chess

class ChessEnv:
 names=('P','N','B','R','Q')
 def __init__(self,board=None):self.board=chess.Board() if board is None else board.copy(stack=True)
 def player(self):return 0 if self.board.turn else 1
 def features(self):return tuple(len(self.board.pieces(t,chess.WHITE))-len(self.board.pieces(t,chess.BLACK)) for t in (1,2,3,4,5))
 def terminal(self):
  # Predeclared policy claims any available threefold/50move draw. Full stack
  # retained. Claim by intended next move is legal and common to all arms.
  o=self.board.outcome(claim_draw=True)
  return None if o is None else 0 if o.winner is None else 1 if o.winner else -1
 def actions(self):return tuple(self.board.legal_moves)
 def in_check(self):return self.board.is_check()
 def tactical(self,a):return self.board.is_capture(a) or a.promotion is not None
 def push(self,a):self.board.push(a)
 def pop(self):self.board.pop()
 def record(self):return dict(initial=self.board.root().fen(),moves=[m.uci() for m in self.board.move_stack],fen=self.board.fen())

class SessionEnv:
 """Same learner/search over FULL GameSession typed choices and history.

 Names explicitly distinguish board-current and hand-base features; no state
 quotient, converter, special game solver or table label. Adapter supports q0
 only until a generic tactical predicate is specified; caller must use qdepth0.
 """
 def __init__(self,session,channels):self.session=copy(session);self.stack=[];self.names=tuple(channels)
 def player(self):return self.session.state.position.side_to_move
 def features(self):
  from results.dev_aux.task2397.material import channels
  fs=channels(self.session.state.position,0)
  return tuple(fs[k].get(t,0) for k,t in self.names)
 def terminal(self):
  from generic_chess.session.result import SessionStatus
  r=self.session.result
  return None if r.status is SessionStatus.ONGOING else 0 if r.winner is None else 1 if r.winner==0 else -1
 def actions(self):
  from scripts.generic_session_win_proof import choices
  class Poll:
   def poll(self):pass
  return tuple(choices(self.session,Poll()))
 def in_check(self):return False # q0 only: full-depth evaluation, never generic qsearch claim
 def tactical(self,a):raise NotImplementedError('no generic qsearch admission')
 def push(self,a):
  from scripts.generic_session_win_proof import execute
  self.stack.append(self.session);self.session=copy(self.session);execute(self.session,a)
 def pop(self):self.session=self.stack.pop()
