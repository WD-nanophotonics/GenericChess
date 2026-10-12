import json,time
from pathlib import Path
from fractions import Fraction
import chess
R=Path.cwd();O=R/'results/dev_aux/task254';O.mkdir(exist_ok=True);D=json.loads((R/'results/dev_aux/task241/declaration.json').read_bytes());T=json.loads((R/'results/dev_aux/task250/tree.json').read_bytes());start=time.monotonic();records=[]
for f in D['roots']:
 b=chess.Board(f['fen']);side=b.turn;feat=tuple(len(b.pieces(t,side))-len(b.pieces(t,not side)) for t in range(1,6));root=next(r for r in T['roots'] if r['root']==f['name']);target=max(Fraction(row['goal']) for row in root['rows']);records.append(dict(root=f['name'],phase=f['phase'],features=list(feat),target=str(target),in_check=b.is_check()))
results=[]
for phase in ('train','heldout','combined'):
 rr=[r for r in records if phase=='combined' or r['phase']==phase];groups={}
 for r in rr:groups.setdefault(tuple(r['features']),[]).append(r)
 floor=Fraction(0);rows=[]
 for f,rs in groups.items():
  ys=[Fraction(r['target']) for r in rs];mean=sum(ys)/len(ys);var=sum((y-mean)**2 for y in ys)/len(ys);floor+=var*len(rs)/len(rr);rows.append(dict(features=list(f),roots=len(rs),conditional_mean=str(mean),conditional_variance=str(var),targets=rs))
 results.append(dict(phase=phase,count_only_arbitrary_function_MSE_lower_bound=str(floor),lower_bound_float=float(floor),groups=rows))
out=dict(complete=True,seconds=time.monotonic()-start,results=results,proof='IdenticalrootPNBRQcounts implyidenticalprediction forANYfunction ofthosecounts, includinglinear/tanh/pricelogstudent. Squared-erroroptimum within eachsamefeature group is its mean; group variance is irreducible lowerbound. Theseexactfinitegoaltargets varybygeometry/check evenatfixedinventory. MeanwhilemeanD3policy achievesgoal optimumforallallowedprices (251), so statevalue-calibration error andpolicypriceimprovement aredifferent judgments.',scope='PosthocfiniteC24geometrydiagnostic notlearnerfit/generalWDL calibration. Doesnotrefute fixedprices averagedunder explicitdistribution, doesnotrequire exactcalibration before deployment, nohumanlabels andnofullChess impossibility.');(O/'analysis.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print([(r['phase'],r['lower_bound_float']) for r in results])
