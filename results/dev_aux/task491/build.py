import json,hashlib,subprocess,time,shutil,re
from pathlib import Path
R=Path.cwd();O=R/'results/dev_aux/task491';B=R/'.local_agent/yaneura31';assert not (B/'build.json').exists();base=R/'.local_agent/yaneura27';S=B/'source';shutil.copytree(base/'source',S,dirs_exist_ok=True);files=[]
for p in sorted(S.rglob('*')):
 if p.is_file():
  rel=p.relative_to(S);assert p.read_bytes()==(base/'source'/rel).read_bytes();files.append(dict(path=rel.as_posix(),sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
assert len(files)==211;p=S/'engine/yaneuraou-engine/yaneuraou-search.cpp';s=p.read_text(encoding='utf-8');original=s;changes=[]
def replace(old,new):
 global s
 if s.count(old)==0:
  pattern='\n'.join('[ \t]*'+re.escape(line.lstrip(' \t')) for line in old.split('\n'));matches=list(re.finditer(pattern,s));assert len(matches)==1,(old[:70],len(matches));old=matches[0].group(0)
 assert s.count(old)==1,(old[:70],s.count(old));s=s.replace(old,new);changes.append(dict(old=old,new=new))
anchor='using namespace Eval;  // Eval::PieceValue';helper='''
#if defined(DEV_AUX_FIRST_FUTILITY) && defined(EVAL_MATERIAL) && MATERIAL_LEVEL == 1
namespace {
thread_local bool aux_first_effect_seen = false;
bool aux_full_capture_mode() {
    static const bool mode = [] { const char* p = std::getenv("DEV_AUX_CAPTURE_FUTILITY_MODE"); return p && std::string(p) == "1"; }();
    return mode;
}
}
#endif
''';replace(anchor,anchor+helper)
# Each move-loop gets local tracking, with no dependence on log line indices.
loop='    while ((move = mp.next_move()) != Move::none())\n    {';assert s.count(loop)==2
newloop=loop+'''
#if defined(DEV_AUX_FIRST_FUTILITY) && defined(EVAL_MATERIAL) && MATERIAL_LEVEL == 1
        bool aux_watch_move = false;
        const Value aux_entry_alpha = alpha, aux_entry_beta = beta;
#endif
''';s=s.replace(loop,newloop);changes.append(dict(old=loop,new=newloop,multiplicity=2))
for kind,needle in [('main','                    Value futilityValue = ss->staticEval + 218 + 223 * lmrDepth'),('q','                Value futilityValue = futilityBase +')]:
 i=s.index(needle);j=s.index(';',i)+1;old=s[i:j];full=old.replace('PieceValue[capturedPiece]','(CapturePieceValue[capturedPiece] + ((!move.is_drop() && move.is_promote()) ? ProDiffPieceValue[pos.piece_on(move.from_sq())] : 0))') if kind=='main' else old.replace('PieceValue[pos.piece_on(move.to_sq())]','(CapturePieceValue[pos.piece_on(move.to_sq())] + ((!move.is_drop() && move.is_promote()) ? ProDiffPieceValue[pos.piece_on(move.from_sq())] : 0))');alt=full.replace('Value futilityValue','const Value aux_full_value');effect='(aux_old_value <= alpha) != (aux_full_value <= alpha)' if kind=='main' else '((aux_old_value <= alpha) != (aux_full_value <= alpha)) || ((aux_old_value <= alpha) && (aux_full_value <= alpha) && std::max(bestValue, aux_old_value) != std::max(bestValue, aux_full_value))';depth='lmrDepth' if kind=='main' else '0'
 code=old+'''\n#if defined(DEV_AUX_FIRST_FUTILITY) && defined(EVAL_MATERIAL) && MATERIAL_LEVEL == 1
                    const Value aux_old_value = futilityValue;
'''+alt+'''
                    if (aux_full_capture_mode()) futilityValue = aux_full_value;
                    if (!aux_first_effect_seen && ('''+effect+''')) {
                        aux_first_effect_seen = true; aux_watch_move = true;
                        sync_cout << "info string auxfirst event phase '''+kind+''' alpha " << alpha << " beta " << beta
                            << " old " << aux_old_value << " full " << aux_full_value << " best " << bestValue
                            << " mode " << aux_full_capture_mode() << " ply " << ss->ply << " depth " << '''+depth+'''
                            << " move " << move.to_usi_string() << " sfen " << pos.sfen() << sync_endl;
                    }
#endif
''';replace(old,code)
log=lambda outcome:'''#if defined(DEV_AUX_FIRST_FUTILITY) && defined(EVAL_MATERIAL) && MATERIAL_LEVEL == 1
                    if (aux_watch_move) sync_cout << "info string auxfirst outcome '''+outcome+'''" << sync_endl;
#endif
'''
replace('                    if (futilityValue <= alpha)\n                        continue;', '                    if (futilityValue <= alpha)\n                    {\n'+log('futility_prune')+'                        continue;\n                    }')
replace('\t\t\t\tif (futilityValue <= alpha)\n                {\n                    bestValue = std::max(bestValue, futilityValue);','\t\t\t\tif (futilityValue <= alpha)\n                {\n'+log('futility_prune')+'                    bestValue = std::max(bestValue, futilityValue);')
replace('                    && !pos.see_ge(move, -margin))\n                    continue;','                    && !pos.see_ge(move, -margin))\n                {\n'+log('SEE_prune')+'                    continue;\n                }')
replace('\t\t\t\tif (!pos.see_ge(move, alpha - futilityBase))\n                {','\t\t\t\tif (!pos.see_ge(move, alpha - futilityBase))\n                {\n'+log('SEE_prune'))
replace('            if (!capture)\n                continue;','            if (!capture)\n            {\n'+log('noncapture_prune')+'                continue;\n            }')
replace('            if (!pos.see_ge(move, -73))\n                continue;','            if (!pos.see_ge(move, -73))\n            {\n'+log('SEE_prune')+'                continue;\n            }')
# Existing do_move calls may also occur in probcut; restrict main Step16 and q Step7 anchors.
for kind,needle in [('main','        do_move(pos, move, st, givesCheck, ss);\n\n        // Add extension to new depth'),('q','        do_move(pos, move, st, givesCheck, ss);\n\n        value = -qsearch<nodeType, ReadTT>')]:
 replace(needle,log('recursive_enter')+needle)
for kind,needle in [('main','\t\tundo_move(pos, move);\n\n\t\tASSERT_LV3(-VALUE_INFINITE < value && value < VALUE_INFINITE);'),('q','        undo_move(pos, move);\n\n\t\tASSERT_LV3(-VALUE_INFINITE < value && value < VALUE_INFINITE);')]:
 code='''#if defined(DEV_AUX_FIRST_FUTILITY) && defined(EVAL_MATERIAL) && MATERIAL_LEVEL == 1
        if (aux_watch_move) sync_cout << "info string auxfirst return value " << value
            << " alpha " << aux_entry_alpha << " beta " << aux_entry_beta
            << " stopped " << threads.stop.load(std::memory_order_relaxed) << sync_endl;
#endif
''';replace(needle,code+needle)
p.write_text(s,encoding='utf-8');decl=dict(question='At the first causallyaffected futility branch, does thresholdcrossing reach recursion orlaterpruning?',source_pin='c1b80eaa09fe13d5f12b1599d1ae4d53c224de30',source_files=files,changed_only=p.relative_to(S).as_posix(),patched_source_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),changes=changes,base_executable_sha256=hashlib.sha256((base/'yaneura-material1-hand-see.exe').read_bytes()).hexdigest(),scope='Singleexperimentalbinary MODE0board/MODE1fullcapture, firstglobalworker effect includes qbestValue accumulator change when bothfutilityprune. Completeposition/side viaSFEN, move/kind/depth/alpha/beta/ply beforefirststateeffect; latertrace notpairedbyline. Outcome futility/SEE/noncapture/recursiveenter, localwindow return/stopped. Loggingqualification againstunchangedhand/full binaries needed. Quietpromotion included. No stable continuation/alltree bound/value/humanproof.',cost='onechangedsearchunit+link/38verifiedcachedhand objects, expected<30s/300sfuse; later64shortmodequeries +64actualunchangedbinary qualification (128go), expected<20s/180sfuse. No games/fit yet, nofees/workers.');(O/'declaration.json').write_text(json.dumps(decl,indent=2),encoding='utf-8');old=json.loads((base/'build.json').read_text(encoding='utf-8'));(B/'objects').mkdir();reused=[];steps=[];t0=time.perf_counter()
for step in old['steps']:
 args=[a.replace(str(base),str(B)) for a in step['args']]
 if step.get('source')=='engine/yaneuraou-engine/yaneuraou-search.cpp':args.insert(1,'-DDEV_AUX_FIRST_FUTILITY')
 elif step.get('source'):
  src=Path(step['args'][-1]);dst=Path(args[-1]);assert src.exists();shutil.copy2(src,dst);assert src.read_bytes()==dst.read_bytes();reused.append(dict(source=step['source'],object_sha256=hashlib.sha256(src.read_bytes()).hexdigest()));continue
 else:args[-1]=str(B/'yaneura-material1-first-futility.exe')
 assert time.perf_counter()-t0<300;r=subprocess.run(args,cwd=S,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=180);steps.append(dict(source=step.get('source','link'),args=args,exit_code=r.returncode,stdout=r.stdout,stderr=r.stderr));(B/'build.json').write_text(json.dumps(dict(steps=steps,reused=reused)),encoding='utf-8');assert r.returncode==0,r.stderr;print('compiled',step.get('source','link'),flush=True)
exe=B/'yaneura-material1-first-futility.exe';out=dict(seconds=time.perf_counter()-t0,executable_sha256=hashlib.sha256(exe.read_bytes()).hexdigest(),reused_object_hashes=reused,compiler_sha256=hashlib.sha256(Path(old['steps'][0]['args'][0]).read_bytes()).hexdigest(),commands=[dict(args=[a.replace(str(R),'DEV_AUX_ROOT') for a in x['args']],exit_code=x['exit_code'],stdout_sha256=hashlib.sha256(x['stdout'].encode()).hexdigest(),stderr_sha256=hashlib.sha256(x['stderr'].encode()).hexdigest()) for x in steps],scope='buildONLY, behaviour/contextqualification pending');(O/'build_summary.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print('BUILT',out['executable_sha256'],out['seconds'])
