"""Locate the rectangle boundary: raw projection or legacy profile assembly?

Existing two cannon definitions, five preexisting densities. Independently sum
orthogonal endpoint probabilities from width/height, without compiled geometry
or projection helpers. quiet=(1-d)^distance; capture=d/2*k*d*(1-d)^(k-1),
k=distance-1, zero at k=0. Equal sources/owners. No price fit/new law/default.
"""
from rect_probe import *
from generic_chess.ai.evaluation.semantic import semantic_opportunity,build_semantic_opportunity_profile
from generic_chess.ai.evaluation.config import EvaluationConfig
from math import isclose

def main():
 p=Path(__file__).parent;out=p/'rect-raw-boundary.json';assert not out.exists()
 cfg=EvaluationConfig();r=dict(complete=False,declaration=__doc__,cases=[])
 for w,h in ((7,5),(9,10)):
  c=compile_ruleset_for_execution(definition(w,h));raw=semantic_opportunity(c,'C',cfg);checks=[]
  for curve in raw['curves']:
   d=curve['density'];quiet=capture=0.
   for x in range(w):
    for y in range(h):
     for distance in (x,w-1-x,y,h-1-y):
      for step in range(1,distance+1):
       k=step-1;quiet+=(1-d)**step
       if k:capture+=d/2*k*d*(1-d)**(k-1)
   quiet/=w*h;capture/=w*h
   assert isclose(quiet,curve['quiet'],rel_tol=1e-12,abs_tol=1e-12)
   assert isclose(capture,curve['capture'],rel_tol=1e-12,abs_tol=1e-12)
   checks.append(dict(density=d,independent_quiet=quiet,independent_capture=capture))
  try:build_semantic_opportunity_profile(c,cfg)
  except ValueError as exc:boundary=str(exc)
  else:raise AssertionError('expected explicit unsupported profile assembly boundary')
  r['cases'].append(dict(shape=[w,h],raw=raw,independent_controls=checks,profile_boundary=boundary))
 r['complete']=True;r['producer_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest();write_record(out,r)
 print([(z['shape'],z['raw']['raw'],z['profile_boundary']) for z in r['cases']])
if __name__=='__main__':main()
