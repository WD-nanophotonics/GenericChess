"""Exact finite-depth material decision intervals on eight TRAIN-only roots.
Not WDL learning or generic full-game price identification. No root fit.
"""
from pathlib import Path
from fractions import Fraction as F
from copy import copy
import json,time,hashlib,math
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.session.session import GameSession
from generic_chess.session.result import SessionStatus
from scripts.generic_session_win_proof import choices,execute
from scripts.generic_win_proof import _Budget
from results.dev_aux.task2148.normal import SessionCompleteMaterialSearch
from results.dev_aux.task2175.receipt import choice_value
from results.dev_aux.task2153.stop_evidence import EvidenceStopReader
OUT=Path('results/dev_aux/task2245')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(n,v):
 with(OUT/n).open('x')as f:json.dump(v,f,indent=2)
def freeze():
 roots=[r for r in json.loads(Path('results/dev_aux/task2244/plan.json').read_text())['roots']if r['family']==31]
 save('plan.json',dict(roots=roots,depth=3,ratio_domain='all positive rational R/N, infinity limit open',source_sha=sha(OUT/'intervals.py'),root_selection='POSTHOCmechanismcounterexample family31of32fixedsixactorroots, selectedbecause2244observedactiondifference. EXPOSEDnotindependentvalidation; completealllegaldepth3tree, no pruning/heuristicleavesabove3.',cap_seconds=300,scope='POSTHOC exposedmechanismwitness, NOTnewstatisticalvalidation orW-Lbenefit. Exact finite-depth static-material intervals only; terminal infinity first andfirst-ordered-choice tie. NOT true WDL labels/tableteacher or fullgameuniqueprice. Comparisons to actual floatnormal receipt are separate, no guide used inthislocaltree.'))
 print('FROZEN_POSTHOC_COUNTEREXAMPLE_ONLY')
def run():
 assert not(OUT/'started.json').exists();p=json.loads((OUT/'plan.json').read_text());assert p['source_sha']==sha(OUT/'intervals.py');start=time.perf_counter();stop=EvidenceStopReader(Path.cwd());save('started.json',dict(plan_sha=sha(OUT/'plan.json')));allrows=[];nodes=0;checks=0
 def poll():stop();assert time.perf_counter()-start<p['cap_seconds']
 for root in p['roots']:
  poll();assert sha(root['rules'])==root['rules_sha'];c=compile_ruleset_for_execution(deserialize_ruleset(Path(root['rules']).read_text()));session=GameSession(c);target=session.state.position.side_to_move;coeff=set();counts={'nodes':0,'leaves':0,'terminals':0}
  def build(s,d):
   poll();counts['nodes']+=1
   if s.result.status is not SessionStatus.ONGOING:
    counts['terminals']+=1
    return dict(terminal=0 if s.result.winner is None else 1 if s.result.winner==target else-1)
   if d==0:
    a=b=0
    for pc in s.state.position.board:
     if pc is None or pc.current_type_id=='K':continue
     sign=1 if pc.owner==target else-1
     if pc.current_type_id=='R':a+=sign
     else:b+=sign
    coeff.add((a,b));counts['leaves']+=1;return dict(line=[a,b])
   bgt=_Budget(100000,30.,None);out=[]
   for choice in choices(s,bgt):
    child=copy(s);execute(child,choice);out.append(dict(choice=choice_value(choice),node=build(child,d-1)))
   assert out
   return dict(maximize=s.state.position.side_to_move==target,edges=out)
  tree=build(session,p['depth']);breaks=set()
  for a,b in coeff:
   for aa,bb in coeff:
    if a!=aa:
     x=F(bb-b,a-aa)
     if x>0:breaks.add(x)
  breaks=sorted(breaks)
  def value(node,x):
   if 'terminal'in node:return (math.inf if node['terminal']>0 else-math.inf if node['terminal']<0 else F(0)),None
   if 'line'in node:a,b=node['line'];return a*x+b,None
   values=[value(e['node'],x)[0]for e in node['edges']];best=(max if node['maximize']else min)(values);i=values.index(best);return best,node['edges'][i]['choice']
  spans=[];points=[];lower=F(0)
  for upper in breaks+[None]:
   x=(lower+upper)/2 if upper is not None else lower+1;score,action=value(tree,x);spans.append(dict(lower=str(lower),upper=None if upper is None else str(upper),probe=str(x),choice=action,score_at_probe=str(score)));lower=upper
  for x in breaks:
   score,action=value(tree,x);points.append(dict(ratio=str(x),choice=action,score=str(score)))
  comparisons=[]
  for x in sorted({F(1,4),F(1,2),F(1),F(2),F(4)}|{F(r['probe'])for r in spans}|set(breaks)):
   poll();expected,choice=value(tree,x)
   def evaluate(pos,t):return sum((1 if pc.owner==t else-1)*(float(x)if pc.current_type_id=='R'else 1.)for pc in pos.board if pc is not None and pc.current_type_id!='K')
   got=SessionCompleteMaterialSearch(c,evaluate,max_depth=p['depth']).choose(session,max_nodes=100000,seconds=5.,cancel=stop);assert got.completed_depth==p['depth']
   observed=choice_value(got.choice);equal=observed==choice;dyadic=x.denominator&(x.denominator-1)==0
   if dyadic:assert equal,(root['family'],x,choice,observed)
   comparisons.append(dict(ratio=str(x),exact_choice=choice,float_choice=observed,choice_equal=equal,dyadic=dyadic,completed_depth=got.completed_depth,normal_nodes=got.nodes));checks+=1
  changes=[]
  for i,x in enumerate(breaks):
   if spans[i]['choice']!=spans[i+1]['choice']or points[i]['choice']!=spans[i]['choice']:changes.append(str(x))
  result=dict(family=root['family'],root_rules_sha=root['rules_sha'],counts=counts,all_leaf_coefficients=[list(x)for x in sorted(coeff)],all_positive_leaf_crossings=[str(x)for x in breaks],actual_root_choice_change_points=changes,spans=spans,boundary_points=points,float_reference_checks=comparisons,tree=tree)
  save(f'family-{root["family"]}.json',result);allrows.append({k:result[k]for k in('family','counts','all_leaf_coefficients','actual_root_choice_change_points')});nodes+=counts['nodes']
 save('result.json',dict(status='COMPLETE_EXACT_DEPTH3_TWO_N_COUNTEREXAMPLE',roots=len(allrows),complete_tree_nodes=nodes,float_checks=checks,seconds=time.perf_counter()-start,summary=allrows,scope=p['scope']));print(json.dumps(dict(roots=len(allrows),nodes=nodes,checks=checks,seconds=time.perf_counter()-start)))
if __name__=='__main__':import sys;{'freeze':freeze,'run':run}[sys.argv[1]]()
