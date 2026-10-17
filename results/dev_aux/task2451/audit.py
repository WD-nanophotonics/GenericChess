"""Independent topology/finite-value checking of the rational arrangement."""
from pathlib import Path
from fractions import Fraction as Q
from itertools import combinations
from math import gcd,inf
from functools import reduce
import json,time
from results.dev_aux.task2392.reader import SharedDeleteStopReader
OUT=Path('results/dev_aux/task2451')
def validate(faces,nodes,box=8):
 planes={tuple(n['features'])for n in nodes if n['depth_remaining']==0 and n['status']=='ongoing'}|{(0,0,0)};lines=set()
 for x,y in combinations(sorted(planes),2):
  d=tuple(a-b for a,b in zip(x,y))
  if d[:2]==(0,0):continue
  div=reduce(gcd,map(abs,d));d=tuple(a//div for a in d)
  if next(a for a in d if a)<0:d=tuple(-a for a in d)
  lines.add(d)
 def ev(d,xy):return d[0]*xy[0]+d[1]*xy[1]+d[2]
 cells=[r for r in faces if r['kind']=='OPEN_CELL'];sigs=set();area=Q(0);vertices=set();segments=set();counts={}
 for row in cells:
  poly=[tuple(map(Q,xy))for xy in row['geometry']];assert len(poly)>=3;point=tuple(map(Q,row['point']));assert all(0<=x<=box and 0<=y<=box for x,y in poly);sig=tuple(1 if ev(d,point)>0 else-1 if ev(d,point)<0 else 0 for d in sorted(lines));assert 0 not in sig and sig not in sigs;sigs.add(sig);assert all(min(ev(d,x)for x in poly)>=0 or max(ev(d,x)for x in poly)<=0 for d in lines);vertices.update(poly);segments.update(tuple(sorted((a,b)))for a,b in zip(poly,poly[1:]+poly[:1]));area+=abs(sum(a[0]*b[1]-a[1]*b[0]for a,b in zip(poly,poly[1:]+poly[:1])))/2
 assert area==box*box
 actual_segments={tuple(sorted(tuple(map(Q,x))for x in r['geometry']))for r in faces if r['kind']=='OPEN_SEGMENT'};actual_vertices={tuple(map(Q,r['point']))for r in faces if r['kind']=='VERTEX'};assert actual_segments==segments and actual_vertices==vertices
 def tree_value(i,point):
  n=nodes[i]
  if n['status']!='ongoing':return Q(0)if n['winner']is None else inf if n['winner']==nodes[0]['side']else-inf
  if n['depth_remaining']==0:return sum(Q(a)*b for a,b in zip(n['features'],(*point,Q(1))))
  return(max if n['side']==nodes[0]['side']else min)(tree_value(j,point)for ch,j in n['children'])
 for row in faces:
  point=tuple(map(Q,row['point']));scores=[tree_value(j,point)for ch,j in nodes[0]['children']];chosen=next(i for i,v in enumerate(scores)if v==max(scores));assert chosen==row['chosen_root_index'];a,b=point;assert scores[4]==max(2*a,a+b)and scores[6]==2 and max(scores)==max(2*a,a+b,Q(2));assert chosen==(6 if a<1 and a+b<2 else 4);counts[str(chosen)]=counts.get(str(chosen),0)+1
 return dict(cells=len(cells),vertices=len(vertices),segments=len(segments),exact_area=str(area),checked_faces=len(faces),selected_counts=counts)
def run():
 t=time.perf_counter();stop=SharedDeleteStopReader(Path.cwd());stop();faces=json.loads(Path('results/dev_aux/task2447/faces.json').read_text());nodes=[json.loads(x)for x in Path('results/dev_aux/task2440/family-2/nodes.jsonl').read_text().splitlines()];checks=validate(faces,nodes);bad=[r for r in faces if not(r['kind']=='OPEN_CELL'and r['index']==0)]
 try:validate(bad,nodes)
 except AssertionError:missing_cell_rejected=True
 else:raise AssertionError('missingcellnotrejected')
 bad=json.loads(json.dumps(faces));bad[0]['chosen_root_index']=6 if bad[0]['chosen_root_index']==4 else 4
 try:validate(bad,nodes)
 except AssertionError:wrong_choice_rejected=True
 else:raise AssertionError('wrongchoicenotrejected')
 float_result=json.loads(Path('results/dev_aux/task2456/result.json').read_text());assert float_result['queries']==float_result['ordinary_D3']==71;stop();result=dict(status='PASS_INDEPENDENT_RATIONAL_COVERAGE_VALUES_AND_BOUNDARY_TIES',**checks,missing_cell_rejected=missing_cell_rejected,wrong_choice_rejected=wrong_choice_rejected,float_qualification=float_result,seconds=time.perf_counter()-t,scope='Geometrycoveragebydisjointleaf-order-signcells/totalarea64, allcellboundarysegments/verticespresent; independentrecursivefinite-treevalues/ties. CapturingNchoseniff boardR<1 ANDboardR+handR<2; capturingR otherwise inclties, fixedNboth1. Exactrationalboundedboxmathematicalmodel, not universalIEEEpolicyproof;71actualfloatingqueriesqualifiedonlyatthesefaces. No newgames/fit/capextension/defaults.')
 (OUT/'result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
if __name__=='__main__':run()
