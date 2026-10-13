import json,hashlib,zipfile,sys,subprocess
from pathlib import Path
R=Path.cwd();O=R/'results/dev_aux';tag=sys.argv[1];assert tag in ['20261013_35'];M=json.loads((O/f'ACTUAL_MATURE_{tag}_manifest.json').read_bytes());extract='--extract' in sys.argv[2:]
if extract:assert subprocess.check_output(['git','branch','--show-current'],cwd=R,text=True).strip()=='sidemission'
for a in M['archives']:
 p=O/a['path'];assert hashlib.sha256(p.read_bytes()).hexdigest()==a['sha256'];members=[r for r in M['files'] if r['archive']==a['path']]
 with zipfile.ZipFile(p) as z:
  assert set(z.namelist())=={r['path'] for r in members}
  for row in members:
   data=z.read(row['path']);assert len(data)==row['bytes'] and hashlib.sha256(data).hexdigest()==row['sha256'];target=(R/row['path']).resolve();assert target.is_relative_to(O.resolve()) and row['path'].split('/')[2].startswith('task') and row['path'].split('/')[2][4:].isdigit()
   if extract:
    if target.exists():assert target.read_bytes()==data,'refuseoverwritechangedscience:'+row['path']
    else:target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
print(json.dumps(dict(verified=True,tag=tag,members=M['members'],extracted=extract)))
