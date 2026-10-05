"""Changed exact cache factorization resumes before any distance observation."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];SOURCE=ROOT/'scripts/audit_diagnostic_native_contact_census.py'
if __name__=='__main__':
    old=json.loads((ROOT/'docs/research/data/diagnostic_native_contact_census_20261005.json').read_text())
    assert not old['complete'] and not old['rows'] and not old['completed_target_slabs'] and old['preprocessing']['canonical_candidates']==2791
    assert not (ROOT/'docs/research/data/diagnostic_native_contact_kernel_20261005.json').exists()
    code=SOURCE.read_text().replace("OUT=ROOT/'docs/research/data/diagnostic_native_contact_census_20261005.json'","OUT=ROOT/'docs/research/data/diagnostic_native_contact_mirrored_20261005.json'")
    code=code.replace('from scripts.native_cube_contact_qualified import QualifiedNativeCubeKernel','from scripts.mirrored_native_cube_kernel import MirroredNativeCubeKernel as QualifiedNativeCubeKernel')
    code=code.replace("SOURCES=('scripts/audit_diagnostic_native_contact_census.py',","SOURCES=('scripts/audit_diagnostic_native_contact_mirrored.py','scripts/mirrored_native_cube_kernel.py','docs/research/DIAGNOSTIC_NATIVE_CONTACT_MIRROR_SCOPE.md','docs/research/data/diagnostic_native_contact_census_20261005.json','scripts/audit_diagnostic_native_contact_census.py',")
    code=code.replace("kernel.stats['canonical_candidates']>5000","kernel.stats['canonical_candidates']+2791>5000")
    code=code.replace('monotonic()-start>=15','monotonic()-start+0.125>=15')
    code=code.replace('cubes=cubes','cubes=sorted(cubes)')
    code=code.replace("r['seconds']=monotonic()-start;","r['seconds']=monotonic()-start;r['cumulative_seconds']=r['seconds']+0.125;r['charged_canonical_candidates']=r.get('preprocessing',{}).get('canonical_candidates',0)+2791;")
    exec(compile(code,str(SOURCE),'exec'),{'__name__':'__main__','__file__':str(SOURCE)})
