import json,zipfile,hashlib,ast,re,pathlib,time
R=pathlib.Path.cwd();O=R/'results/dev_aux';M=json.loads((O/'ACTUAL_MATURE_20261012_29_manifest.json').read_bytes());start=time.perf_counter();counts={'python':0,'json':0,'jsonl_lines':0};problems=[];patterns=[rb'(?i)[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}',rb'U0C6[A-Z0-9]+',rb'T0C6[A-Z0-9]+',rb'C0C6[A-Z0-9]+',rb'(?i)(?:xox[baprs]-[A-Za-z0-9-]+|ghp_[A-Za-z0-9]+|sk-proj-[A-Za-z0-9_-]+)',rb'C:[/\\]Users[/\\]wdai']
with zipfile.ZipFile(O/M['archive']) as z:
 for row in M['files']:
  data=z.read(row['path']);assert hashlib.sha256(data).hexdigest()==row['sha256'];assert (R/row['path']).read_bytes()==data
  for pat in patterns:
   if re.search(pat,data):problems.append({'path':row['path'],'kind':'privacy_pattern'})
  suffix=pathlib.Path(row['path']).suffix
  if suffix=='.py':ast.parse(data.decode('utf-8-sig'));counts['python']+=1
  elif suffix=='.json':json.loads(data.decode('utf-8-sig'));counts['json']+=1
  elif suffix=='.jsonl':
   for line in data.splitlines():json.loads(line);counts['jsonl_lines']+=1
assert not problems,problems
for path in [O/'SEGMENT_20261012_29.md',O/'package_segment29.py',O/'restore_segment29.py']:
 data=path.read_bytes();assert not any(re.search(pat,data) for pat in patterns),str(path)
# Keep unique originals; large science only in reviewed exact ZIP.
exclude=R/'.git/info/exclude';s=exclude.read_text(encoding='utf-8');added=[]
for path in M['archive_only_paths']:
 if '/'+path not in s.splitlines():s+='\n/'+path+'\n';added.append(path)
exclude.write_text(s,encoding='utf-8');a=R/'.gitattributes';s=a.read_text(encoding='utf-8')
for n in [467, 468, 469, 470, 472, 477, 478, 479, 480, 481, 482, 484, 491, 492, 493, 495, 496, 497, 498, 499, 500, 501, 502, 503, 504, 506, 507, 508, 509, 510, 511, 512, 513, 514, 515, 516, 517, 518]:
 rule=f'results/dev_aux/task{n}/** -text whitespace=cr-at-eol'
 if rule not in s:s+='\n'+rule+'\n'
for pat in ['*_20261012_29*','package_segment29.py','restore_segment29.py','qa_segment29.py']:
 rule=f'results/dev_aux/{pat} -text whitespace=cr-at-eol'
 if rule not in s:s+='\n'+rule+'\n'
a.write_text(s,encoding='utf-8');print(json.dumps({'status':'PASS','manifest_members':M['members'],'counts':counts,'privacy_problems':problems,'excluded_large_originals':len(M['archive_only_paths']),'raw_bytes':M['raw_bytes'],'archive_bytes':M['archive_bytes'],'seconds':time.perf_counter()-start}))
