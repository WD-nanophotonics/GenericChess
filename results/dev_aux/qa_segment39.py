from pathlib import Path
import json,hashlib,zipfile,ast,re,time
R=Path.cwd();start=time.monotonic();m=json.loads((R/'results/dev_aux/ACTUAL_MATURE_20261014_39_manifest.json').read_bytes());dest=R/'.local_agent/restore_segment39';dest.mkdir(exist_ok=False);expected={x['path']:x for x in m['members']};counts=dict(files=0,python=0,json=0,jsonl_lines=0);seen=set();private=re.compile(r'TYPE=DOT_REPLY|REQUEST_ID=GC-SLACK-|[A-Za-z0-9_.+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}|xox[baprs]-[A-Za-z0-9-]+|sk-[A-Za-z0-9]{20,}')
for arc in m['archives']:
 p=R/'results/dev_aux'/arc['name'];assert p.stat().st_size==arc['size'] and hashlib.sha256(p.read_bytes()).hexdigest()==arc['sha256']
 with zipfile.ZipFile(p) as z:
  assert z.testzip() is None
  for name in z.namelist():
   assert name in expected and name not in seen;seen.add(name);raw=z.read(name);e=expected[name];assert len(raw)==e['size'] and hashlib.sha256(raw).hexdigest()==e['sha256'];text=raw.decode('utf-8-sig');assert not private.search(text),(name,private.search(text).group())
   if name.endswith('.py'):ast.parse(text);counts['python']+=1
   elif name.endswith('.json'):json.loads(text);counts['json']+=1
   elif name.endswith('.jsonl'):
    for l in text.splitlines():json.loads(l);counts['jsonl_lines']+=1
   target=(dest/name).resolve();assert target.is_relative_to(dest.resolve());target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw);assert hashlib.sha256(target.read_bytes()).hexdigest()==e['sha256'];counts['files']+=1
assert seen==set(expected);out=dict(status='PASS_ALL_ARCHIVE_HASH_JSON_AST_PRIVACY_AND_PRIVATE_FULL_RESTORE',counts=counts,raw_bytes=m['raw_bytes'],compressed_bytes=sum(a['size'] for a in m['archives']),seconds=time.monotonic()-start,scope='Exact179savedAgentrecords includingfailures; allrawdata retained. Stockqualification39doesnotconvertinvalidruns to validscience. No privateSlack/account/userauthoredinput found.');(R/'results/dev_aux/QA_20261014_39.json').write_text(json.dumps(out,indent=2));print(out)
