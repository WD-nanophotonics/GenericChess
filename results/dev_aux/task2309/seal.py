"""Preserve21archive failure and seal exact current-byte anchor input overlay."""
from pathlib import Path
import json,hashlib,zipfile,ast,re
root=Path.cwd();out=root/'results/dev_aux';prior=json.loads((out/'ARCHIVE_MANIFEST_20261016_79.json').read_text());oldroot=root/'.local_agent/archive-replay79-cbf70e8db7f74be6b05efb51648b2872'
files={};overrides={};checks=[]
for name in('results/dev_aux/task2282/inputs.json','results/dev_aux/task2300/restore.py','results/dev_aux/task2309/seal.py'):
 raw=(root/name).read_bytes();old=(oldroot/name).read_bytes()if(oldroot/name).exists()else None
 assert not re.search(rb'(?i)(?:[A-Z]:[/\\]Users[/\\]|[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}|xox[baprs]-[A-Za-z0-9-]{15,}|gh[pousr]_[A-Za-z0-9]{20,})',raw)
 if old is not None:
  overrides[name]=hashlib.sha256(old).hexdigest()
  if name.endswith('inputs.json'):assert json.loads(raw)==json.loads(old)
  checks.append(dict(path=name,previous_sha=hashlib.sha256(old).hexdigest(),current_sha=hashlib.sha256(raw).hexdigest(),change='JSON-equivalent exactactualinput publicationprojection'if name.endswith('inputs.json')else'Explicitreplayharness22archive manifest/count correction; no producerchange'))
 if name.endswith('.py'):ast.parse(raw.decode())
 files[name]=dict(sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))
manifest=dict(files=files,overrides=overrides,scope='22ndsupplement: exactcurrentold2282input usedby79anchorbytecomparison; JSONidenticaltooldraw. Updatedreplayharnessandthissealeronly; no producer/refit/rule/reward/capchange.')
archive=out/'SOURCE_PIN_SUPPLEMENT_20261016_79.zip';assert not archive.exists()
with zipfile.ZipFile(archive,'x',zipfile.ZIP_DEFLATED)as z:
 z.writestr('MANIFEST_20261016_79_SUPPLEMENT.json',json.dumps(manifest,indent=2))
 for name in files:z.write(root/name,name)
with zipfile.ZipFile(archive)as z:assert z.testzip()is None
sha=hashlib.sha256(archive.read_bytes()).hexdigest();archives=dict(prior['archives']);archives[archive.name]=sha
(out/'ARCHIVE_MANIFEST_20261016_79_FINAL.json').write_text(json.dumps(dict(archives=archives,supplement_sha=sha,prior='ARCHIVE_MANIFEST_20261016_79.json',scope=manifest['scope']),indent=2))
(out/'REPLAY_FAILURE_20261016_79.json').write_text(json.dumps(dict(status='FIRST21_REPLAY_FAILED',stage='closed2293',related_tests_passed=23,closed2290_passed=True,error='AssertionError: old2282/current2287 inputbytes mismatch',cause='Earlierraw78 archive preserves prettyJSON;79anchors actually use publishedLF input projection. JSONidentical, actualbytepin must remain explicit.',correction=checks,earlier_archives_immutable=True,producers_rerun=False),indent=2))
print(json.dumps(dict(status='PASS_EXPLICIT22_SUPPLEMENT',sha=sha,files=len(files))))
