"""Seal exact current optional research source; independently restore tests."""
from pathlib import Path
import hashlib,json,zipfile,subprocess,sys,os
OUT=Path('results/dev_aux');ARCHIVE=OUT/'SOURCE_REPRO_20261015_61.zip'
def sha(data):return hashlib.sha256(data).hexdigest()
def package():
 files={}
 with zipfile.ZipFile(OUT/'SOURCE_REPRO_CURRENT_20261015_60.zip') as z:
  for name in z.namelist():
   if name.endswith('/') or 'MANIFEST' in Path(name).name.upper():continue
   files[name]=Path(name).read_bytes() if Path(name).is_file() else z.read(name)
 for name in ['scripts/generic_session_cached_phase_player.py','scripts/generic_session_proof_bank.py','tests/development/test_generic_session_cached_phase_player.py']:
  files[name]=Path(name).read_bytes()
 for task in range(1861,1875):
  for p in (OUT/f'task{task}').rglob('*'):
   if p.is_file() and p.suffix in ('.py','.ini') and '__pycache__' not in p.parts:files[p.as_posix()]=p.read_bytes()
 # Inputs needed to import/exercise scripts, not raw account or executables.
 for name in ['results/dev_aux/task1872/rules.json','results/dev_aux/task1846/rules.json']:
  files[name]=Path(name).read_bytes()
 markers=json.loads(Path('.local_agent/publication_exclusions59.json').read_text())
 for name,data in files.items():
  assert not name.startswith('.local_agent/') and '..' not in Path(name).parts
  assert all(v.encode() not in data for m in markers for v in (m,m.replace('\\','/'),json.dumps(m)[1:-1])),name
 manifest=dict(status='EXACT_CURRENT_SOURCE',files={n:dict(bytes=len(b),sha256=sha(b)) for n,b in sorted(files.items())},scope='Exact currentresearch code,26testmodules/purePython testdependencies plus scripts and scopedruleinputs. Evidence/closedplans/games separately published. ExistingPython/OS/toolchain external, no binary/compiler/privateSlack. Older1848/1863sources remain pinned separately, no source relabel.',tests=298)
 with zipfile.ZipFile(ARCHIVE,'x',compression=zipfile.ZIP_DEFLATED) as z:
  for name,data in sorted(files.items()):z.writestr(name,data)
  z.writestr('MANIFEST61SOURCE.json',json.dumps(manifest,indent=2).encode())
 with zipfile.ZipFile(ARCHIVE) as z:
  assert z.testzip() is None
  for name,row in manifest['files'].items():assert sha(z.read(name))==row['sha256']
 result=dict(status='SEALED_CRC_ALL_MEMBER_SHA',archive=ARCHIVE.as_posix(),files=len(files),bytes=ARCHIVE.stat().st_size,sha256=sha(ARCHIVE.read_bytes()))
 with (OUT/'task1874/source_archive.json').open('x') as f:json.dump(result,f,indent=2)
 print(json.dumps(result))
def restore():
 destination=Path('.local_agent/repro61').resolve();destination.mkdir(exist_ok=False)
 with zipfile.ZipFile(ARCHIVE) as z:
  manifest=json.loads(z.read('MANIFEST61SOURCE.json'))
  for name,row in manifest['files'].items():
   assert '..' not in Path(name).parts and not Path(name).is_absolute();data=z.read(name);assert sha(data)==row['sha256'];p=destination/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
 targets=sorted(p.as_posix() for p in Path('tests/development').glob('test_*.py') if p.name in {Path(n).name for n in manifest['files'] if n.startswith('tests/development/test_')})
 assert len(targets)==26
 boot="import sys,pathlib; root=pathlib.Path.cwd();sys.path.insert(0,str(root/'.venv/Lib/site-packages'));import pytest,generic_chess;assert pathlib.Path(pytest.__file__).is_relative_to(root);assert pathlib.Path(generic_chess.__file__).is_relative_to(root);code=pytest.main("+repr(targets+['-q','--junitxml=restored-tests.xml'])+");assert all(not getattr(m,'__file__',None) or pathlib.Path(m.__file__).is_relative_to(root) for n,m in sys.modules.items() if n.startswith(('generic_chess','scripts.','_pytest','pytest')));raise SystemExit(code)"
 env=dict(os.environ);env['PYTHONPATH']='';env['PYTEST_DISABLE_PLUGIN_AUTOLOAD']='1';env['PYTEST_ADDOPTS']=''
 proc=subprocess.run([sys.executable,'-S','-c',boot],cwd=destination,env=env,capture_output=True,timeout=120)
 (destination/'tests.log').write_bytes(proc.stdout+proc.stderr)
 import xml.etree.ElementTree as ET
 suite=ET.parse(destination/'restored-tests.xml').getroot();suites=list(suite) if suite.tag=='testsuites' else [suite];counts={k:sum(int(x.attrib.get(k,0)) for x in suites) for k in ('tests','failures','errors','skipped')};assert proc.returncode==0 and counts['tests']==298 and counts['failures']==counts['errors']==0
 result=dict(status='PASS_CURRENT_SOURCE_INDEPENDENT_RESTORE',counts=counts,source_archive_sha=sha(ARCHIVE.read_bytes()),source_files=len(manifest['files']),scope='Existinginterpreter/OS, -S restoredpurepytestdeps, cwd/newdirectory and runtime modulepath assertions; no originalprojectimport, Native rerun or freshmachine claim.')
 with (OUT/'task1874/restore.json').open('x') as f:json.dump(result,f,indent=2)
 print(json.dumps(result))
if __name__=='__main__':{'package':package,'restore':restore}[sys.argv[1]]()
