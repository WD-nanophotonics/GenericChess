import json,hashlib,subprocess,time,shutil
from pathlib import Path
R=Path.cwd();O=R/'results/dev_aux/task477';B=R/'.local_agent/yaneura29';assert not (B/'build.json').exists();S=B/'source';base=R/'.local_agent/yaneura26';shutil.copytree(base/'source',S,dirs_exist_ok=True);files=[]
for p in sorted(S.rglob('*')):
 if p.is_file():
  rel=p.relative_to(S);assert p.read_bytes()==(base/'source'/rel).read_bytes();files.append(dict(path=rel.as_posix(),sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
assert len(files)==211
p=S/'engine/yaneuraou-engine/yaneuraou-search.cpp';text=p.read_text(encoding='utf-8');patches=[]
main='''#if defined(DEV_AUX_FUTILITY_TRACE) && defined(EVAL_MATERIAL) && MATERIAL_LEVEL == 1
                    static thread_local unsigned aux_main_trace_count = 0;
                    if (capturedPiece != NO_PIECE && aux_main_trace_count < 64) {
                        ++aux_main_trace_count;
                        sync_cout << "info string auxfutility main alpha " << alpha
                            << " base " << (ss->staticEval + 218 + 223 * lmrDepth + 131 * captHist / 1024)
                            << " value " << futilityValue << " board " << PieceValue[capturedPiece]
                            << " full " << (CapturePieceValue[capturedPiece] + (move.is_promote() ? ProDiffPieceValue[movedPiece] : 0))
                            << " pruned " << (futilityValue <= alpha) << " ply " << ss->ply
                            << " depth " << lmrDepth << " move " << move.to_usi_string()
                            << " sfen " << pos.sfen() << sync_endl;
                    }
#endif
'''
q='''#if defined(DEV_AUX_FUTILITY_TRACE) && defined(EVAL_MATERIAL) && MATERIAL_LEVEL == 1
                static thread_local unsigned aux_q_trace_count = 0;
                if (pos.piece_on(move.to_sq()) != NO_PIECE && aux_q_trace_count < 64) {
                    ++aux_q_trace_count;
                    const Piece aux_victim = pos.piece_on(move.to_sq());
                    sync_cout << "info string auxfutility q alpha " << alpha << " base " << futilityBase
                        << " value " << futilityValue << " board " << PieceValue[aux_victim]
                        << " full " << (CapturePieceValue[aux_victim] + (move.is_promote() ? ProDiffPieceValue[pos.piece_on(move.from_sq())] : 0))
                        << " pruned " << (futilityValue <= alpha) << " ply " << ss->ply
                        << " depth " << 0 << " move " << move.to_usi_string()
                        << " sfen " << pos.sfen() << sync_endl;
                }
#endif
'''
for name,needle,patch in [('main','                    if (futilityValue <= alpha)\n                        continue;',main),('q','				if (futilityValue <= alpha)\n                {',q)]:
 assert text.count(needle)==1,(name,text.count(needle));text=text.replace(needle,patch+needle);patches.append(dict(kind=name,anchor=needle,patch=patch));(O/(name+'_trace.inc')).write_text(patch,encoding='utf-8')
p.write_text(text,encoding='utf-8');decl=dict(question='Does an actual capture-futility branch prune a legal capture whose immediate full board+hand/promotion gain crosses its alpha threshold?',source_pin='c1b80eaa09fe13d5f12b1599d1ae4d53c224de30',base_executable_sha256=hashlib.sha256((base/'yaneura-material1-cold-reuse.exe').read_bytes()).hexdigest(),source_files=files,changed_only=p.relative_to(S).as_posix(),patched_source_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),patches=patches,scope='LoggingONLY, same predicates/numericmargins/return/search. Perprocess64records pertemplate specialization. Main branch mayprecede legality; nativelegal filter required. Q branch afterlegal. ReconstructcurrentSFEN only, notfullsearchedbranchhistory/all-defense value. No default/UI or basebinary changes.',cost='onechanged39-unit object andlink using exactverified cachedotherobjects, expected<30s/300sfuse; no search while467active, later fixedshortcontrols/qualification only. No workers/fees/longrun.');(O/'declaration.json').write_text(json.dumps(decl,indent=2),encoding='utf-8')
old=json.loads((base/'build.json').read_text(encoding='utf-8'));(B/'objects').mkdir();steps=[];reused=[];t0=time.perf_counter()
for j,step in enumerate(old['steps']):
 args=[a.replace(str(base),str(B)) for a in step['args']]
 if step.get('source')=='engine/yaneuraou-engine/yaneuraou-search.cpp':
  args.insert(1,'-DDEV_AUX_FUTILITY_TRACE')
 elif 'source' in step:
  origin=Path(step['args'][-1]);target=Path(args[-1]);assert origin.exists();shutil.copy2(origin,target);assert target.read_bytes()==origin.read_bytes();reused.append(dict(source=step['source'],object_sha256=hashlib.sha256(origin.read_bytes()).hexdigest()));continue
 else:args[-1]=str(B/'yaneura-material1-futility-trace.exe')
 assert time.perf_counter()-t0<300;r=subprocess.run(args,cwd=S,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=180);steps.append(dict(source=step.get('source','link'),args=args,exit_code=r.returncode,stdout=r.stdout,stderr=r.stderr));(B/'build.json').write_text(json.dumps(dict(steps=steps,reused=reused),indent=2),encoding='utf-8');assert r.returncode==0,r.stderr;print('compiled',step.get('source','link'),flush=True)
exe=B/'yaneura-material1-futility-trace.exe';out=dict(seconds=time.perf_counter()-t0,executable_sha256=hashlib.sha256(exe.read_bytes()).hexdigest(),compiler_sha256=hashlib.sha256(Path(old['steps'][0]['args'][0]).read_bytes()).hexdigest(),reused_object_hashes=reused,commands=[dict(args=[a.replace(str(R),'DEV_AUX_ROOT') for a in x['args']],exit_code=x['exit_code'],stdout_sha256=hashlib.sha256(x['stdout'].encode()).hexdigest(),stderr_sha256=hashlib.sha256(x['stderr'].encode()).hexdigest()) for x in steps],scope='buildONLY; no search/qualification/proof claimed');(O/'build_summary.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print('BUILT',out['executable_sha256'],out['seconds'])
