import json,time,hashlib,collections
from pathlib import Path
from fractions import Fraction
R=Path.cwd();O=R/'results/dev_aux/task299';O.mkdir(exist_ok=False);D=json.loads((R/'results/dev_aux/task296/declaration.json').read_bytes());X=json.loads((R/'results/dev_aux/task296/result.json').read_bytes());train=X['train'];start=time.monotonic();A=[[Fraction(v) for v in z['x']] for z in train];y=[Fraction(z['y']) for z in train]
G=[[sum(a[i]*a[j] for a in A) for j in range(5)] for i in range(5)];h=[sum(a[i]*t for a,t in zip(A,y)) for i in range(5)];aug=[G[i]+[h[i]] for i in range(5)];pivots=[]
for col in range(5):
 p=next(i for i in range(col,5) if aug[i][col]);aug[col],aug[p]=aug[p],aug[col];pivot=aug[col][col];pivots.append(str(pivot));aug[col]=[v/pivot for v in aug[col]]
 for i in range(5):
  if i!=col:q=aug[i][col];aug[i]=[x-q*z for x,z in zip(aug[i],aug[col])]
w=[r[-1] for r in aug];sse=sum((sum(a[i]*w[i] for i in range(5))-t)**2 for a,t in zip(A,y));normal=[sum(a[i]*(sum(a[j]*w[j] for j in range(5))-t) for a,t in zip(A,y)) for i in range(5)];assert normal==[0]*5;assert all(abs(float(w[i])-X['fit']['coefficients'][k])<1e-12 for i,k in enumerate('PNBRQ'));assert abs(float(sse/len(A))-X['fit']['fit_MSE'])<1e-12
out=dict(complete=True,independent_exact_fraction_OLS=True,normal_equations_exact_zero=True,positive_direction=False,Gram=[[str(v) for v in row] for row in G],rhs=[str(v) for v in h],pivots=pivots,coefficients={k:str(v) for k,v in zip('PNBRQ',w)},MSE=str(sse/len(A)),seconds=time.monotonic()-start,scope='ExactGaussJordan normal equations corroboratefullrank NumPyOLS and3negativecoefficients; no humanreference, statisticalidentifiability ornewtraininglabel. Nopositiveclipping/adoption. Eachsourcefeature/terminaltarget will separatelyreplay in sourceaudit.')
(O/'audit.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps(out,indent=2))