from pathlib import Path
import subprocess,json,time,hashlib
R=Path.cwd();S=R/'.local_agent/yaneura25/source';O=R/'results/dev_aux/task359';O.mkdir(exist_ok=True)
p=S/'usi.cpp';t=p.read_text(encoding='utf-8');needle='else if (token == "auxprices")';assert t.count(needle)==1
t=t.replace(needle,'else if (token == "auxstate") { auto& pos=engine.get_position(); sync_cout << "info string auxstate " << pos.state()->materialValue << " " << Eval::material(pos) << " " << engine.evaluate() << " " << pos.is_repetition() << " " << pos.sfen() << sync_endl; }\n    '+needle);p.write_text(t,encoding='utf-8')
b=json.loads((R/'results/dev_aux/task358/build.json').read_text(encoding='utf-8'));args=b['steps'][6]['args'];t0=time.monotonic();r=subprocess.run(args,cwd=S,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=180);out=[{'args':args,'exit_code':r.returncode,'stdout':r.stdout,'stderr':r.stderr}];print('compile',r.returncode,r.stderr[-2000:]);
if r.returncode==0:
 args=b['steps'][-1]['link_args'];r=subprocess.run(args,cwd=S,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=180);out.append({'args':args,'exit_code':r.returncode,'stdout':r.stdout,'stderr':r.stderr});print('link',r.returncode,r.stderr[-2000:])
exe=S.parent/'yaneura-material1-aux.exe';(O/'build.json').write_text(json.dumps({'seconds':time.monotonic()-t0,'steps':out,'sha256':hashlib.sha256(exe.read_bytes()).hexdigest()},indent=2),encoding='utf-8')