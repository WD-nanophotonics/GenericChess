"""Logical boundary caveat; abstract finite horizon trees, NOT chess game evidence."""
from pathlib import Path
from fractions import Fraction
import json
O=Path('results/dev_aux/task1924')
def run():
 # Same global lexicographic action tie rule at both distinct input states.
 # Every cutoff leaf is ongoing; fixed continuation then gives indicated W/L.
 states=[{'a':dict(feature=(1,-1),later_WL=1),'z':dict(feature=(0,1),later_WL=-1)}, {'a':dict(feature=(0,1),later_WL=1),'z':dict(feature=(1,-1),later_WL=-1)}]
 results=[]
 for rho in [Fraction(1,2),Fraction(1),Fraction(1999,1000),Fraction(2),Fraction(2001,1000),Fraction(3),Fraction(4)]:
  choices=[];rewards=[]
  for state in states:
   utilities={a:v['feature'][0]*rho+v['feature'][1] for a,v in state.items()};action=min(utilities,key=lambda a:(-utilities[a],a));choices.append(action);rewards.append(state[action]['later_WL'])
  results.append(dict(ratio=str(rho),actions=choices,actual_abstract_continuation_WL=rewards,mean_WL=str(Fraction(sum(rewards),2))))
 assert all(r['mean_WL']==('1' if r['ratio']=='2' else '0') for r in results)
 out=dict(status='PASS_ABSTRACT_LOGICAL_CAVEAT',states=states,checks=results,exact_argument='ForALLrho<2, feature(0,1) preferredinbothstates; forallrho>2, feature(1,-1) preferredinboth. Atboundary2both tieandfixedlexa selects oppositefeatureassignments acrossdifferentstates. Frozencontinuations then give meanW-L1 onlyat2, otherwise0. Thus isolatedboundaryoptimum canexist despitefiniteopenchambers.',scope='Abstractfinite-horizonsearch/price-freecontinuation table, NOTaGenericChesslegal-ruleconstruction, newtrainingdata, mockgameexperiment orreportedrealWDL. Itrefutesonly inference fromfinitecrossingsALONEtoimpossibilityofanyuniquecontinuousparametermaximizer. Current9vectorchamberlemma/Nativescopeunchanged.',research_consequence='DoNOTrequireuniquecontinuouspointasgoal; usefulstableintervalsandnewmuactualW-Lmatter. Moremultiplicitiesrefinefiniteintervals butneitherpromise noruniversallyexcludeisolatedboundaryoptima. AvoidoverstatingDotfiniteinventorycautionasanimpossibilitytheorem.')
 with (O/'result.json').open('x') as f:json.dump(out,f,indent=2)
 print('ExactabstractboundarycaveatPASS; no newphysicalgame/search/Genericlegalityclaim.')
if __name__=='__main__':run()
