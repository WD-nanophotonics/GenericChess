"""Bounded source/data capsule and source-only independent replay for segment66."""
from pathlib import Path
import json,hashlib,zipfile,subprocess,sys,os,re,xml.etree.ElementTree as ET
def clean(files):
    markers=json.loads(Path('.local_agent/publication_exclusions59.json').read_text(encoding='utf-8-sig'))
    for name,data in files.items():
        assert not name.startswith('.local_agent/') and '..' not in Path(name).parts and not Path(name).is_absolute()
        assert all(value.encode() not in data for marker in markers for value in (marker,marker.replace('\\','/'),json.dumps(marker)[1:-1])),name
        assert not re.search(rb'(?:xox[baprs]-[A-Za-z0-9-]{20,}|sk-[A-Za-z0-9_-]{30,}|-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----)',data),name

OUT=Path('results/dev_aux');HERE=OUT/'task1989'
SOURCE=OUT/'SOURCE_REPRO_20261016_66.zip';EVIDENCE=OUT/'EVIDENCE_20261016_66.zip'
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
    # Every producer must have closed; source/evidence snapshots never race journals.
    assert read(OUT/'task1979/completion.json')['status']=='COMPLETE'
    assert read(OUT/'task1983/completion.json')['status']=='COMPLETE'
    assert read(OUT/'task1994/completion.json')['status']=='COMPLETE'
    assert read(OUT/'task1991/retired-before-start.json')['calls']==0
    selected=read(OUT/'task1985/selection.json')
    if len(selected['confirmation_prices'])>1:assert read(OUT/'task1987/completion.json')['status']=='COMPLETE'
    assert read(OUT/'task1980/result.json')['status']=='PASS'
    files={};evidence={}
    base=OUT/'SOURCE_REPRO_20261016_65.zip'
    assert sha(base.read_bytes())=='9992a3ddffb7d6441959a900178d2c5ac2c6241445aa2efe23476093c65179c1'
    with zipfile.ZipFile(base) as z:
        for n in z.namelist():
            if not n.endswith('/') and 'MANIFEST' not in Path(n).name.upper():files[n]=z.read(n)
    for task in range(1977,1996):
        folder=OUT/f'task{task}'
        for p in folder.rglob('*'):
            if not p.is_file() or '__pycache__' in p.parts or p.suffix not in ('.py','.json','.jsonl','.ini'):continue
            if p.name in ('restore.json',):continue
            evidence[p.as_posix()]=p
            if p.suffix in ('.py','.ini'):files[p.as_posix()]=p
            if p.suffix=='.json':
                obj=read(p)
                def pins(x):
                    if isinstance(x,dict):
                        for k,v in x.items():
                            if k in ('source_sha','all_source_pins') and isinstance(v,dict):
                                for name,digest in v.items():
                                    source=Path(name)
                                    if source.is_file() and not source.is_absolute() and not name.startswith('.local_agent'):
                                        assert sha(source.read_bytes())==digest,(name,p.as_posix())
                                        files[source.as_posix()]=source
                            pins(v)
                    elif isinstance(x,list):
                        for v in x:pins(v)
                pins(obj)
    for name in ('task1963/cohort0/feasibility.json','task1963/cohort1/feasibility.json','task1967/feasibility.json','task1978/cohort0/feasibility.json','task1978/cohort1/feasibility.json','task1895/states.jsonl','task1896/coverage.json'):
        p=OUT/name;files[p.as_posix()]=p
    files['scripts/generic_inventory_proof_transport.py']=Path('scripts/generic_inventory_proof_transport.py')
    source=seal(SOURCE,files,'MANIFEST66SOURCE.json','Prior65 exact Core/testdependencies/GPLsource plus all66 executed code/pins/oldcensus/current input data. No Nativebinary/compiler/privateSlack. SameOS/interpreter; directGit may normalize line endings.')
    ev=seal(EVIDENCE,evidence,'MANIFEST66EVIDENCE.json','All closed66 experiments/plans/source/actual records/Nativejournals/results/retained failures. Late finalreport/session/restore/QA/delivery are directGit outside sealed archives. No unique evidence deleted.')
    write(OUT/'ARCHIVE_MANIFEST_20261016_66.json',dict(status='SEALED_CRC_ALL_MEMBER_SHA',archives=[source,ev],raw_transport='Exact Native journals remain local and publicly archive-only to avoid duplicate huge Git blobs; not erased or excluded by origin.'))
    print(json.dumps(dict(source=source,evidence=ev)),flush=True)
def restore():
    dest=Path('.local_agent/repro66').resolve();dest.mkdir(exist_ok=False);(dest/'rechecks').mkdir()
    for archive,manifest in ((SOURCE,'MANIFEST66SOURCE.json'),(EVIDENCE,'MANIFEST66EVIDENCE.json')):
        with zipfile.ZipFile(archive) as z:
            assert z.testzip() is None;m=json.loads(z.read(manifest))
            for name,row in m['files'].items():
                assert not Path(name).is_absolute() and '..' not in Path(name).parts
                data=z.read(name);assert sha(data)==row['sha256'];p=dest/name;p.parent.mkdir(parents=True,exist_ok=True)
                if p.exists():assert p.read_bytes()==data,name
                else:p.write_bytes(data)
    env=dict(os.environ);env.update(PYTHONPATH='',PYTEST_DISABLE_PLUGIN_AUTOLOAD='1',PYTEST_ADDOPTS='')
    common="import sys,pathlib,json,time;root=pathlib.Path.cwd();sys.path.insert(0,str(root/'.venv/Lib/site-packages'));"
    targets=['tests/development/test_generic_session_cached_phase_player.py','tests/development/test_generic_session_proof_bank.py','results/dev_aux/task1979/test_schedule.py','results/dev_aux/task1981/test_transport.py']
    boot=common+"import pytest,generic_chess;assert pathlib.Path(pytest.__file__).is_relative_to(root);assert pathlib.Path(generic_chess.__file__).is_relative_to(root);raise SystemExit(pytest.main("+repr(targets+['-q','--basetemp=rechecks/pytest66','--junitxml=tests66.xml'])+"))"
    result=subprocess.run([sys.executable,'-S','-c',boot],cwd=dest,env=env,capture_output=True,timeout=120);(dest/'tests.log').write_bytes(result.stdout+result.stderr)
    assert result.returncode==0,result.stderr.decode(errors='replace')
    xml=ET.parse(dest/'tests66.xml').getroot();suites=list(xml) if xml.tag=='testsuites' else [xml];counts={k:sum(int(s.attrib.get(k,0)) for s in suites) for k in ('tests','failures','errors','skipped')};assert counts==dict(tests=50,failures=0,errors=0,skipped=0)
    replay=common+'''start=time.perf_counter()
import shutil
import results.dev_aux.task1980.audit as a
import results.dev_aux.task1982.train_stability as b
import results.dev_aux.task1984.audit_cost as c
import results.dev_aux.task1981.exhaustive as d
import results.dev_aux.task1985.choose as e
import results.dev_aux.task1988.audit as f
import results.dev_aux.task1995.audit as g
import results.dev_aux.task1990.mechanism as h
import results.dev_aux.task1993.root_domination as i
import results.dev_aux.task1988.precision as j
import results.dev_aux.task1985.racing_posthoc as k
import results.dev_aux.task1995.mechanism as l
mods=[a,b,c,d,e,f,g,h,i,j,k,l]
for n,m in enumerate(mods):
 m.OUT=root/'rechecks'/str(n);m.OUT.mkdir()
shutil.copyfile(root/'results/dev_aux/task1981/plan.json',d.OUT/'plan.json')
a.main();b.main();c.check('task1977','probe.json',720);c.check('task1983','filter.json',1440);d.run();e.run();f.run();g.run();h.run();i.run();j.run();k.run();l.run()
x=json.loads((a.OUT/'result.json').read_text());probe=json.loads((c.OUT/'probe.json').read_text());fil=json.loads((c.OUT/'filter.json').read_text());pool=json.loads((f.OUT/'result.json').read_text());sym=json.loads((g.OUT/'result.json').read_text())
ps=[v['physical'] for v in x['cohorts']]+[probe['physical'],fil['physical'],pool['physical'],sym['physical']]
assert all(not getattr(m,'__file__',None) or pathlib.Path(m.__file__).is_relative_to(root) for name,m in sys.modules.items() if name.startswith(('generic_chess','scripts.','results.')))
print(json.dumps(dict(status='PASS_ALL66_REPLAY',games=sum(v['games'] for v in ps),moves=sum(v['moves'] for v in ps),native_bindings=sum(v['actual_native'] for v in ps),proof_adopting_actual_wins=sum(v['proof_games'] for v in ps),census_states=45720,census_edges=208080,seconds=time.perf_counter()-start,study_new_Native_or_PN_or_search_calls=0)))'''
    result=subprocess.run([sys.executable,'-S','-c',replay],cwd=dest,env=env,capture_output=True,timeout=180);(dest/'replay.log').write_bytes(result.stdout+result.stderr)
    assert result.returncode==0,result.stderr.decode(errors='replace');summary=json.loads(result.stdout.decode().splitlines()[-1])
    write(HERE/'restore.json',dict(status='PASS_INDEPENDENT_RESTORE',tests=counts,replay=summary,source_sha256=sha(SOURCE.read_bytes()),evidence_sha256=sha(EVIDENCE.read_bytes()),scope='Newdirectory/Python-S/restoredpuredependencies/modulepathassertions, sameOS/interpreter. Full actualGameRecord/Nativehistory/profiles/locks/physicalterminals and completecensus edges rechecked. No newstudyNative/PN/search or independentfreshmachine/rebuiltNativegameclaims. Proof/cache mechanismunit tests execute actualprovers. All originalresults unchanged.'))
    print(json.dumps(summary),flush=True)
if __name__=='__main__':{'package':package,'restore':restore}[sys.argv[1]]()
