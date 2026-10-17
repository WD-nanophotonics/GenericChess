"""Episode-frozen TDLeaf study: same trainer/search, distinct update semantics."""
from pathlib import Path
import json,hashlib
import results.dev_aux.task2492.run as trainer
from results.dev_aux.task2492.episode import TDLeafEpisode
class EpisodeAdapter(TDLeafEpisode):
 def __init__(self,eta,lam,coherence=False):
  if coherence:raise ValueError('episode study does not use TC')
  super().__init__(eta,lam)
if __name__=='__main__':
 out=Path('results/dev_aux/task2497');plan=json.loads((out/'plan.json').read_text())
 for name,h in plan['pins'].items():assert hashlib.sha256(Path(name).read_bytes()).hexdigest()==h
 trainer.OUT=out;trainer.TDLeaf=EpisodeAdapter;trainer.run()
