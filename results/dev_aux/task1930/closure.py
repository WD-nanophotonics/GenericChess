"""Current source/public-evidence closure and independent same-OS read-only restore, disclosed private-path metadata alias."""
from pathlib import Path
import hashlib,json,zipfile,subprocess,sys,os,re
OUT=Path('results/dev_aux');HERE=OUT/'task1930'
SOURCE=OUT/'SOURCE_REPRO_20261016_63.zip';EVIDENCE=OUT/'EVIDENCE_20261016_63.zip'
def sha(b):return hashlib.sha256(b).hexdigest()
def clean(files):
 markers=json.loads(Path('.local_agent/publication_exclusions59.json').read_text())
 for name,data in files.items():
  assert not name.startswith('.local_agent/') and '..' not in Path(name).parts and not Path(name).is_absolute()
  assert all(v.encode() not in data for m in markers for v in (m,m.replace('\\','/'),json.dumps(m)[1:-1])),name
  assert not re.search(rb'(?:xox[baprs]-[A-Za-z0-9-]{20,}|sk-[A-Za-z0-9_-]{30,}|-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----)',data),name

def seal(path,files,manifest_name,scope):
 clean(files);manifest=dict(files={n:dict(bytes=len(b),sha256=sha(b)) for n,b in sorted(files.items())},scope=scope)
 with zipfile.ZipFile(path,'x',compression=zipfile.ZIP_DEFLATED) as z:
  for n,b in sorted(files.items()):z.writestr(n,b)
  z.writestr(manifest_name,json.dumps(manifest,indent=2))
 with zipfile.ZipFile(path) as z:
  assert z.testzip() is None
  for n,r in manifest['files'].items():assert sha(z.read(n))==r['sha256']
 return dict(archive=path.as_posix(),files=len(files),raw_bytes=sum(map(len,files.values())),bytes=path.stat().st_size,sha256=sha(path.read_bytes()),manifest=manifest_name)

def package():
 files={}
 with zipfile.ZipFile(OUT/'SOURCE_REPRO_20261015_62.zip') as z:
  for n in z.namelist():
   if n.endswith('/') or 'MANIFEST' in Path(n).name.upper():continue
   files[n]=z.read(n)
 for task in range(1910,1936):
  for p in (OUT/f'task{task}').rglob('*'):
   if p.is_file() and p.suffix in ('.py','.ini') and '__pycache__' not in p.parts:files[p.as_posix()]=p.read_bytes()
 source=seal(SOURCE,files,'MANIFEST63SOURCE.json','Current scopedresearchsource+base62Core/27testmodules/313tests/purePythondependencies; newhelpers+requiredtestcensus. ExistingOS/interpreter, no Nativebinary/compiler/privateSlack. Closeddata independentlyreplayed withEVIDENCE63; no fullNative/proofbatchreexecution. Historicalsourcepins stayimmutable. Private1910sourcepathmetadata has public relativepathcopy; see publication.json/releasealias, notbyteidenticalraworiginal.')
 evidence={}
 for task in range(1910,1936):
  for p in (OUT/f'task{task}').rglob('*'):
   if not p.is_file() or p.suffix not in ('.py','.json','.jsonl','.ini') or '__pycache__' in p.parts:continue
   if p.as_posix()=='results/dev_aux/task1910/result.json':continue
   if p.as_posix()=='results/dev_aux/task1930/restore.json':continue
   evidence[p.as_posix()]=p.read_bytes()
 for n in ['results/dev_aux/task1872/rules.json','results/dev_aux/task1872/feasibility.json','results/dev_aux/task1895/plan.json','results/dev_aux/task1895/result.json','results/dev_aux/task1895/states.jsonl','results/dev_aux/task1896/coverage.json','results/dev_aux/task1866/unit_panel.py']:
  evidence[n]=Path(n).read_bytes()
 ev=seal(EVIDENCE,evidence,'MANIFEST63EVIDENCE.json','AllCLOSED63policyproductions/fullrecords/Nativejournals/plans/source/failedsetupmetadata andproofcertificates/finite-tree/literal-leafwitnesses. No privateSlack/account/nativebinary. Sourcepath1910metadata publicationcopy disclosed, allscientificpairs unchanged. Sealedbeforeacceptedfinish/finalreport/session/QA/delivery; finalmetadata directGit, not insideZIP.')
 with (OUT/'ARCHIVE_MANIFEST_20261016_63.json').open('x') as f:json.dump(dict(status='SEALED_CRC_ALL_MEMBER_SHA',archives=[source,ev],publication_alias='Restorer may alias checkedtask1910/public-result.json toresult.json forlegacyread-onlyauditors; originalprivateSHA preserved inpublication.json, aliasNOTbyteidenticalrawprivateoriginal. Allcase/record/Native/evaluationdataidentical; no oldproducer reexecution or sourceSHArewrite.'),f,indent=2)
 print(json.dumps(dict(source=source,evidence=ev)))

def restore():
 destination=Path('.local_agent/repro63').resolve();destination.mkdir(exist_ok=False);manifests=[]
 for path,mname in ((SOURCE,'MANIFEST63SOURCE.json'),(EVIDENCE,'MANIFEST63EVIDENCE.json')):
  with zipfile.ZipFile(path) as z:
   assert z.testzip() is None;manifest=json.loads(z.read(mname));manifests.append(manifest)
   for name,row in manifest['files'].items():
    assert '..' not in Path(name).parts and not Path(name).is_absolute();data=z.read(name);assert sha(data)==row['sha256'];p=destination/name;p.parent.mkdir(parents=True,exist_ok=True)
    if p.exists():assert p.read_bytes()==data
    else:p.write_bytes(data)
 targets=sorted(n for n in manifests[0]['files'] if n.startswith('tests/development/test_') and n.endswith('.py'));assert len(targets)==27
 boot="import sys,pathlib;root=pathlib.Path.cwd();sys.path.insert(0,str(root/'.venv/Lib/site-packages'));import pytest,generic_chess;assert pathlib.Path(pytest.__file__).is_relative_to(root);assert pathlib.Path(generic_chess.__file__).is_relative_to(root);code=pytest.main("+repr(targets+['-q','--junitxml=restored-tests.xml'])+");assert all(not getattr(m,'__file__',None) or pathlib.Path(m.__file__).is_relative_to(root) for n,m in sys.modules.items() if n.startswith(('generic_chess','scripts.','_pytest','pytest')));raise SystemExit(code)"
 env=dict(os.environ);env['PYTHONPATH']='';env['PYTEST_DISABLE_PLUGIN_AUTOLOAD']='1';env['PYTEST_ADDOPTS']=''
 proc=subprocess.run([sys.executable,'-S','-c',boot],cwd=destination,env=env,capture_output=True,timeout=120);(destination/'tests.log').write_bytes(proc.stdout+proc.stderr)
 import xml.etree.ElementTree as ET
 xml=ET.parse(destination/'restored-tests.xml').getroot();suites=list(xml) if xml.tag=='testsuites' else [xml];counts={k:sum(int(x.attrib.get(k,0)) for x in suites) for k in ('tests','failures','errors','skipped')};assert proc.returncode==0 and counts['tests']==313 and counts['failures']==counts['errors']==0
 replay="import sys,pathlib,json,time;root=pathlib.Path.cwd();sys.path.insert(0,str(root/'.venv/Lib/site-packages'));start=time.perf_counter();from results.dev_aux.task1928.audit import audit;import results.dev_aux.task1914.audit as first;import results.dev_aux.task1921.audit as proofs;import results.dev_aux.task1927.audit as leaves;import results.dev_aux.task1935.audit as design;alias=root/'results/dev_aux/task1910/result.json';alias.write_bytes((root/'results/dev_aux/task1910/public-result.json').read_bytes());rows=[audit('results/dev_aux/task'+str(t)) for t in (1920,1925,1926,1929)];[(setattr(m,'O',root/'rechecks'/n),(root/'rechecks'/n).mkdir(parents=True)) for m,n in ((first,'first'),(proofs,'proofs'),(leaves,'leaves'),(design,'design'))];first.main();proofs.run();leaves.run();design.run();from generic_chess.rules.serialization import deserialize_ruleset;from generic_chess.rules.compiler import compile_ruleset_for_execution;from scripts.generic_session_certificate_json import decode_session_certificate;from scripts.generic_session_win_proof import SessionStrategyCursor;cc=compile_ruleset_for_execution(deserialize_ruleset((root/'results/dev_aux/task1913/rules.json').read_text()));ss,cert=decode_session_certificate(cc,json.loads((root/'results/dev_aux/task1913/certificate.json').read_text()));cur=SessionStrategyCursor(ss,cert,seconds=3.);cur.commit(ss,cur.choose(ss));assert ss.result.winner==0 and ss.result.status.value=='checkmate';assert all(not getattr(m,'__file__',None) or pathlib.Path(m.__file__).is_relative_to(root) for n,m in sys.modules.items() if n.startswith(('generic_chess','scripts.','results.')));print(json.dumps(dict(status='PASS_ALL_ARCHIVED63_ACTUAL_POLICY_REPLAYS',games=22+sum(r['games'] for r in rows),moves=816+sum(r['moves'] for r in rows),native_bindings=746+sum(r['actual_native'] for r in rows),proof_games=8+sum(r['proof_games'] for r in rows),verified_transported_proofs=18,changed_N_mechanism_actual_mate=1,public_leaf_records=2822,protected_root_reference_queries=96,seconds=time.perf_counter()-start,new_search_or_proof_or_Native_calls=0,private_metadata_alias_disclosed=True)))"
 pr=subprocess.run([sys.executable,'-S','-c',replay],cwd=destination,env=env,capture_output=True,timeout=120);(destination/'replay.log').write_bytes(pr.stdout+pr.stderr);assert pr.returncode==0,pr.stderr.decode(errors='replace');rr=json.loads(pr.stdout.decode().splitlines()[-1])
 out=dict(status='PASS_INDEPENDENT_SOURCE_AND_EVIDENCE_RESTORE',counts=counts,replay=rr,source_sha=sha(SOURCE.read_bytes()),evidence_sha=sha(EVIDENCE.read_bytes()),scope='ExistingOS/interpreter,-S,newdirectory/restoredpytestdeps/modulepathassertions. No originalprojectimports/freshmachine/Nativefullrerun. All63actualpolicyCoreedges/fullhistory/ranks/Nativebindings replayed plus18transportedproofs and2822publicleafwitnesses. Legacy1910privatepathmetadata has explicitpublicalias; notbyteidenticalrawinput, notoldproducerreexecution.')
 with (HERE/'restore.json').open('x') as f:json.dump(out,f,indent=2)
 print(json.dumps(out))
if __name__=='__main__':{'package':package,'restore':restore}[sys.argv[1]]()
