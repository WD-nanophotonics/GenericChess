"""Section3 temporal-coherence mechanics only; NOT prediction-decay reproduction.

New opt-in research adapter. It never changes the active fixed-rate96 producer.
Reference: Beal/Smith IJCAI1999 section3, https://www.ijcai.org/Proceedings/99-1/Papers/081.pdf .
Our PV/tanh[-1,1]/fixed-lambda choices differ from the material-specific paper.
"""
from math import isfinite
from results.dev_aux.task2492.episode import TDLeafEpisode

class CoordinateTC:
 def __init__(self,dimension,eta=.05):
  if type(dimension)is not int or dimension<1 or not isfinite(eta)or eta<0:raise ValueError('TC domain')
  self.dimension,self.eta=dimension,float(eta);self.net=[0.]*dimension;self.absolute=[0.]*dimension
 @property
 def rates(self):return [abs(n)/a if a else 1. for n,a in zip(self.net,self.absolute)]
 def update(self,model,recommended):
  if len(model.weights)!=self.dimension:raise ValueError('dimension')
  rows=[tuple(map(float,r))for r in recommended]
  if any(len(r)!=self.dimension or not all(map(isfinite,r))for r in rows):raise ValueError('invalid impulse')
  net=[sum(r[j]for r in rows)for j in range(self.dimension)]
  absolute=[sum(abs(r[j])for r in rows)for j in range(self.dimension)]
  before=self.rates;delta=[self.eta*a*b for a,b in zip(before,net)]
  # Apply using OLD rates; accumulate RAW recommended impulses, never actual
  # rate-scaled moves. This permits recovery after a coordinate rate reaches0.
  model.apply(delta)
  self.net=[a+b for a,b in zip(self.net,net)];self.absolute=[a+b for a,b in zip(self.absolute,absolute)]
  return dict(impulses=len(rows),recommended_net=net,recommended_absolute=absolute,rates_before=before,rates_after=self.rates,delta=delta)

class TCEpisode(TDLeafEpisode):
 def __init__(self,dimension,eta=.05,lam=.95):
  super().__init__(eta,lam);self.tc=CoordinateTC(dimension,eta)
 def finish(self,model,outcome):
  if self.snapshot is not None and tuple(model.weights)!=self.snapshot:raise ValueError('episode weights changed')
  if outcome is not None and outcome not in(-1,0,1):raise ValueError('actual outcome domain')
  elig=[0.]*len(model.weights);rows=[];loss=0.;terminal_credit=0.
  for i,(value,grad)in enumerate(self.rows):
   target=self.rows[i+1][0]if i+1<len(self.rows)else outcome
   if target is None:break
   elig=[self.lam*e+g for e,g in zip(elig,grad)];error=target-value;loss+=error**2/2;impulse=[error*e for e in elig];rows.append(impulse)
   if i+1==len(self.rows):terminal_credit=sum(abs(x)for x in impulse)
  record=self.tc.update(model,rows);record.update(samples=len(rows),observed_searches=len(self.rows),loss=loss/max(1,len(rows)),censored=outcome is None,terminal_credit_l1=terminal_credit,changed=any(record['delta']));self.reset();return record
