"""Temporal/owner transfer of frozen template-any orders; no new population.
Use prior declared early0..7/late8..16 and owner parity partitions, all zeros.
Both replicates retained. Compare full-pair loss to current frozen v3 order;
negative means improvement. No selection of a favorable time/source law.
"""
from pathlib import Path
from fractions import Fraction as F
from itertools import combinations
import sys,json,hashlib
sys.path.insert(0,str(Path.cwd()))
from scripts.research_record import write_record
p=Path(__file__).parent;fact=json.loads((p/'source-saturation-factorial.json').read_bytes());phase=json.loads((p/'phase-audit.json').read_bytes());decls={}
for f in ('reply-declaration.json','reply8-declaration.json'):decls.update(json.loads((p/f).read_bytes())['prices'])
out=dict(scope=__doc__,rules=[],inputs={n:hashlib.sha256((p/n).read_bytes()).hexdigest() for n in ('source-saturation-factorial.json','phase-audit.json','reply-declaration.json','reply8-declaration.json')})
for r in fact['rules']:
 bg=next(x for x in phase['rules'] if x['seed']==r['seed'])['tasks']['immediate']['backgrounds'];old=decls[str(r['seed'])]['semantic_v3'];row=dict(seed=r['seed'],replicates=[])
 for rep in r['replicates']:
  values={t:F(v) for t,v in rep['methods']['template_any']['values'].items()};changes=[]
  for b in bg:
   means={t:F(v) for t,v in b['utility'].items()};pairs=list(combinations(sorted(means),2));delta=F()
   def selected(table,a,b):return means[a] if table[a]>table[b] else means[b] if table[b]>table[a] else (means[a]+means[b])/2
   for a,t in pairs:delta+=selected(old,a,t)-selected(values,a,t)
   changes.append(dict(ply=b['ply'],delta=delta/len(pairs)))
  def avg(items):return sum((x['delta'] for x in items),F())/len(items)
  primary=avg(changes);assert primary==F(rep['methods']['template_any']['loss_minus_current'])
  strata={name:avg([b for b in changes if pred(b['ply'])]) for name,pred in [('early0_7',lambda v:v<8),('late8_16',lambda v:v>=8),('owner0',lambda v:v%2==0),('owner1',lambda v:v%2==1)]}
  row['replicates'].append(dict(seed=rep['seed'],primary=primary,strata=strata,backgrounds=changes));print(r['seed'],rep['seed'],strata,flush=True)
 out['rules'].append(row)
out['producer_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest();write_record(p/'template-phase-audit.json',out)
