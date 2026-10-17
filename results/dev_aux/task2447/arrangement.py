"""Exact rational arrangement of ALL leaf-order lines in a bounded 2D box.
A full finite min/max tree is affine on each open arrangement cell. Its action
and leaf ordering are constant on each open boundary segment and vertex too.
This proves finite-tree choice cells, never actual WDL or unique prices.
"""
from pathlib import Path
from fractions import Fraction as F
from math import gcd,inf
from functools import reduce
from itertools import combinations
import json,time,hashlib,datetime
from results.dev_aux.task2392.reader import SharedDeleteStopReader
OUT=Path('results/dev_aux/task2447')
def area(poly):return abs(sum(a[0]*b[1]-a[1]*b[0]for a,b in zip(poly,poly[1:]+poly[:1])))/2
def value(line,p):return line[0]*p[0]+line[1]*p[1]+line[2]
def clip(poly,line,sign):
 result=[]
 for a,b in zip(poly,poly[1:]+poly[:1]):
  va=sign*value(line,a);vb=sign*value(line,b)
  if va>=0:result.append(a)
  if(va<0<vb)or(vb<0<va):
   t=va/(va-vb);result.append((a[0]+t*(b[0]-a[0]),a[1]+t*(b[1]-a[1])))
 clean=[]
 for p in result:
  if not clean or clean[-1]!=p:clean.append(p)
 if len(clean)>1 and clean[0]==clean[-1]:clean.pop()
 return clean
def lines_for(planes):
 lines=set()
 for x,y in combinations(planes,2):
  d=tuple(a-b for a,b in zip(x,y))
  if d[0]==d[1]==0:continue
  g=reduce(gcd,(abs(a)for a in d));d=tuple(a//g for a in d)
  if next(a for a in d if a)!=abs(next(a for a in d if a)):d=tuple(-a for a in d)
  lines.add(d)
 return sorted(lines)
def fold(nodes,point):
 values={};leaves={}
 for n in reversed(nodes):
  i=n['index']
  if n['status']!='ongoing':values[i]=F(0)if n['winner']is None else inf if n['winner']==nodes[0]['side']else-inf;leaves[i]=i
  elif n['depth_remaining']==0:values[i]=sum(F(a)*b for a,b in zip(n['features'],(*point,F(1))));leaves[i]=i
  else:
   best=(max if n['side']==nodes[0]['side']else min)(values[j]for ch,j in n['children']);j=next(j for ch,j in n['children']if values[j]==best);values[i]=best;leaves[i]=leaves[j]
 best=max(values[j]for ch,j in nodes[0]['children']);index=next(k for k,(ch,j)in enumerate(nodes[0]['children'])if values[j]==best)
 return index,best,[values[j]for ch,j in nodes[0]['children']],leaves
def run():
 assert not(OUT/'started.json').exists();p=json.loads((OUT/'plan.json').read_text());stop=SharedDeleteStopReader(Path.cwd());t=time.perf_counter();folder=Path(p['tree']);nodes=[json.loads(x)for x in(folder/'nodes.jsonl').read_text().splitlines()]
 for n,h in p['pins'].items():assert hashlib.sha256(Path(n).read_bytes()).hexdigest()==h
 assert all(n['complete']for n in nodes);planes=set(tuple(n['features'])for n in nodes if n['depth_remaining']==0 and n['status']=='ongoing');planes.add((0,0,0));lines=lines_for(planes);B=F(p['box_max']);cells=[[(F(0),F(0)),(B,F(0)),(B,B),(F(0),B)]];(OUT/'started.json').write_text(json.dumps(dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),cap=p['cap_seconds'])));
 def poll():
  stop()
  if time.perf_counter()-t>=p['cap_seconds']:raise TimeoutError('original_parametric_cap')
 for line in lines:
  poll();new=[]
  for poly in cells:
   vv=[value(line,x)for x in poly]
   if min(vv)<0<max(vv):
    for sign in(-1,1):
     clipped=clip(poly,line,sign)
     if len(clipped)>=3 and area(clipped)>0:new.append(clipped)
   else:new.append(poly)
  cells=new;assert len(cells)<=p['max_cells']
 assert sum(area(c)for c in cells)==B*B
 vertices=set();segments=set();samples=[]
 for k,poly in enumerate(cells):
  poll();assert all(min(value(line,v)for v in poly)>=0 or max(value(line,v)for v in poly)<=0 for line in lines)
  center=tuple(sum(v[i]for v in poly)/len(poly)for i in(0,1));samples.append(('OPEN_CELL',k,center,poly))
  vertices.update(poly)
  for a,b in zip(poly,poly[1:]+poly[:1]):segments.add(tuple(sorted((a,b))))
 for k,(a,b)in enumerate(sorted(segments)):samples.append(('OPEN_SEGMENT',k,tuple((a[i]+b[i])/2 for i in(0,1)),[a,b]))
 for k,v in enumerate(sorted(vertices)):samples.append(('VERTEX',k,v,[v]))
 assert len(samples)<=p['max_samples'];rows=[];formula_checks=[];selected={}
 # Concrete root actions fixed before evaluation from actual legal captures.
 A=p['capture_R_index'];N=p['capture_N_index']
 for kind,k,point,geometry in samples:
  poll();choice,score,table,leaves=fold(nodes,point);a,b=point;expected_A=max(2*a,a+b);expected_N=F(2);formula_checks.append(table[A]==expected_A and table[N]==expected_N and score==max(expected_A,expected_N));selected[str(choice)]=selected.get(str(choice),0)+1
  rows.append(dict(kind=kind,index=k,point=list(map(str,point)),geometry=[[str(x),str(y)]for x,y in geometry],chosen_root_index=choice,root_score=str(score),capture_R_score=str(table[A]),capture_N_score=str(table[N]),root_leaf=leaves[0],root_leaf_features=nodes[leaves[0]]['features']))
 (OUT/'faces.json').write_text(json.dumps(rows,indent=2));result=dict(status='PASS_COMPLETE_RATIONAL_LEAF_ORDER_ARRANGEMENT',tree_nodes=len(nodes),leaf_planes=sorted(planes),comparison_lines=lines,box=[0,p['box_max']],open_cells=len(cells),open_segments=len(segments),vertices=len(vertices),representatives=len(samples),total_exact_area=str(sum(area(c)for c in cells)),selected_counts=selected,root_capture_R_formula='max(2*boardR,boardR+handR)',root_capture_N_formula='2',root_max_of_two_formula_holds_all_faces=all(formula_checks),seconds=time.perf_counter()-t,scope=p['scope']+' FullarrangementofALLfiniteleafpairorderlines partitionsfullfiniteCoretree. Everyopen2Dcell/edge/vertex checkedwithEXACTrationalarithmetic andstablefirsttie; notjustdensergrid. Leaforderingconstantoneachface provesfinitevalue/rootpolicy there. Boundedboxonly; rootpolicyregionnotactualWDL/uniqueprices/globalruleoptimality.')
 (OUT/'result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
if __name__=='__main__':run()
