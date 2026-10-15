"""Bounded source/data capsule and source-only independent replay for segment65."""
from pathlib import Path
import json,hashlib,zipfile,subprocess,sys,os,re,xml.etree.ElementTree as ET
def clean(files):
    markers=json.loads(Path('.local_agent/publication_exclusions59.json').read_text(encoding='utf-8-sig'))
    for name,data in files.items():
        assert not name.startswith('.local_agent/') and '..' not in Path(name).parts and not Path(name).is_absolute()
        assert all(value.encode() not in data for marker in markers for value in (marker,marker.replace('\\','/'),json.dumps(marker)[1:-1])),name
        assert not re.search(rb'(?:xox[baprs]-[A-Za-z0-9-]{20,}|sk-[A-Za-z0-9_-]{30,}|-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----)',data),name

OUT=Path('results/dev_aux');HERE=OUT/'task1971'
SOURCE=OUT/'SOURCE_REPRO_20261016_65.zip';EVIDENCE=OUT/'EVIDENCE_20261016_65.zip'
def sha(b):return hashlib.sha256(b).hexdigest()
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def write(p,x):
    with Path(p).open('x',encoding='utf-8') as f:json.dump(x,f,indent=2)
def seal(path,entries,manifest,scope):
    checked={};raw=0
    with zipfile.ZipFile(path,'x',compression=zipfile.ZIP_DEFLATED) as z:
        for name,item in sorted(entries.items()):
            data=item.read_bytes() if isinstance(item,Path) else item
            clean({name:data})
            if name.endswith('.zip'):
                import io
                with zipfile.ZipFile(io.BytesIO(data)) as nested:
                    assert nested.testzip() is None
                    clean({n:nested.read(n) for n in nested.namelist() if not n.endswith('/')})
            checked[name]=dict(bytes=len(data),sha256=sha(data));raw+=len(data);z.writestr(name,data)
        z.writestr(manifest,json.dumps(dict(files=checked,scope=scope),indent=2))
    with zipfile.ZipFile(path) as z:
        assert z.testzip() is None
        for name,row in checked.items():assert sha(z.read(name))==row['sha256']
    return dict(archive=path.as_posix(),files=len(checked),raw_bytes=raw,bytes=path.stat().st_size,sha256=sha(path.read_bytes()),manifest=manifest)
def package():
    assert read(OUT/'task1965/completion.json')['status']=='COMPLETE'
    assert read(OUT/'task1968/completion.json')['status']=='COMPLETE'
    assert read(OUT/'task1974/completion.json')['status']=='COMPLETE'
    assert read(OUT/'task1966/result.json')['status']==read(OUT/'task1969/result.json')['status']=='PASS'
    files={}
    assert sha((OUT/'SOURCE_REPRO_20261016_64.zip').read_bytes())=='381a6cac284d5827a1b38dd89c3ddbc1887f362e1e5958b5d66883174ba7c01a'
    with zipfile.ZipFile(OUT/'SOURCE_REPRO_20261016_64.zip') as z:
        for n in z.namelist():
            if not n.endswith('/') and 'MANIFEST' not in Path(n).name.upper():files[n]=z.read(n)
    evidence={}
    for task in range(1961,1977):
        folder=OUT/f'task{task}'
        for p in folder.rglob('*'):
            if not p.is_file() or '__pycache__' in p.parts or p.suffix not in ('.py','.json','.jsonl','.ini'):continue
            if p.as_posix()=='results/dev_aux/task1971/restore.json':continue
            evidence[p.as_posix()]=p
            if p.suffix in ('.py','.ini'):files[p.as_posix()]=p
            if p.suffix=='.json':
                obj=read(p)
                def pins(x):
                    if isinstance(x,dict):
                        for k,v in x.items():
                            if k=='source_sha' and isinstance(v,dict):
                                for name,digest in v.items():
                                    path=Path(name)
                                    if path.is_file() and not path.is_absolute() and not name.startswith('.local_agent'):
                                        assert sha(path.read_bytes())==digest,(name,p.as_posix())
                                        files[path.as_posix()]=path
                            pins(v)
                    elif isinstance(x,list):
                        for v in x:pins(v)
                pins(obj)
    for name in ('task1822/qualification.json','task1846/qualification.json','task1919/feasibility.json','task1922/feasibility.json','task1933/feasibility.json','task1938/feasibility.json','task1941/feasibility.json'):
        p=OUT/name;files[p.as_posix()]=p
    source=seal(SOURCE,files,'MANIFEST65SOURCE.json','Base64Core/source/testdependencies/GPLNativeSource plus current65executedhelpers and exactpinnedpriordata. ExistingOS/interpreter; no Nativebinary/compiler/privateSlack. Capsules preserve exactexecution bytes; directGit textmaycanonicalizenewlines. No fullNative/proofstudy rerun claimed.')
    ev=seal(EVIDENCE,evidence,'MANIFEST65EVIDENCE.json','Allclosed65coldprobe/twofreshTRAIN_RACE_FULL_DEV/opponentpopulation physicalrecords/Nativejournals/plans/source/failed1964prequalification/corrections. No privateSlack/account/nativebinary. Sealedbeforelatefinalreport/session/QA/delivery/restore, whicharedirectGit.')
    write(OUT/'ARCHIVE_MANIFEST_20261016_65.json',dict(status='SEALED_CRC_ALL_MEMBER_SHA',archives=[source,ev],raw_transport='Newgame andqualification journals remain exactlocal and publicinEVIDENCE65; archive-only avoids duplicatehugeGitblobs. No data erased.',historical_source='SOURCE64 contents reused; pinsrequiredby65 includedexactcurrentworkingbytes. No64study reexecution or oldcap/source rewrite.'))
    print(json.dumps(dict(source=source,evidence=ev)),flush=True)
def restore():
    dest=Path('.local_agent/repro65').resolve();dest.mkdir(exist_ok=False)
    for path,manifest in ((SOURCE,'MANIFEST65SOURCE.json'),(EVIDENCE,'MANIFEST65EVIDENCE.json')):
        with zipfile.ZipFile(path) as z:
            assert z.testzip() is None;m=json.loads(z.read(manifest))
            for name,row in m['files'].items():
                assert not Path(name).is_absolute() and '..' not in Path(name).parts
                data=z.read(name);assert sha(data)==row['sha256'];p=dest/name;p.parent.mkdir(parents=True,exist_ok=True)
                if p.exists():assert p.read_bytes()==data,name
                else:p.write_bytes(data)
    env=dict(os.environ);env.update(PYTHONPATH='',PYTEST_DISABLE_PLUGIN_AUTOLOAD='1',PYTEST_ADDOPTS='')
    common="import sys,pathlib,json,time;root=pathlib.Path.cwd();sys.path.insert(0,str(root/'.venv/Lib/site-packages'));"
    targets=['tests/development/test_generic_session_cached_phase_player.py','tests/development/test_generic_session_proof_bank.py','results/dev_aux/task1965/test_campaign.py']
    boot=common+"import pytest,generic_chess;assert pathlib.Path(pytest.__file__).is_relative_to(root);assert pathlib.Path(generic_chess.__file__).is_relative_to(root);raise SystemExit(pytest.main("+repr(targets+['-q','--basetemp=rechecks/pytest65','--junitxml=tests65.xml'])+"))"
    result=subprocess.run([sys.executable,'-S','-c',boot],cwd=dest,env=env,capture_output=True,timeout=120);(dest/'tests.log').write_bytes(result.stdout+result.stderr)
    assert result.returncode==0,result.stderr.decode(errors='replace')
    xml=ET.parse(dest/'tests65.xml').getroot();suites=list(xml) if xml.tag=='testsuites' else [xml];counts={k:sum(int(s.attrib.get(k,0)) for s in suites) for k in ('tests','failures','errors','skipped')};assert counts==dict(tests=34,failures=0,errors=0,skipped=0)
    replay=common+"start=time.perf_counter();import results.dev_aux.task1966.audit as a;import results.dev_aux.task1969.audit as b;import results.dev_aux.task1970.train_stability as c;import results.dev_aux.task1961.clock_control as d;import results.dev_aux.task1975.audit as e;import results.dev_aux.task1972.cost as f;import results.dev_aux.task1973.mechanism as g;import results.dev_aux.task1976.inventory_cost as h;from results.dev_aux.task1956.physical_audit import audit;mods=[a,b,c,d,e,f,g,h];[(setattr(m,'OUT',root/'rechecks'/str(i)),(root/'rechecks'/str(i)).mkdir(parents=True)) for i,m in enumerate(mods)];a.main();b.main();c.run();d.run();e.main();f.run();g.run();h.run();cold=audit('results/dev_aux/task1962');x=json.loads((a.OUT/'result.json').read_text());y=json.loads((b.OUT/'result.json').read_text());low=json.loads((e.OUT/'result.json').read_text());ps=[v['physical'] for v in x['cohorts']]+[y['physical'],cold,low['physical']];assert all(not getattr(m,'__file__',None) or pathlib.Path(m.__file__).is_relative_to(root) for n,m in sys.modules.items() if n.startswith(('generic_chess','scripts.','results.')));print(json.dumps(dict(status='PASS_ALL65_REPLAY',games=sum(v['games'] for v in ps),moves=sum(v['moves'] for v in ps),native_bindings=sum(v['actual_native'] for v in ps),proof_adopting_actual_wins=sum(v['proof_games'] for v in ps),seconds=time.perf_counter()-start,study_new_Native_or_PN_or_search_calls=0,controlled_clock_real_prover_calls=2)))"
    result=subprocess.run([sys.executable,'-S','-c',replay],cwd=dest,env=env,capture_output=True,timeout=180);(dest/'replay.log').write_bytes(result.stdout+result.stderr)
    assert result.returncode==0,result.stderr.decode(errors='replace');summary=json.loads(result.stdout.decode().splitlines()[-1])
    write(HERE/'restore.json',dict(status='PASS_INDEPENDENT_RESTORE',tests=counts,replay=summary,source_sha256=sha(SOURCE.read_bytes()),evidence_sha256=sha(EVIDENCE.read_bytes()),scope='Newdirectory/Python-S/restoredpuredependencies/modulepathassertions, sameOS/interpreter. Actualcases/Nativehistory/profileACKs/optimizerlocks/TRUEterminals replayed; no newstudyNative/PN/depthsearch. Cachemechanismunit testsandclockcontrol doexecuteactualprovers. No freshmachine/fullNativeexperiment rerun.'))
    print(json.dumps(summary),flush=True)
if __name__=='__main__':{'package':package,'restore':restore}[sys.argv[1]]()
