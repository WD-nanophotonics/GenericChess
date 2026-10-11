"""Recover only hash-verified producer Python in this sidemission clone; no jobs."""
import hashlib,json,zipfile,subprocess
from pathlib import Path
root=Path(__file__).resolve().parents[3]
branch=subprocess.check_output(['git','branch','--show-current'],cwd=root,text=True).strip()
if branch!='sidemission':raise RuntimeError('DEV_AUX recovery requires sidemission')
report={'indices':[],'extracted':[]}
for name in ('availability_core_20261011','representation_outcome_20261011','physical_outcome_20261011'):
 index=json.loads((root/'docs/research/data'/f'{name}.json').read_text())
 archive=root/index['archive']['path']
 assert hashlib.sha256(archive.read_bytes()).hexdigest()==index['archive']['sha256'],name
 members={m['member']:m for m in index['members']}
 with zipfile.ZipFile(archive) as z:
  for member,meta in members.items():
   raw=z.read(member)
   assert len(raw)==meta['bytes'] and hashlib.sha256(raw).hexdigest()==meta['sha256'],member
   if member.startswith('.local_agent/') and member.endswith('.py'):
    dest=(root/member).resolve();assert dest.is_relative_to(root/'.local_agent')
    if dest.exists() and dest.read_bytes()!=raw:raise RuntimeError('Refuse overwrite of changed producer '+member)
    dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(raw)
    report['extracted'].append({'path':member,'sha256':meta['sha256']})
 report['indices'].append({'name':name,'archive_sha256':index['archive']['sha256'],'members_verified':len(members)})
source=Path(__file__).parent/'weighted_adapter_original.py';dest=root/'.local_agent/weighted-backend-20261011/bridge.py'
raw=source.read_bytes()
if dest.exists() and dest.read_bytes()!=raw:raise RuntimeError('Refuse overwrite of changed weighted adapter')
dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(raw)
report['weighted_adapter_sha256']=hashlib.sha256(raw).hexdigest()
(root/'.local_agent/archive_recovery_verification.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'complete':True,'members_verified':sum(x['members_verified'] for x in report['indices']),'python_producers':len(report['extracted']),'no_experiment_executed':True},indent=2))
