from pathlib import Path
import hashlib,json
from results.dev_aux.task2616.summarize import reward_bounds,contrast
from results.dev_aux.task2616.train_tree import candidate_update,initial,encode_bound
from results.dev_aux.task2492.learning import Model,Receipt,Sample,TreeStrap

ROOT=Path.cwd();D=ROOT/'results/dev_aux/task2616'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def test_registration_and_slot_shape():
 reg=json.loads((D/'registration.json').read_text());p=json.loads((D/'plan.json').read_text());ep=json.loads((D/'eval-plan.json').read_text())
 assert reg['status']=='REGISTERED_PRE_RUN' and reg['no_training_yet'] and reg['no_evaluation_yet']
 assert sha(D/'plan.json')==reg['plan_sha256'] and sha(D/'eval-plan.json')==reg['eval_plan_sha256']
 assert len(p['conditions']['seeds'])==4 and len(ep['slots'])==1024
 assert {s[4] for s in ep['slots']}=={'initial','TD','WDL','TreeStrap'}
 assert p['budget']['expected_new_run_seconds']<7200 and p['budget']['hard_cap_seconds']==5400
 assert p['conditions']['training']['global_hard_cap_seconds']==1200 and ep['cap_seconds']==3600
 assert ep['node_budget_per_slot_both_actors']==20000
 assert not any((D/n).exists() for n in ('tree-started.json','eval-started.json'))

def test_source_pinset():
 runreg=json.loads((D/'runner-registration.json').read_text())
 assert runreg['status']=='READY_PRE_RUN'
 for name,h in runreg['runtime_pins'].items():assert sha(ROOT/name)==h,name

def test_initial_vectors_bind_to_seed():
 import random
 for seed in (1977,8173,27182,31415):
  r=random.Random(seed);assert initial(seed)==[1.0]+[r.uniform(.5,1.5) for _ in range(4)]

def test_tree_update_candidate_complete_only():
 m=Model([1,1,1,1,1]); learner=TreeStrap(eta=.05)
 sample=Sample((0,1,0,0,0),2.,3.,1)
 complete=Receipt(None,2.5,(0,1,0,0,0),False,(sample,),1,True,0,0.,'complete')
 incomplete=Receipt(None,None,None,False,(),1,False,0,0.,'resource')
 before=list(m.weights)
 assert candidate_update(learner,m,1,0,complete) is None and m.weights==before
 assert candidate_update(learner,m,0,0,incomplete) is None and m.weights==before
 stats=candidate_update(learner,m,0,0,complete)
 assert stats['samples']==1 and stats['active']==1 and m.weights!=before

def test_unknown_completion_bounds_preserve_known_draw():
 assert reward_bounds(None)==(-1,1) and reward_bounds(0)==(0,0)
 table={(0,1,700001,0,'uniform','A'):1,(0,1,700001,0,'uniform','B'):None}
 rows=contrast(table,[(0,1,700001,0,'uniform')],'A','B')
 assert rows['sum_bound']==[0,2]
 assert rows['counts']['unknown_endpoint']==1

def test_infinities_are_serialized_as_strings():
 import math
 assert encode_bound(math.inf)=='+inf' and encode_bound(-math.inf)=='-inf'
