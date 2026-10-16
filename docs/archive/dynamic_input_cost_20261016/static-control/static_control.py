from pathlib import Path
import sys,sysconfig,subprocess,json,hashlib,time
R=Path.cwd();P=R/'.local_agent/dynamic-input-20261016';S=P/'static-baseline-source';S.mkdir(exist_ok=False)
# Exact published base C, not an active counter in the timing path.
for name in('native_module.c','native_semantic_runtime.h'):(S/name).write_bytes(subprocess.check_output(['git','show','HEAD:generic_chess/_native/'+name]))
cmd=[str(R/'.venv/Lib/site-packages/ziglang/zig.exe'),'cc','-target','x86_64-windows-gnu','-shared','-O2','-I'+sysconfig.get_path('include'),'-I'+str(S),'-I'+str(R/'generic_chess/_native'),'-L'+str(Path(sys.base_prefix)/'libs'),'-lpython312',*[str(S/f.name if f.name=='native_module.c'else f)for f in sorted((R/'generic_chess/_native').glob('*.c'))],'-o',str(P/'static_base_native_core.pyd')];r=subprocess.run(cmd,capture_output=True,timeout=120);assert r.returncode==0,r.stderr
sys.path[:0]=[str(P),str(R)];from component import *
import importlib.util
spec=importlib.util.spec_from_file_location('staticbase._native_core',P/'static_base_native_core.pyd');base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base);fresh=json.loads((P/'fresh-recovered-results.json').read_bytes());cases=[r for b in(4,8,12,16)for r in[r for r in fresh['rows']if r['kind']=='EXECUTED_ROOT'and r['board']==b][:2]]
plan=dict(question='Does reduced derived-feature work help DEFAULT static API caller cost too, or mainly activefeature evaluators?',cases=[dict(seed=r['seed'],board=r['board'],root=r['root'])for r in cases],arms=['published_base','final_product'],depth=3,nodes=4096,q=0,tt=0,seconds=None,repetitions=2,whole_seconds=90,expected_seconds=10,max_queries=32,source_base=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),base_module_sha256=hashlib.sha256((S/'native_module.c').read_bytes()).hexdigest(),scope='Latealreadyexposedroot scope, no game/fit/strength. Fullpublicresult/serialization charged in caller, kernel vs readytime distinct; balancedarms, noexclusivePCclaim. Outsideimmutable360querycapsule.')
write_record(P/'static-plan.json',plan);rows=[];start=time.perf_counter()
for case in cases:
 d=json.loads((P/case['root']).read_bytes());x=compile_legacy_ruleset_for_semantic_execution(deserialize_ruleset(json.dumps(d['ruleset'])));c=SearchMetadataAdapter(ir=x.ir,_legacy_compiled=x._legacy_compiled,support=x.support);s=GameSession.replay(c,deserialize_game_record(json.dumps(d['game_record'])));nrs=dict(published_base=compile_native_semantic_rules(c,backend_module=base),final_product=compile_native_semantic_rules(c));bv={t.type_id:0 if t.is_anchor else 100 for t in c.piece_types};before=record_value(s.state)
 for rep in range(2):
  pair=[]
  for arm in(['published_base','final_product']if rep==0 else['final_product','published_base']):
   stopped();assert time.perf_counter()-start<90;e=SemanticSearchEngine(c,nrs[arm],board_values=bv,hand_values=bv,tt_megabytes=0,ordering_cache_enabled=False);t=time.perf_counter();r=e.search(s,SearchLimits(max_depth=3,max_nodes=4096,max_time_seconds=None,quiescence_max_depth=0,quiescence_hard_max_depth=0),root_window_pruning=True);z=dict(seed=case['seed'],board=case['board'],arm=arm,rep=rep,result=record_value(r),caller_seconds=time.perf_counter()-t,root_restored=record_value(s.state)==before);assert z['root_restored'];rows.append(z);pair.append(z)
  assert{k:v for k,v in pair[0]['result'].items()if k!='elapsed_seconds'}=={k:v for k,v in pair[1]['result'].items()if k!='elapsed_seconds'}
write_record(P/'static-results.json',dict(complete=True,rows=rows,queries=len(rows),seconds=time.perf_counter()-start,scope=plan['scope']));import statistics;out=[]
for b in(4,8,12,16):
 rr=[]
 for seed in[r['seed']for r in cases if r['board']==b]:
  for rep in(0,1):
   z={r['arm']:r for r in rows if r['seed']==seed and r['rep']==rep};rr.append(z['final_product']['caller_seconds']/z['published_base']['caller_seconds'])
 out.append(dict(board=b,ratios=rr,median_ratio=statistics.median(rr)))
write_record(P/'static-analysis.json',dict(complete=True,rows=out,scope='Small staticcallercontrol, not5xuniversalsearchgain/strength. Kernel/nodeworkunchanged; fullmetadata costs separate.'));print('STATIC',len(rows),out,flush=True)
