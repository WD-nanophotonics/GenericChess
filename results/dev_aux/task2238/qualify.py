"""Qualification of small direct ordering intervention, not an efficacy claim."""
from pathlib import Path
from copy import copy
import json,hashlib,time
from fractions import Fraction as F
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.session.session import GameSession
from generic_chess.session.result import SessionStatus
from scripts.generic_session_win_proof import choices,execute
from scripts.generic_win_proof import _Budget
from results.dev_aux.task2148.normal import SessionCompleteMaterialSearch
from results.dev_aux.task2238.normal import SeededMaterialSearch
from results.dev_aux.task2238.study import Guide
from results.dev_aux.task2153.stop_evidence import EvidenceStopReader
OUT=Path('results/dev_aux/task2238')
def run():
 assert not(OUT/'qualification.json').exists();start=time.perf_counter();stop=EvidenceStopReader(Path.cwd());seeds=[1977,8173];guide=Guide();rankchecks=0;different=0
 for i,r in enumerate(guide.rows.values()):
  if i%256==0:stop();assert time.perf_counter()-start<300
  if r['status']!='ongoing':continue
  if r['label']=='WIN':
   candidates=[e for e in r['actions']if e['child_value']==-1];rank=min(guide.indices[e['child']]['rank']for e in candidates);candidates=[e for e in candidates if guide.indices[e['child']]['rank']==rank];assert r['rank']==rank+1
  elif r['label']=='LOSS':
   rank=max(guide.indices[e['child']]['rank']for e in r['actions']);candidates=[e for e in r['actions']if guide.indices[e['child']]['rank']==rank];assert r['rank']==rank+1
  else:candidates=[e for e in r['actions']if e['child_value']==0]
  selected=[min(candidates,key=lambda e:hashlib.sha256((str(seed)+':'+e['action']).encode()).hexdigest())for seed in seeds];assert all(e in r['actions']for e in selected);different+=selected[0]['action']!=selected[1]['action'];rankchecks+=2
 roots=sorted([r for r in json.loads(Path('results/dev_aux/task2220/inputs.json').read_text())['roots']if r['split']=='TRAIN'],key=lambda r:r['family'])[:8];checks=[]
 for root in roots:
  stop();c=compile_ruleset_for_execution(deserialize_ruleset(Path(root['rules']).read_text()));s=GameSession(c)
  for ratio in(.25,.5,.75,1.,2.):
   def ev(pos,target):return sum((1 if pc.owner==target else-1)*(ratio if pc.current_type_id=='R'else 1.)for pc in pos.board if pc is not None and pc.current_type_id!='K')
   base=SessionCompleteMaterialSearch(c,ev,max_depth=2).choose(s,max_nodes=10000,seconds=5.,cancel=stop);assert base.completed_depth==2
   for seed in seeds:
    player=SeededMaterialSearch(c,ev,max_depth=2,priority_seed=seed);a=list(choices(s,_Budget(1000,5.,None)));b=player.prioritized(s,_Budget(1000,5.,None));assert len(a)==len(b)and set(a)==set(b)and b==player.prioritized(s,_Budget(1000,5.,None));d=player.choose(s,max_nodes=10000,seconds=5.,cancel=stop);assert d.completed_depth==2 and d.score==base.score;assert d.choice in b
    child=copy(s);execute(child,d.choice);checks.append(dict(family=root['family'],ratio=ratio,seed=seed,completed_depth=d.completed_depth,score=str(d.score),same_choice=d.choice==base.choice,nodes=d.nodes))
 result=dict(status='PASS_STABLE_COMPLETE_LEGAL_ORDER_EQUAL_D2_VALUES_AND_STRICT_GUIDE_RANKS',seeds=seeds,normal_checks=len(checks),guide_rank_checks=rankchecks,guide_rows_with_different_tied_choice=different,checks=checks,seconds=time.perf_counter()-start,scope='ActionprioritysortedBEFOREalphabeta;no posthoc randomselectionfrombound-equalchildren. Entire legalchoice set/stability/currentSession preserved; fullD2valueequal on8TRAINx5pricesx2seeds. Allloadedlowinventoryguide strictWDL/rankquality unchanged, onlytieprioritychanges. No efficacyclaim orcompletehistoryWINproof.')
 (OUT/'qualification.json').write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items()if k!='checks'}))
if __name__=='__main__':run()
