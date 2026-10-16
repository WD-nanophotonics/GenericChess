"""Independent exact-tree/public-session consumer; no original producer entry."""
from pathlib import Path
from copy import copy
from fractions import Fraction as F
import json,math,hashlib
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.session.session import GameSession
from generic_chess.session.result import SessionStatus
from scripts.generic_session_win_proof import choices,execute
from scripts.generic_win_proof import _Budget
from results.dev_aux.task2175.receipt import choice_value
from results.dev_aux.task2153.stop_evidence import EvidenceStopReader
OUT=Path('results/dev_aux/task2253')
def run():
 stop=EvidenceStopReader(Path.cwd());checks=[];totalnodes=0
 for task in(2231,2245):
  folder=Path(f'results/dev_aux/task{task}');plan=json.loads((folder/'plan.json').read_text());done=json.loads((folder/'result.json').read_text())
  for root in plan['roots']:
   stop();saved=json.loads((folder/f'family-{root["family"]}.json').read_text());assert hashlib.sha256(Path(root['rules']).read_bytes()).hexdigest()==root['rules_sha'];s=GameSession(compile_ruleset_for_execution(deserialize_ruleset(Path(root['rules']).read_text())));target=s.state.position.side_to_move;count=0;coeff=set()
   def check(session,node,depth):
    nonlocal count
    stop();count+=1
    if session.result.status is not SessionStatus.ONGOING:
     assert node==dict(terminal=0 if session.result.winner is None else 1 if session.result.winner==target else-1);return
    if depth==0:
     aa=bb=0
     for pc in session.state.position.board:
      if pc is None or pc.current_type_id=='K':continue
      sign=1 if pc.owner==target else-1
      if pc.current_type_id=='R':aa+=sign
      else:bb+=sign
     assert node==dict(line=[aa,bb]);coeff.add((aa,bb));return
    assert node['maximize']==(session.state.position.side_to_move==target);legal=list(choices(session,_Budget(100000,5.,None)));assert [choice_value(a)for a in legal]==[e['choice']for e in node['edges']]
    for a,e in zip(legal,node['edges']):child=copy(session);execute(child,a);check(child,e['node'],depth-1)
   check(s,saved['tree'],plan['depth']);assert count==saved['counts']['nodes']and sorted(coeff)==[tuple(x)for x in saved['all_leaf_coefficients']]
   crossings=sorted({F(b2-b,a-a2)for a,b in coeff for a2,b2 in coeff if a!=a2 and F(b2-b,a-a2)>0});assert [str(x)for x in crossings]==saved['all_positive_leaf_crossings']
   def evaluate(node,x):
    if 'terminal'in node:return math.inf if node['terminal']>0 else-math.inf if node['terminal']<0 else F(0),None
    if 'line'in node:a,b=node['line'];return a*x+b,None
    vv=[evaluate(e['node'],x)[0]for e in node['edges']];v=(max if node['maximize']else min)(vv);return v,node['edges'][vv.index(v)]['choice']
   for row in saved['spans']:
    value,choice=evaluate(saved['tree'],F(row['probe']));assert row['score_at_probe']==str(value)and row['choice']==choice
   for row in saved['boundary_points']:
    value,choice=evaluate(saved['tree'],F(row['ratio']));assert row['score']==str(value)and row['choice']==choice
   for row in saved['float_reference_checks']:
    value,choice=evaluate(saved['tree'],F(row['ratio']));assert row['exact_choice']==choice
    if row['dyadic']:assert row['float_choice']==choice
   checks.append(dict(task=task,family=root['family'],complete_public_nodes=count,all_affine_crossings=[str(x)for x in crossings],actual_choice_change_points=saved['actual_root_choice_change_points']));totalnodes+=count
 result=dict(status='PASS_COMPLETE_PUBLIC_TREE_EDGES_AFFINE_LEAVES_AND_INTERVAL_CHOICES',roots=len(checks),nodes=totalnodes,checks=checks,scope='IndependentfullpublicSessionedge/terminalreplayofsavedcompleteD2/D3treesandexactrationalintervalvalues. No search/fit/rewardgame producers; posthocfamily31remainsmechanismwitness,notheldoutW-L.')
 with(OUT/'result.json').open('x')as f:json.dump(result,f,indent=2)
 print(json.dumps({k:v for k,v in result.items()if k!='checks'}))
if __name__=='__main__':run()
