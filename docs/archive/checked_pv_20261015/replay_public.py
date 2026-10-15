"""Restore and qualify this frozen technical archive; never overwrite an existing tree."""
from pathlib import Path
import argparse,hashlib,json,subprocess,sys,sysconfig,uuid,zipfile,shutil

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--zig',type=Path,required=True);ap.add_argument('--destination',type=Path);args=ap.parse_args()
 artifact=Path(__file__).resolve().parent;manifest=json.loads((artifact/'manifest.json').read_text(encoding='utf-8'));archive=artifact/'evidence.zip'
 assert hashlib.sha256(archive.read_bytes()).hexdigest()==manifest['archive_sha256']
 dest=(args.destination or Path('.local_agent')/('checked-pv-public-'+uuid.uuid4().hex[:8])).resolve();dest.mkdir(parents=True,exist_ok=False)
 with zipfile.ZipFile(archive) as z:
  assert z.testzip() is None
  for row in manifest['members']:
   target=(dest/row['restore_to']).resolve();assert target.is_relative_to(dest);data=z.read(row['member']);assert hashlib.sha256(data).hexdigest()==row['public_sha256'];target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
 suffix=sysconfig.get_config_var('EXT_SUFFIX');zig=args.zig.resolve();prior=dest/'.local_agent/immediate-goal-20261015';prior.mkdir(parents=True,exist_ok=True)
 outcomes=[]
 for label,target in [('v1',dest/'generic_chess'/('_native_core'+suffix)),('v2',prior/('final_v2'+suffix))]:
  src=dest/'replay'/('src_'+label);cmd=[str(zig),'cc','-target','x86_64-windows-gnu','-shared','-O2','-I'+sysconfig.get_paths()['include'],'-I'+str(src),'-L'+str(Path(sys.base_prefix)/'libs'),'-lpython312',*[str(p)for p in sorted(src.glob('*.c'))],'-o',str(target)]
  r=subprocess.run(cmd,cwd=dest,capture_output=True,timeout=180);(dest/f'build-{label}.log').write_bytes(r.stdout+r.stderr);assert r.returncode==0,(label,r.stderr.decode(errors='replace'));outcomes.append(dict(build=label,exit=r.returncode))
  if label=='v2':shutil.copyfile(target,dest/'replay'/('wide'+suffix))
 commands=[('api',[sys.executable,'-m','pytest','-c','pytest.ini','-p','no:cacheprovider','--basetemp','replay/pytest-public','tests/product/test_native_immediate_win_goal.py','tests/product/test_native_explicit_semantic_backend.py','tests/product/test_native_pv_replay_boundaries.py','tests/product/test_h50b2e_semantic_search_engine.py','-q']),('fullstate',[sys.executable,'replay/qualify.py',str(Path.cwd()/'.local_agent')]),('q32-history',[sys.executable,'.local_agent/pv-contract-20261015/q32_history_replay.py'])]
 for label,cmd in commands:
  r=subprocess.run(cmd,cwd=dest,capture_output=True,timeout=180);(dest/f'{label}.log').write_bytes(r.stdout+r.stderr);assert r.returncode==0,(label,r.stdout.decode(errors='replace'),r.stderr.decode(errors='replace'));outcomes.append(dict(check=label,exit=r.returncode))
 result=dict(complete=True,outcomes=outcomes,scope='Rebuilt historical V1/V2, API and full state/history qualification; frozen search costs are not rerun. Existing Python312/pytest/Zig environment, not clean-machine installer. Latest PENDING repair is qualified separately at065eff0d.')
 (dest/'public-replay.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result));print('RESTORED',dest)
if __name__=='__main__':main()
