"""Run from the DEV_AUX repository root with the eight pinned archives.
Fresh unique ignored output, no source-state/stop/cap reset and no network.
No study producers run. Receipt remains inside the unique replay directory.
"""
from pathlib import Path
import zipfile,json,hashlib,subprocess,sys,os,time,xml.etree.ElementTree as ET
root=Path.cwd();target=root/'.local_agent'/('archive-replay71-'+__import__('uuid').uuid4().hex);assert not target.exists();target.mkdir();start=time.perf_counter();checks=0;unique=set();archives=['SOURCE_REPRO_20261016_70_PUBLIC.zip','EVIDENCE_20261016_70.zip','SOURCE_REPRO_20261016_71.zip','EVIDENCE_20261016_71.zip','TEACHER_CORE_20261016_71.zip','TEACHER_WDL_20261016_71.zip','SOURCE_PIN_SUPPLEMENT_20261016_71.zip','LATE_EVIDENCE_20261016_71.zip']
for name in archives:
 with zipfile.ZipFile(root/'results/dev_aux'/name)as z:
  member=next(n for n in z.namelist()if n.startswith('MANIFEST'));m=json.loads(z.read(member));files=m['files'];files={r['path']:r for r in files}if isinstance(files,list)else files
  for n,row in files.items():
   path=target/n;assert path.resolve().is_relative_to(target.resolve())and not Path(n).is_absolute();path.parent.mkdir(parents=True,exist_ok=True);h=hashlib.sha256()
   existing=None
   if path.exists():
    h0=hashlib.sha256()
    with path.open('rb')as f:
     for b in iter(lambda:f.read(1024*1024),b''):h0.update(b)
    existing=h0.hexdigest()
   if existing==row['sha256']:pass
   else:
    if existing is not None:assert m.get('overrides',{}).get(n)==existing,'undeclaredarchiveoverlay'
    with z.open(n)as f,path.open('wb')as out:
     for b in iter(lambda:f.read(1024*1024),b''):h.update(b);out.write(b)
    assert h.hexdigest()==row['sha256']
   checks+=1;unique.add(n)
 print(name+' extracted/verified',flush=True)
site=str(target/'.venv/Lib/site-packages');env={**os.environ,'PYTHONUTF8':'1','PYTHONPATH':'','PYTEST_DISABLE_PLUGIN_AUTOLOAD':'1'}
tests=['results/dev_aux/task2055/test_schedule.py','results/dev_aux/task2072/test_filter.py','results/dev_aux/task2075/test_numbered_readback.py','results/dev_aux/task2086/test_rank_certificate.py','tests/workflow/test_slack_transport.py','results/dev_aux/task2088/test_provider.py','results/dev_aux/task2100/test_campaign.py','results/dev_aux/task2102/test_semantics.py','results/dev_aux/task2105/test_trigger.py','results/dev_aux/task2115/test_publication_pins.py']
base="import sys;from pathlib import Path;sys.path.insert(0,"+repr(site)+");import generic_chess;assert Path(generic_chess.__file__).resolve().is_relative_to(Path.cwd());"
bootstrap=base+"import pytest;assert Path(pytest.__file__).resolve().is_relative_to(Path.cwd());assert not Path('.replay_tests71_owned').exists();raise SystemExit(pytest.main("+repr(tests+['-q','--basetemp=.replay_tests71_owned','--junitxml=.replay71.xml','--tb=short'])+"))"
for stage,code in [('tests',bootstrap),('replay',base+"from results.dev_aux.task2113.replay import run;run();from results.dev_aux.task2107 import audit;audit.OUT=Path('.replay_output/71/late-pn');audit.OUT.mkdir();audit.run(2100,publication_projection='results/dev_aux/task2115/projection.json');from results.dev_aux.task2114 import history_cursor;history_cursor.OUT=Path('.replay_output/71/late-history');history_cursor.OUT.mkdir();history_cursor.run();assert 'generic_chess.learning.alphasho_bridge'not in sys.modules")]:
 with (target/f'{stage}.log').open('w',encoding='utf-8')as log:r=subprocess.run([sys.executable,'-S','-c',code],cwd=target,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=600)
 if r.returncode:raise RuntimeError(stage+'failed; exactprivate logpreserved')
 print(stage+'PASS',flush=True)
x=ET.parse(target/'.replay71.xml').getroot();suites=[x]if x.tag=='testsuite'else list(x);counts={k:sum(int(s.get(k,0))for s in suites)for k in('tests','errors','failures','skipped')};summary=json.loads((target/'.replay_output/71/summary.json').read_text(encoding='utf-8'));result=dict(status='PASS_NEW_DIRECTORY_ARCHIVE_ONLY_REPLAY',archive_payload_checks=checks,unique_paths=len(unique),archive_names=archives,tests=counts,consumers=summary,seconds=time.perf_counter()-start,scope='FreshGitignoredfolder, ONLYeightreviewedarchives, Python-S/PYTHONPATHempty/actualmodulepathassertions. NoNative/census/train/policycampaign/newcounterfactuals; unitstestsinclude4bounded32nodePNqueriesandrankconstruction. SamehostPython/OS/runtimeunbundled;70purePythontests/noNumPyrequired. ONEunusedbridgepublicationpathprojectionexplicitlyreportedandnotimported; NOTfulloriginalbyteidentity. Threeexisting2068testsimportNumPy-dependentoldfitcode andwereonlyinthelocal71testpass; initialrestorationtrialfailedcollectionbecauseNumPyunbundled,preserved/correctedwithoutsourcechanges. Late2100partialand2114historyconsumersincluded; no original research clocks reset.')
(target/'RESTORE_RECEIPT.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print('REPLAY_RECEIPT='+str(target/'RESTORE_RECEIPT.json'));print(json.dumps(result))
