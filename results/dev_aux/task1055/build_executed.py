from pathlib import Path
import json,hashlib,subprocess,difflib,time
R=Path.cwd();O=R/'results/dev_aux/task1054';O.mkdir(exist_ok=False);(O/'scope_correction.json').write_text(json.dumps(dict(status='QUALIFIED_INTERPRETATION',source='1052/1053',observation='Abovebound witness flips c1a1->c1b1 inbothmode0and3, other3controls samemoves withsomecp/depth differences',correction='Mode0 fixesPieceValue andSEErecapturepriors butCapturePieceValue stillfollowscandidate config. Cannotclaimpureleaf suffices; onlyjointPieceValuealignment notnecessary. 1052originaldecisionwordingpreservedandqualified.',new_go=0),indent=2),encoding='utf-8')
O=R/'results/dev_aux/task1055';O.mkdir(exist_ok=False);B=R/'.local_agent/leaf-native41';S=B/'source';S.mkdir(parents=True,exist_ok=False);prior=json.loads((R/'results/dev_aux/task147/build.json').read_bytes());D=json.loads((R/'results/dev_aux/task137/declaration.json').read_bytes());old=R/'.local_agent/alignment-order/source';objects=R/'.local_agent/alignment-order/objects';compiler=R/D['compiler_relative'];sourcechecks=[]
for row in prior['sources']:
 p=old/row['source'];assert hashlib.sha256(p.read_bytes()).hexdigest()==row['sha256'],row['source'];obj=objects/(row['source'].replace('/','_')+'.o');assert obj.is_file();sourcechecks.append(dict(source=row['source'],source_sha256=row['sha256'],object_sha256=hashlib.sha256(obj.read_bytes()).hexdigest()))
original=(old/'uci.cpp').read_text();needle='      else if (token == "eval")     trace_eval(pos);';assert original.count(needle)==1
insert='''#ifdef GENERICCHESS_MATERIAL_DEVELOPMENT
      else if (token == "devauxleafr")
      {
          int price = 0;
          is >> price;
          if (!is || price < 1 || price > 3328)
              sync_cout << "info string DEV_AUX leafR invalid" << sync_endl;
          else
          {
              Search::clear();
              for (Phase phase : {MG, EG})
                  EvalPieceValue[phase][make_piece(WHITE, ROOK)] =
                  EvalPieceValue[phase][make_piece(BLACK, ROOK)] = Value(price);
              sync_cout << "info string DEV_AUX leafR " << int(EvalPieceValue[MG][ROOK])
                        << " nativeR " << int(PieceValue[MG][ROOK])
                        << " captureR " << int(CapturePieceValue[MG][ROOK]) << sync_endl;
          }
      }
#endif
'''
changed=original.replace(needle,insert+needle,1);(S/'uci.cpp').write_text(changed,encoding='utf-8');(O/'leaf_override.patch').write_text(''.join(difflib.unified_diff(original.splitlines(True),changed.splitlines(True),fromfile='mode3/uci.cpp',tofile='leaf-native41/uci.cpp')),encoding='utf-8')
plan=dict(status='FROZEN_BEFORE_TINY_DIAGNOSTIC_BUILD',question='Can exactleafR vsnativeR consumers be independentlyreadback foroneobservedaboveboundwitness?',patch='OneownedUCIdevauxleafrcommand setsEvalPieceValueonlyafterSearch::clear, explicitMG/EG bothcolors; CapturePieceValue/PieceValue/PSQT nativeunchanged. Notproduct/default intervention.',baseline_binary_sha256='c378f0b3fc9f99d48e3089294a7c6adf5d5215bcac070200424d0d24f4d4b460',source_pin=D['source_pin'],sources=sourcechecks,compiler_sha256=hashlib.sha256(compiler.read_bytes()).hexdigest(),flags=prior['flags'],cost='Compileonechangedtranslationunit thenlink29ownedobjects,300sfuse expected<5s; originalsource/binary/objects unchanged, no worker/network. Defaultsame-inputquery controlsrequiredbeforeadoption.',scope='Newconditionalmechanismdiagnostic notstrength/fitnessgain orfullgenericpriceAPI')
(O/'plan.json').write_text(json.dumps(plan,indent=2),encoding='utf-8');start=time.monotonic();obj=B/'uci_override.o';binary=B/'fairy-leaf-native.exe';cmd=[str(compiler),*prior['flags'],'-I',str(old),'-c',str(S/'uci.cpp'),'-o',str(obj)];r=subprocess.run(cmd,cwd=R,capture_output=True,text=True,timeout=180);(O/'compile.log').write_text(r.stdout+r.stderr,encoding='utf-8');error=None;status='COMPILE_FAILED'
if r.returncode==0:
 linkobjects=[obj if row['source']=='uci.cpp' else objects/(row['source'].replace('/','_')+'.o') for row in prior['sources']];r=subprocess.run([str(compiler),*map(str,linkobjects),'-pthread','-static','-o',str(binary)],cwd=R,capture_output=True,text=True,timeout=90);(O/'link.log').write_text(r.stdout+r.stderr,encoding='utf-8');status='COMPLETE' if r.returncode==0 else 'LINK_FAILED'
result=dict(status=status,returncode=r.returncode,seconds=time.monotonic()-start,binary_relative=str(binary.relative_to(R)),binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest() if status=='COMPLETE' else None,unchanged_original_binary=hashlib.sha256((R/'.local_agent/alignment-order/fairy-order-toggle.exe').read_bytes()).hexdigest()==plan['baseline_binary_sha256']);(O/'build.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(result)
assert status=='COMPLETE',r.stderr[-1500:]
