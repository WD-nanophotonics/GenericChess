"""Actual mapping boundary probes; original product functions remain unchanged."""
import ast,hashlib,json,sys,time
from pathlib import Path
ROOT=Path.cwd();E=ROOT/'.local_agent/pinned_bebe';sys.path.insert(0,str(E));B=Path(__file__).resolve().parent;D=json.loads((B/'DECLARATION.json').read_bytes())
from native_initial_fixture import _initial
from generic_chess.native import semantic as sem
from generic_chess.native import semantic_engine as eng
c,n,pos=_initial();before=sem.snapshot(n,pos);type_ids=tuple(n.type_ids);keys=[f'{owner}:{t}' for owner in (0,1) for t in type_ids]
valid={k:(0,)*9 for k in keys};valid[keys[0]]=(1,0,0,0,0,0,0,0,-1);valid[keys[1]]=(2,0,0,0,0,0,0,0,-2)
long=dict(valid);long[keys[0]]=valid[keys[0]]+valid[keys[1]];long[keys[1]]=()
short=dict(valid);short[keys[0]]=(0,)*8;short[keys[1]]=(0,)+valid[keys[1]]
cases=[('valid_all_rows9',valid),('compensating_first18_second0',long),('compensating_first8_second10',short)]
raw=(E/'generic_chess/native/semantic.py').read_bytes();node=next(n for n in ast.parse(raw).body if isinstance(n,ast.FunctionDef) and n.name=='semantic_iterative_search')
class TotalFix(ast.NodeTransformer):
 def visit_Compare(self,n):
  if ast.unparse(n)=='len(spatial_occupancy_values) != len(expected) * 9':n.comparators[0]=ast.parse('2 * len(expected) * 9',mode='eval').body
  return self.generic_visit(n)
 def visit_Constant(self,n):
  if n.value=='semantic spatial evaluator profile length must match type_count * 9':n.value='semantic spatial evaluator profile length must match 2 * type_count * 9'
  return n
node=TotalFix().visit(node);ast.fix_missing_locations(node);ns=dict(sem.__dict__);exec(compile(ast.Module(body=[node],type_ignores=[]),'<prior total-length candidate>','exec'),ns);run=ns['semantic_iterative_search'];original=sem.semantic_iterative_search

native_rules=n
old_spatial=eng._spatial_tuple
spatial_raw=(E/'generic_chess/native/semantic_engine.py').read_text()
spatial_node=next(n for n in ast.parse(spatial_raw).body if isinstance(n,ast.FunctionDef) and n.name=='_spatial_tuple')
for n in ast.walk(spatial_node):
 if isinstance(n,ast.If) and ast.unparse(n.test)=='isinstance(values, Mapping)':
  ri=next(i for i,v in enumerate(n.body) if isinstance(v,ast.Assign) and isinstance(v.targets[0],ast.Name) and v.targets[0].id=='rows')
  n.body[ri:ri+2]=ast.parse("rows = [tuple(int(v) for v in values[f'{owner}:{type_id}']) for owner in (0,1) for type_id in type_ids]\nif any(len(row) != SPATIAL_CELL_COUNT for row in rows): raise ValueError('each spatial owner/type mapping row must contain nine values')\nresult = tuple(value for row in rows for value in row)").body
ast.fix_missing_locations(spatial_node);ens=dict(eng.__dict__);exec(compile(ast.Module(body=[spatial_node],type_ignores=[]),'<auxiliary spatial row candidate>','exec'),ens)
class_node=next(n for n in ast.parse(spatial_raw).body if isinstance(n,ast.ClassDef) and n.name=='SemanticSearchEngine');exec(compile(ast.Module(body=[class_node],type_ignores=[]),'<private constructor with row validator>','exec'),ens);candidate=ens['SemanticSearchEngine']
for n in ast.walk(node):
 if isinstance(n,ast.If) and ast.unparse(n.test)=='isinstance(spatial_occupancy_values, Mapping)':
  ai=next(i for i,v in enumerate(n.body) if isinstance(v,ast.Assign) and isinstance(v.targets[0],ast.Name) and v.targets[0].id=='spatial_occupancy_values')
  n.body[ai:ai+1]=ast.parse("spatial_rows = tuple(tuple(int(v) for v in spatial_occupancy_values[f'{owner}:{type_id}']) for owner in (0,1) for type_id in expected)\nif any(len(row) != 9 for row in spatial_rows): raise ValueError('each spatial owner/type mapping row must contain nine values')\nspatial_occupancy_values = tuple(value for row in spatial_rows for value in row)").body
ast.fix_missing_locations(node);sns=dict(sem.__dict__);exec(compile(ast.Module(body=[node],type_ignores=[]),'<auxiliary one-shot total and row candidate>','exec'),sns);run=sns['semantic_iterative_search']
(B/'proposed_spatial_tuple.py').write_text(ast.unparse(spatial_node)+'\n',encoding='utf-8');(B/'proposed_one_shot.py').write_text(ast.unparse(node)+'\n',encoding='utf-8')
n=native_rules
out={'complete':False,'source_pin':D['source_pin'],'scope':'Private AST-copy mapping-row correction plus previous total-length correction. Constructor/one-shotD0 entry only; scale/hash/feature/strength scope unchanged. Flat sequence interface unchanged.','rows':[]}
for name,mapping in cases:
 for route in D['routes']:
  try:
   if route=='persistent_constructor':
    instance=candidate(c,n,spatial_occupancy_values=mapping,tt_megabytes=0);flat=instance.native_evaluator_values['spatial_occupancy'];result={'bound_flat_spatial':flat}
   else:
    r=run(n,pos,0,max_nodes=1,max_time_seconds=.1,tt_megabytes=0,spatial_occupancy_values=mapping);result={'depth':r['completed_depth'],'qnodes':r['qnodes'],'score':r['score']}
   accepted=True;error=None
  except Exception as e:accepted=False;result=None;error={'type':type(e).__name__,'message':str(e)}
  assert sem.snapshot(n,pos)==before
  assert accepted==(name=='valid_all_rows9')
  if not accepted:assert error['type']=='ValueError' and 'row must contain nine' in error['message']
  out['rows'].append(dict(case=name,route=route,accepted=accepted,error=error,result=result,root_restored=True))
assert sem.semantic_iterative_search is original and eng._spatial_tuple is old_spatial
out['complete']=True;out['original_product_functions_unchanged']=True;(B/'repair_result.json').write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8');print(json.dumps(out['rows']))
