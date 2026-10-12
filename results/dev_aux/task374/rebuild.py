"""Reconstruct the exact experimental sources, then optional serial build. Never overwrite evidence."""
import argparse,hashlib,io,json,os,re,subprocess,tarfile,time,urllib.request
from pathlib import Path
HERE=Path(__file__).resolve().parent

def patch_source(S):
 p=S/'main.cpp';t=p.read_text(encoding='utf-8').replace('\ufeff','');assert t.count('Bitboards::init();')==1;t='#include "aux_material.h"\n'+t;t=t.replace('Bitboards::init();','aux_material_init();\n\tBitboards::init();');p.write_text(t,encoding='utf-8')
 (S/'aux_material.h').write_bytes((HERE/'aux_material.h').read_bytes())
 p=S/'numa.h';p.write_text('#include <iterator>\n'+p.read_text(encoding='utf-8-sig'),encoding='utf-8')
 p=S/'usi.cpp';t=p.read_text(encoding='utf-8');needle='else if (token == "e")';assert t.count(needle)==1;t=t.replace(needle,(HERE/'usi_hook.inc').read_text(encoding='utf-8')+needle);needle='#if !defined(__EMSCRIPTEN__)\n\t// --- Keep Alive';assert t.count(needle)==1;t=t.replace(needle,'#if !defined(__EMSCRIPTEN__) && !defined(DEV_AUX_NO_READY_KEEPALIVE)\n\t// --- Keep Alive');p.write_text(t,encoding='utf-8')
 p=S/'position.cpp';t=p.read_text(encoding='utf-8-sig');a=t.index('        // 歩で取れるなら、まず歩で取る。',t.index('bool Position::see_ge'));b=t.index('#if !STOCKFISH\n        /*',a);t=t[:a]+(HERE/'candidate_see.inc').read_text(encoding='utf-8')+t[b:];p.write_text(t,encoding='utf-8')
 p=S/'engine/yaneuraou-engine/yaneuraou-search.cpp';t=p.read_text(encoding='utf-8-sig');needle='Engine::run_heavy_job([] { Eval::load_eval(); });';assert t.count(needle)==1;t=t.replace(needle,'#if defined(EVAL_MATERIAL) && MATERIAL_LEVEL == 1\n    Eval::load_eval(); // noop: no heavy-loading keepalive thread needed in this experiment\n#else\n    '+needle+'\n#endif');p.write_text(t,encoding='utf-8')

def verify_sources(S):
 m=json.loads((HERE/'source_manifest.json').read_text(encoding='utf-8'));changed={x['path']:x for x in m['changed_files']}
 for f in m['files']:
  expect=changed.get(f['path'],{}).get('patched_sha256',f['sha256']);p=S.parent/f['path'];assert hashlib.sha256(p.read_bytes()).hexdigest()==expect,f['path']
 assert hashlib.sha256((S/'aux_material.h').read_bytes()).hexdigest()==m['added_header_sha256']
 return len(m['files'])+1

def main():
 p=argparse.ArgumentParser();p.add_argument('--source-only',action='store_true');p.add_argument('--output',default='.local_agent/yaneura25-reproduction');a=p.parse_args();R=Path.cwd().resolve();assert subprocess.check_output(['git','branch','--show-current'],cwd=R,text=True).strip()=='sidemission';O=(R/a.output).resolve();assert O.is_relative_to(R/'.local_agent') and not O.exists(),'fresh private output required';O.mkdir(parents=True)
 m=json.loads((HERE/'source_manifest.json').read_text(encoding='utf-8'));url=m['url'];received=[]
 with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'GenericChess-DEV_AUX-source-reproduction'}),timeout=60) as r:
  with tarfile.open(fileobj=r,mode='r|gz') as tf:
   for item in tf:
    parts=Path(item.name).parts
    if not item.isfile() or len(parts)<3 or parts[1]!='source':continue
    rel=Path(*parts[1:]);assert '..' not in rel.parts and not rel.is_absolute();b=tf.extractfile(item).read();dst=O/rel;dst.parent.mkdir(parents=True,exist_ok=True);dst.write_bytes(b);received.append(rel.as_posix())
 assert set(received)=={f['path'] for f in m['files']}
 for f in m['files']:assert hashlib.sha256((O/f['path']).read_bytes()).hexdigest()==f['sha256'],f['path']
 S=O/'source';patch_source(S);count=verify_sources(S);print('Exact patched sources',count,flush=True)
 if a.source_only:return
 compiler=R/'.local_agent/alignment-build/toolchain/llvm-mingw-20261006-ucrt-x86_64/bin/clang++.exe';assert compiler.is_file();make=(S/'Makefile').read_text(encoding='utf-8');base=make.split('SOURCES  = \\\n',1)[1].split('\nCUDA_SOURCES',1)[0];sources=re.findall(r'[A-Za-z0-9_/]+\.cpp',base)+['book/makebook.cpp','book/makebook2025.cpp','engine/yaneuraou-engine/yaneuraou-search.cpp'];flags=['-std=c++17','-fno-exceptions','-fno-rtti','-O3','-ffast-math','-DNDEBUG','-DNO_EXCEPTIONS','-DUNICODE','-DYANEURAOU_ENGINE_MATERIAL','-DMATERIAL_LEVEL=1','-DUSE_SSE2','-msse2','-DTARGET_CPU="SSE2"','-Wno-unused-parameter','-fno-threadsafe-statics'];B=O/'objects';B.mkdir();objects=[];steps=[];t0=time.monotonic()
 for i,src in enumerate(sources):
  obj=B/f'{i}.o';args=[str(compiler),*(['-DDEV_AUX_NO_READY_KEEPALIVE'] if src=='usi.cpp' else []),*flags,'-c',src,'-o',str(obj)];r=subprocess.run(args,cwd=S,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=180);steps.append({'args':args,'exit_code':r.returncode,'stdout':r.stdout,'stderr':r.stderr});(O/'build_progress.json').write_text(json.dumps(steps,indent=2),encoding='utf-8');assert r.returncode==0,r.stderr;objects.append(str(obj));print(i,src,flush=True)
 exe=O/'yaneura-material1-aux.exe';args=[str(compiler),*objects,'-static','-lpthread','-fuse-ld=lld','-Wl,--stack,25000000','-o',str(exe)];r=subprocess.run(args,cwd=S,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=180);steps.append({'args':args,'exit_code':r.returncode,'stdout':r.stdout,'stderr':r.stderr});(O/'build.json').write_text(json.dumps({'steps':steps,'seconds':time.monotonic()-t0,'source_count':count,'sha256':hashlib.sha256(exe.read_bytes()).hexdigest() if exe.exists() else None},indent=2),encoding='utf-8');assert r.returncode==0,r.stderr;print('Built',exe)
if __name__=='__main__':main()