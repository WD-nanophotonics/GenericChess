"""Validate exact published standalone candidate loading and combined boundaries."""
import copy,hashlib,importlib.util,json,sys,subprocess
from pathlib import Path
R=Path.cwd();E=R/'.local_agent/pinned_bebe';sys.path.insert(0,str(E));B=Path(__file__).resolve().parent
from native_initial_fixture import _initial
from generic_chess.native import semantic_engine as eng
from generic_chess.session.session import GameSession
from generic_chess.ai.limits import SearchLimits
candidate=R/'results/dev_aux/task066/proposed_native_binding.py';data=candidate.read_bytes()
assert data==subprocess.check_output(['git','show','08c47ddb65359b44d0e9a492f174dd019728ab18:results/dev_aux/task066/proposed_native_binding.py'])
spec=importlib.util.spec_from_file_location('generic_chess.native._aux_binding',candidate);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);C=m.SemanticSearchEngine
c,n,_=_initial();s=GameSession(c);state=s.state;w=tuple(s._search_witnesses);zeros={t:0 for t in n.type_ids};rows=[]
for lengths in [(18,0),(8,10)]:
 mapping={f'{o}:{t}':[0]*9 for o in (0,1) for t in n.type_ids};mapping['0:P']=[0]*lengths[0];mapping['1:P']=[0]*lengths[1]
 try:C(c,n,board_values=zeros,hand_values=zeros,spatial_occupancy_values=mapping);raise AssertionError('bad rows accepted')
 except ValueError as err:rows.append({'case':'row'+str(lengths),'rejected':str(err)})
model=json.loads((R/'results/dev_aux/task065/result.json').read_bytes())['rows'][0]['values']['compact_nonlinear'];p=C(c,n,board_values=zeros,hand_values=zeros,compact_values=model,tt_megabytes=1,evaluator_scale=1);old=p._capsule;values=copy.deepcopy(p.native_evaluator_values)
for name,kw in [('scale',{'evaluator_scale':0}),('C_profile',{'compact_values':{}})]:
 try:p.bind_evaluator(zeros,zeros,**kw);raise AssertionError('bad bind accepted')
 except ValueError as err:rows.append({'case':name,'rejected':str(err)})
 assert p._capsule is old and p.native_evaluator_values==values
limits=SearchLimits(max_depth=2,max_nodes=4096,max_time_seconds=2,quiescence_max_depth=0)
def run(name,expected):
 v=p.search(s,limits);assert v.completed_depth==2 and v.termination_reason=='completed' and v.score==expected
 rows.append({'case':name,'score':v.score,'depth':v.completed_depth,'nodes':v.nodes,'qnodes':v.qnodes,'termination':v.termination_reason})
run('initial',0);exposed=p.native_evaluator_values['compact_nonlinear'];exposed['output_bias']=100.;run('getter_copy_mutation',0)
model['hidden_bias'][0]=50.;model['output_weights'][0]=1.;run('caller_nested_mutation',0);assert p._capsule is old
p.bind_evaluator(zeros,zeros,compact_values=exposed,evaluator_scale=1);assert p._capsule is not old;run('valid_rebind',100)
assert s.state==state and tuple(s._search_witnesses)==w and eng.SemanticSearchEngine is not C
out={'complete':True,'candidate_sha256':hashlib.sha256(data).hexdigest(),'published_bytes_equal':True,'controls':rows,'product_namespace_unchanged':True,'session_history_unchanged':True,'scope':'Exact standalone artifact import;four short D2 andfour input-rejection controls;not allocator/concurrent faults, ordering execution or full domain certification.'}
(B/'result.json').write_bytes((json.dumps(out,indent=2)+'\n').encode());print(json.dumps(out))
