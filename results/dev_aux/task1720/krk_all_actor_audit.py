"""Every KRK table slot and ALL valid actor-model move frontiers, independent."""
import sys
from pathlib import Path
sys.path=[p for p in sys.path if Path(p).resolve()!=Path(__file__).resolve().parent]
import json,ast,importlib.util,time,hashlib,collections
R=Path.cwd();O=R/'results/dev_aux/task1749';O.mkdir(exist_ok=False);start=time.perf_counter();deadline=time.monotonic()+300;results=[];error=None
sp=importlib.util.spec_from_file_location('STOP',R/'results/dev_aux/task166/run.py');STOP=importlib.util.module_from_spec(sp);sp.loader.exec_module(STOP)
tree=ast.parse((R/'results/dev_aux/task1720/krk_table.py').read_text(encoding='utf-8-sig'));defs={n.name:n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef)}
for W,model,qual in [(4,'results/dev_aux/task1675/rules.py','results/dev_aux/task1675/qualify_literal.py'),(8,'results/dev_aux/task1688/rules.py','results/dev_aux/task1688/qualify_literal_fixed.py')]:
 try:
  A=W*W;wdl=(R/f'results/dev_aux/task1741/wdl{W}.bin').read_bytes();proof=json.loads((R/f'results/dev_aux/task1741/proof{W}.json').read_bytes());assert hashlib.sha256(wdl).hexdigest()==proof['wdl_sha256']
  sp=importlib.util.spec_from_file_location('T',R/model);T=importlib.util.module_from_spec(sp);sp.loader.exec_module(T)
  tr=ast.parse((R/qual).read_text(encoding='utf-8-sig'));fn=next(x for x in tr.body if isinstance(x,ast.FunctionDef) and x.name=='ref');ns={};exec(compile(ast.Module(body=[fn],type_ignores=[]),'independent_actor','exec'),ns);ref=ns['ref']
  kn={z:[x+W*y for x in range(max(0,z%W-1),min(W,z%W+2)) for y in range(max(0,z//W-1),min(W,z//W+2)) if x+W*y!=z] for z in range(A)};fast={'W':W,'A':A,'kingneighbors':kn}
  exec(compile(ast.Module(body=[defs[n] for n in ('far','hit','valid','idx','decode','moves')],type_ignores=[]),'original_fast_rule','exec'),fast)
  cc=collections.Counter();h=hashlib.sha256()
  for i,v in enumerate(wdl):
   if i%1024==0:STOP.stop();assert time.monotonic()<deadline
   k,b,r,c=fast['decode'](i);s=['.']*A;s[k]='K';s[b]='k';s[r]='R';s=tuple(s+[c]);assert T.valid(s)==(v!=255);cc['all_slots_validity_checked']+=1
   if v==255:continue
   expected={chr(97+a%W)+str(1+a//W)+chr(97+z%W)+str(1+z//W):j for a,z,j in fast['moves'](k,b,r,c)};actual={}
   for u,t in ref(s):
    actual[u]=-1 if 'R' not in t else fast['idx'](t[:-1].index('K'),t[:-1].index('k'),t[:-1].index('R'),t[-1])
   assert actual==expected,(W,i,s,actual,expected)
   cc['all_valid_frontiers_checked']+=1;cc['all_legal_children_checked']+=len(actual)
   h.update(i.to_bytes(4,'little'))
   for u,j in sorted(actual.items()):h.update(u.encode());h.update(j.to_bytes(4,'little',signed=True))
  assert cc['all_valid_frontiers_checked']==proof['counts']['valid'] and cc['all_legal_children_checked']==proof['counts']['edges']
  result=dict(width=W,status='PASS_EVERY_SLOT_VALIDITY_AND_ALL_ACTOR_FRONTIERS',counts=dict(cc),frontier_sha256=h.hexdigest());results.append(result);print(result,flush=True)
 except BaseException as ex:error=type(ex).__name__+':'+str(ex);break
out=dict(status='PASS_EXHAUSTIVE_INDEPENDENT_KRK_RULE_EQUIVALENCE' if error is None else 'PARTIAL_PRESERVED',error=error,results=results,seconds=time.perf_counter()-start,actual_native_go=0,scope='Every4/8idvalidity vsfullmodel; allvalidKRKfrontiers vsindependentactor model, completewhiteRbothturns. BlackRcolorbijection+actualNative160perft separate1746. No WDLlabels substituted forplayedoutcomes.')
(O/'result.json').write_text(json.dumps(out,indent=2));print(out)

