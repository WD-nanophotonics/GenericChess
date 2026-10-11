"""Combine reviewed private candidates and run existing focused regressions."""
import ast,copy,hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path.cwd();E=ROOT/'.local_agent/pinned_bebe';sys.path.insert(0,str(E));B=Path(__file__).resolve().parent;D=json.loads((B/'DECLARATION.json').read_bytes())
from generic_chess.native import semantic_engine as eng,semantic as sem
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
cls=Freeze().visit(cls);ast.fix_missing_locations(cls);ns=dict(eng.__dict__);ns['_aux_deepcopy']=copy.deepcopy
spatial_source=(ROOT/'results/dev_aux/task063/proposed_spatial_tuple.py').read_text();exec(compile(spatial_source,'<candidate row helper>','exec'),ns)
original_bind=next(x for x in cls.body if isinstance(x,ast.FunctionDef) and x.name=='bind_evaluator');exec(compile(ast.Module(body=[copy.deepcopy(original_bind)],type_ignores=[]),'<staged original with payload copy>','exec'),ns);ns['_original_bind']=ns['bind_evaluator']
wrapper=ast.parse((ROOT/'results/dev_aux/task064/proposed_bind_evaluator.py').read_text()).body[0];cls.body=[wrapper if x is original_bind else x for x in cls.body];exec(compile(ast.Module(body=[cls],type_ignores=[]),'<combined auxiliary class>','exec'),ns);Candidate=ns['SemanticSearchEngine']
source="from copy import deepcopy as _aux_deepcopy\nfrom generic_chess.native import semantic_engine as _base\nglobals().update({k:v for k,v in vars(_base).items() if not k.startswith('__')})\n\n"+spatial_source+'\n'+ast.unparse(original_bind).replace('def bind_evaluator(','def _original_bind(',1)+'\n\n'+ast.unparse(cls)+'\n';(B/'proposed_native_binding.py').write_text(source,encoding='utf-8')
one_source=(ROOT/'results/dev_aux/task063/proposed_one_shot.py').read_text();sns=dict(sem.__dict__);exec(compile(one_source,'<combined one-shot candidate>','exec'),sns)
for target in D['tests']:
 path=target.split('::')[0];frozen=subprocess.check_output(['git','show',D['source_pin']+':'+path]);assert Path(path).read_bytes().replace(b'\r\n',b'\n')==frozen.replace(b'\r\n',b'\n'),path
oldclass,oldalias,oldrun=eng.SemanticSearchEngine,eng.NativeSemanticSearchEngine,sem.semantic_iterative_search
eng.SemanticSearchEngine=eng.NativeSemanticSearchEngine=Candidate;sem.semantic_iterative_search=sns['semantic_iterative_search']
try:
 import pytest
 exit_code=pytest.main(['-q','--basetemp='+str(ROOT/'.local_agent/candidate-binding-pytest'),*D['tests']])
finally:eng.SemanticSearchEngine=oldclass;eng.NativeSemanticSearchEngine=oldalias;sem.semantic_iterative_search=oldrun
out={'complete':exit_code==0,'pytest_exit_code':exit_code,'declaration':D,'combined_candidate_sha256':hashlib.sha256(source.encode()).hexdigest(),'original_namespace_restored':True,'scope':'Existing four binding/compact regressions on private combined candidate;not full suite, allocator/thread fault or ordering/policy equivalence acceptance.'};(B/'validation.json').write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8');raise SystemExit(exit_code)
