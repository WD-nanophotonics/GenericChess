"""Closed-inventory order-equivalence of two-type material minimax.
Theorem scope is exact arithmetic, theta-independent choices and identical work.
This is NOT universal full-game price equivalence or timing equivalence.
"""
from pathlib import Path
from fractions import Fraction as F
from itertools import product
import json,hashlib,time
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.session.session import GameSession
from results.dev_aux.task2148.normal import SessionCompleteMaterialSearch
from results.dev_aux.task2175.receipt import choice_value
from results.dev_aux.task2153.stop_evidence import EvidenceStopReader
OUT=Path('results/dev_aux/task2233')
def save(n,v):
 with(OUT/n).open('x')as f:json.dump(v,f,indent=2)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def signature(lines,x):
 values=[a*x+b for a,b in lines]
 return [(u>v)-(u<v)for u in values for v in values]
def run():
 assert not(OUT/'result.json').exists();start=time.perf_counter();stop=EvidenceStopReader(Path.cwd())
 # Capture closure: at most one R for each side, and a single N initially.
 # Target may own N or oppose it. Use both orientations, with ALL removal subsets.
 orientations={str(sign):sorted(set((r0-r1,sign*n)for r0,r1,n in product((0,1),repeat=3)))for sign in(-1,1)};panels=[]
 for sign,lines in orientations.items():
  crossings=sorted({F(bb-b,a-aa)for a,b in lines for aa,bb in lines if a!=aa and F(bb-b,a-aa)>0});assert crossings==[F(1,2),F(1)]
  probes=[F(1,4),F(1,2),F(3,4),F(1),F(2)];intervals=[(F(0),F(1,2)),(F(1,2),F(1)),(F(1),None)]
  certificates=[]
  for lo,hi in intervals:
   mid=(lo+hi)/2 if hi is not None else lo+1
   sig=signature(lines,mid)
   # No affine crossing inside a cell; these sign vectors are exact witnesses.
   certificates.append(dict(lower=str(lo),upper=None if hi is None else str(hi),probe=str(mid),pair_signs=sig))
  panels.append(dict(target_N_sign=sign,all_coefficients=lines,positive_breakpoints=[str(x)for x in crossings],intervals=certificates))
 # Actual implementation sanity only. Dyadic interior prices avoid rounding at boundaries.
 roots=sorted([r for r in json.loads(Path('results/dev_aux/task2220/inputs.json').read_text())['roots']if r['split']=='TRAIN'],key=lambda r:r['family'])[:8]
 save('plan.json',dict(source_sha=sha(OUT/'ordering.py'),roots=roots,depths=[1,2,3,4],ratios=[1.25,2.,4.,8.],normal_nodes=100000,seconds_per_call=10.,cap_seconds=300,selection='first8TRAINonly, all4depths/all4predefineddyadicprices>1; noDEV/refit/outcome-basedrootselection'))
 checks=[]
 for root in roots:
  c=compile_ruleset_for_execution(deserialize_ruleset(Path(root['rules']).read_text()));session=GameSession(c)
  for depth in(1,2,3,4):
   ref=None
   for ratio in(1.25,2.,4.,8.):
    stop();assert time.perf_counter()-start<300
    def evaluate(pos,target):return sum((1 if pc.owner==target else-1)*(ratio if pc.current_type_id=='R'else 1.)for pc in pos.board if pc is not None and pc.current_type_id!='K')
    got=SessionCompleteMaterialSearch(c,evaluate,max_depth=depth).choose(session,max_nodes=100000,seconds=10.,cancel=stop);assert got.completed_depth==depth
    value=(choice_value(got.choice),got.nodes,got.session_transitions,got.material_leaves,got.terminal_leaves)
    if ref is None:ref=value
    else:assert value==ref,(root['family'],depth,ratio,value,ref)
    checks.append(dict(family=root['family'],depth=depth,ratio=ratio,choice=value[0],nodes=value[1],transitions=value[2],material_leaves=value[3],completed_depth=got.completed_depth,seconds=got.seconds))
 save('result.json',dict(status='PASS_EXACT_LEAF_ORDER_PARTITION_AND128_IMPLEMENTATION_CHECKS',panels=panels,checks=checks,seconds=time.perf_counter()-start,proof='For each fixed target orientation every reachable finite material leaf is a*x+b from the listed capture-closed coefficient set; terminal draw is0alreadyincluded andterminalW/Lare+/-infinity. Inside each open cell pairwise order AND ties of ALL possible leaves remain identical. Induction through finite max/min preserves score order/tie argchoices. Alpha-beta comparisons/pruning also remain identical given theta-independent actionorder and same depth/node work. Fixed low-inventoryguide ignoresratio. Therefore exact-arithmetic policies andwhole deterministic trajectories agree within eachcell,conditional onidentical searchwork; notjust128sampledrecords.',limitations='Restricted RNinventory/no promotion/drop/aux; no claimfornewinventories,genericfullrulesorwallclockidenticalcutoffs. Floatingoverflow/cancellation nearboundaries excludedbytheorem;128dyadicactualD1-D4calls corroborateonly8TRAINroots. This proves a sufficient coarse partition, some roots coarser; notallcellsnecessarilydistinguishable inW-L. No proof2isoptimal; allratios>1 areunidentifiableunderthese exactpolicyconditions.'))
 print(json.dumps(dict(status='PASS_EXACT_ORDER_PARTITION',checks=len(checks),seconds=time.perf_counter()-start)))
if __name__=='__main__':run()
