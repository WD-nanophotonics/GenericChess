"""Exact counterexamples to extrapolating the RN77 price class to other inventories."""
from fractions import Fraction as F
from itertools import product
from pathlib import Path
import json
OUT=Path('results/dev_aux/task2237')
def crossings(r0,r1,n0,n1):
 lines=sorted({(a-b,c-d)for a,b,c,d in product(range(r0+1),range(r1+1),range(n0+1),range(n1+1))})
 points=sorted({F(bb-b,a-aa)for a,b in lines for aa,bb in lines if a!=aa and F(bb-b,a-aa)>0})
 predicted=sorted({F(j,i)for i in range(1,r0+r1+1)for j in range(1,n0+n1+1)})
 assert points==predicted
 return dict(inventory=dict(R_target=r0,R_other=r1,N_target=n0,N_other=n1),leaf_coefficients=lines,positive_breakpoints=[str(x)for x in points],largest_breakpoint=str(points[-1])if points else None)
def run():
 cases=[crossings(*counts)for counts in product(range(3),repeat=4)if sum(counts)>0]
 assert len(cases)==80
 # Two legal positive material leaves become ordered differently across x=2.
 # This is an algebraic inventory counterexample, NOT evidence both can be
 # reached in one legal decision tree or price2 is optimal.
 ratios=[F(3,2),F(5,2)];example=[dict(x=str(x),one_R=str(x),two_N='2',prefers_R=x>2)for x in ratios]
 result=dict(status='PASS_80_CAPTURE_CLOSED_INVENTORY_ORDER_PARTITIONS',cases=cases,counterexample_two_N=example,proof='All possible removal-subset coefficients form contiguous integer rectangles [-R_other,R_target] x [-N_other,N_target]. Pairwise differences cover everyinteger in[-R_total,R_total]x[-N_total,N_total]; positiveaffineequalities occur exactlyx=j/i with1<=i<=R_total,1<=j<=N_total. Terminaldraw0alreadyincluded. Restricting actual legal reachability canCOARSENthis partition, neveraddcrossings. Min/maxcomparison-only invariance followswithinanycell; magnitude-basedsearchheuristicsnotcovered.',interpretation='The RN77 tested closure hasR_total2,N_total1 soallx>1shareleaforder. AddingsecondNpermitsanewcrossingat2;withRtotal2/Ntotal2thefullsetis1/2,1,2 (NOT3/2) and caninprinciple distinguish1.25from2/4; notsufficientwithoutactualdecisionconflicts. Rulemovementchangesalonewhileinventoryfixedcannotremoveleaforderinvariance. This supports choosinga changedinventorybefore more within-cellprice training; notnewteacher/fit/testadoption.',scope='Symbolic finite-inventoryupperpartition only, notlegalstatecensus/WDL/realplayer policy acrossclocks. No humanprice input orclaimnewinventorysolved.')
 with(OUT/'result.json').open('x')as f:json.dump(result,f,indent=2)
 print('PASS80_EXACT_INVENTORY_PARTITIONS_AND2N_COUNTEREXAMPLE')
if __name__=='__main__':run()
