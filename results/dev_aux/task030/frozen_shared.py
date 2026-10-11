"""Private mechanical shared-code premise. Actual effect operands remain pattern-owned."""
import ast,copy,inspect,textwrap,time,importlib.util
from pathlib import Path
s=importlib.util.spec_from_file_location('first_effect_probe',Path(__file__).with_name('compiled_effect_probe.py'));d=importlib.util.module_from_spec(s);s.loader.exec_module(d)
m=d.m;baseline=d.baseline;prepared_semantic=None;plans={};metadata={}
class Unroll(ast.NodeTransformer):
 def __init__(self,kinds,helper_names):self.kinds=kinds;self.helper_names=helper_names
 def visit_For(self,node):
  if ast.unparse(node.iter)!='pattern.effects':return self.generic_visit(node)
  result=[]
  for i,kind in enumerate(self.kinds):
   result.append(ast.Assign(targets=[ast.Name(id='effect',ctx=ast.Store())],value=ast.Subscript(value=ast.Attribute(value=ast.Name(id='pattern',ctx=ast.Load()),attr='effects',ctx=ast.Load()),slice=ast.Constant(i),ctx=ast.Load())))
   body=copy.deepcopy(node.body);name=self.helper_names[kind]
   class Rename(ast.NodeTransformer):
    def visit_Name(self,n):
     if n.id=='_apply_effect':n.id=name
     return n
   flat=[]
   for n in body:
    n=d.FoldKind(kind).visit(Rename().visit(n));flat.extend(n if isinstance(n,list) else [n])
   for n in flat:
    if isinstance(n,ast.Continue):break
    result.append(n)
  return result

def prepare(semantic):
 global prepared_semantic,plans,metadata
 start=time.perf_counter();env=dict(vars(m));helper_names={};source_bytes=0;templates={};local={}
 all_kinds=sorted({e.kind for p in semantic.ir.patterns for e in p.effects})
 for i,kind in enumerate(all_kinds):
  name='_shared_effect_'+str(i);helper_names[kind]=name
  fn=ast.parse(textwrap.dedent(inspect.getsource(m._apply_effect))).body[0];fn.name=name;fn=d.FoldKind(kind).visit(fn)
  tree=ast.fix_missing_locations(ast.Module(body=[fn],type_ignores=[]));source_bytes+=len(ast.unparse(tree).encode());exec(compile(tree,'<private compiled shared effect>','exec'),env)
 for pattern in semantic.ir.patterns:
  kinds=tuple(e.kind for e in pattern.effects)
  if kinds not in templates:
   tree=ast.parse(textwrap.dedent(inspect.getsource(baseline)));tree=ast.fix_missing_locations(Unroll(kinds,helper_names).visit(tree));source_bytes+=len(ast.unparse(tree).encode());exec(compile(tree,'<private compiled shared transition>','exec'),env);templates[kinds]=env['_transition']
  local[pattern.pattern_id]=(pattern,templates[kinds])
 prepared_semantic=semantic;plans=local
 metadata=dict(patterns=len(local),templates=len(templates),effect_helpers=len(helper_names),generated_source_bytes=source_bytes,prepare_seconds=time.perf_counter()-start)
 return dict(metadata)
def candidate(self,position,action,binding,checkpoint=None):
 entry=plans.get(binding.pattern.pattern_id) if self.semantic is prepared_semantic else None
 if entry is not None and binding.pattern is entry[0]:return entry[1](self,position,action,binding,checkpoint=checkpoint)
 return baseline(self,position,action,binding,checkpoint=checkpoint)
def install(active):m.SemanticEngine._transition=candidate if active else baseline
