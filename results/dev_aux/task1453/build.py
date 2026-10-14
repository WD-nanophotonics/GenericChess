from pathlib import Path
import json,hashlib,difflib,subprocess,time
R=Path.cwd();O=R/'results/dev_aux/task1454';O.mkdir(exist_ok=False);B=R/'.local_agent/leaf-rnbp-46';S=B/'source';S.mkdir(parents=True,exist_ok=False)
old=R/'.local_agent/leaf-rnb-46/source/uci.cpp';source=old.read_text();marker='      else if (token == "devauxleafrnb")';assert source.count(marker)==1
new=r'''      else if (token == "devauxleafrnbp")
      {
          int rook = 0, knight = 0, bishop = 0, pawn = 0;
          is >> rook >> knight >> bishop >> pawn;
          if (!is || rook < 1 || rook > 4096 || knight < 1 || knight > 1440 || bishop < 1 || bishop > 4096 || pawn < 1 || pawn > 1440)
              sync_cout << "info string DEV_AUX leafRNBP invalid" << sync_endl;
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
                  EvalPieceValue[phase][make_piece(WHITE, PAWN)] =
                  EvalPieceValue[phase][make_piece(BLACK, PAWN)] = Value(pawn);
              }
              sync_cout << "info string DEV_AUX leafRNBP " << int(EvalPieceValue[MG][ROOK])
                        << " " << int(EvalPieceValue[MG][KNIGHT]) << " " << int(EvalPieceValue[MG][BISHOP]) << " " << int(EvalPieceValue[MG][PAWN])
                        << " nativeP " << int(PieceValue[MG][PAWN])
                        << " nativeR " << int(PieceValue[MG][ROOK])
                        << " nativeN " << int(PieceValue[MG][KNIGHT])
                        << " nativeB " << int(PieceValue[MG][BISHOP])
                        << " captureP " << int(CapturePieceValue[MG][PAWN])
                        << " captureR " << int(CapturePieceValue[MG][ROOK])
                        << " captureN " << int(CapturePieceValue[MG][KNIGHT])
                        << " captureB " << int(CapturePieceValue[MG][BISHOP]) << sync_endl;
          }
      }
'''
changed=source.replace(marker,new+marker);(S/'uci.cpp').write_text(changed);(O/'uci.cpp').write_text(changed)
(O/'leaf_rnb.patch').write_text(''.join(difflib.unified_diff(source.splitlines(True),changed.splitlines(True),fromfile='leaf-rnb-46/uci.cpp',tofile='leaf-rnbp-46/uci.cpp')))
prior=json.loads((R/'results/dev_aux/task147/build.json').read_bytes());D=json.loads((R/'results/dev_aux/task137/declaration.json').read_bytes());compiler=R/D['compiler_relative'];base=R/'.local_agent/alignment-order/source';objs=R/'.local_agent/alignment-order/objects';sources=[]
for row in prior['sources']:
 p=base/row['source'];assert hashlib.sha256(p.read_bytes()).hexdigest()==row['sha256'];obj=objs/(row['source'].replace('/','_')+'.o');assert obj.is_file();sources.append(dict(source=row['source'],source_sha256=row['sha256'],object_sha256=hashlib.sha256(obj.read_bytes()).hexdigest()))
plan=dict(status='FROZEN_RESEARCH_ONLY_R_N_B_ATOMIC_LEAF_COMMAND',source_pin=D['source_pin'],old_binary_sha256=hashlib.sha256((R/'.local_agent/leaf-rnb-46/fairy-leaf-rnb.exe').read_bytes()).hexdigest(),old_uci_sha256=hashlib.sha256(old.read_bytes()).hexdigest(),new_uci_sha256=hashlib.sha256((S/'uci.cpp').read_bytes()).hexdigest(),sources=sources,flags=prior['flags'],compiler_sha256=hashlib.sha256(compiler.read_bytes()).hexdigest(),intervention='Add atomic devauxleafrnbp R N B P. Only EvalPieceValue MG/EG bothcolors. Keep all native SEE/capture/order/PSQT720, oldcommands/binary/source immutable. Own researchonly,no product/default/UI.',decision='Prepare pawn leaf axis after completedR/B studies, explicitmechanicalpromotion/EP semantics; no pricelearningyet, no humanfit or pruningchange.',scope='FutureKRNBPvKRNBP 2R2N2B2P, Pawns canpromoteqrbn withQ1664. R/B<=4096,N/P<=1440; fixedoriginal2N remain, allother6actors<=4096 so27456belowmateband31754; no drops/creation/castling. EP+promotion explicitlegality required beforegames.',timeout_compile=180,timeout_link=90)
(O/'plan.json').write_text(json.dumps(plan,indent=2));start=time.monotonic();obj=B/'uci_override.o';binary=B/'fairy-leaf-rnb.exe'
r=subprocess.run([str(compiler),*prior['flags'],'-I',str(base),'-c',str(S/'uci.cpp'),'-o',str(obj)],cwd=R,capture_output=True,text=True,timeout=180);(O/'compile.log').write_text(r.stdout+r.stderr);status='COMPILE_FAILED'
if r.returncode==0:
 objects=[obj if row['source']=='uci.cpp' else objs/(row['source'].replace('/','_')+'.o') for row in prior['sources']]
 r=subprocess.run([str(compiler),*map(str,objects),'-pthread','-static','-o',str(binary)],cwd=R,capture_output=True,text=True,timeout=90);(O/'link.log').write_text(r.stdout+r.stderr);status='COMPLETE' if r.returncode==0 else 'LINK_FAILED'
out=dict(status=status,returncode=r.returncode,seconds=time.monotonic()-start,binary=str(binary.relative_to(R)),binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest() if status=='COMPLETE' else None,old_binary_unchanged=hashlib.sha256((R/'.local_agent/leaf-rnb-46/fairy-leaf-rnb.exe').read_bytes()).hexdigest()==plan['old_binary_sha256'],old_source_unchanged=hashlib.sha256(old.read_bytes()).hexdigest()==plan['old_uci_sha256'])
(O/'build.json').write_text(json.dumps(out,indent=2));print(out);assert status=='COMPLETE'
