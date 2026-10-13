from pathlib import Path
import json,hashlib,subprocess,time,shutil
R=Path.cwd();O=R/'results/dev_aux/task837';O.mkdir(exist_ok=False);B=R/'.local_agent/provenance38';B.mkdir(exist_ok=False)
src=R/'.local_agent/yaneura27/source';p=src/'engine/yaneuraou-engine/yaneuraou-search.cpp';s=p.read_text(encoding='utf-8-sig');original=hashlib.sha256(p.read_bytes()).hexdigest()
helper='''\nstatic Value aux_return_trace(const Position& pos, int ply, Value v, int site) {\n    sync_cout << "info string auxreturn " << site << " " << ply << " " << int(v) << " " << int(pos.side_to_move()) << " " << int(pos.state()->materialValue) << " " << pos.sfen() << sync_endl;\n    return v;\n}\n'''
s=s.replace('using namespace Eval;  // Eval::PieceValue','using namespace Eval;  // Eval::PieceValue\n'+helper)
changes={}
for expr in ['bestValue','(2 * beta + eval) / 3']:
 needle='return '+expr+';'; changes[expr]=s.count(needle);s=s.replace(needle,'return aux_return_trace(pos, ss->ply, '+expr+', __LINE__);')
assert changes['bestValue']==8 and changes['(2 * beta + eval) / 3']==1,changes
out=B/'yaneuraou-search.cpp';out.write_text(s,encoding='utf-8');build=json.loads((R/'.local_agent/yaneura27/build.json').read_bytes());step=next(x for x in build['steps'] if x.get('source')=='engine/yaneuraou-engine/yaneuraou-search.cpp');args=list(step['args']);args[args.index('-c')+1]=str(out);args[args.index('-o')+1]=str(B/'search.o');args.extend(['-I'+str(src/'engine/yaneuraou-engine'),'-I'+str(src)])
plan=dict(status='FROZEN_BEFORE_BUILD',question='Which returned scores are soft bounds or corrected material rather than a printed PV material leaf?',source_sha256=original,changed_return_sites=changes,limits='32 cold diagnostic queries, original2profiles, balanced256/1024; at most300seconds queries. Telemetry does NOT claim complete propagated leaf gradients or original wall timing.',original_executable_sha256='c69d96c10244b65da124d66c653449bc701680f4e3da05ec48b3979ef950d2e2',instrumented_source_sha256=hashlib.sha256(out.read_bytes()).hexdigest())
(O/'plan.json').write_text(json.dumps(plan,indent=2),encoding='utf-8');(O/'instrumentation.diff').write_text(helper+'\nREPLACEMENTS '+json.dumps(changes),encoding='utf-8')
t=time.monotonic();r=subprocess.run(args,cwd=src,capture_output=True,text=True,timeout=180);rec=dict(compile_exit=r.returncode,compile_stdout=r.stdout,compile_stderr=r.stderr,seconds=time.monotonic()-t);(B/'compile.json').write_text(json.dumps(rec,indent=2),encoding='utf-8');print(rec);assert r.returncode==0
link=build['steps'][-1];print('LINK_STEP',link.keys());(B/'original_link.json').write_text(json.dumps(link,indent=2),encoding='utf-8')
