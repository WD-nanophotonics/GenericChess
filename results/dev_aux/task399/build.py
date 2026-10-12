import json,hashlib,subprocess,re,time,shutil
from pathlib import Path
R=Path.cwd();O=R/'results/dev_aux/task399';O.mkdir(exist_ok=True);B=R/'.local_agent/yaneura26';assert not B.exists();S=B/'source';S.mkdir(parents=True);manifest=json.loads((R/'results/dev_aux/task374/source_manifest.json').read_text(encoding='utf-8'));changed={x['path']:x for x in manifest['changed_files']};copied=[]
for row in manifest['files']:
 rel=Path(row['path']).relative_to('source');p=R/'.local_agent/yaneura25/source'/rel;expected=changed.get(row['path'],{}).get('patched_sha256',row['sha256']);assert hashlib.sha256(p.read_bytes()).hexdigest()==expected,row['path'];q=S/rel;q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(p.read_bytes());copied.append(dict(path=rel.as_posix(),base_patched_sha256=expected))
p=R/'.local_agent/yaneura25/source/aux_material.h';assert hashlib.sha256(p.read_bytes()).hexdigest()==manifest['added_header_sha256'];(S/'aux_material.h').write_bytes(p.read_bytes())
p=S/'engine/yaneuraou-engine/yaneuraou-search.cpp';s=p.read_text(encoding='utf-8');needle='    resize_threads();';assert s[s.index('void YaneuraOuEngine::isready()'):s.index('void YaneuraOuEngine::clear()')].count(needle)==1;patch='''#if defined(DEV_AUX_COLD_REUSE) && defined(EVAL_MATERIAL) && MATERIAL_LEVEL == 1
    // DEV_AUX scoped single-Engine/fixed-option experiment; retain cold TT/history resets.
    static bool aux_previous_scoped_ready = false;
    const bool aux_scoped_ready = size_t(options["Threads"]) == 1
        && size_t(options["USI_Hash"]) == 16
        && std::string(options["NumaPolicy"]) == "auto"
        && std::string(options["BookFile"]) == "no_book";
    if (aux_previous_scoped_ready && aux_scoped_ready && threads.size() == 1) {
        threads.wait_for_search_finished();
        threads.clear(); // fills worker/shared histories, without invalidating shared references
    } else
        resize_threads();
    aux_previous_scoped_ready = aux_scoped_ready;
#else
    resize_threads();
#endif''';i=s.index(needle,s.index('void YaneuraOuEngine::isready()'));s=s[:i]+patch+s[i+len(needle):];p.write_text(s,encoding='utf-8');(O/'cold_reuse.inc').write_text(patch,encoding='utf-8')
compiler=R/'.local_agent/alignment-build/toolchain/llvm-mingw-20261006-ucrt-x86_64/bin/clang++.exe';base=json.loads((R/'results/dev_aux/task358/build.json').read_text(encoding='utf-8'));sources=[x['source'] for x in base['steps'] if 'source' in x];assert len(sources)==39;flags=['-std=c++17','-fno-exceptions','-fno-rtti','-O3','-ffast-math','-DNDEBUG','-DNO_EXCEPTIONS','-DUNICODE','-DYANEURAOU_ENGINE_MATERIAL','-DMATERIAL_LEVEL=1','-DUSE_SSE2','-msse2','-DTARGET_CPU="SSE2"','-Wno-unused-parameter','-fno-threadsafe-statics'];objdir=B/'objects';objdir.mkdir();objects=[];steps=[];start=time.perf_counter()
for i,src in enumerate(sources):
 obj=objdir/f'{i}.o';args=[str(compiler),*(['-DDEV_AUX_NO_READY_KEEPALIVE'] if src=='usi.cpp' else []),*(['-DDEV_AUX_COLD_REUSE'] if src=='engine/yaneuraou-engine/yaneuraou-search.cpp' else []),*flags,'-c',src,'-o',str(obj)];r=subprocess.run(args,cwd=S,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=180);steps.append(dict(source=src,args=args,exit_code=r.returncode,stdout=r.stdout,stderr=r.stderr));(B/'build_progress.json').write_text(json.dumps(steps,indent=2),encoding='utf-8');assert r.returncode==0,r.stderr;objects.append(str(obj));print(i,src,flush=True)
exe=B/'yaneura-material1-cold-reuse.exe';args=[str(compiler),*objects,'-static','-lpthread','-fuse-ld=lld','-Wl,--stack,25000000','-o',str(exe)];r=subprocess.run(args,cwd=S,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=180);steps.append(dict(args=args,exit_code=r.returncode,stdout=r.stdout,stderr=r.stderr));assert r.returncode==0,r.stderr;raw=dict(steps=steps,seconds=time.perf_counter()-start,executable_sha256=hashlib.sha256(exe.read_bytes()).hexdigest());(B/'build.json').write_text(json.dumps(raw,indent=2),encoding='utf-8')
summary=dict(seconds=raw['seconds'],units=len(sources),executable_sha256=raw['executable_sha256'],base_executable_sha256='9741bfd2670d015997a4b10f64595b2874e87c299e49e91edced31be6f647843',fixed_source=manifest['pin'],compiler_sha256=hashlib.sha256(compiler.read_bytes()).hexdigest(),commands=[dict(args=[a.replace(str(R),'${DEV_AUX_ROOT}') for a in step['args']],exit_code=step['exit_code'],stdout_sha256=hashlib.sha256(step['stdout'].encode()).hexdigest(),stderr_sha256=hashlib.sha256(step['stderr'].encode()).hexdigest()) for step in steps],base_sources=copied,added_header_sha256=manifest['added_header_sha256'],new_search_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),patch_sha256=hashlib.sha256((O/'cold_reuse.inc').read_bytes()).hexdigest(),scope='freshprivate211file verified base copy; serial39unit build; reuse worker ONLY scoped Material1/Threads1/Hash16/Numaauto/nobook/singleEngine unchangedoption driver. TTclear/sharedworkerhistoryclear/engine managerclear/fullhistory positions retain. Experimental-only; no oldbinary/source/controller/default change; behaviourqualification pending. Rawabsolute buildrecords private')
(O/'build_summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8');print('BUILT',summary['executable_sha256'],summary['seconds'],flush=True)