"""Independent static-interval/RMS arithmetic from saved initial TRAIN trees."""
from pathlib import Path
from math import tanh,sqrt,isclose
import json,chess,hashlib,random
OUT=Path('results/dev_aux/task2520');BASE=Path('results/dev_aux/task2517')
def run():
 p=json.loads((BASE/'plan.json').read_text());done=json.loads((BASE/'result.json').read_text());rr=[json.loads(x)for x in(BASE/'queries.jsonl').read_text().splitlines()];tree=[];root=[];moves=0
 for n,h in p['pins'].items():assert hashlib.sha256(Path(n).read_bytes()).hexdigest()==h,n
 assert[(r['seed'],r['family'])for r in rr]==[(s,f)for s in p['seeds']for f in p['families']]
 for r in rr:
  rng=random.Random(r['seed']);weights=[1.]+[rng.uniform(.5,1.5)for _ in range(4)];assert r['weights']==weights;b=chess.Board();rng=random.Random(r['family'])
  for _ in range(p['prefix_plies']):
   if b.outcome(claim_draw=True)is not None:break
   m=rng.choice(sorted(b.legal_moves,key=lambda a:a.uci()));b.push(m);moves+=1
  assert r['record']['moves']==[m.uci()for m in b.move_stack]and r['record']['fen']==b.fen();assert r['complete'];directions=[]
  for phi,lower,upper,depth in r['samples']:
   value=tanh(sum(w*x for w,x in zip(weights,phi))/10);lo=-1. if lower is None else tanh(lower/10);hi=1. if upper is None else tanh(upper/10);err=lo-value if value<lo else hi-value if value>hi else 0.;directions.append([0. if i==0 else err*x*(1-value*value)/10 for i,x in enumerate(phi)])
  mean=[sum(v[j]for v in directions)/max(1,len(directions))for j in range(5)];last=directions[-1]if directions else[0.]*5
  if directions:
   root_phi=[len(b.pieces(t,True))-len(b.pieces(t,False))for t in range(1,6)];assert r['samples'][-1][0]==root_phi and r['samples'][-1][1]==r['samples'][-1][2]
  assert all(isclose(x,y,abs_tol=1e-13,rel_tol=1e-10)for x,y in zip(mean,r['tree_direction']));assert all(isclose(x,y,abs_tol=1e-13,rel_tol=1e-10)for x,y in zip(last,r['root_direction']));tree.append(mean);root.append(last)
 tr=sqrt(sum(sum(x*x for x in v)for v in tree)/len(tree));ro=sqrt(sum(sum(x*x for x in v)for v in root)/len(root));assert isclose(tr,done['tree_RMS'],rel_tol=1e-10,abs_tol=1e-13)and isclose(ro,done['root_RMS'],rel_tol=1e-10,abs_tol=1e-13);assert isclose(tr/ro,done['factor'],rel_tol=1e-10);record=dict(status='PASS_ALL_INITIAL_TRAIN_STATIC_GRADIENTS_SINGLE_RMS_FACTOR',rows=len(rr),legal_prefix_plies=moves,tree_RMS=tr,root_RMS=ro,factor=tr/ro,zero_tree=sum(not any(v)for v in tree),zero_root=sum(not any(v)for v in root),scope='Independentscalar arithmeticall128initialfrozenTRAINtrees/legalprefixes, includeszero directions. No newsearch/eta grid/fitnessselection. 64plycalibrationdistribution vs16plyselfplayprefix; initialnormonly, laterdriftnotcontrolled. Same4initialseeds/32sharedfamilies, not128independentexamples.');(OUT/'calibration-audit.json').write_text(json.dumps(record,indent=2));print(json.dumps(record))
if __name__=='__main__':run()
