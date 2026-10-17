"""Opt-in generic terminal guard; frozen86/87 Chess adapter bytes stay original."""
from results.dev_aux.task2492.adapters import SessionEnv
from generic_chess.session.result import SessionStatus
class NonScoringTerminal(RuntimeError):
 def __init__(self,result):
  self.result=result
  super().__init__('Non-scoring terminal is not W/L/D: '+result.status.value+'/'+str(result.declaration_outcome))
class ScoringSessionEnv(SessionEnv):
 def terminal(self):
  result=self.session.result
  if result.status is SessionStatus.NO_CONTEST or result.declaration_outcome in('RESTART','NO_CONTEST'):
   raise NonScoringTerminal(result)
  return super().terminal()
