"""Scoped AST-copy feasibility; original wrapper and product remain unchanged."""
import ast,json,hashlib,subprocess,sys
from pathlib import Path
sys.path[:0]=[str(Path.cwd()),str(Path.cwd()/'tests/product')]
from test_h50b2a_semantic_native_search import _initial
from generic_chess.native import semantic as sem
B=Path(__file__).parent;d=json.loads((B/'DECLARATION.json').read_bytes());decl=json.loads((B/'repair-declaration.json').read_bytes());raw=subprocess.check_output(['git','show',d['source_pin']+':generic_chess/native/semantic.py']);tree=ast.parse(raw);node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='semantic_iterative_search')
class Fix(ast.NodeTransformer):
 def __init__(self):self.count=0
 def visit_Compare(self,n):
  if ast.unparse(n)=='len(spatial_occupancy_values) != len(expected) * 9':n.comparators[0]=ast.parse('2 * len(expected) * 9',mode='eval').body;self.count+=1
  return self.generic_visit(n)
 def visit_Constant(self,n):
  if n.value=='semantic spatial evaluator profile length must match type_count * 9':n.value='semantic spatial evaluator profile length must match 2 * type_count * 9'
  return n
f=Fix();node=f.visit(node);assert f.count==1;ast.fix_missing_locations(node);source=(ast.unparse(node)+'\n').encode();(B/'proposed_wrapper.py').write_bytes(source);ns=dict(sem.__dict__);exec(compile(ast.Module(body=[node],type_ignores=[]),'<auxiliary length correction>','exec'),ns);run=ns['semantic_iterative_search'];original=sem.semantic_iterative_search
c,n,pos=_initial();before=sem.snapshot(n,pos);full=(0,)*(2*len(n.type_ids)*9);half=full[:len(full)//2];mapping={f'{owner}:{t}':(0,)*9 for owner in (0,1) for t in n.type_ids};rows=[]
for name,v in [('absent',None),('full_mapping',mapping),('full_sequence',full),('half_sequence',half)]:
 try:
  r=run(n,pos,0,max_nodes=1,max_time_seconds=.1,tt_megabytes=0,spatial_occupancy_values=v);row={'case':name,'accepted':True,'depth':r['completed_depth'],'qnodes':r['qnodes'],'score':r['score'],'hash':r['evaluator_config_hash']}
 except Exception as e:row={'case':name,'accepted':False,'error':type(e).__name__,'message':str(e)}
 assert sem.snapshot(n,pos)==before;rows.append(row)
assert all(x['accepted'] for x in rows[:3]) and not rows[3]['accepted'];assert all(x['depth']==x['qnodes']==0 for x in rows[:3]);assert sem.semantic_iterative_search is original
out={'complete':True,'declaration':decl,'original_source_sha256':hashlib.sha256(raw).hexdigest(),'proposed_ast_sha256':hashlib.sha256(source).hexdigest(),'rows':rows,'root_native_snapshot_unchanged':True,'original_function_unchanged':True,'scope':decl['limits']};(B/'repair-result.json').write_bytes((json.dumps(out,indent=2)+'\n').encode());print(json.dumps(rows))
