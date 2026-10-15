"""Exact finite leaf-order chambers implied by the frozen capture-only inventory."""
from pathlib import Path
from itertools import product,combinations
from collections import Counter
from fractions import Fraction
import json,hashlib,time
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.session.session import GameSession
O=Path('results/dev_aux/task1917')
def run():
 start=time.perf_counter();rs=deserialize_ruleset(Path('results/dev_aux/task1872/rules.json').read_text());c=compile_ruleset_for_execution(rs);roots=json.loads(Path('results/dev_aux/task1872/feasibility.json').read_text())['roots']
 assert c.capture_disposition=='remove_from_game' and not rs.semantic_actions and not c.declarations
 assert {p.type_id for p in c.piece_types}=={'K','R','N'} and all(not p.is_promotable for p in c.piece_types)
 assert not any(any(v for m in masks for v in m) for masks in c.drop_allowed.values())
 initial=[]
 for root in roots:
  s=GameSession(c,root['setup']);counts=Counter((p.owner,p.current_type_id) for p in s.state.position.board if p is not None);assert all(counts[side,typ]==1 for side in (0,1) for typ in ('K','R','N'));initial.append(dict(family=root['family'],counts={str(k):v for k,v in counts.items()}))
 vectors=list(product(range(-1,2),repeat=2));crossings=[]
 for a,b in combinations(vectors,2):
  dr=a[0]-b[0];dn=a[1]-b[1]
  if dr and Fraction(-dn,dr)>0:crossings.append(dict(left=a,right=b,ratio=str(Fraction(-dn,dr))))
 thresholds=sorted({Fraction(x['ratio']) for x in crossings});assert thresholds==[Fraction(1,2),Fraction(1),Fraction(2)]
 def order(r):
  d={}
  for dr,dn in vectors:d.setdefault(Fraction(dr)*r+dn,[]).append([dr,dn])
  return [v for _,v in sorted(d.items())]
 chambers=[dict(interval='(0,1/2)',representative='1/4',order=order(Fraction(1,4))),dict(interval='(1/2,1)',representative='3/4',order=order(Fraction(3,4))),dict(interval='(1,2)',representative='3/2',order=order(Fraction(3,2))),dict(interval='(2,infinity)',representative='3',order=order(Fraction(3)))]
 # Exact positive scaling N is irrelevant to these complete finite-tree orders.
 assert order(Fraction(3))==order(Fraction(4))==order(Fraction(1000000))
 v4={4*dr+dn:2*dr+dn for dr,dn in vectors};assert len(v4)==9 and all(v4[x]<=v4[y] for x in v4 for y in v4 if x<=y)
 v4.update({-1000000000:-1000000000,1000000000:1000000000})
 assert all(v4[min(x,y)]==min(v4[x],v4[y]) and v4[max(x,y)]==max(v4[x],v4[y]) for x in v4 for y in v4)
 out=dict(status='PASS_EXACT_FINITE_ORDER_ARGUMENT',ruleset_fingerprint=c.ruleset_fingerprint,initial_inputs_checked=len(initial),root_inventory=initial,inventory_invariant='EachsideinitiallyoneRoneN; no creation/promotion/drop/semanticmechanics, onlyremove. Allreachableleaves have netR,netNin{-1,0,1}; anchors excluded.',leaf_vectors=vectors,feasibility='Ninevectors are a SAFE OVERAPPROXIMATION, not a proof allareactuallyreachable. Actualreachableleaforders canonlyhavefewercrossings.',positive_ratio_crossings=crossings,thresholds=[str(x) for x in thresholds],chambers=chambers,boundary_orders={str(r):order(r) for r in thresholds},rho4_to_rho2_nondecreasing_map={str(k):v for k,v in sorted(v4.items())},finite_lattice_pairs_checked=len(v4)**2,seconds=time.perf_counter()-start,theorem='For a FIXED complete finite game tree/horizon, utilities at nonterminal leaves dR*rho+dN, actualWIN/LOSSlexicographically above/belowfiniteleaves, actualDRAW0. Anytwo positiveprices in sameopenchamber induce identicalleafweakorders. A strictlyincreasingmap commutes min/max, so identicalrootoptimalactionsets. Fixedprice-independenttiebreak givesidenticalpolicy. Chance-nodeexpectations wouldnotfollowthislemma.',boundary='rho2 isaboundary. rho4 strictlyrefines itsleaforders, andrho2 ismonotonenondecreasingcollapseofrho4. On SAMEcompletefinite tree, bestactionsat4 aresubsetofbestactionsat2. Thus2vs4mayresolve ties butcannotestimateauniquefiniteratioabove2.',limits='NOTtheorem thatactualselectiveNative2/4policies coincide or thatentireexperimentshaveequalfitness. Nativefixedmargins/SEE/pruning/variabledepth/time canbreakmonotoneinvariance; proofbudget/time-sensitive trees alsochange. Notpopulation/game-theoretic chessprice, notuniversalnonidentifiability. Morepiecescounts/promotion/drop/mechanicschangeleafvectorlattice. No newgames, enginequeries, humanreferencevalues or fitting.',research_implication='SparseoneeachpieceisgoodforcoarseR>N capability, intrinsicallypoorforuniqueexchange-rate identification in purecomplete material search. A futureinputlaw shouldincludevaryingmultiplicities/actualexchangeconflicts, frozenbeforeoutcomes; maturesearchheuristics separatelycontrolled. Do not repairoldDEV orpickpricesfromtheorem.')
 with (O/'result.json').open('x') as f:json.dump(out,f,indent=2)
 print(json.dumps({k:out[k] for k in ['status','initial_inputs_checked','thresholds','finite_lattice_pairs_checked','seconds']}))
if __name__=='__main__':run()
