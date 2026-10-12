import json,itertools,time
from fractions import Fraction
from pathlib import Path
R=Path.cwd();O=R/'results/dev_aux/task243';O.mkdir(exist_ok=True);X=json.loads((R/'results/dev_aux/task242/result.json').read_bytes());F=json.loads((R/'results/dev_aux/task242/features.json').read_bytes());S=json.loads((R/'results/dev_aux/task241/result.json').read_bytes());groups={};witnesses=[];start=time.monotonic()
for row in F['rows']:
 sig=tuple(sorted(set(tuple(z['features']) if 'features' in z else ('terminal',z['terminal']) for z in row['branches']),key=str));groups.setdefault(row['root'],{}).setdefault(sig,[]).append(row)
for name,gs in groups.items():
 for sig,rs in gs.items():
  lo=min(Fraction(r['goal']) for r in rs);hi=max(Fraction(r['goal']) for r in rs)
  if hi>lo:
   low=next(r for r in rs if Fraction(r['goal'])==lo);high=next(r for r in rs if Fraction(r['goal'])==hi);witnesses.append(dict(root=name,low_move=low['move'],high_move=high['move'],goals=[str(lo),str(hi)],unique_leaf_feature_set=[list(x) for x in sig],proof='Identicalsets ofterminalconstants andPNBRQleafvectors => identicalminoverbranches forEVERYpricevector (alsooutside625grid), so no materialweight canstrictlyrankthesetwo moves. Differentreplymultiplicities/geometry affectuniformmategoal, notminmaterial.'))
summary=[]
for phase in ('train','heldout'):
 roots=[r for r in X['root_policies'] if r['phase']==phase];unitidx=312;canonical=sum(Fraction(r['goal_values'][unitidx]) for r in roots)/len(roots);favorable=sum(Fraction(r['tie_goal_max'][unitidx]) for r in roots)/len(roots);adverse=sum(Fraction(r['tie_goal_min'][unitidx]) for r in roots)/len(roots);oracle=sum(Fraction(r['exact_goal_optimum']) for r in roots)/len(roots);anygrid=sum(max(Fraction(v) for v in r['tie_goal_max']) for r in roots)/len(roots);summary.append(dict(phase=phase,unit_canonical=str(canonical),unit_favorable_tie=str(favorable),unit_adverse_tie=str(adverse),true_goal_oracle=str(oracle),rootwise_best_tie_any625=str(anygrid),unit_canonical_gap=str(oracle-canonical),unit_favorable_gap=str(oracle-favorable),anygrid_favorable_gap=str(oracle-anygrid),scope='Favorabletie usesgoal hindsight/notdeployed orlearned; rootwisebestgriddifferentpriceperroot/notglobalprice optimum.'))
out=dict(complete=True,seconds=time.monotonic()-start,all_witnesses=len(witnesses),witnesses=witnesses,summary=summary,scope='Exactfiniteaffine equivalence proofs; doesnotproveallQ/Rpricelearningimpossible. Zero finalWDLclaim; originaltrain/heldgeometry alreadyexposeddevelopment.');(O/'analysis.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps(dict(witnesses=len(witnesses),summary=summary),indent=2))
