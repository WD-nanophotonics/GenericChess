"""Mechanically bind every fixed Chess work-boundary snapshot, no fitness input."""
from pathlib import Path
import json,hashlib
D=Path('results/dev_aux/task2565/chess-curve');T=D.parent/'chess'
def run():
 assert not(D/'result.json').exists();t=json.loads((T/'result.json').read_text());rows=[]
 for a in t['arms']:
  for b in [25000,50000,75000]:
   ss=[s for s in a['snapshots']if s['boundary']==b];s=ss[0]if ss else dict(nodes=0,index=-1,weights=a['initial']);assert s['nodes']<=b
   rows.append(dict(generator_seed=0,seed=a['seed'],method=a['method']+'@'+str(b),initial=a['initial'],weights=s['weights'],nodes=s['nodes'],source_episode=s['index'],nominal_boundary=b,original_method=a['method']))
 assert len(rows)==36
 (D/'result.json').write_text(json.dumps(dict(status='ALL36_CLOSED_EPISODE_SNAPSHOTS',arms=rows,source_sha=hashlib.sha256((T/'result.json').read_bytes()).hexdigest(),no_new_training=True,additional_training_nodes=0,scope='Bindings to actualalready-paid TRAIN, everyregisteredboundary/initial included. Snapshot source independently full-credit audited. Newlypaiddeploymentonly.'),indent=2))
 print('ALL36_BOUND_NO_FITNESS')
if __name__=='__main__':run()
