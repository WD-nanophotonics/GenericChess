import json,hashlib,time,subprocess,shutil,difflib,os
from pathlib import Path
R=Path.cwd();O=R/'results/dev_aux/task611';O.mkdir(exist_ok=True);S=R/'.local_agent/yaneura27/source';P=R/'.local_agent/yaneura33_capture';assert P.resolve().is_relative_to(R.resolve()) and not P.exists();start=time.monotonic();P.mkdir();shutil.copytree(S,P/'source');(P/'objects').mkdir();original={p.relative_to(S).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in S.rglob('*') if p.is_file()};B=json.loads((R/'.local_agent/yaneura27/build.json').read_bytes())
header='''#ifndef DEV_AUX_CAPTURE_DIAG_H
#define DEV_AUX_CAPTURE_DIAG_H
#include <cstdint>
#include <cstdlib>
namespace YaneuraOu { namespace AuxCaptureDiag {
inline const bool GainMode = [](){const char* v=std::getenv("DEV_AUX_CAPTURE_GAIN_MODE");if(!v || (v[0]=='0' && !v[1]))return false;if(v[0]=='1' && !v[1])return true;std::exit(2);return false;}();
inline std::uint64_t C[7]={};
inline void reset(){for(auto& x:C)x=0;}
inline void record(int oldValue,int newValue,int alpha,int oldGain,int newGain){++C[0];C[1]+=oldValue<=alpha;C[2]+=newValue<=alpha;C[3]+=(oldValue<=alpha && newValue>alpha);C[4]+=(oldValue>alpha && newValue<=alpha);C[5]+=newGain>oldGain;C[6]+=newGain<oldGain;}
}}
#endif
''';(P/'source/aux_capture_diag.h').write_text(header,encoding='utf-8')
changes=[]
path='engine/yaneuraou-engine/yaneuraou-search.cpp';target=P/'source'/path;old=target.read_text(encoding='utf-8');new='#include "../../aux_capture_diag.h"\n'+old;needle='''Value futilityValue = ss->staticEval + 218 + 223 * lmrDepth
                                        + PieceValue[capturedPiece] + 131 * captHist / 1024;''';assert new.count(needle)==1;replacement='''const int auxOldGain = int(PieceValue[capturedPiece]);
                    const int auxNewGain = int(CapturePieceValue[capturedPiece])
                        + (move.is_promote() ? int(ProDiffPieceValue[pos.piece_on(move.from_sq())]) : 0);
                    const Value auxCommon = ss->staticEval + 218 + 223 * lmrDepth + 131 * captHist / 1024;
                    const Value auxOldValue = auxCommon + auxOldGain;
                    const Value auxNewValue = auxCommon + auxNewGain;
                    AuxCaptureDiag::record(auxOldValue,auxNewValue,alpha,auxOldGain,auxNewGain);
                    Value futilityValue = AuxCaptureDiag::GainMode ? auxNewValue : auxOldValue;''';new=new.replace(needle,replacement);target.write_text(new,encoding='utf-8');changes+=list(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='a/'+path,tofile='b/'+path))
path='usi.cpp';target=P/'source'/path;old=target.read_text(encoding='utf-8');new='#include "aux_capture_diag.h"\n'+old;needle='Search::LimitsType limits = parse_limits(is);';assert new.count(needle)==1;new=new.replace(needle,needle+'\n    AuxCaptureDiag::reset();');needle='else if (token == "auxprices") {';assert new.count(needle)==1;command='''else if (token == "auxcapture") {
        sync_cout << "info string auxcapture " << int(AuxCaptureDiag::GainMode);
        for(auto x:AuxCaptureDiag::C) std::cout << " " << x;
        std::cout << sync_endl;
    }
    ''';new=new.replace(needle,command+needle);target.write_text(new,encoding='utf-8');changes+=list(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='a/'+path,tofile='b/'+path))
(O/'capture_diag.patch').write_text(''.join(changes),encoding='utf-8');(O/'aux_capture_diag.h').write_text(header,encoding='utf-8');plan=dict(question='ONEcapturegainprojection channel: actualfutilitydecisions andshortpairedgoals, unchangedleaf/SEE/order/fullhistory',original_executable_sha256=B['executable_sha256'],original_source_sha256=original,modified_only=['usi.cpp','engine/yaneuraou-engine/yaneuraou-search.cpp','aux_capture_diag.h'],counter_fields=['eligible','old_pruned','new_pruned','rescued_by_new','newly_pruned_by_new','new_gain_larger','new_gain_smaller'],thread_constraint='Threads1 actualadapter; counters resetbeforego/readonly afterbestmove, no worker/concurrentcounterreader',build_fuse_seconds=180,expected_cost='Originalfull39object buildabout38s; newprivateprototypeexpectedunder1min, no product/default/UI modifications oroldsourceoverwrite',scope='Samecounterbinaryruntime0old/1hand+promotion ONEfutilitygain; source arithmeticcommon/add remainsalgebraicallysame mode0. Otherchannels untouched. Fullwarmqualification requiredbeforeexperiment, no debugginglabels/humanprices fitness.');(O/'declaration.json').write_text(json.dumps(plan,indent=2),encoding='utf-8');steps=[]
for i,step in enumerate(B['steps']):
 assert time.monotonic()-start<180;args=[a.replace(str(R/'.local_agent/yaneura27/objects'),str(P/'objects')).replace(str(R/'.local_agent/yaneura27/yaneura-material1-hand-see.exe'),str(P/'yaneura-capture-diag.exe')) for a in step['args']];t=time.monotonic();proc=subprocess.run(args,cwd=P/'source',capture_output=True,text=True,timeout=max(1,180-(time.monotonic()-start)));steps.append(dict(source=step['source'],exit_code=proc.returncode,seconds=time.monotonic()-t,stdout=proc.stdout,stderr=proc.stderr));(P/'build_progress.json').write_text(json.dumps(dict(steps=steps,seconds=time.monotonic()-start),indent=2),encoding='utf-8');assert proc.returncode==0,(step['source'],proc.stderr[-3000:]);print('compile',i,step['source'],round(time.monotonic()-start,1),flush=True)
assert all(hashlib.sha256((S/path).read_bytes()).hexdigest()==h for path,h in original.items());exe=P/'yaneura-capture-diag.exe';result=dict(status='BUILT_PRIVATE_ONLY',executable_sha256=hashlib.sha256(exe.read_bytes()).hexdigest(),original_source_unchanged=True,seconds=time.monotonic()-start,compile_steps=len(steps),steps=[{k:s[k] for k in ['source','exit_code','seconds']} for s in steps],prototype_source_sha256={p.relative_to(P/'source').as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in (P/'source').rglob('*') if p.is_file()},no_go_yet=True,scope=plan['scope']);(O/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print('BUILD_COMPLETE',round(result['seconds'],3),result['executable_sha256'])