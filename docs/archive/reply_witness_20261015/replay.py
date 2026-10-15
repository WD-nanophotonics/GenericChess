r"""Verify archive hashes and rebuild the frozen final sources on Windows/Python3.12.
Run from repository root: .venv\Scripts\python.exe docs/archive/reply_witness_20261015/replay.py
Requires existing project's Zig compiler and Python headers/libs. Does not rerun timing studies.
"""
from pathlib import Path
import sys,sysconfig,subprocess,zipfile,json,hashlib,uuid,time
R=Path.cwd();A=Path(__file__).resolve().parent;M=json.loads((A/'manifest.json').read_text(encoding='utf-8-sig'))
assert hashlib.sha256((A/'evidence.zip').read_bytes()).hexdigest()==M['archive_sha256']
dest=R/'.local_agent'/('reply-public-replay-'+uuid.uuid4().hex[:8]);dest.mkdir(parents=True);start=time.perf_counter()
with zipfile.ZipFile(A/'evidence.zip')as z:
 assert z.testzip()is None
 for row in M['members']:
  blob=z.read(row['member']);assert hashlib.sha256(blob).hexdigest()==row['public_sha256']
  if row['member'].startswith('frozen_export/'):
   target=dest/row['member'][len('frozen_export/'):];assert target.resolve().is_relative_to(dest.resolve());target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(blob)
logs=[];suffix=sysconfig.get_config_var('EXT_SUFFIX')
for name,source,target in [('v1',dest/'generic_chess/_native',dest/'generic_chess'/('_native_core'+suffix)),('v2',dest/'replay/src_v2',dest/'replay'/('wide'+suffix))]:
 cmd=[str(R/'.venv/Lib/site-packages/ziglang/zig.exe'),'cc','-target','x86_64-windows-gnu','-shared','-O2','-I'+sysconfig.get_paths()['include'],'-I'+str(source),'-L'+str(Path(sys.base_prefix)/'libs'),'-lpython312',*[str(p)for p in sorted(source.glob('*.c'))],'-o',str(target)]
 r=subprocess.run(cmd,capture_output=True,timeout=180);(dest/f'build-{name}.log').write_bytes(r.stdout+r.stderr);assert r.returncode==0,(name,r.stderr.decode(errors='replace'));logs.append(dict(build=name,exit=r.returncode))
for label,args in [('focused',['-m','pytest','-q','-c','pytest.ini','-p','no:cacheprovider','--basetemp','replay/pytest-public','tests/product/test_native_geometry_first_source.py','tests/product/test_native_q_history_deferral.py','tests/product/test_native_pending_continuation.py','tests/product/test_native_pv_replay_boundaries.py','tests/development/test_reference_history_scope.py','tests/development/test_reference_declaration_scope.py']),('fullstate',['replay/qualify.py',str(R/'.local_agent')])]:
 r=subprocess.run([sys.executable]+args,cwd=dest,capture_output=True,timeout=300);(dest/f'{label}.log').write_bytes(r.stdout+r.stderr);assert r.returncode==0,(label,r.stdout.decode(errors='replace'),r.stderr.decode(errors='replace'));logs.append(dict(check=label,exit=r.returncode))
result=dict(complete=True,seconds=time.perf_counter()-start,rows=logs,focused_tests=38,fullstate=json.loads((dest/'replay/qualification.json').read_text()),scope='Sanitized published archive sources rebuilt, no copied binaries/older private inputs; existing machine toolchain, not clean-machine installer or timing replication.')
(dest/'result.json').write_bytes(json.dumps(result,indent=2).encode());print(json.dumps(dict(complete=True,seconds=result['seconds'],focused=38,roots=result['fullstate']['roots'],legal_actions=result['fullstate']['legal_actions'])))
