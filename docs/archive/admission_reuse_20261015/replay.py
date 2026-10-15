r"""Rebuild and replay the published source baseline plus exact admission overrides.
Run from root: .venv\Scripts\python.exe docs/archive/admission_reuse_20261015/replay.py
Requires the existing Windows/Python3.12/Zig toolchain; no timing reruns.
"""
from pathlib import Path
import sys,json,zipfile,hashlib,uuid,subprocess,sysconfig,time
R=Path.cwd();A=Path(__file__).resolve().parent;m=json.loads((A/'manifest.json').read_bytes());base=R/m['baseline_archive'];assert hashlib.sha256(base.read_bytes()).hexdigest()==m['baseline_sha256'];assert hashlib.sha256((A/'evidence.zip').read_bytes()).hexdigest()==m['archive_sha256'];dest=R/'.local_agent'/('admission-public-replay-'+uuid.uuid4().hex[:8]);dest.mkdir();start=time.perf_counter()
with zipfile.ZipFile(base)as z:
 for name in z.namelist():
  if name.startswith('frozen_export/'):
   p=dest/name[len('frozen_export/'):];assert p.resolve().is_relative_to(dest.resolve());p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(z.read(name))
with zipfile.ZipFile(A/'evidence.zip')as z:
 assert z.testzip()is None
 for item in m['members']:
  blob=z.read(item['member']);assert hashlib.sha256(blob).hexdigest()==item['public_sha256']
  if item['member'].startswith('overrides/'):
   p=dest/item['member'][len('overrides/'):];assert p.resolve().is_relative_to(dest.resolve());p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(blob)
rows=[];suffix=sysconfig.get_config_var('EXT_SUFFIX')
for name,source,target in [('v1',dest/'generic_chess/_native',dest/'generic_chess'/('_native_core'+suffix)),('v2',dest/'replay/src_v2',dest/'replay'/('wide'+suffix))]:
 cmd=[str(R/'.venv/Lib/site-packages/ziglang/zig.exe'),'cc','-target','x86_64-windows-gnu','-shared','-O2','-I'+sysconfig.get_paths()['include'],'-I'+str(source),'-L'+str(Path(sys.base_prefix)/'libs'),'-lpython312',*[str(p)for p in sorted(source.glob('*.c'))],'-o',str(target)]
 r=subprocess.run(cmd,capture_output=True,timeout=180);(dest/f'build-{name}.log').write_bytes(r.stdout+r.stderr);assert r.returncode==0,r.stderr.decode(errors='replace');rows.append(dict(build=name,exit=r.returncode))
checks=['tests/product/test_native_geometry_first_source.py','tests/product/test_native_q_history_deferral.py','tests/product/test_native_pending_continuation.py','tests/product/test_native_pv_replay_boundaries.py','tests/development/test_reference_history_scope.py','tests/development/test_reference_declaration_scope.py','tests/product/test_semantic_compilation_reuse.py','tests/product/test_movement_graph_bitsets.py','tests/product/test_compiled_attack_index.py','tests/product/test_compiled_endpoint_fallback.py']
for label,args in [('focused',['-m','pytest','-o','addopts=','-q','-c','pytest.ini','-p','no:cacheprovider','--basetemp','replay/pytest-admission']+checks),('fullstate',['replay/qualify.py',str(R/'.local_agent')])]:
 r=subprocess.run([sys.executable]+args,cwd=dest,capture_output=True,timeout=300);(dest/f'{label}.log').write_bytes(r.stdout+r.stderr);assert r.returncode==0,(label,r.stdout.decode(errors='replace'),r.stderr.decode(errors='replace'));rows.append(dict(check=label,exit=r.returncode))
result=dict(complete=True,seconds=time.perf_counter()-start,rows=rows,focused_tests=81,fullstate=json.loads((dest/'replay/qualification.json').read_bytes()),scope='Sanitized public baseline+overrides, V1/V2 rebuilt with existing machine toolchain; no copied binary/private originals/timing replication.')
(dest/'result.json').write_bytes(json.dumps(result,indent=2).encode());print(json.dumps(result,indent=2))
