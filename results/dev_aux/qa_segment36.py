import json,zipfile,hashlib,ast,re,time,sys
from pathlib import Path
R=Path.cwd();O=R/'results/dev_aux';tag=sys.argv[1];M=json.loads((O/f'ACTUAL_MATURE_{tag}_manifest.json').read_bytes());start=time.perf_counter();counts=dict(python=0,json=0,jsonl_lines=0);patterns=[rb'(?i)[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}',rb'U0C6[A-Z0-9]+',rb'T0C6[A-Z0-9]+',rb'C0C6[A-Z0-9]+',rb'(?i)(?:xox[baprs]-[A-Za-z0-9-]+|ghp_[A-Za-z0-9]+|sk-proj-[A-Za-z0-9_-]+)',rb'C:[/\\]Users[/\\]wdai']
for a in M['archives']:
 p=O/a['path'];assert p.stat().st_size==a['bytes'] and hashlib.sha256(p.read_bytes()).hexdigest()==a['sha256'];members=[r for r in M['files'] if r['archive']==a['path']]
 with zipfile.ZipFile(p) as z:
  assert set(z.namelist())=={r['path'] for r in members}
  for row in members:
   data=z.read(row['path']);assert len(data)==row['bytes'] and hashlib.sha256(data).hexdigest()==row['sha256'] and (R/row['path']).read_bytes()==data;assert not any(re.search(pat,data) for pat in patterns),row['path'];suffix=Path(row['path']).suffix
   if suffix=='.py':ast.parse(data.decode('utf-8-sig'));counts['python']+=1
   elif suffix=='.json':json.loads(data.decode('utf-8-sig'));counts['json']+=1
   elif suffix=='.jsonl':
    for line in data.splitlines():json.loads(line);counts['jsonl_lines']+=1
print('Exactarchive/AST/JSON/privacy PASS',tag,flush=True)
exclude=R/'.git/info/exclude';s=exclude.read_text(encoding='utf-8')
for path in M['archive_only_paths']:
 if '/'+path not in s.splitlines():s+='\n/'+path+'\n'
exclude.write_text(s,encoding='utf-8');attr=R/'.gitattributes';s=attr.read_text(encoding='utf-8')
for rule in [f"{path.split('/')[0]}/{path.split('/')[1]}/{path.split('/')[2]}/** -text whitespace=cr-at-eol" for path in {r['path'] for r in M['files']}]+[f'results/dev_aux/*20261013* -text whitespace=cr-at-eol',f'results/dev_aux/*segment36* -text whitespace=cr-at-eol',f'results/dev_aux/*restore_segment36* -text whitespace=cr-at-eol']:
 if rule not in s.splitlines():s+='\n'+rule+'\n'
attr.write_text(s,encoding='utf-8');out=dict(status='PASS',manifest_tag=tag,members=M['members'],counts=counts,raw_bytes=M['raw_bytes'],archive_bytes=M['archive_bytes'],archive_only_originals=len(M['archive_only_paths']),privacy_problems=[],seconds=time.perf_counter()-start,unique_originals_deleted=False);(O/f'QA_{tag}.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps(out))
