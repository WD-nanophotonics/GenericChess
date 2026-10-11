"""Four actual compact payload/cache lineage calls, synthetic constant model."""
import copy,hashlib,json,sys,ast
from pathlib import Path
ROOT=Path.cwd();E=ROOT/'.local_agent/pinned_bebe';sys.path.insert(0,str(E));B=Path(__file__).resolve().parent;D=json.loads((B/'DECLARATION.json').read_bytes())
from native_initial_fixture import _initial
from generic_chess.native.semantic_engine import SemanticSearchEngine
from generic_chess.native.compiler import build_semantic_compile_payload
from generic_chess.session.session import GameSession
from generic_chess.ai.limits import SearchLimits
from scripts.research_record import record_value
c,n,packed=_initial();s=GameSession(c);state=s.state;w=tuple(s._search_witnesses);payload,report=build_semantic_compile_payload(c);dimension=2*len(n.type_ids)*payload['board_size']**2+2+5
for a in payload['aux_slots']:dimension+=(2 if a['value_kind']==0 else 6) if a['scope']==1 else (1 if a['value_kind']==0 else 3)
model={'input_mean':[0.]*dimension,'input_scale':[1.]*dimension,'hidden_weights':[[0.]*dimension for _ in range(16)],'hidden_bias':[0.]*16,'output_weights':[0.]*16,'output_bias':0.,'target_scale':1.,'width':16,'hand_type_indices':[0],'perspective':'owner0'}

from generic_chess.native import semantic_engine as engine_module
raw=(E/'generic_chess/native/semantic_engine.py').read_text();cls=next(x for x in ast.parse(raw).body if isinstance(x,ast.ClassDef) and x.name=='SemanticSearchEngine')
class Freeze(ast.NodeTransformer):
 def visit_Assign(self,node):
  if any(isinstance(t,ast.Attribute) and t.attr in ('_compact_values','_ordering_compact_values') for t in node.targets):
   if isinstance(node.value,ast.IfExp) and isinstance(node.value.orelse,ast.Call):node.value.orelse=ast.Call(func=ast.Name(id='_aux_deepcopy',ctx=ast.Load()),args=[node.value.orelse],keywords=[])
  return self.generic_visit(node)
 def visit_Dict(self,node):
  for i,k in enumerate(node.keys):
   if isinstance(k,ast.Constant) and k.value=='compact_nonlinear':node.values[i]=ast.Call(func=ast.Name(id='_aux_deepcopy',ctx=ast.Load()),args=[node.values[i]],keywords=[])
  return self.generic_visit(node)
cls=Freeze().visit(cls);ast.fix_missing_locations(cls);ns=dict(engine_module.__dict__);ns['_aux_deepcopy']=copy.deepcopy;exec(compile(ast.Module(body=[cls],type_ignores=[]),'<private compact payload copy candidate>','exec'),ns);Candidate=ns['SemanticSearchEngine']
(B/'proposed_freeze_changes.py').write_text("from copy import deepcopy as _aux_deepcopy\n\n"+'\n\n'.join(ast.unparse(x) for x in cls.body if isinstance(x,ast.FunctionDef) and x.name in ('__init__','_set_checkpoint_values','_set_ordering_checkpoint_values','bind_evaluator','native_evaluator_values'))+'\n',encoding='utf-8')
zeros={t:0 for t in n.type_ids};p=Candidate(c,n,board_values=zeros,hand_values=zeros,compact_values=model,tt_megabytes=1,evaluator_scale=1);original_capsule=p._capsule;limits=SearchLimits(max_depth=2,max_nodes=4096,max_time_seconds=2,quiescence_max_depth=0);rows=[]
def run(name):
 v=p.search(s,limits);assert v.completed_depth==2 and v.termination_reason=='completed';rows.append(dict(case=name,decision=record_value(v),tt_info=p.tt_info(),reported_output_bias=p.native_evaluator_values['compact_nonlinear']['output_bias']));return v
old=run('old_zero_profile');exposed=p.native_evaluator_values['compact_nonlinear'];assert exposed is not p._compact_values;exposed['output_bias']=100.
got=run('mutated_getter_copy');assert got.score==0 and p._capsule is original_capsule
model['hidden_bias'][0]=50.;model['output_weights'][0]=1.
nested=run('mutated_original_nested_lists');assert nested.score==0 and p._compact_values['hidden_bias'][0]==p._compact_values['output_weights'][0]==0 and p._capsule is original_capsule
p.bind_evaluator(zeros,zeros,compact_values=exposed,evaluator_scale=1);assert p._capsule is not original_capsule
new=run('valid_explicit_rebind');assert new.score==100 and p.native_evaluator_values['compact_nonlinear']['output_bias']==100
assert s.state==state and tuple(s._search_witnesses)==w
out={'complete':True,'source_pin':D['source_pin'],'rows':rows,'class_source_sha256':hashlib.sha256((ast.unparse(cls)+'\n').encode()).hexdigest(),'original_class_unchanged':engine_module.SemanticSearchEngine is not Candidate,'scope':'Private AST copy deep-copies compact leaf/ordering payload assignments and getter compact output;four actual D2 leaf/TT calls. Leaf constructor/getter/nested caller mutation and explicit rebind checked. Ordering execution, checkpoint-ID mutation, concurrent/allocator-fault paths not independently certified.'}
(B/'repair_result.json').write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8');print(json.dumps([{'case':r['case'],'score':r['decision']['score']} for r in rows]))
