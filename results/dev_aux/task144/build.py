"""Build separatedexperiment revealing residualhardcodedSEErecaptureprices."""
import json,hashlib,zipfile,subprocess,time,difflib,sys
from pathlib import Path
R=Path.cwd();O=R/'results/dev_aux/task144';O.mkdir(exist_ok=True);B=R/'.local_agent/alignment-see';B.mkdir(exist_ok=True)
D=json.loads((R/'results/dev_aux/task137/declaration.json').read_bytes());C=R/D['compiler_relative'];pin=D['source_pin']
with zipfile.ZipFile(R/'.local_agent/alignment-build/fairy-source.zip') as z:
 for name in z.namelist():
  target=(B/'source'/name).resolve();assert target.is_relative_to((B/'source').resolve())
 z.extractall(B/'source')
S=B/'source'/('Fairy-Stockfish-'+pin)/'src'
(S/'evaluate.cpp').write_bytes((R/'.local_agent/material-selfplay/evaluate.cpp').read_bytes())
price_original=(S/'psqt.cpp').read_text();price=(R/'.local_agent/alignment-build/source'/('Fairy-Stockfish-'+pin)/'src/psqt.cpp').read_text()
price=price.replace('const bool alignSearch = aligned && std::string(aligned) == "1";','const int alignmentMode = aligned && std::string(aligned) == "2" ? 2 : (aligned && std::string(aligned) == "1" ? 1 : 0);\n  const bool alignSearch = alignmentMode != 0;')
price=price.replace('(alignSearch ? 1 : 0)','alignmentMode');(S/'psqt.cpp').write_text(price,encoding='utf-8')
p=S/'position.cpp';original=p.read_text();changed=original
needle='  int swap = PieceValue[MG][piece_on(to)] - threshold;'
insert='''#ifdef GENERICCHESS_MATERIAL_DEVELOPMENT
  // One furtherablation: recaptureconstants only, class-attackerorder unchanged.
  static const bool alignRecapture = [] {
      const char* value = std::getenv("GENERICCHESS_ALIGN_SEARCH_PRICES");
      return value && std::string(value) == "2";
  }();
#else
  constexpr bool alignRecapture = false;
#endif
'''
assert changed.count(needle)==1;changed=changed.replace(needle,insert+'\n'+needle,1)
for name,pt in [('Pawn','PAWN'),('Knight','KNIGHT'),('Bishop','BISHOP'),('Rook','ROOK'),('Queen','QUEEN')]:
 old='(swap = '+name+'ValueMg - swap)';new='(swap = (alignRecapture ? PieceValue[MG]['+pt+'] : '+name+'ValueMg) - swap)'
 assert changed.count(old)==1;changed=changed.replace(old,new,1)
changed='#include <cstdlib>\n'+changed;p.write_text(changed,encoding='utf-8')
uci=S/'uci.cpp';uci_original=uci.read_text()
needle='      else if (token == "eval")     trace_eval(pos);'
insert='''#ifdef GENERICCHESS_MATERIAL_DEVELOPMENT
      else if (token == "devauxsee")
      {
          std::string moveText;
          int threshold = 0;
          is >> moveText >> threshold;
          Move move = UCI::to_move(pos, moveText);
          if (move == MOVE_NONE || threshold < -10000 || threshold > 10000)
              sync_cout << "info string DEV_AUX SEE invalid" << sync_endl;
          else
              sync_cout << "info string DEV_AUX SEE " << moveText << " "
                        << threshold << " " << (pos.see_ge(move, Value(threshold)) ? 1 : 0)
                        << sync_endl;
      }
#endif
'''
assert uci_original.count(needle)==1;uci_changed=uci_original.replace(needle,insert+needle,1);uci.write_text(uci_changed,encoding='utf-8')
patches=''
for name,a,b in [('psqt.cpp',price_original,price),('position.cpp',original,changed),('uci.cpp',uci_original,uci_changed)]:
 patches+=''.join(difflib.unified_diff(a.splitlines(True),b.splitlines(True),fromfile='a/src/'+name,tofile='b/src/'+name))
(O/'price_and_recapture.patch').write_text(patches,encoding='utf-8')
prior=json.loads((R/'results/dev_aux/task137/build.json').read_bytes());flags=prior['compile_flags'];sources=[x['source'] for x in prior['commands']]
objects=B/'objects';objects.mkdir(exist_ok=True);binary=B/'fairy-see-toggle.exe'
decl=dict(task_id='144',question='Do residualhardcodedSEErecapture constants disagreewithcandidate-material targetexchange?',source_pin=pin,build_parent_sha256=hashlib.sha256((R/'results/dev_aux/task137/build.json').read_bytes()).hexdigest(),modes=dict(off=0,table_only=1,table_and_recapture=2),intervention='Mode2replacesfivefixedPawn/Knight/Bishop/Rook/QueenValueMgrecaptureconstants withconfiguredPieceValueMG; samePSQTtablealignment asmode1. Fixedclass-orderPNBRQ, margins andotherpriorsremain. No fullSEEalignmentclaim.',witness=dict(fen='7k/3nB3/5p2/6P1/8/8/8/K7 w - - 0 1',move='e7f6',candidate=dict(P=208,K=0,N=232,B=328,R=396,Q=510),thresholds=[0,111,112,113,207,208,209]),cost='Oneadditionalserialownedbuild estimated<1min,900sfuse;21actualSEEqueries+leaf/tableacks<5s. No newtraining, no currentbatchfiles/binary modified.',prediction='Candidate-material targetswap BxP NxB PxN has208-328+232=112; threshold113rejects. Mode1still781recaptureN yieldsdifferentSEEthreshold behavior; mode2mayresolvepriceconstant mismatch. ThisdoesnotprovestrengthorfullyexactSEE.')
(O/'declaration.json').write_text(json.dumps(decl,indent=2),encoding='utf-8')
start=time.monotonic();records=[];error=None;status='INTERRUPTED'
try:
 for name in sources:
  cmd=[str(C),*flags,'-c',str(S/name),'-o',str(objects/(name.replace('/','_')+'.o'))]
  r=subprocess.run(cmd,cwd=S,capture_output=True,text=True,timeout=min(180,max(1,900-(time.monotonic()-start))))
  (objects/(name.replace('/','_')+'.log')).write_text(r.stdout+r.stderr,encoding='utf-8')
  records.append(dict(source=name,sha256=hashlib.sha256((S/name).read_bytes()).hexdigest(),returncode=r.returncode))
  if r.returncode:raise RuntimeError(name+': '+r.stderr[-1600:])
 r=subprocess.run([str(C),*[str(objects/(name.replace('/','_')+'.o')) for name in sources],'-pthread','-static','-o',str(binary)],cwd=S,capture_output=True,text=True,timeout=90)
 if r.returncode:raise RuntimeError('link:'+r.stderr[-1600:])
 status='COMPLETE'
except BaseException as ex:error=type(ex).__name__+': '+str(ex)
out=dict(status=status,seconds=time.monotonic()-start,source_pin=pin,flags=flags,sources=records,binary_relative=str(binary.relative_to(R)),binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest() if status=='COMPLETE' else None,error=error,original_active_learning_binary_unchanged=True)
(O/'build.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps({k:out[k] for k in ('status','seconds','binary_sha256','error')}));sys.exit(0 if status=='COMPLETE' else 3)
