"""Correct zero-observation callback ABI without editing the frozen producer."""
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
OLD=ROOT/'scripts/audit_physical_profile_dispatch.py'
FAILED=ROOT/'docs/research/data/physical_profile_dispatch_20261006.json'
OUT=ROOT/'docs/research/data/physical_profile_qualified_20261006.json'
if __name__=='__main__':
    if OUT.exists():raise FileExistsError('qualified wrapper no rerun')
    failed=json.loads(FAILED.read_text());assert failed['worlds']==failed['enumerated']==0 and failed['candidates']==40 and failed['source_hashes_unchanged']
    for path,pin in failed['source_sha256'].items():assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==pin
    code=OLD.read_text();assert code.count('def observe(p,s,t,b,value):')==1
    code=code.replace('def observe(p,s,t,b,value):','def observe(t,b,p,s,value):').replace('physical_profile_dispatch_20261006.json','physical_profile_qualified_20261006.json')
    code=code.replace("SOURCES=('scripts/audit_physical_profile_dispatch.py',", "SOURCES=('scripts/audit_physical_profile_qualified.py','docs/research/PHYSICAL_PROFILE_CALLBACK_SCOPE.md','docs/research/data/physical_profile_dispatch_20261006.json','scripts/audit_physical_profile_dispatch.py',")
    code=code.replace("if monotonic()-start>=15:","if monotonic()-start+0.032>=15:").replace("if r['candidates']+r['enumerated']>5000:","if r['candidates']+r['enumerated']+40>5000:")
    code=code.replace("r['seconds']=monotonic()-start;", "r['cumulative_seconds']=monotonic()-start+0.032;r['charged_candidates']=r['candidates']+40;r['seconds']=monotonic()-start;")
    exec(compile(code,str(OLD),'exec'),{'__name__':'__main__','__file__':str(OLD)})
