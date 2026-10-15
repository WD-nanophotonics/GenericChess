"""Exploratory simultaneous-family bootstrap and explicit sign-symmetry sensitivity."""
from pathlib import Path
from collections import Counter
import json,random,time
O=Path('results/dev_aux/task1959')
def sign_tail(ds):
 ints=[round(2*d) for d in ds if d];assert all(abs(2*d-round(2*d))<1e-10 for d in ds);dist=Counter({0:1})
 for d in ints:
  nxt=Counter()
  for total,n in dist.items():nxt[total+d]+=n;nxt[total-d]+=n
  dist=nxt
 obs=abs(sum(ints));return sum(n for v,n in dist.items() if abs(v)>=obs)/(2**len(ints))
def run():
 beg=time.perf_counter();report=json.loads(Path('results/dev_aux/task1953/result.json').read_text());cols={(f['opponent_nodes'],name):v['family_deltas'] for f in report['factorial'] for name,v in f['effects'].items()};means={k:sum(ds)/32 for k,ds in cols.items()};primary=[k for k in cols if k[1] in ('price_with_proof','price_without_proof')];allkeys=list(cols);rng=random.Random(20261016641959);errors4=[];errors14=[]
 for _ in range(20000):
  ids=rng.choices(range(32),k=32);err={k:abs(sum(ds[i] for i in ids)/32-means[k]) for k,ds in cols.items()};errors4.append(max(err[k] for k in primary));errors14.append(max(err.values()))
 errors4.sort();errors14.sort();q4=errors4[18999];q14=errors14[18999];rows=[]
 for key,ds in cols.items():
  p=sign_tail(ds);rows.append(dict(opponent_nodes=key[0],contrast=key[1],mean=means[key],sign_symmetric_two_sided_tail=p,bonferroni14_sensitivity=min(1.,14*p),bonferroni4_sensitivity=min(1.,4*p) if key in primary else None,posthoc_simultaneous4_family_band=[means[key]-q4,means[key]+q4] if key in primary else None,posthoc_simultaneous14_family_band=[means[key]-q14,means[key]+q14]))
 out=dict(status='EXPLORATORY_MULTIPLICITY_AND_ASSUMPTION_SENSITIVITY',family_count=32,rows=rows,bootstrap_maxerror95=dict(four_price_contrasts=q4,all14technicalcontrasts=q14),seconds=time.perf_counter()-beg,scope='Same32families resampledjointly acrossopponents/methods, not64independentclusters. These are POSTHOCsensitivityfamilies, notretroactivelyprespecifiedconfirmatorytests or reliable exactsmall-samplecoverage. Sign-flip convolution isexactONLY underindependent conditionalfair/symmetricfamily-signnull, NOTgenericnullE[d]=0. Bootstrapbands remainfinite-budgeteventobjective, notfullWDLorhumanvalue/recovery. No price/arm/budget choice follows.')
 (O/'result.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps(dict(status=out['status'],primary=[r for r in rows if r['contrast'] in ('price_with_proof','price_without_proof')],maxerror=out['bootstrap_maxerror95'],seconds=out['seconds'])))
if __name__=='__main__':run()
