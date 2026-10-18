"""Property-derived prediction-quality function, NOT a verified paper erratum.

The scanned1999 Q definition has internally inconsistent x/s quadratics.
This module independently solves its stated continuous two-line/zero-mean
construction; deployed in NO game/training run96. Do not label exact replica.
"""
from math import sqrt,isfinite
SWITCH=(sqrt(17.)-1.)/4.

def breakpoint(p):
 if not isfinite(p)or not .5<=p<=1.:raise ValueError('mirrored probability domain')
 q=1.-p
 if p<=SWITCH:
  c=p*(p*p+q*q);disc=16*p*p-8*(1+p)*c
  return 2*c/(4*p+sqrt(max(0.,disc)))
 b=2*q-p*p;return(-b+sqrt(b*b+4*(1+p)*q*q))/(2*(1+p))

def quality(current,earlier):
 if not all(isfinite(p)and 0<=p<=1 for p in(current,earlier)):raise ValueError('probability domain')
 p,pp=(current,earlier)if current>=.5 else(1-current,1-earlier);r=abs(p-pp);z=breakpoint(p)
 return 1-r/z if r<=z else-p*(r-z)/(p-z)

def mean_integral(p,z):
 """Analytic integral over earlier probability U[0,1], p in[.5,1]."""
 q=1-p
 if z<=q:return z-p*((q-z)**2+(p-z)**2)/(2*(p-z))
 return q+z/2-q*q/(2*z)-p*(p-z)/2
