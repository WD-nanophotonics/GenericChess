import json
from warm_adapter import ControlledEngine
class GameBarrierEngine(ControlledEngine):
 def search(self,initial,history,nodes=1024):
  j=self.journal;self.journal=None
  try:q=super().search(initial,history,nodes)
  finally:self.journal=j
  if j:j.write(json.dumps(q)+'\n');j.flush()
  return q
