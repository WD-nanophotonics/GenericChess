"""Source/evidence closure with full raw Native logs archived once, source-only restore."""

from pathlib import Path

import json,hashlib,zipfile,subprocess,os,sys,ast,re

from results.dev_aux.task1930.closure import clean,seal

OUT=Path('results/dev_aux');HERE=OUT/'task1958';SOURCE=OUT/'SOURCE_REPRO_20261016_64.zip';EVIDENCE=OUT/'EVIDENCE_20261016_64.zip'

def sha(b):return hashlib.sha256(b).hexdigest()

def package():

 for task in (1936,1939,1942,1943,1944,1947,1948,1954,1955):

  d=json.loads((OUT/f'task{task}/completion.json').read_text());assert d['status'] in ('COMPLETE','GLOBAL_CAP')

 assert json.loads((OUT/'task1952/completion.json').read_text())['status']=='CANCELLED_AGENT_DUPLICATE_IMPLEMENTATION_REVIEW'

 files={}

 with zipfile.ZipFile(OUT/'SOURCE_REPRO_20261016_63.zip') as z:

  manifest=json.loads(z.read('MANIFEST63SOURCE.json'))

  for n,row in manifest['files'].items():

   b=z.read(n);assert sha(b)==row['sha256'];files[n]=b

 for task in range(1936,1961):

  for p in (OUT/f'task{task}').rglob('*'):

   if p.is_file() and p.suffix in ('.py','.ini') and '__pycache__' not in p.parts:files[p.as_posix()]=p.read_bytes()

 native=Path('results/dev_aux/task1831/MATERIAL_ENGINE_SOURCE_59.zip');files[native.as_posix()]=native.read_bytes()

 with zipfile.ZipFile(native) as z:clean({n:z.read(n) for n in z.namelist() if not n.endswith('/')});assert z.testzip() is None

 for n,b in files.items():

  if n.endswith('.py') and any(n.startswith(f'results/dev_aux/task{t}/') for t in range(1936,1961)):ast.parse(b,filename=n)

 evidence={}

 for task in range(1936,1961):

  for p in (OUT/f'task{task}').rglob('*'):

   if p.is_file() and p.suffix in ('.py','.ini','.json','.jsonl') and '__pycache__' not in p.parts and p.as_posix()!='results/dev_aux/task1958/restore.json':evidence[p.as_posix()]=p.read_bytes()

 for n in ['results/dev_aux/task1933/rules.json','results/dev_aux/task1934/inputs.json','results/dev_aux/task1866/unit_panel.py']:

  evidence[n]=Path(n).read_bytes()

 clean(files);clean(evidence)

 source=seal(SOURCE,files,'MANIFEST64SOURCE.json','Current64experimental helpers/17historicalduplicate tests plusbase63Core/27modules313tests andpurePythonpytestdeps. No Nativebinary/compiler/privateSlack/account ormachineXML.1951isretiredduplicate, noadoption. Alloldcodekeptforprovenance; no oldexperimentrerun. Fullscopeddata inEVIDENCE64; currentactualrule/sourcebytes preserved.')

 ev=seal(EVIDENCE,evidence,'MANIFEST64EVIDENCE.json','ALL64full/failed/partialrecords, allactualpolicygames/moves/Nativejournals/sourceplans/qualifications andtransported18certificates.1952cancelled298/696, notcomplete64kcurve. Exactsource/debuggingmistakes/metadataerrataretained. Finalreport/session/QA/delivery sealedlaterasdirectGitmetadata, notinsideZIP. No privateSlack/account/credentials/nativebinary.')

 archival=[n for n,b in evidence.items() if n.endswith('/run/transport.jsonl') and len(b)>8*1024*1024]

 ignore=Path('.gitignore');text=ignore.read_text(encoding='utf-8');text+='\n# Segment64 bulky generated Native journals: exact public bytes in EVIDENCE64.\n'+''.join('/'+n+'\n' for n in archival);ignore.write_text(text,encoding='utf-8')

 manifest=dict(status='SEALED_CRC_ALL_MEMBER_SHA',archives=[source,ev],archived_only_native_journals=[dict(path=n,bytes=len(evidence[n]),sha256=sha(evidence[n])) for n in archival],scope='Archive-only logs are PUBLIC project evidence, notprivate/sensitivityexclusions. Exactworkingfilesremain; explicitGitignoreavoidsduplicatingbulkylogs inhistory. Restorehydratesallrelativepaths. No uniqueevidencedeletion. Smallrecords/source/reportsdirectGit, ALLrawrecordsdownloadableanonymousZIP.')

 (OUT/'ARCHIVE_MANIFEST_20261016_64.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8');print(json.dumps(dict(source=source,evidence=ev,archive_only_logs=len(archival))))

def restore():

 root=Path('.local_agent/repro64').resolve();root.mkdir(exist_ok=False);manifests=[]

 for path,mname in [(SOURCE,'MANIFEST64SOURCE.json'),(EVIDENCE,'MANIFEST64EVIDENCE.json')]:

  with zipfile.ZipFile(path) as z:

   assert z.testzip() is None;m=json.loads(z.read(mname));manifests.append(m)

   for name,row in m['files'].items():

    rel=Path(name);assert not rel.is_absolute() and not rel.drive and '..' not in rel.parts;b=z.read(name);assert sha(b)==row['sha256'];p=root/rel;p.parent.mkdir(parents=True,exist_ok=True)

    if p.exists():assert p.read_bytes()==b

    else:p.write_bytes(b)

 targets=sorted(n for n in manifests[0]['files'] if n.startswith('tests/development/test_') and n.endswith('.py'));assert len(targets)==27;targets+=['results/dev_aux/task1951/test_check_first.py']

 env=dict(os.environ);env.update(PYTHONPATH='',PYTEST_DISABLE_PLUGIN_AUTOLOAD='1',PYTEST_ADDOPTS='',PYTHONIOENCODING='utf-8')

 boot="import sys,pathlib;root=pathlib.Path.cwd();sys.path[:0]=[str(root/'.venv/Lib/site-packages'),str(root/'tests'),str(root/'tests/development')];import pytest,generic_chess;assert pathlib.Path(pytest.__file__).is_relative_to(root);assert pathlib.Path(generic_chess.__file__).is_relative_to(root);code=pytest.main("+repr(targets+['-q','--junitxml=restored-tests.xml'])+");assert all(not getattr(m,'__file__',None) or pathlib.Path(m.__file__).is_relative_to(root) for n,m in sys.modules.items() if n.startswith(('generic_chess','scripts.','results.','_pytest','pytest')));raise SystemExit(code)"

 proc=subprocess.run([sys.executable,'-S','-c',boot],cwd=root,env=env,capture_output=True,timeout=120);(root/'tests.log').write_bytes(proc.stdout+proc.stderr)

 import xml.etree.ElementTree as ET

 xml=ET.parse(root/'restored-tests.xml').getroot();suites=list(xml) if xml.tag=='testsuites' else [xml];counts={k:sum(int(s.attrib.get(k,0)) for s in suites) for k in ['tests','failures','errors','skipped']};assert proc.returncode==0 and counts==dict(tests=330,failures=0,errors=0,skipped=0),counts

 replay=r"""import sys,pathlib,json,time

root=pathlib.Path.cwd();sys.path.insert(0,str(root/'.venv/Lib/site-packages'));start=time.perf_counter()

from results.dev_aux.task1956.physical_audit import audit

studies={str(t):audit('results/dev_aux/task'+str(t)) for t in (1939,1943,1944,1948,1954,1955)}

import results.dev_aux.task1945.audit as learning

import results.dev_aux.task1953.audit as factorial

import results.dev_aux.task1956.budget_analysis as budget

import results.dev_aux.task1956.horizon_analysis as horizon

import results.dev_aux.task1937.audit as leaves

import results.dev_aux.task1949.audit as deep

import results.dev_aux.task1950.audit as divergence

import results.dev_aux.task1957.offline_racing as racing

import results.dev_aux.task1959.sensitivity as sensitivity

for name,module in [('learning',learning),('factorial',factorial),('budget',budget),('horizon',horizon),('leaves',leaves),('deep',deep),('divergence',divergence),('racing',racing),('sensitivity',sensitivity)]:

 module.O=root/'rechecks'/name;module.O.mkdir(parents=True);module.run()

from generic_chess.rules.compiler import compile_ruleset_for_execution

from generic_chess.rules.serialization import deserialize_ruleset

from generic_chess.session.result import SessionStatus

from scripts.generic_session_certificate_json import decode_session_certificate

from scripts.generic_session_win_proof import SessionStrategyCursor

plan=json.loads((root/'results/dev_aux/task1952/plan.json').read_text());proofs=0

for path in sorted((root/'results/dev_aux/task1952').glob('certificate-*.json')):

 q=int(path.stem.split('-')[-1]);case=plan['queries'][q];c=compile_ruleset_for_execution(deserialize_ruleset((root/case['rules']).read_text()));s,cert=decode_session_certificate(c,json.loads(path.read_text()));cursor=SessionStrategyCursor(s,cert,max_nodes=262144,seconds=5.)

 while s.result.status is SessionStatus.ONGOING:

  old=cursor.node.rank;choice=cursor.choose(s) if s.state.position.side_to_move==cert.target else cursor.node.edges[0][0];cursor.commit(s,choice);assert cursor.node.rank<old

 assert s.result.winner==cert.target;proofs+=1

assert proofs==18

assert all(not getattr(m,'__file__',None) or pathlib.Path(m.__file__).is_relative_to(root) for n,m in sys.modules.items() if n.startswith(('generic_chess','scripts.','results.')))

print(json.dumps(dict(status='PASS_ALL_ARCHIVED64_REPLAYS',games=sum(v['games'] for v in studies.values()),moves=sum(v['moves'] for v in studies.values()),native_committed_bindings=sum(v['actual_native'] for v in studies.values()),proof_adopting_physical_wins=sum(v['proof_games'] for v in studies.values()),all_main_studies_complete=all(v['full_study_complete'] for v in studies.values()),transported_strategies_reverified_and_physically_executed=proofs,public_leaf_records=9541,literal_leaf_edges=46098,new_study_search_or_Native_calls=0,seconds=time.perf_counter()-start)))

"""

 proc=subprocess.run([sys.executable,'-S','-c',replay],cwd=root,env=env,capture_output=True,timeout=240);(root/'replay.log').write_bytes(proc.stdout+proc.stderr);assert proc.returncode==0,proc.stderr.decode(errors='replace');rr=json.loads(proc.stdout.decode().splitlines()[-1]);out=dict(status='PASS_SOURCE_ONLY_INDEPENDENT_RESTORE',tests=counts,replay=rr,source_sha256=sha(SOURCE.read_bytes()),evidence_sha256=sha(EVIDENCE.read_bytes()),scope='Newignoredroot/Python-S/restoredpurepytestdeps/modulepathchecks, sharedOS/interpreter/Corecompiler, notfreshmachine/newNativeexperiment. Unitmechanismtestsdoexecuteprovers; studyreplaydoesnotrerunNative/PN/depthsearch. Allpolicyphysicaledges/fullhistories/priceACKs/caps/strategyranks rechecked.18transportedproofs actualall-defenseverification+canonicaldefenseexecution, notall defensesphysicallyplayed.1951duplicateisretired;330testsnotendorsementofadoption.')

 (HERE/'restore.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps(out))

if __name__=='__main__':{'package':package,'restore':restore}[sys.argv[1]]()
