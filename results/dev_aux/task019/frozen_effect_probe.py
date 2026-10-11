"""Private rule-mechanical effect specialization. Original refs/effects/checkpoints retained."""
import ast,copy,inspect,textwrap,time
import generic_chess.core.semantic_executor as m
baseline=m.SemanticEngine._transition
prepared_semantic=None
plans={}
metadata={}

class FoldKind(ast.NodeTransformer):
 def __init__(self,kind,effect_name='effect'):self.kind=kind;self.effect_name=effect_name
 def visit_If(self,node):
  node=self.generic_visit(node)
  test=node.test
  if isinstance(test,ast.Compare) and len(test.ops)==1:
   left=test.left
   known=isinstance(left,ast.Name) and left.id=='kind' or isinstance(left,ast.Attribute) and isinstance(left.value,ast.Name) and left.value.id==self.effect_name and left.attr=='kind'
   right=test.comparators[0]
   if known:
    value=ast.literal_eval(right)
    yes=self.kind==value if isinstance(test.ops[0],ast.Eq) else self.kind in value if isinstance(test.ops[0],ast.In) else None
    if yes is not None:return node.body if yes else node.orelse
  return node

class Unroll(ast.NodeTransformer):
 def __init__(self,pattern,env):self.pattern=pattern;self.env=env;self.bytes=0
 def visit_For(self,node):
  if ast.unparse(node.iter)!='pattern.effects':return self.generic_visit(node)
  result=[]
  for i,effect in enumerate(self.pattern.effects):
   ename='_bound_effect_'+str(i);self.env[ename]=effect
   fn=ast.parse(textwrap.dedent(inspect.getsource(m._apply_effect))).body[0]
   fn.name='_compiled_effect_'+str(i)
   fn=FoldKind(effect.kind).visit(fn)
   unit=ast.fix_missing_locations(ast.Module(body=[fn],type_ignores=[]))
   self.bytes+=len(ast.unparse(unit).encode());exec(compile(unit,'<private compiled semantic effect>','exec'),self.env)
   assign=ast.Assign(targets=[ast.Name(id='effect',ctx=ast.Store())],value=ast.Name(id=ename,ctx=ast.Load()))
   body=copy.deepcopy(node.body)
   class Rename(ast.NodeTransformer):
    def visit_Name(self,n):
     if n.id=='_apply_effect':n.id=fn.name
     return n
   body=[Rename().visit(n) for n in body]
   body=[FoldKind(effect.kind).visit(n) for n in body]
   result.append(assign)
   flat=[]
   for n in body:flat.extend(n if isinstance(n,list) else [n])
   for n in flat:
    if isinstance(n,ast.Continue):break
    result.append(n)
  return result

def prepare(semantic):
 global prepared_semantic,plans,metadata
 start=time.perf_counter();local={};source_bytes=0
 for pattern in semantic.ir.patterns:
  env=dict(vars(m));tree=ast.parse(textwrap.dedent(inspect.getsource(baseline)))
  transform=Unroll(pattern,env);tree=transform.visit(tree);tree=ast.fix_missing_locations(tree)
  source_bytes+=transform.bytes+len(ast.unparse(tree).encode())
  exec(compile(tree,'<private compiled semantic transition>','exec'),env)
  local[pattern.pattern_id]=(pattern,env['_transition'])
 prepared_semantic=semantic;plans=local
 metadata=dict(patterns=len(local),generated_source_bytes=source_bytes,prepare_seconds=time.perf_counter()-start)
 return dict(metadata)

def candidate(self,position,action,binding,checkpoint=None):
 entry=plans.get(binding.pattern.pattern_id) if self.semantic is prepared_semantic else None
 if entry is not None and binding.pattern is entry[0]:
  return entry[1](self,position,action,binding,checkpoint=checkpoint)
 return baseline(self,position,action,binding,checkpoint=checkpoint)

def install(active):m.SemanticEngine._transition=candidate if active else baseline
