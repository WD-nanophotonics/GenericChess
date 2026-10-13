from pathlib import Path
import json,collections,re
from fractions import Fraction as F
R=Path.cwd();load=lambda n:[json.loads(s) for s in (R/f'results/dev_aux/task{n}/games.jsonl').read_text().splitlines()]
def canon(g):
 g=json.loads(json.dumps(g))
 for k in ['game','budget','scale']:g.pop(k,None)
 for q in g['queries']:
  q.pop('game',None)
  q['metadata']['uci_info']=[re.sub(r'\b(time|nps) \d+','',s) for s in q['metadata']['uci_info']]
 return g
key=lambda g:(g['price'],g['opponent'],g['root']['seed'],g['color'])
old={key(g):g for g in load(1133) if g['arm']=='J' and g['price'] in [90,164]}
b=load(1145);s=load(1149)
# root dictionaries differ only in documentary metadata; compare decision/action state, queries.
def decision(g):
 d=canon(g);return {k:d[k] for k in ['price','opponent','color','weights','actions','queries','termination','label','final_fen']}
control1=sum(decision(g)==decision(old[key(g)]) for g in b if g['budget']==64)
bm={key(g):g for g in b if g['budget']==64}
control2=sum(decision(g)==decision(bm[key(g)]) for g in s if g['scale']==1)
assert control1==64 and control2==64
p=R/'results/dev_aux/task1147/result.json';d=json.loads(p.read_bytes());d['baseline_decision_controls']=dict(cached_full8_vsbudget64=control1,scale1_vsbudget64=control2,omitted='game identifier, rootdocumentaryfields, metadata time/nps only; move/score/depth/nodes/PV/actions/outcomes exact')
cost=[]
for n,field in [(1145,'budget'),(1149,'scale')]:
 for v in sorted(set(g[field] for g in load(n))):
  gs=[g for g in load(n) if g[field]==v];nodes=ms=go=0
  for g in gs:
   for q in g['queries']:
    lines=q['metadata']['uci_info'];last=[l.split() for l in lines if ' nodes ' in l and ' time ' in l]
    if last:
     fs=last[-1];nodes+=int(fs[fs.index('nodes')+1]);ms+=int(fs[fs.index('time')+1])
    go+=1
  cost.append(dict(task=n,parameter=field,value=v,go=go,reported_last_nodes_sum=nodes,reported_last_internal_milliseconds_sum=ms,actual_terminal=sum(g['label']!='C' for g in gs),censored=sum(g['label']=='C' for g in gs)))
d['reported_internal_work']=cost
p.write_text(json.dumps(d,indent=2));print(d)
