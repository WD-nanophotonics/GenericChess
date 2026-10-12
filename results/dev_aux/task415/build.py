import json,hashlib,subprocess,time,shutil
from pathlib import Path
R=Path.cwd();O=R/'results/dev_aux/task415';O.mkdir(exist_ok=True);B=R/'.local_agent/yaneura27';assert not B.exists();S=B/'source';shutil.copytree(R/'.local_agent/yaneura26/source',S);base=json.loads((R/'results/dev_aux/task399/build_summary.json').read_text(encoding='utf-8'));verified=[]
for p in sorted(S.rglob('*')):
 if p.is_file():
  rel=p.relative_to(S);old=R/'.local_agent/yaneura26/source'/rel;assert p.read_bytes()==old.read_bytes();verified.append(dict(path=rel.as_posix(),sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
assert len(verified)==211
p=S/'position.cpp';s=p.read_text(encoding='utf-8');i=s.index('    int swap = PieceValue[piece_on(to)] - threshold;');end=s.index('        if (selected == KNIGHT)',i);part=s[i:end];changes=[]
def replace(old,new):
 global part
 assert part.count(old)==1,old
 part=part.replace(old,new);changes.append(dict(old=old,new=new))
replace('    int swap = PieceValue[piece_on(to)] - threshold;','''#if defined(DEV_AUX_HAND_SEE) && defined(EVAL_MATERIAL) && MATERIAL_LEVEL == 1
    int swap = CapturePieceValue[piece_on(to)]
        + ((!drop && m.is_promote()) ? ProDiffPieceValue[piece_on(from)] : 0) - threshold;
#else
    int swap = PieceValue[piece_on(to)] - threshold;
#endif''')
replace('    swap = PieceValue[from_pt] - swap;','''#if defined(DEV_AUX_HAND_SEE) && defined(EVAL_MATERIAL) && MATERIAL_LEVEL == 1
    const PieceType aux_after_from_pt = (!drop && m.is_promote())
        ? PieceType(int(from_pt) + 8) : from_pt;
    swap = CapturePieceValue[aux_after_from_pt] - swap;
#else
    swap = PieceValue[from_pt] - swap;
#endif''')
replace('        int cheapest = 100000000;','''        int cheapest = 100000000;
#if defined(DEV_AUX_HAND_SEE) && defined(EVAL_MATERIAL) && MATERIAL_LEVEL == 1
        const auto& aux_see_prices = CapturePieceValue;
#else
        const auto& aux_see_prices = PieceValue;
#endif''')
replace('PieceValue[pt] < cheapest','aux_see_prices[pt] < cheapest')
replace('cheapest = PieceValue[pt];','cheapest = aux_see_prices[pt];')
replace('swap = PieceValue[selected] - swap','swap = aux_see_prices[selected] - swap')
s=s[:i]+part+s[end:];p.write_text(s,encoding='utf-8');(O/'hand_see.inc').write_text(part,encoding='utf-8')
decl=dict(question='Does board+hand capture and first promotion accounting change finite witnessed SEE predicates and actual scoped search behaviour?',changed_source='position.cpp::see_ge only compileguarded Material1',base_executable_sha256=base['executable_sha256'],fixed_source=base['fixed_source'],base_sources=verified,position_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),changes=changes,scope='capture swing includes captured board+demoted hand; first move promotion and capture-cost of promoted actor; LVA by capture swing. Subsequent recapture promotions still omitted, candidate arbitrary-price LVA not minimax/all-defence proof, no general SEE/strength/default claim',cost='39serial compile/link expected<1min; finite old391witnesses and predeclared sparse exchange cases only first, no newtraining/no olddata rewrite')
(O/'declaration.json').write_text(json.dumps(decl,indent=2),encoding='utf-8');compiler=R/'.local_agent/alignment-build/toolchain/llvm-mingw-20261006-ucrt-x86_64/bin/clang++.exe';old=json.loads((R/'.local_agent/yaneura26/build.json').read_text(encoding='utf-8'));steps=[];t0=time.perf_counter();(B/'objects').mkdir()
for j,step in enumerate(old['steps']):
 args=[a.replace(str(R/'.local_agent/yaneura26'),str(B)) for a in step['args']]
 if step.get('source')=='position.cpp':args.insert(1,'-DDEV_AUX_HAND_SEE')
 if 'source' not in step:args[-1]=str(B/'yaneura-material1-hand-see.exe')
 r=subprocess.run(args,cwd=S,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=180);steps.append(dict(source=step.get('source'),args=args,exit_code=r.returncode,stdout=r.stdout,stderr=r.stderr));(B/'build_progress.json').write_text(json.dumps(steps),encoding='utf-8');assert r.returncode==0,r.stderr;print(j,step.get('source','link'),flush=True)
exe=B/'yaneura-material1-hand-see.exe';out=dict(seconds=time.perf_counter()-t0,executable_sha256=hashlib.sha256(exe.read_bytes()).hexdigest(),compiler_sha256=hashlib.sha256(compiler.read_bytes()).hexdigest(),steps=steps);(B/'build.json').write_text(json.dumps(out,indent=2),encoding='utf-8');pub=dict(seconds=out['seconds'],executable_sha256=out['executable_sha256'],compiler_sha256=out['compiler_sha256'],commands=[dict(args=[a.replace(str(R),'DEV_AUX_ROOT') for a in x['args']],exit_code=x['exit_code'],stdout_sha256=hashlib.sha256(x['stdout'].encode()).hexdigest(),stderr_sha256=hashlib.sha256(x['stderr'].encode()).hexdigest()) for x in steps]);(O/'build_summary.json').write_text(json.dumps(pub,indent=2),encoding='utf-8');print('BUILT',pub['executable_sha256'],pub['seconds'])
