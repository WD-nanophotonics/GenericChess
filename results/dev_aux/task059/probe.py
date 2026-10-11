"""Five predeclared evaluator API calls; no timed cohort or product mutation."""
import ast,hashlib,json,subprocess,sys
from pathlib import Path
sys.path[:0]=[str(Path.cwd()),str(Path.cwd()/'tests/product')]
from test_h50b2a_semantic_native_search import _initial
from generic_chess.native import semantic as sem
from generic_chess.native.semantic_engine import SemanticSearchEngine
B=Path(__file__).parent;D=json.loads((B/'DECLARATION.json').read_bytes());R=D['source_pin']
sources={}
for p in ['generic_chess/native/semantic.py','generic_chess/native/semantic_engine.py','generic_chess/_native/native_module.c','tests/product/test_h50b2a_semantic_native_search.py','generic_chess/learning/material.py']:
 raw=subprocess.check_output(['git','show',R+':'+p]);own=Path(p).read_bytes();assert own.replace(b'\r\n',b'\n')==raw.replace(b'\r\n',b'\n'),p;sources[p]={'git_sha256':hashlib.sha256(raw).hexdigest(),'checkout_sha256':hashlib.sha256(own).hexdigest()}
c,n,pos=_initial();full=(0,)*(2*len(n.type_ids)*9);half=(0,)*(len(n.type_ids)*9);mapping={f'{owner}:{t}':(0,)*9 for owner in (0,1) for t in n.type_ids}
binary=next(Path('generic_chess').rglob('_native_core.cp312-win_amd64.pyd'));before=sem.snapshot(n,pos)
out={'complete':False,'declaration':D,'sources':sources,'binary_sha256':hashlib.sha256(binary.read_bytes()).hexdigest(),'type_ids':list(n.type_ids),'full_length':len(full),'half_length':len(half),'rows':[]}
for name,values in [(D['cases'][0],None),(D['cases'][1],mapping),(D['cases'][2],full),(D['cases'][3],half)]:
 try:
  r=sem.semantic_iterative_search(n,pos,0,max_nodes=1,max_time_seconds=.1,spatial_occupancy_values=values,tt_megabytes=0);row={'case':name,'accepted':True,'completed_depth':r['completed_depth'],'qnodes':r['qnodes'],'evaluator_config_hash':r['evaluator_config_hash']}
 except Exception as e:row={'case':name,'accepted':False,'error_type':type(e).__name__,'message':str(e)}
 assert sem.snapshot(n,pos)==before;row['root_snapshot_restored']=True;out['rows'].append(row)
e=SemanticSearchEngine(c,n,spatial_occupancy_values=full,tt_megabytes=0);v=e.native_evaluator_values;assert v['spatial_occupancy']==full
out['rows'].append({'case':D['cases'][4],'accepted':True,'exact_bound_values':v,'checkpoint_id':e.checkpoint_id,'scope':'Constructor acceptance and getter only; no persistent search.'})
assert out['rows'][0]['accepted'] and out['rows'][4]['accepted']
for row in out['rows'][1:4]:assert not row['accepted'] and row['error_type']=='ValueError'
assert all('type_count * 9' in row['message'] for row in out['rows'][1:4]);assert '2 * type_count * 9' in out['rows'][3]['message']
out['complete']=True;B.joinpath('result.json').write_bytes((json.dumps(out,indent=2)+'\n').encode());print(json.dumps(out['rows']))
