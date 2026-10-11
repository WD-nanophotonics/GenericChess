"""Finite private rank-merge equivalence, unchanged guards and poll order."""
import ast,collections,copy,hashlib,heapq,inspect,json,sys,time,textwrap
from dataclasses import replace
from pathlib import Path
B=Path(__file__).parent;ROOT=B.resolve().parents[2];sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from generic_chess import build_builtin_ruleset,compile_ruleset_for_execution
from generic_chess.core.semantic_executor import SemanticEngine as S
from generic_chess.rules.ir import _incoming_attack_sources
from generic_chess.session.session import GameSession
from scripts.reserve_refresh_diagnostic import stopped
import generic_chess.core.semantic_executor as m
original=S.is_square_attacked;make_original=S._make_binding
tree=ast.parse(textwrap.dedent(inspect.getsource(original)))
class Merge(ast.NodeTransformer):
 def visit_Assign(self,n):
  if len(n.targets)==1 and isinstance(n.targets[0],ast.Name) and n.targets[0].id=='selected':
   n.targets[0].id='groups';return n
  if len(n.targets)==1 and isinstance(n.targets[0],ast.Name) and n.targets[0].id=='rows' and isinstance(n.value,ast.GeneratorExp):
   assert ast.unparse(n.value)=='(row for rank, row in selected)'
   n.value=ast.parse('(row for rank, row in heapq.merge(*groups))',mode='eval').body;return n
  return self.generic_visit(n)
 def visit_Expr(self,n):
  if isinstance(n.value,ast.Call) and isinstance(n.value.func,ast.Attribute) and isinstance(n.value.func.value,ast.Name) and n.value.func.value.id=='selected':
   if n.value.func.attr=='extend':n.value.func.value.id='groups';n.value.func.attr='append';return n
   if n.value.func.attr=='sort':return None
  return self.generic_visit(n)
tree=ast.fix_missing_locations(Merge().visit(tree));candidate_source=ast.unparse(tree)+'\n'
ns=dict(vars(m));ns['heapq']=heapq;exec(compile(tree,'<private rank-merge only>','exec'),ns);candidate=ns['is_square_attacked']
(B/'candidate_function.py').write_text(candidate_source,encoding='utf-8')
rows=[];fault_rows=[];started=time.monotonic();trace=None
def make(self,*args,**kwargs):
 pattern,gid,tid,piece,source,target,promotion,path,position=args
 if trace is not None:trace.append(('binding',pattern.pattern_id,gid,tid,source,target,promotion,tuple(path)))
 return make_original(self,*args,**kwargs)
def observe(fn,engine,pos,target,owner,stop=None):
 global trace
 trace=[];seen=0;fault=InterruptedError('one exact rank-merge callback');raised=False
 def checkpoint():
  nonlocal seen
  seen+=1;trace.append(('checkpoint',seen))
  if seen==stop:raise fault
 try:result=fn(engine,pos,target,owner,checkpoint=checkpoint)
 except InterruptedError as exc:
  assert exc is fault;raised=True;result=None
 value=list(trace);trace=None
 return result,seen,value,raised
try:
 S._make_binding=make
 for game in ('western_chess','standard_shogi'):
  stopped();assert time.monotonic()-started<120
  c=compile_ruleset_for_execution(build_builtin_ruleset(game));engine=S(c);root=GameSession(c).state.position
  a,b=next(iter(engine.iter_legal_action_bindings(root)));child=engine._transition(root,a,b)
  # Every compiled grouping is globally ranked and internally ordered.
  structural=0
  for key,groups in c._incoming_attack_sources.items():
   flattened=[]
   for typed in groups.values():
    for entries in typed.values():
     ranks=[rank for rank,row in entries];assert ranks==sorted(ranks) and len(set(ranks))==len(ranks)
     flattened.extend(entries)
   assert sorted(rank for rank,row in flattened)==list(range(len(c._incoming_attack_paths[key])))
   merged=list(heapq.merge(*(entries for typed in groups.values() for entries in typed.values())))
   assert merged==sorted(flattened,key=lambda x:x[0]);structural+=1
  for phase,pos in (('initial',root),('first_legal_child',child)):
   before=repr(pos)
   for owner in (0,1):
    for target in range(len(pos.board)):
     old=observe(original,engine,pos,target,owner);new=observe(candidate,engine,pos,target,owner)
     assert old==new and not old[3] and repr(pos)==before
     digest=hashlib.sha256(repr(old[2]).encode()).hexdigest()
     rows.append({'game':game,'phase':phase,'owner':owner,'target':target,'result':old[0],'callbacks':old[1],'binding_events':sum(x[0]=='binding' for x in old[2]),'exact_trace_sha256':digest,'source_groups_verified':structural})
   # Every callback prefix on four predeclared targets per owner, initial only.
   if phase=='initial':
    for owner in (0,1):
     for target in (0,len(pos.board)//3,2*len(pos.board)//3,len(pos.board)-1):
      full=observe(original,engine,pos,target,owner)
      for stop in range(1,full[1]+1):
       old=observe(original,engine,pos,target,owner,stop);new=observe(candidate,engine,pos,target,owner,stop)
       assert old==new and old[3] and old[1]==stop and repr(pos)==before
      fault_rows.append({'game':game,'owner':owner,'target':target,'all_callback_prefixes':full[1],'exact_fault_arms':2*full[1],'original_exception_identity_preserved':True,'full_parent_unchanged':True})
  key,entries=next((key,v) for key,v in c._incoming_attack_paths.items() if len(v)>2)
  duplicated=entries+(entries[0],);groups=_incoming_attack_sources({key:duplicated})[key]
  result=list(heapq.merge(*(entries for typed in groups.values() for entries in typed.values())))
  assert tuple(row for rank,row in result)==duplicated and tuple(rank for rank,row in result)==tuple(range(len(duplicated)))
finally:S._make_binding=make_original
out={'complete':True,'baseline_executor_sha256':hashlib.sha256(inspect.getsource(original).encode()).hexdigest(),
 'candidate_function_sha256':hashlib.sha256(candidate_source.encode()).hexdigest(),
 'scope':'580query pairs:2builtin initial/one actual legal child all owners/targets;16selected cancellation target cases all prefixes; structural duplicates retained; no timing',
 'rows':rows,'fault_rows':fault_rows,'decision':'Finite result and exact binding/checkpoint traces agree. Private candidate only; no caller cost gain, frozen generated-domain scope or deployment acceptance.',
 'limits':'Compiled rank order and mapping convention assumed; no adversarial metadata mutation, no concurrency or memory-failure equivalence.120sec internal between-case guard is not external timeout.'}
(B/'rank_merge.json').write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8')
print('query pairs',len(rows),'all exact trace; fault target cases',len(fault_rows),'fault arms',sum(r['exact_fault_arms'] for r in fault_rows))
