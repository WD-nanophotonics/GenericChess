from pathlib import Path
import json,hashlib,difflib,subprocess,time
R=Path.cwd();O=R/'results/dev_aux/task1385';O.mkdir();B=R/'.local_agent/leaf-rb-45';S=B/'source';S.mkdir(parents=True)
old=R/'.local_agent/leaf-4096-43/source/uci.cpp';source=old.read_text();marker='      else if (token == "devauxleafr")'
assert source.count(marker)==1
new=r'''      else if (token == "devauxleafrb")
      {
          int rook = 0, bishop = 0;
          is >> rook >> bishop;
          if (!is || rook < 1 || rook > 4096 || bishop < 1 || bishop > 4096)
              sync_cout << "info string DEV_AUX leafRB invalid" << sync_endl;
          else
          {
              Search::clear();
              for (Phase phase : {MG, EG})
              {
                  EvalPieceValue[phase][make_piece(WHITE, ROOK)] =
                  EvalPieceValue[phase][make_piece(BLACK, ROOK)] = Value(rook);
                  EvalPieceValue[phase][make_piece(WHITE, BISHOP)] =
                  EvalPieceValue[phase][make_piece(BLACK, BISHOP)] = Value(bishop);
              }
              sync_cout << "info string DEV_AUX leafRB " << int(EvalPieceValue[MG][ROOK])
                        << " " << int(EvalPieceValue[MG][BISHOP])
                        << " nativeR " << int(PieceValue[MG][ROOK])
                        << " nativeB " << int(PieceValue[MG][BISHOP])
                        << " captureR " << int(CapturePieceValue[MG][ROOK])
                        << " captureB " << int(CapturePieceValue[MG][BISHOP]) << sync_endl;
          }
      }
'''
changed=source.replace(marker,new+marker)
(S/'uci.cpp').write_text(changed);(O/'uci.cpp').write_text(changed)
(O/'leaf_rb.patch').write_text(''.join(difflib.unified_diff(source.splitlines(True),changed.splitlines(True),fromfile='leaf-4096-43/uci.cpp',tofile='leaf-rb-45/uci.cpp')))
prior=json.loads((R/'results/dev_aux/task147/build.json').read_bytes());D=json.loads((R/'results/dev_aux/task137/declaration.json').read_bytes());compiler=R/D['compiler_relative'];base=R/'.local_agent/alignment-order/source';objs=R/'.local_agent/alignment-order/objects';sources=[]
for row in prior['sources']:
 p=base/row['source'];assert hashlib.sha256(p.read_bytes()).hexdigest()==row['sha256'];obj=objs/(row['source'].replace('/','_')+'.o');assert obj.is_file();sources.append(dict(source=row['source'],source_sha256=row['sha256'],object_sha256=hashlib.sha256(obj.read_bytes()).hexdigest()))
plan=dict(status='FROZEN_RESEARCH_ONLY_R_B_LEAF_COMMAND',source_pin=D['source_pin'],old_binary_sha256=hashlib.sha256((R/'.local_agent/leaf-4096-43/fairy-leaf-4096.exe').read_bytes()).hexdigest(),old_uci_sha256=hashlib.sha256(old.read_bytes()).hexdigest(),new_uci_sha256=hashlib.sha256((S/'uci.cpp').read_bytes()).hexdigest(),sources=sources,flags=prior['flags'],compiler_sha256=hashlib.sha256(compiler.read_bytes()).hexdigest(),intervention='Add atomic devauxleafrb R B1..4096 only in experimental build; old devauxleafr remains untouched. Only EvalPieceValue MG/EG bothcolors R/B; native SEE/capture/order/PSQT untouched. OldR/N binary/source immutable. No product/default/UI/primarywrites.',decision='Prepare one-extra-type feasibility after finiteH48 KRN signal; no B price fitting/claim here. KRRNBvKRRNB stock max4R+2B+2N=26016<32000 withN720 andR/B4096; excludesP/Q/drop/promotion/history variants.',timeout_compile=180,timeout_link=90)
(O/'plan.json').write_text(json.dumps(plan,indent=2));start=time.monotonic();obj=B/'uci_override.o';binary=B/'fairy-leaf-rb.exe'
r=subprocess.run([str(compiler),*prior['flags'],'-I',str(base),'-c',str(S/'uci.cpp'),'-o',str(obj)],cwd=R,capture_output=True,text=True,timeout=180);(O/'compile.log').write_text(r.stdout+r.stderr);status='COMPILE_FAILED'
if r.returncode==0:
 objects=[obj if row['source']=='uci.cpp' else objs/(row['source'].replace('/','_')+'.o') for row in prior['sources']]
 r=subprocess.run([str(compiler),*map(str,objects),'-pthread','-static','-o',str(binary)],cwd=R,capture_output=True,text=True,timeout=90);(O/'link.log').write_text(r.stdout+r.stderr);status='COMPLETE' if r.returncode==0 else 'LINK_FAILED'
result=dict(status=status,returncode=r.returncode,seconds=time.monotonic()-start,binary=str(binary.relative_to(R)),binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest() if status=='COMPLETE' else None,old_binary_unchanged=hashlib.sha256((R/'.local_agent/leaf-4096-43/fairy-leaf-4096.exe').read_bytes()).hexdigest()==plan['old_binary_sha256'],old_source_unchanged=hashlib.sha256(old.read_bytes()).hexdigest()==plan['old_uci_sha256'])
(O/'build.json').write_text(json.dumps(result,indent=2));print(result);assert status=='COMPLETE'
