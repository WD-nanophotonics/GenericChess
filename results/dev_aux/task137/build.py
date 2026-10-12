"""Serialownedexperimentalbuild with explicitprocess-local table toggle."""
import json,hashlib,subprocess,time,sys
from pathlib import Path
R=Path.cwd();O=R/'results/dev_aux/task137';D=json.loads((O/'declaration.json').read_bytes());S=R/D['source_relative'];C=R/D['compiler_relative'];B=R/'.local_agent/alignment-build/objects';B.mkdir(exist_ok=True)
p=S/'psqt.cpp';original=(R/'.local_agent/material-selfplay/psqt.cpp').read_text(encoding='utf-8');assert 'GENERICCHESS_ALIGN_SEARCH_PRICES' not in original
insertion='''
// DEV_AUX scoped Standard-Chess price-table ablation, defaultoff perprocess.
#ifdef GENERICCHESS_MATERIAL_DEVELOPMENT
  const char* aligned = std::getenv("GENERICCHESS_ALIGN_SEARCH_PRICES");
  const bool alignSearch = aligned && std::string(aligned) == "1";
  if (alignSearch)
      for (PieceType pt : {PAWN, KNIGHT, BISHOP, ROOK, QUEEN})
          for (Phase phase : {MG, EG})
              if (v->pieceValue[phase][pt])
                  PieceValue[phase][make_piece(WHITE, pt)] =
                  PieceValue[phase][make_piece(BLACK, pt)] = Value(v->pieceValue[phase][pt]);
  std::cout << "info string DEV_AUX alignment " << (alignSearch ? 1 : 0);
  for (PieceType pt : {PAWN, KNIGHT, BISHOP, ROOK, QUEEN})
      std::cout << " " << int(pt) << ":" << PieceValue[MG][pt] << ":" << PieceValue[EG][pt];
  std::cout << std::endl;
#endif
'''
changed=original.replace('void init(const Variant* v) {','void init(const Variant* v) {\n'+insertion,1)
changed='#include <cstdlib>\n#include <iostream>\n'+changed
p.write_text(changed,encoding='utf-8')
import difflib
(O/'search_price_toggle.patch').write_text(''.join(difflib.unified_diff(original.splitlines(True),changed.splitlines(True),fromfile='a/src/psqt.cpp',tofile='b/src/psqt.cpp')),encoding='utf-8')
sources='benchmark.cpp bitbase.cpp bitboard.cpp endgame.cpp evaluate.cpp main.cpp material.cpp misc.cpp movegen.cpp movepick.cpp pawns.cpp position.cpp psqt.cpp search.cpp thread.cpp timeman.cpp tt.cpp uci.cpp ucioption.cpp tune.cpp syzygy/tbprobe.cpp nnue/evaluate_nnue.cpp nnue/features/half_ka_v2.cpp partner.cpp parser.cpp piece.cpp variant.cpp xboard.cpp nnue/features/half_ka_v2_variants.cpp'.split()
flags=['-include','iterator','-std=c++17','-O2','-DNDEBUG','-fno-exceptions','-DIS_64BIT','-DNO_PREFETCH','-DNNUE_EMBEDDING_OFF','-DGENERICCHESS_MATERIAL_DEVELOPMENT','-msse2','-pthread']
start=time.monotonic();commands=[];status='INTERRUPTED';binary=R/'.local_agent/alignment-build/fairy-toggle.exe';error=None
try:
 version=subprocess.run([str(C),'--version'],capture_output=True,text=True,check=True,timeout=20).stdout
 for i,name in enumerate(sources):
  if time.monotonic()-start>900:raise TimeoutError('declaredserialbuildfuse')
  # Respectreal persistentstops without changing anotherAgentstate.
  for root in (R,R.parent/'GenericChess 2'):
   for state in ('rollout','advisor','slack'):
    x=json.loads((root/f'.local_agent/{state}.json').read_bytes())
    if x.get('user_paused') or x.get('stopped'):raise RuntimeError('persistentuserstop')
  obj=B/(name.replace('/','_')+'.o');cmd=[str(C),*flags,'-c',str(S/name),'-o',str(obj)]
  run=subprocess.run(cmd,cwd=S,capture_output=True,text=True,timeout=min(180,max(1,900-(time.monotonic()-start))))
  (B/(name.replace('/','_')+'.log')).write_text(run.stdout+run.stderr,encoding='utf-8')
  commands.append(dict(source=name,source_sha256=hashlib.sha256((S/name).read_bytes()).hexdigest(),args=flags,returncode=run.returncode,object_sha256=hashlib.sha256(obj.read_bytes()).hexdigest() if run.returncode==0 else None))
  print(json.dumps(dict(compiled=i+1,total=len(sources),source=name,code=run.returncode,seconds=round(time.monotonic()-start,2))),flush=True)
  if run.returncode:raise RuntimeError('compilefailed:'+name+' '+run.stderr[-1800:])
 cmd=[str(C),*[str(B/(name.replace('/','_')+'.o')) for name in sources],'-pthread','-static','-o',str(binary)]
 run=subprocess.run(cmd,cwd=S,capture_output=True,text=True,timeout=90);(B/'link.log').write_text(run.stdout+run.stderr,encoding='utf-8')
 if run.returncode:raise RuntimeError('linkfailed:'+run.stderr[-1800:])
 status='COMPLETE'
except BaseException as ex:error=type(ex).__name__+': '+str(ex)
record=dict(status=status,build_seconds=time.monotonic()-start,source_pin=D['source_pin'],toolchain_sha256=D['toolchain_sha256'],compiler_version=locals().get('version'),compile_flags=flags,commands=commands,link_flags=['-pthread','-static'],binary_relative=str(binary.relative_to(R)),binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest() if status=='COMPLETE' else None,experimental_psqt_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),error=error,scope='Ownedexperimentalcompile of exactpinnedsource withmaterialpatch plusoneprocess-env tabletoggle. No source-to-binary identityclaim for old477628ae; singlebinarysamecompiler comparison controls newablation.')
(O/'build.json').write_text(json.dumps(record,indent=2),encoding='utf-8');print(json.dumps({k:record[k] for k in ('status','build_seconds','binary_sha256','error')}))
sys.exit(0 if status=='COMPLETE' else 3)
