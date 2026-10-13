from pathlib import Path
from fractions import Fraction as F
import json,collections,ast
R=Path.cwd();O=R/'results/dev_aux/task1181';O.mkdir(exist_ok=False)
def row(g):
    d = {t: sum((1 if c == g['color'] else -1 for t2, c in zip(g['root']['types'], g['root']['colors']) if t2 == t)) for t in [4, 2]}
    return ([F(d[4]), F(d[2]), F(g['opponent'] == 'uniform_random')], F((g['label'] == 'W') - (g['label'] == 'L')))

def fit(games, restricted=False):
    rr = [row(g) for g in games]
    rr = [([x[0] + x[1], x[2]], y) for x, y in rr] if restricted else rr
    n = len(rr[0][0])
    A = [[sum((x[i] * x[j] for x, y in rr)) for j in range(n)] + [sum((x[i] * y for x, y in rr))] for i in range(n)]
    for j in range(n):
        pivot = next((i for i in range(j, n) if A[i][j]), None)
        if pivot is None:
            return None
        A[j], A[pivot] = (A[pivot], A[j])
        v = A[j][j]
        A[j] = [a / v for a in A[j]]
        for i in range(n):
            if i != j:
                v = A[i][j]
                A[i] = [a - v * b for a, b in zip(A[i], A[j])]
    return [A[i][-1] for i in range(n)]

def assess(games, b, restricted=False):
    vals = []
    for g in games:
        x, y = row(g)
        x = [x[0] + x[1], x[2]] if restricted else x
        p = sum((a * c for a, c in zip(x, b)))
        vals.append((p - y) ** 2)
    return str(sum(vals) / len(vals))
out=[]
for n in [1154,1170]:
 gs=[json.loads(s) for s in (R/f'results/dev_aux/task{n}/games.jsonl').read_text().splitlines()]
 gs=[g for g in gs if n==1154 or (g['arm']=='J' and g['price']==720)]
 for prefix in ([4] if n==1154 else [4,8,16]):
  selected=[g for g in gs if g['root']['composition_ordinal']<prefix]
  comps=sorted(set(g['root']['composition'] for g in selected))
  for omit in [None]+comps:
   ss=[g for g in selected if g['root']['composition']!=omit]
   for role in ['all','whitecandidate','blackcandidate']:
    rr=[g for g in ss if role=='all' or g['color']==(role=='whitecandidate')];b=fit(rr)
    positive=bool(b and b[0]>0 and b[1]>0)
    out.append(dict(source=n,prefix_percomposition=prefix,omit=omit,role=role,N=len(rr),coefficients=list(map(str,b)) if b else None,positive_ratio=str(b[0]/b[1]) if positive else None,train_MSE=assess(rr,b) if b else None,scope='Postcollectiondiagnostictrainingonly, notnewheldoutprediction or retrainedpolicytest.'))
(O/'result.json').write_text(json.dumps(dict(status='EXACT_TEACHER_COEFFICIENT_STABILITY_NO_DEPLOYMENT',rows=out,new_go=0),indent=2))
for x in out:
 if x['omit'] is None:print(x)
