from pathlib import Path
import re,json,subprocess,time,hashlib
R=Path.cwd(); S=R/'.local_agent/yaneura25/source'; O=R/'results/dev_aux/task357';O.mkdir(exist_ok=True)
header=r'''#include "evaluate.h"
#include <cstdlib>
#include <sstream>
#include <iostream>
static void aux_material_init() {
 const char* raw=std::getenv("DEV_AUX_SHOGI_VALUES");
 if (!raw) { std::cerr << "Missing DEV_AUX_SHOGI_VALUES" << std::endl; std::exit(2); }
 std::istringstream in(raw); int v[16]={0};
 for(int i=1;i<=14;++i) if(!(in>>v[i]) || (i==8 ? v[i]!=0 : v[i]<32 || v[i]>4096)) std::exit(2);
 int extra; if(in>>extra) std::exit(2);
 if(v[1]!=90) std::exit(2);
 using namespace YaneuraOu;
 for(int c=0;c<2;++c) for(int pt=0;pt<16;++pt) {
  int pc=16*c+pt; int base=(pt>=9 && pt<=14)?pt-8:pt;
  Eval::PieceValue[pc]=v[pt]; Eval::PieceValueM[pc]=(c==0?1:-1)*v[pt];
  Eval::CapturePieceValue[pc]=(pt==0 || pt==8 || pt==15)?0:v[pt]+v[base];
  Eval::ProDiffPieceValue[pc]=(base>=1 && base<=6)?v[base+8]-v[base]:0;
 }
}
'''
(S/'aux_material.h').write_text(header,encoding='utf-8')
p=S/'main.cpp';t=p.read_text(encoding='utf-8');assert '#include "aux_material.h"' not in t;t='#include "aux_material.h"\n'+t;t=t.replace('Bitboards::init();','aux_material_init();\n\tBitboards::init();');p.write_text(t,encoding='utf-8')
p=S/'usi.cpp';t=p.read_text(encoding='utf-8');needle='else if (token == "e")';assert t.count(needle)==1
hook=r'''else if (token == "auxprices") {
        for(int pc=0;pc<32;++pc)
          sync_cout << "info string auxprice " << pc << " " << Eval::PieceValue[pc] << " " << Eval::PieceValueM[pc] << " " << Eval::CapturePieceValue[pc] << " " << Eval::ProDiffPieceValue[pc] << sync_endl;
    }
    '''
t=t.replace(needle,hook+needle);p.write_text(t,encoding='utf-8')
m=(S/'Makefile').read_text(encoding='utf-8');base=m.split('SOURCES  = \\\n',1)[1].split('\nCUDA_SOURCES',1)[0];sources=re.findall(r'[A-Za-z0-9_/]+\.cpp',base)+['book/makebook.cpp','book/makebook2025.cpp','engine/yaneuraou-engine/yaneuraou-search.cpp']
compiler=R/'.local_agent/alignment-build/toolchain/llvm-mingw-20261006-ucrt-x86_64/bin/clang++.exe'
flags=['-std=c++17','-fno-exceptions','-fno-rtti','-O3','-ffast-math','-DNDEBUG','-DNO_EXCEPTIONS','-DUNICODE','-DYANEURAOU_ENGINE_MATERIAL','-DMATERIAL_LEVEL=1','-DUSE_SSE2','-msse2','-DTARGET_CPU="SSE2"','-Wno-unused-parameter','-fno-threadsafe-statics']
B=S.parent/'objects';B.mkdir(exist_ok=True);t0=time.monotonic();steps=[];objects=[]
for i,src in enumerate(sources):
 obj=B/f'{i}.o';args=[str(compiler),*flags,'-c',src,'-o',str(obj)];t=time.monotonic();r=subprocess.run(args,cwd=S,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=180);steps.append({'source':src,'args':args,'seconds':time.monotonic()-t,'exit_code':r.returncode,'stdout':r.stdout,'stderr':r.stderr});(O/'build_progress.json').write_text(json.dumps(steps,indent=2),encoding='utf-8');print(i,src,r.returncode,round(steps[-1]['seconds'],2),flush=True)
 if r.returncode: print(r.stderr[-4000:]);break
 objects.append(str(obj))
else:
 exe=S.parent/'yaneura-material1-aux.exe';args=[str(compiler),*objects,'-static','-lpthread','-fuse-ld=lld','-Wl,--stack,25000000','-o',str(exe)];r=subprocess.run(args,cwd=S,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=180);steps.append({'link_args':args,'exit_code':r.returncode,'stdout':r.stdout,'stderr':r.stderr}); print('LINK',r.returncode,r.stderr[-4000:],flush=True)
 result={'source_sha':'c1b80eaa09fe13d5f12b1599d1ae4d53c224de30','seconds':time.monotonic()-t0,'steps':steps,'executable_sha256':hashlib.sha256(exe.read_bytes()).hexdigest() if exe.exists() else None};(O/'build.json').write_text(json.dumps(result,indent=2),encoding='utf-8')