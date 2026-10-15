"""Complete D3 ordinal scale bridge, no Native queries."""
import sys
from pathlib import Path
sys.path=[p for p in sys.path if Path(p).resolve()!=Path(__file__).resolve().parent]
import json,importlib.util,functools,time,collections,ast
R=Path.cwd();O=R/'results/dev_aux/task1733';O.mkdir(exist_ok=False);plan=json.loads((R/'results/dev_aux/task1732/plan.json').read_bytes());start=time.perf_counter();deadline=time.monotonic()+600;expanded=0
sp=importlib.util.spec_from_file_location('T',R/plan['model']);T=importlib.util.module_from_spec(sp);sp.loader.exec_module(T)
sp=importlib.util.spec_from_file_location('STOP',R/'results/dev_aux/task166/run.py');STOP=importlib.util.module_from_spec(sp);sp.loader.exec_module(STOP)
tree=ast.parse((R/'results/dev_aux/task1688/qualify_literal_fixed.py').read_text(encoding='utf-8-sig'));fn=next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name=='ref');fn.body[-1]=ast.Return(value=ast.Tuple(elts=[fn.body[-1].value,ast.Call(func=ast.Name(id='check',ctx=ast.Load()),args=[ast.Name(id='d',ctx=ast.Load()),ast.Name(id='c',ctx=ast.Load())],keywords=[])],ctx=ast.Load()));ast.fix_missing_locations(fn);ns={};exec(compile(ast.Module(body=[fn],type_ignores=[]),'actor_reference','exec'),ns);ref=functools.lru_cache(maxsize=60000)(ns['ref'])
@functools.lru_cache(maxsize=100000)
def full(s,depth,price,root,ply):
 global expanded
 expanded+=1
 if expanded%2048==0:STOP.stop();assert time.monotonic()<deadline and expanded<=4000000
 ll,ch=ref(s)
 if not ll:return (-32000+ply if s[-1]==root else 32000-ply) if ch else 0
 if depth==0:
  w=dict(zip('RNBP',price));value=sum((1 if p.isupper() else -1)*w.get(p.upper(),0) for p in s[:-1] if p!='.')
  return value if root==0 else -value
 vals=[full(t,depth-1,price,root,ply+1) for u,t in ll]
 return (max if s[-1]==root else min)(vals)
records=[];error=None
try:
 for f in plan['families']:
  for color,root in enumerate(f['roots']):
   s=tuple(root);ll,ch=ref(s);assert ll==T.moves(s)
   for hi,low in plan['scale_pairs']:
    hi=tuple(hi);low=tuple(low);a={u:full(t,2,hi,s[-1],1) for u,t in ll};b={u:full(t,2,low,s[-1],1) for u,t in ll}
    # Mate priority unscaled; every nonmate leaf max 3actors*1728 below31000.
    assert all((a[u]==b[u] if abs(a[u])>31000 else a[u]==2*b[u]) for u in a)
    ah=sorted(u for u,v in a.items() if v==max(a.values()));al=sorted(u for u,v in b.items() if v==max(b.values()));assert ah==al
    records.append(dict(family=f['family'],color=color,state=s,high=hi,low=low,high_action_values=a,low_action_values=b,best_actions=ah))
except BaseException as ex:error=type(ex).__name__+':'+str(ex)
(O/'records.json').write_text(json.dumps(records));out=dict(status='PASS_COMPLETE_D3_SCALE_ORDINAL_BRIDGE' if error is None else 'PARTIAL_PRESERVED',error=error,root_pairs=len(records),expanded=expanded,seconds=time.perf_counter()-start,actual_native_go=0,reference_cache=ref.cache_info()._asdict(),value_cache=full.cache_info()._asdict(),scope='All96exposedTRAINroots x2ratios, allD3rootactions explicitMAX/MIN independentactorlegal. Mateterminalbeforeleaf, 32000-ply outranks materialmax5184; halvingmaterial preservesallactionordering andbestsets. NotfullgameoptimalWDL/equalNativework/searchquality proof.')
(O/'result.json').write_text(json.dumps(out,indent=2));print(out)

