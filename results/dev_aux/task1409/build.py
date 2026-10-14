from pathlib import Path
import json,hashlib,difflib,subprocess,time
R=Path.cwd();O=R/'results/dev_aux/task1410';O.mkdir(exist_ok=False);B=R/'.local_agent/leaf-rnb-46';S=B/'source';S.mkdir(parents=True,exist_ok=False)
old=R/'.local_agent/leaf-rb-45/source/uci.cpp';source=old.read_text();marker='      else if (token == "devauxleafrb")';assert source.count(marker)==1
new=r'''      else if (token == "devauxleafrnb")
      {
          int rook = 0, knight = 0, bishop = 0;
          is >> rook >> knight >> bishop;
          if (!is || rook < 1 || rook > 4096 || knight < 1 || knight > 1440 || bishop < 1 || bishop > 4096)
              sync_cout << "info string DEV_AUX leafRNB invalid" << sync_endl;
          else
          {
              Search::clear();
              for (Phase phase : {MG, EG})
              {
                  EvalPieceValue[phase][make_piece(WHITE, ROOK)] =
                  EvalPieceValue[phase][make_piece(BLACK, ROOK)] = Value(rook);
                  EvalPieceValue[phase][make_piece(WHITE, KNIGHT)] =
                  EvalPieceValue[phase][make_piece(BLACK, KNIGHT)] = Value(knight);
                  EvalPieceValue[phase][make_piece(WHITE, BISHOP)] =
                  EvalPieceValue[phase][make_piece(BLACK, BISHOP)] = Value(bishop);
              }
              sync_cout << "info string DEV_AUX leafRNB " << int(EvalPieceValue[MG][ROOK])
                        << " " << int(EvalPieceValue[MG][KNIGHT]) << " " << int(EvalPieceValue[MG][BISHOP])
                        << " nativeR " << int(PieceValue[MG][ROOK])
                        << " nativeN " << int(PieceValue[MG][KNIGHT])
                        << " nativeB " << int(PieceValue[MG][BISHOP])
                        << " captureR " << int(CapturePieceValue[MG][ROOK])
                        << " captureN " << int(CapturePieceValue[MG][KNIGHT])
                        << " captureB " << int(CapturePieceValue[MG][BISHOP]) << sync_endl;
          }
      }
'''
changed=source.replace(marker,new+marker);(S/'uci.cpp').write_text(changed);(O/'uci.cpp').write_text(changed)
(O/'leaf_rnb.patch').write_text(''.join(difflib.unified_diff(source.splitlines(True),changed.splitlines(True),fromfile='leaf-rb-45/uci.cpp',tofile='leaf-rnb-46/uci.cpp')))
prior=json.loads((R/'results/dev_aux/task147/build.json').read_bytes());D=json.loads((R/'results/dev_aux/task137/declaration.json').read_bytes());compiler=R/D['compiler_relative'];base=R/'.local_agent/alignment-order/source';objs=R/'.local_agent/alignment-order/objects';sources=[]
for row in prior['sources']:
 p=base/row['source'];assert hashlib.sha256(p.read_bytes()).hexdigest()==row['sha256'];obj=objs/(row['source'].replace('/','_')+'.o');assert obj.is_file();sources.append(dict(source=row['source'],source_sha256=row['sha256'],object_sha256=hashlib.sha256(obj.read_bytes()).hexdigest()))
plan=dict(status='FROZEN_RESEARCH_ONLY_R_N_B_ATOMIC_LEAF_COMMAND',source_pin=D['source_pin'],old_binary_sha256=hashlib.sha256((R/'.local_agent/leaf-rb-45/fairy-leaf-rb.exe').read_bytes()).hexdigest(),old_uci_sha256=hashlib.sha256(old.read_bytes()).hexdigest(),new_uci_sha256=hashlib.sha256((S/'uci.cpp').read_bytes()).hexdigest(),sources=sources,flags=prior['flags'],compiler_sha256=hashlib.sha256(compiler.read_bytes()).hexdigest(),intervention='Add atomic devauxleafrnb R N B. Only EvalPieceValue MG/EG bothcolors. Keep all native SEE/capture/order/PSQT720, oldcommands/binary/source immutable. Own researchonly,no product/default/UI.',decision='Test common leafscore unit scaling with identical ratios and frozen WL policies, sourcefixed214futility andothermargins are not scaled. Not retraining to humanprices or changing pruning.',scope='OnlyKRRNBvKRRNB 4R+2N+2B, R/B<=4096,N<=1440 gives27456<mate32000; noP/Q/promotion/drop/creation. Inputstockverifiedbeforegames.',timeout_compile=180,timeout_link=90)
(O/'plan.json').write_text(json.dumps(plan,indent=2));start=time.monotonic();obj=B/'uci_override.o';binary=B/'fairy-leaf-rnb.exe'
r=subprocess.run([str(compiler),*prior['flags'],'-I',str(base),'-c',str(S/'uci.cpp'),'-o',str(obj)],cwd=R,capture_output=True,text=True,timeout=180);(O/'compile.log').write_text(r.stdout+r.stderr);status='COMPILE_FAILED'
if r.returncode==0:
 objects=[obj if row['source']=='uci.cpp' else objs/(row['source'].replace('/','_')+'.o') for row in prior['sources']]
 r=subprocess.run([str(compiler),*map(str,objects),'-pthread','-static','-o',str(binary)],cwd=R,capture_output=True,text=True,timeout=90);(O/'link.log').write_text(r.stdout+r.stderr);status='COMPLETE' if r.returncode==0 else 'LINK_FAILED'
out=dict(status=status,returncode=r.returncode,seconds=time.monotonic()-start,binary=str(binary.relative_to(R)),binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest() if status=='COMPLETE' else None,old_binary_unchanged=hashlib.sha256((R/'.local_agent/leaf-rb-45/fairy-leaf-rb.exe').read_bytes()).hexdigest()==plan['old_binary_sha256'],old_source_unchanged=hashlib.sha256(old.read_bytes()).hexdigest()==plan['old_uci_sha256'])
(O/'build.json').write_text(json.dumps(out,indent=2));print(out);assert status=='COMPLETE'
