"""Static applicability checks; never imports an engine or executes generated code."""
import ast,hashlib,json,subprocess
from pathlib import Path
B=Path(__file__).parent;ROOT=B.parents[2]
PRIMARY=Path(r'C:\Users\wdai\Documents\ChatGPT\GenericChess 2')
module='generic_chess/core/semantic_executor.py'
own=(ROOT/module).read_bytes();primary=(PRIMARY/module).read_bytes()
left=ast.parse(own);right=ast.parse(primary)
getfn=lambda name:next(n for n in ast.walk(left) if isinstance(n,ast.FunctionDef) and n.name==name)
transition=getfn('_transition');helper=getfn('_apply_effect')
loops=[n for n in ast.walk(transition) if isinstance(n,ast.For) and ast.unparse(n.iter)=='pattern.effects']
assert len(loops)==1
loop=loops[0]
assert isinstance(loop.target,ast.Name) and loop.target.id=='effect' and not loop.orelse
assert len(loop.body)==3
assert ast.unparse(loop.body[0])=='_checkpoint(checkpoint)'
aux=loop.body[1];apply=loop.body[2]
assert isinstance(aux,ast.If) and not aux.orelse and isinstance(aux.body[-1],ast.Continue)
assert ast.unparse(aux.body[0])=='aux_effects.append(effect)' and len(aux.body)==2
assert isinstance(apply,ast.Expr) and isinstance(apply.value,ast.Call) and isinstance(apply.value.func,ast.Name) and apply.value.func.id=='_apply_effect'
assert not any(isinstance(n,(ast.Break,ast.Yield,ast.YieldFrom,ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef)) for n in ast.walk(loop))
assignments=[n for n in ast.walk(helper) if isinstance(n,ast.Name) and n.id=='kind' and isinstance(n.ctx,ast.Store)]
assert len(assignments)==1 and any(isinstance(n,ast.Assign) and ast.unparse(n)=='kind = effect.kind' for n in helper.body)
assert not any(isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef)) for n in list(ast.walk(helper))[1:])
folds=[]
for fn in (transition,helper):
 for n in ast.walk(fn):
  if not isinstance(n,ast.If) or not isinstance(n.test,ast.Compare):continue
  test=n.test;l=test.left
  known=isinstance(l,ast.Name) and l.id=='kind' or isinstance(l,ast.Attribute) and isinstance(l.value,ast.Name) and l.value.id=='effect' and l.attr=='kind'
  if not known:continue
  assert len(test.ops)==len(test.comparators)==1 and isinstance(test.ops[0],(ast.Eq,ast.In))
  literal=ast.literal_eval(test.comparators[0])
  assert isinstance(literal,str) or isinstance(literal,tuple) and all(isinstance(v,str) for v in literal)
  folds.append({'function':fn.name,'condition':ast.unparse(test),'literal':literal})
irraw=(ROOT/'generic_chess/rules/ir.py').read_bytes();ir=ast.parse(irraw)
for name in ('CompiledEffect','CompiledMovePattern'):
 cls=next(n for n in ir.body if isinstance(n,ast.ClassDef) and n.name==name)
 assert any(isinstance(d,ast.Call) and isinstance(d.func,ast.Name) and d.func.id=='dataclass' and any(k.arg=='frozen' and isinstance(k.value,ast.Constant) and k.value.value is True for k in d.keywords) for d in cls.decorator_list)
 if name=='CompiledMovePattern':
  field=next(n for n in cls.body if isinstance(n,ast.AnnAssign) and isinstance(n.target,ast.Name) and n.target.id=='effects')
  assert ast.unparse(field.annotation)=='tuple[CompiledEffect, ...]'
pinned=subprocess.check_output(['git','show','b4108a68a7ee06327be39cb3a222939644085a52:'+module],cwd=ROOT)
assert ast.dump(ast.parse(pinned),include_attributes=False)==ast.dump(left,include_attributes=False)
out={'complete':True,'source_sha256':hashlib.sha256(own).hexdigest(),'primary_working_source_sha256':hashlib.sha256(primary).hexdigest(),'primary_ast_same':ast.dump(left,include_attributes=False)==ast.dump(right,include_attributes=False),'own_baseline_ast_same':True,'ir_source_sha256':hashlib.sha256(irraw).hexdigest(),'effect_loop_body':[ast.unparse(n) for n in loop.body],'folded_literal_conditions':folds,'frozen_effect_and_pattern':True,'scope':'static shape prerequisites only; no engine execution, full compiler proof or live-hook compatibility','limitations':['A future original-loop for-else, dynamic kind expression or nested continue is outside the verified shape; the private transformer has no automatic shape admission guard.','Captured module globals bypass a later live _apply_effect hook; primary independently reports this negative.','One module-global prepared carrier preserves foreign fallback but offers no measured reuse or thread-safety evidence.','No rule-specific coordinate shortcuts or merging same kind sequences into equivalent rules follows.']}
(B/'static_applicability.json').write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8')
print(json.dumps(out,indent=2))
