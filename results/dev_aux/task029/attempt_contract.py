"""Exact frozen observer functions on three tiny single-transition controls."""
import ast,collections,json,sys,time
from pathlib import Path
B=Path(__file__).parent
fixture_tree=ast.parse((B.parent/'task023/same_kind_operands.py').read_text(encoding='utf-8'));prefix=[]
for n in fixture_tree.body:
 if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='out' for t in n.targets):break
 prefix.append(n)
e={'__file__':str(B.parent/'task023/same_kind_operands.py')}
exec(compile(ast.Module(body=prefix,type_ignores=[]),'<public fixture only>','exec'),e)
f=e['env'];c=e['compiled'];m=f['p'].m
engine=f['semantic_engine_for'](c);pos=f['GameSession'](c).state.position
a,b=next((a,b) for a,b in engine.iter_legal_action_bindings(pos) if b.pattern.name=='same_kind_first')
producer=ast.parse((B.parent/'task027/physical_profile.py').read_text(encoding='utf-8'))
functions=[n for n in producer.body if isinstance(n,ast.FunctionDef) and n.name in ('consumer','trial','transition','init','freeze')]
assert {n.name for n in functions}=={'consumer','trial','transition','init','freeze'}
original={'transition':m.SemanticEngine._transition,'trial':m.SemanticEngine._trial_child_if_s3_legal,'init':m._WorkingPosition.__init__,'freeze':m._WorkingPosition.to_position}
out={'complete':False,'scope':'three actual one-trial controls, frozen primary observer functions; targeted callback fault in saved init/freeze seam, no caller cost run','rows':[]}
for case in ('normal','init_fails_before_copy','freeze_fails_before_publication'):
 f['stopped']();fault=MemoryError('one observer attempt control');hits=[]
 env={'sys':sys,'time':time,'saved':dict(original),'stage':'finite-control',
 'stack':[],'rows':collections.defaultdict(collections.Counter),'counts':collections.Counter(),'orphan':collections.Counter()}
 if case!='normal':
  def fail(*args,**kw):
   hits.append(case);raise fault
  env['saved']['init' if case.startswith('init') else 'freeze']=fail
 exec(compile(ast.Module(body=functions,type_ignores=[]),'<exact primary method observers>','exec'),env)
 before=repr(pos);child=None;raised=None
 try:
  m.SemanticEngine._transition=env['transition'];m.SemanticEngine._trial_child_if_s3_legal=env['trial']
  m._WorkingPosition.__init__=env['init'];m._WorkingPosition.to_position=env['freeze']
  try:child=engine._trial_child_if_s3_legal(b.pattern,pos,a,b)
  except MemoryError as exc:
   assert exc is fault;raised=type(exc).__name__
 finally:
  m.SemanticEngine._transition=original['transition'];m.SemanticEngine._trial_child_if_s3_legal=original['trial']
  m._WorkingPosition.__init__=original['init'];m._WorkingPosition.to_position=original['freeze']
 assert repr(pos)==before and not env['stack']
 assert (child is not None)==(case=='normal')
 assert hits==([] if case=='normal' else [case])
 counts=dict(env['counts'])
 assert counts['transitions']==counts['copies']==1
 assert counts.get('freezes',0)==(0 if case.startswith('init') else 1)
 rows={k:{n:v for n,v in value.items() if n not in ('copy','freeze','trans')} for k,value in env['rows'].items()}
 out['rows'].append({'case':case,'actual_fault_hits':len(hits),'returned_child':child is not None,
 'original_exception_preserved':raised=='MemoryError' if raised else None,'attempt_counts':counts,
 'trial_outcome_rows':rows,'parent_full_repr_unchanged':True})
out['complete']=True
out['decision']='finally counters measure entered method attempts: normal and failed freeze both count1copy/1freeze/1transition despite no returned child on failure. In primary completed record this does not prove a failed attempt occurred; preserve per-outcome success distinction.'
(B/'attempt_contract.json').write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8')
print(json.dumps(out,indent=2))
