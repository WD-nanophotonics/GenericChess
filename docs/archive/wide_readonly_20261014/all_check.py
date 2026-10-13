"""Bounded private attribution: all actual SemanticEngine.in_check callers."""
from contextlib import contextmanager
from generic_chess.core import semantic_executor as se
@contextmanager
def installed(compiled,provider):
 old=se.SemanticEngine.in_check
 fingerprint=compiled.support.ruleset_fingerprint
 def new(self,position,side,checkpoint=None):
  if self.support.ruleset_fingerprint==fingerprint:
   value=provider(position,side,checkpoint=checkpoint)
   if value is not None:return value
  return old(self,position,side,checkpoint=checkpoint)
 se.SemanticEngine.in_check=new
 try:yield
 finally:se.SemanticEngine.in_check=old
