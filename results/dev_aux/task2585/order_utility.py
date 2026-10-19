"""Existing-record cross-check (Dot reply 1792397818.663009): per seed/checkpoint,
SC-Fx descriptive order-score difference beside paired W-L per prefix/foe.
No new games, no selection; order is descriptive only (external P<(N,B)<R<Q)."""
from pathlib import Path
import json,itertools
from results.dev_aux.task2568.summary import contrast
E=Path('results/dev_aux/task2584')
PAIRS=[(0,1),(0,2),(0,3),(0,4),(1,3),(2,3),(1,4),(2,4),(3,4)]
def score(w):return sum(w[a]<w[b]for a,b in PAIRS)
def run():
 ep=json.loads((E/'eval-plan.json').read_text());bind=json.loads((E/'result.json').read_text());rows={tuple(g['slot']):g for g in map(json.loads,(E/'eval-games.jsonl').open())}
 W={(a['method'],a['seed']):a['weights']for a in bind['arms']};seeds=sorted({a['seed']for a in bind['arms']});cells=[]
 for b,s,p,o in itertools.product(('1.25M','2.5M'),seeds,(8,64),ep['foes']):
  sc,fx=f'SelfCandidate@{b}|plain',f'Fixednu@{b}|plain';slots=[x for x in ep['slots']if x[1]==s and ep['root_recipes'][str(x[2])]['plies']==p and x[5]==o]
  c=contrast(rows,slots,sc,fx);d=score(W[sc,s])-score(W[fx,s])
  cells.append(dict(checkpoint=b,seed=s,prefix=p,foe=o,order_SC=score(W[sc,s]),order_Fx=score(W[fx,s]),order_diff=d,WL_diff=c['bounds'],n=c['n'],counts=c['counts']))
 counter=[c for c in cells if c['order_diff']>0 and c['WL_diff'][1]<0]
 agree=[c for c in cells if c['order_diff']>0 and c['WL_diff'][0]>0]
 init={}
 for p,o in itertools.product((8,64),ep['foes']):
  cc={}
  for x in ep['slots']:
   if x[4]=='initial|plain'and ep['root_recipes'][str(x[2])]['plies']==p and x[5]==o:
    r=rows[tuple(x)]['reward'];k='U'if r is None else'W'if r>0 else'L'if r<0 else'D';cc[k]=cc.get(k,0)+1
  init[f'{p}/{o}']=cc
 out=dict(status='COMPLETE_EXISTING_RECORDS_ONLY',source_dot_reply_ts='1792397818.663009',cells=cells,order_up_WL_down=len(counter),order_up_WL_up=len(agree),order_up_cells=sum(c['order_diff']>0 for c in cells),total_cells=len(cells),counterexamples=counter,initial_absolute_WDL=init,scope='Descriptive order vs paired finite W-L, 4 initializations, repeated cells not independent, foes exposed. A counterexample refutes only the strong claim that more traditional order implies stronger on this panel.')
 (E.parent/'task2585'/'order-utility.json').write_text(json.dumps(out,indent=2))
 print(json.dumps({k:v for k,v in out.items()if k not in('cells','counterexamples')},indent=1))
 for c in counter:print('COUNTER',c['checkpoint'],c['seed'],c['prefix'],c['foe'],c['order_SC'],c['order_Fx'],c['WL_diff'])
if __name__=='__main__':run()
