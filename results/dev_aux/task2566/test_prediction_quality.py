from math import sqrt
import pytest
from results.dev_aux.task2566.prediction_quality import quality,breakpoint,mean_integral,SWITCH

def test_shape_mirror_range_and_terminal_extremes():
 assert quality(1,0)==-1 and quality(0,1)==-1
 for i in range(101):
  p=i/100;assert quality(p,p)==1
  for j in range(101):
   q=j/100;v=quality(p,q);assert -1-1e-12<=v<=1+1e-12;assert v==pytest.approx(quality(1-p,1-q),abs=1e-12)

def test_zero_mean_via_independent_numerical_integration():
 # Composite trapezoid treats piecewise endpoints independently of root formula.
 for p in [.0,.1,.219,.25,.5,.7,SWITCH,.8,.95,1.]:
  n=10000;mean=(quality(p,0)+quality(p,1))/2+sum(quality(p,j/n)for j in range(1,n));assert abs(mean/n)<1e-7

def test_roots_match_independent_bisection_and_both_regimes_join():
 for i in range(101):
  p=.5+i/200;lo=1e-10;hi=p-1e-10
  for _ in range(60):
   mid=(lo+hi)/2
   if mean_integral(p,mid)>0:hi=mid
   else:lo=mid
  z=breakpoint(p);assert z==pytest.approx((lo+hi)/2,abs=1e-12);assert abs(mean_integral(p,z))<1e-12
 assert breakpoint(SWITCH)==pytest.approx(1-SWITCH);assert abs(breakpoint(SWITCH-1e-10)-breakpoint(SWITCH+1e-10))<1e-8

def test_scanned_equations_are_not_silently_used_or_called_corrected_source():
 p=.75;printed_disc=16*p*p-8*(1+p)*p;assert printed_disc<0
 assert breakpoint(.5)==pytest.approx(1/6)and breakpoint(1)==pytest.approx(.5)

@pytest.mark.parametrize('p,q',[(float('nan'),.5),(-.1,.5),(.5,1.1)])
def test_reject_invalid_probabilities(p,q):
 with pytest.raises(ValueError):quality(p,q)
def test_printed_alternative_y_still_violates_zero_mean_at_half():
 p=.5;printed_y=(sqrt(33)-3)/12
 # At p=.5 all r lie belowq; integrating the same printed brokenline yields
 # this nonzero expectation, independently corroborated by Dot, not an erratum.
 assert mean_integral(p,printed_y)==pytest.approx((sqrt(33)-5)/8)
 assert abs(mean_integral(p,printed_y))>.09
 assert abs(mean_integral(p,breakpoint(p)))<1e-12
