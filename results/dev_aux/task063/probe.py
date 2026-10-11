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
out={'complete':False,'declaration':D,'type_ids':type_ids,'one_shot_total_candidate_sha256':hashlib.sha256((ast.unparse(node)+'\n').encode()).hexdigest(),'source_files':{p:hashlib.sha256((E/p).read_bytes()).hexdigest() for p in ['generic_chess/native/semantic.py','generic_chess/native/semantic_engine.py','generic_chess/learning/material.py']},'binary_sha256':hashlib.sha256((E/'generic_chess/_native_core.cp312-win_amd64.pyd').read_bytes()).hexdigest(),'rows':[]}
for name,mapping in cases:
 for route in D['routes']:
  try:
   if route=='persistent_constructor':
    instance=eng.SemanticSearchEngine(c,n,spatial_occupancy_values=mapping,tt_megabytes=0);flat=instance.native_evaluator_values['spatial_occupancy'];result={'bound_flat_spatial':flat,'checkpoint_id':instance.checkpoint_id}
   else:
    flat=None;r=run(n,pos,0,max_nodes=1,max_time_seconds=.1,tt_megabytes=0,spatial_occupancy_values=mapping);result={'depth':r['completed_depth'],'qnodes':r['qnodes'],'score':r['score'],'evaluator_config_hash':r['evaluator_config_hash']}
   accepted=True;error=None
  except Exception as e:accepted=False;result=None;error={'type':type(e).__name__,'message':str(e)}
  assert sem.snapshot(n,pos)==before
  out['rows'].append(dict(case=name,route=route,row_lengths={k:len(v) for k,v in mapping.items()},input_mapping=mapping,accepted=accepted,error=error,result=result,root_restored=True))
assert all(x['accepted'] for x in out['rows']);assert sem.semantic_iterative_search is original
out['complete']=True;(B/'result.json').write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8');print(json.dumps([{k:x[k] for k in ['case','route','accepted']} for x in out['rows']]))
