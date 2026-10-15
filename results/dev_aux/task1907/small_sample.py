"""Exposed paired-family small-sample sensitivity; no new scientific labels."""
from pathlib import Path
from itertools import product
import json,math
OUT=Path('results/dev_aux/task1907')
def check(name,values):
 nonzero=[x for x in values if x];observed=abs(sum(nonzero));tot=2**len(nonzero);tail=sum(abs(sum(sign*x for sign,x in zip(signs,nonzero)))>=observed-1e-12 for signs in product((-1,1),repeat=len(nonzero)))
 loo=[sum(values[:i]+values[i+1:])/(len(values)-1) for i in range(len(values))]
 return dict(name=name,families=len(values),informative_nonzero=len(nonzero),positive=sum(x>0 for x in values),negative=sum(x<0 for x in values),mean=sum(values)/len(values),leave_one_family_out=[min(loo),max(loo)],two_sided_signflip_tail_under_symmetry=tail/tot,enumerated_signs=tot)
def run():
 a=json.loads(Path('results/dev_aux/task1883/audit_report.json').read_text());b=json.loads(Path('results/dev_aux/task1891/audit_report.json').read_text());h=json.loads(Path('results/dev_aux/task1902/horizon_report.json').read_text());r=json.loads(Path('results/dev_aux/task1905/range_report.json').read_text());rows=[]
 for x in a['comparisons']:
  if not x['identical_cell']:rows.append(check('1881DEV2minus'+str(x['initial']),x['family_deltas']))
 for x in b['comparisons']:rows.append(check('1890CONFIRMopp'+str(x['opponent_nodes']),x['family_deltas']))
 rows.append(check('1899EXPOSEDH48',h['learned_minus_unit']['family_deltas']));rows.append(check('1904EXPOSEDTRAIN4minus2',r['ratio4_minus2']['family_deltas']))
 out=dict(status='COMPLETE_PAID_SMALL_SAMPLE_SENSITIVITY',rows=rows,scope='Signflip assumes independent symmetric pairedfamilyeffects undernull; NOT an exactrandomizedtrial pvalue or a test for allmean-zero distributions. Price/horizon/range stages have different exposure/selection histories, no multiplicitycorrection or thresholdselection. Mainpoint: H48 bootstrapCIexcludes0 but only4informativefamilies, signflip tail.125 and no newindependentconfirmation. Preserve all originalCIs/results; no winner/reward/parameterchange.',new_games=0,new_proof_or_native_calls=0,artifact_scope='Late directGit diagnostic; immutable SOURCE62/EVIDENCE62 sealedbeforethis helper still contain all its rawinputdatasets. No added testmodule or sourcepolicy change.')
 with (OUT/'result.json').open('x') as f:json.dump(out,f,indent=2)
 print(json.dumps(out))
if __name__=='__main__':run()
