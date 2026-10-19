"""DEV_AUX104 (AUX_CLAUDE) runner: SAME task2565 Generic code on NEW 5x5 rules.

Two hooks, both installed BEFORE importing the audited modules (they bind names at import):
- task2565.train.compiled() also loads task2588/rules-<gs>.json (task2586 hook, D repointed);
- task2565.train.CHANNELS = rule-derived channels, built as in task2525 (board P first, then the
  other non-anchor types sorted; hand types sorted). Every registered rule must yield the same tuple.
Usage: python -m results.dev_aux.task2588.run {train|audit|unpruned|evaluate|deployment} DIR
"""
from pathlib import Path
import json,sys
import results.dev_aux.task2586.run as R
D=Path('results/dev_aux/task2588');R.D=D
def channels_for(types):
 ch=tuple((kind,t)for kind in('board','hand')for t in sorted(types))
 return(('board','P'),)+tuple(x for x in ch if x!=('board','P'))
def panel_channels():
 reg=json.loads((D/'registration.json').read_text());return tuple(tuple(x)for x in reg['channels'])
def main(step,directory):
 T=R.install();T.CHANNELS=panel_channels()
 if step=='train':T.run(directory)
 else:R.main(step,directory)
if __name__=='__main__':main(sys.argv[1],sys.argv[2])
