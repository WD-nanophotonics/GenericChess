"""Resume a zero-observation interface failure within the original budget."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'scripts/audit_native_cube_contact_closure.py'
if __name__=='__main__':
    old=json.loads((ROOT/'docs/research/data/native_cube_contact_closure_20261005.json').read_text())
    assert not old['complete'] and not old['rows'] and not old['controls'] and old['enumerated']==0 and old['canonical_candidates']==96
    target=ROOT/'docs/research/data/native_cube_contact_qualified_20261005.json'
    if target.exists():raise FileExistsError('frozen qualified cube study')
    code=SOURCE.read_text().replace("OUT=ROOT/'docs/research/data/native_cube_contact_closure_20261005.json'","OUT=ROOT/'docs/research/data/native_cube_contact_qualified_20261005.json'")
    code=code.replace('from scripts.native_cube_contact_closure import NativeCubeKernel,cube_contact_census','from scripts.native_cube_contact_closure import cube_contact_census\nfrom scripts.native_cube_contact_qualified import QualifiedNativeCubeKernel as NativeCubeKernel')
    code=code.replace("SOURCES=('scripts/audit_native_cube_contact_closure.py',","SOURCES=('scripts/audit_native_cube_contact_qualified.py','scripts/native_cube_contact_qualified.py','docs/research/NATIVE_CUBE_CONTACT_QUALIFIED_SCOPE.md','docs/research/data/native_cube_contact_closure_20261005.json','scripts/audit_native_cube_contact_closure.py',")
    code=code.replace('canonical_candidates=0,enumerated=0','canonical_candidates=96,enumerated=0')
    code=code.replace('monotonic()-start>=15','monotonic()-start+0.032>=15')
    code=code.replace("r['seconds']=monotonic()-start;","r['seconds']=monotonic()-start;r['cumulative_seconds']=r['seconds']+0.032;")
    exec(compile(code,str(SOURCE),'exec'),{'__name__':'__main__','__file__':str(SOURCE)})
