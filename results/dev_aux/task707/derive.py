import json,hashlib,collections
from pathlib import Path
from fractions import Fraction as F
R=Path.cwd();O=R/'results/dev_aux/task707'
for n in [688,697]:assert json.loads((R/f'results/dev_aux/task{n}/result.json').read_bytes())['status'].startswith('PASS_ALL_')
models=[]
for task,label in [(687,'A_mean12_24'),(696,'B_q12only')]:
 p=R/f'results/dev_aux/task{task}';r=json.loads((p/'result.json').read_bytes());gs=[json.loads(t) for t in (p/'games.jsonl').open(encoding='utf-8')];rows=[]
 for row in r['rows']:
  summary=collections.Counter();cells=[]
  for ref in row['batch']['sources']:
   g=gs[ref['line']-1];cell={}
   for cap in [12,24]:
    acts=g['actions'][:cap];captures=[a for a in acts if a['captured'] is not None];own=sum(a['actor']==g['color'] for a in captures);opp=len(captures)-own;assert 2*(own-opp)==g['quantity12' if cap==12 else 'quantity24'];victims=collections.Counter(a['captured'].lower() for a in captures if a['actor']==g['color']);cell[str(cap)]=dict(quantity=2*(own-opp),candidate_captures=own,opponent_captures=opp,candidate_capture_types=dict(victims),promotions=sum(a['promotion'] for a in acts),drops=sum(a['drop'] is not None for a in acts));summary[f'candidate_captures_{cap}']+=own;summary[f'opponent_captures_{cap}']+=opp;summary[f'promotions_{cap}']+=cell[str(cap)]['promotions'];summary[f'drops_{cap}']+=cell[str(cap)]['drops']
   cells.append(dict(replica=g['replica'],family=g['root']['source_family'],color=g['color'],horizons=cell))
  rows.append(dict(names=row['names'],weights=row['batch']['weights'],cells=cells,totals=dict(summary)))
 models.append(dict(method=label,rows=rows,actual_games=len(gs),source_sha256=hashlib.sha256((p/'games.jsonl').read_bytes()).hexdigest()))
out=dict(status='ALL256_DEV_CAPTURE_OWNERSHIP_IDENTITIES_PASS',models=models,new_go=0,scope='Allactualdev128A+128B independentfullpathqualified. Eachhorizonq equals2*(candidatecapturenumber-opponentcapturenumber) frominitialzero ownership imbalance. Board+hand conserved38; drops/promotions zeroimmediate quantitychange, every nonroyalcapture equal2 regardlessvictimpiece. This explainsobjective semantics, NOTproofany piecevalue cannot emerge through dynamics ornewtrajectoryfitness/humanlabels. Retainalltypes/terminal/promotion/drop/counts.');(O/'result.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps([dict(method=m['method'],rows=[dict(names=r['names'],totals=r['totals']) for r in m['rows']]) for m in models]))
