from pathlib import Path
import cProfile,pstats,json,hashlib,time
R=Path.cwd();B=Path(__file__).resolve().parent
source=(R/'results/dev_aux/task082/probe.py').read_bytes()
namespace={'__file__':str(R/'results/dev_aux/task082/probe.py')}
exec(compile(source.split(b'rows=[];started=')[0],'<fixed raw eager driver>','exec'),namespace)
namespace['ARM']='raw_eager_terminal';namespace['d'].update(nodes=100000,seconds=90)
name,c,initial,w,ev=next(row for row in namespace['roots'] if row[0]=='seed1008-ply8')
namespace['StopCheck'].stopped();prof=cProfile.Profile();t=time.perf_counter();prof.enable()
v=namespace['search'](c,initial,w,ev,True);prof.disable();caller=time.perf_counter()-t
stats=pstats.Stats(prof);rows=[]
for (file,line,function),(cc,nc,tt,ct,callers) in stats.stats.items():
 file=file.replace(str(R/'.local_agent/pinned_bebe'),'pinned_bebe').replace(str(R),'auxiliary_root')
 rows.append({'file':file,'line':line,'function':function,'primitive_calls':cc,'total_calls':nc,'self_seconds':tt,'cumulative_seconds':ct})
rows.sort(key=lambda r:r['self_seconds'],reverse=True)
out={'complete':True,'source_sha256':hashlib.sha256(source).hexdigest(),'root':name,'caller_seconds':caller,'decision':v,'profile_total_calls':stats.total_calls,'profile_total_seconds':stats.total_tt,'functions':rows,'scope':'one instrumented exposedcall,profilingoverheadnot ordinarycaller/speedcomparison;all inclusivecosts overlap,exclusiveC primitivesnot fulloperation attribution'}
(B/'result.json').write_bytes((json.dumps(out,indent=2)+'\n').encode());print(v['reason'],v['score'],caller);print(json.dumps(rows[:12],indent=2))
