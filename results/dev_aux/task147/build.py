"""Additionalfixedattacker-order intervention; separatebinary, nolearning rerun."""
import json,hashlib,subprocess,time,sys,difflib,shutil
from pathlib import Path
R=Path.cwd();O=R/'results/dev_aux/task147';O.mkdir(exist_ok=True);B=R/'.local_agent/alignment-order';B.mkdir(exist_ok=True)
PIN='9f778da667f6e07dae1e85d3e2ea204fc6dee94d';old=R/'.local_agent/alignment-see/source'/('Fairy-Stockfish-'+PIN)/'src';S=B/'source';shutil.copytree(old,S,dirs_exist_ok=True)
p=S/'psqt.cpp';prev=p.read_text();new=prev.replace('const int alignmentMode = aligned && std::string(aligned) == "2" ? 2 : (aligned && std::string(aligned) == "1" ? 1 : 0);','const int alignmentMode = aligned && std::string(aligned) == "3" ? 3 : (aligned && std::string(aligned) == "2" ? 2 : (aligned && std::string(aligned) == "1" ? 1 : 0));');assert new!=prev;p.write_text(new,encoding='utf-8')
pos=S/'position.cpp';original=pos.read_text();changed=original.replace('return value && std::string(value) == "2";','return value && (std::string(value) == "2" || std::string(value) == "3");',1)
marker='  int swap = PieceValue[MG][piece_on(to)] - threshold;';insert='''#ifdef GENERICCHESS_MATERIAL_DEVELOPMENT
  static const bool alignOrder = [] {
      const char* value = std::getenv("GENERICCHESS_ALIGN_SEARCH_PRICES");
      return value && std::string(value) == "3";
  }();
#else
  constexpr bool alignOrder = false;
#endif
'''
assert changed.count(marker)==1;changed=changed.replace(marker,insert+'\n'+marker,1)
marker='      res ^= 1;'
insert='''      PieceType leastPricedType = NO_PIECE_TYPE;
      if (alignOrder)
      {
          Value leastPrice = VALUE_INFINITE;
          for (PieceType pt : {PAWN, KNIGHT, BISHOP, ROOK, QUEEN})
              if ((stmAttackers & pieces(pt)) && PieceValue[MG][pt] < leastPrice)
              {
                  leastPrice = PieceValue[MG][pt];
                  leastPricedType = pt;
              }
      }

'''
assert changed.count(marker)==1;changed=changed.replace(marker,insert+marker,1)
for pt in ('PAWN','KNIGHT','BISHOP','ROOK','QUEEN'):
 marker='if ((bb = stmAttackers & pieces('+pt+')))'
 replacement='if ((bb = stmAttackers & pieces('+pt+')) && (!alignOrder || leastPricedType == '+pt+'))'
 assert changed.count(marker)==1;changed=changed.replace(marker,replacement,1)
pos.write_text(changed,encoding='utf-8')
(O/'attacker_price_order.patch').write_text(''.join(difflib.unified_diff(prev.splitlines(True),new.splitlines(True),fromfile='mode2/psqt.cpp',tofile='mode3/psqt.cpp'))+''.join(difflib.unified_diff(original.splitlines(True),changed.splitlines(True),fromfile='mode2/position.cpp',tofile='mode3/position.cpp')),encoding='utf-8')
decl=dict(task_id='147',question='Does fixedPNBRQleast-attackerpriority remain inconsistent when learnedpositivepricesare nonmonotonic?',source_pin=PIN,modes=[0,1,2,3],mode3='Mode2plusselectleastconfiguredMG standardattackerclass at eachSEErecapture; sameclass tieorder andLSBwithinclass; dynamicpins/xrays andkingbranchretainoriginal. ScopedStandardChess, not generalexactSEE.',witness=dict(fen='7k/3n2b1/4Rp2/6P1/8/8/8/K7 w - - 0 1',move='e6f6',candidate=dict(P=208,K=0,N=2000,B=52,R=396,Q=510),thresholds=[-189,-188,-187,0,207,208,209]),prediction='Legalrestrictedtargetexchange value-188: BlackcheapBcanrecaptureR, Whitestops; fixedclassSEE choosesexpensiveNfirstandcanaccept0. Mode3candidatepriceordering shouldreject0. Pricechoice is synthetic counterexample withinprevious52..3328domain, nothumanfit ortrainingcandidate.',cost='Oneownserialbuild~20s,28SEEqueries<2s,900sfuse; noadditionaltraining orchange tocompleted7104batch.',scope='Syntheticprice-consistency witness; notpolicygain/strength/fullrules-oracle. Alloldfrozenoutputs retained.')
(O/'declaration.json').write_text(json.dumps(decl,indent=2),encoding='utf-8')
prior=json.loads((R/'results/dev_aux/task137/build.json').read_bytes());D=json.loads((R/'results/dev_aux/task137/declaration.json').read_bytes());C=R/D['compiler_relative'];flags=prior['compile_flags'];sources=[x['source'] for x in prior['commands']];obj=B/'objects';obj.mkdir(exist_ok=True);binary=B/'fairy-order-toggle.exe';start=time.monotonic();records=[];error=None;status='INTERRUPTED'
try:
 for name in sources:
  for root in (R,R.parent/'GenericChess 2'):
   for state in ('rollout','advisor','slack'):
    stop=json.loads((root/f'.local_agent/{state}.json').read_bytes())
    if stop.get('user_paused') or stop.get('stopped'):raise RuntimeError('persistentstop')
  run=subprocess.run([str(C),*flags,'-c',str(S/name),'-o',str(obj/(name.replace('/','_')+'.o'))],cwd=S,capture_output=True,text=True,timeout=min(180,max(1,900-(time.monotonic()-start))))
  (obj/(name.replace('/','_')+'.log')).write_text(run.stdout+run.stderr,encoding='utf-8');records.append(dict(source=name,sha256=hashlib.sha256((S/name).read_bytes()).hexdigest(),returncode=run.returncode))
  if run.returncode:raise RuntimeError(name+': '+run.stderr[-1600:])
 run=subprocess.run([str(C),*[str(obj/(name.replace('/','_')+'.o')) for name in sources],'-pthread','-static','-o',str(binary)],cwd=S,capture_output=True,text=True,timeout=90)
 if run.returncode:raise RuntimeError('link:'+run.stderr[-1600:])
 status='COMPLETE'
except BaseException as ex:error=type(ex).__name__+': '+str(ex)
record=dict(status=status,seconds=time.monotonic()-start,flags=flags,sources=records,binary_relative=str(binary.relative_to(R)),binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest() if status=='COMPLETE' else None,error=error)
(O/'build.json').write_text(json.dumps(record,indent=2),encoding='utf-8');print(json.dumps({k:record[k] for k in ('status','seconds','binary_sha256','error')}));sys.exit(0 if status=='COMPLETE' else 3)
