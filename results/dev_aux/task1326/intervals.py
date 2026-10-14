from pathlib import Path
import json,collections
from fractions import Fraction as F
R=Path.cwd();O=R/'results/dev_aux/task1364';O.mkdir()
roots=json.loads((R/'results/dev_aux/task1325/roots.json').read_bytes())['roots'];rows=[];hist=collections.Counter()
for root in roots:
 tree=root['symbolic']['tree'];aff={(q['R'],q['N']) for ls in tree.values() for q in ls if 'terminal' not in q};assert all(abs(a)<=1 and abs(b)<=1 and abs(a)+abs(b)<=2 for a,b in aff)
 cuts={F(1,2),F(256,45)}
 for a,b in aff:
  for c,d in aff:
   if a!=c:
    x=F(d-b,a-c)
    if F(1,2)<x<F(256,45):cuts.add(x)
 cuts=sorted(cuts)
 v=lambda q,x:F(q['terminal']*1000000) if 'terminal' in q else q['R']*x+q['N']
 cells=[]
 for a,b in zip(cuts,cuts[1:]):
  x=(a+b)/2;sc={u:min(v(q,x) for q in ls) for u,ls in tree.items()};best=sorted(u for u,z in sc.items() if z==max(sc.values()));cells.append(dict(kind='open',domain=[str(a),str(b)],best=best,lex=best[0]))
 for x in cuts:
  sc={u:min(v(q,x) for q in ls) for u,ls in tree.items()};best=sorted(u for u,z in sc.items() if z==max(sc.values()));cells.append(dict(kind='point',domain=[str(x),str(x)],best=best,lex=best[0]))
 hist.update(str(x) for x in cuts);rows.append(dict(seed=root['seed'],affine_coefficients=sorted(aff),cuts=[str(x) for x in cuts],cells=cells))
out=dict(status='COMPLETE_CACHED64_D2_EXACT_PRICE_CELLS_AND_TIES',rows=rows,cut_root_counts=dict(hist),new_go=0,scope='Priceblind exchange sampler uses balanced initial material and at most one capture by each side atD2; nonterminal leaf coefficients R,N in{-1,0,1}. Pair leaf breakpoints only .5,1,2 positive interior, hence all r>2 share D2 decisions (terminal priority fixed). Says nothing directly about mature deeper selective tree or true longerWL. This detects limited curriculum price-resolution, not universal value impossibility.')
(O/'result.json').write_text(json.dumps(out,indent=2));print(dict(hist))
