"""Bind tested working candidate to exact immutable remote product source."""
import ast,hashlib,io,json,subprocess,zipfile
from pathlib import Path
B=Path(__file__).parent;ROOT=B.parents[2]
PIN='80a6bd06d5e093cd29ad51c7a01cc6719b357533'
git=lambda *args:subprocess.check_output(['git',*args],cwd=ROOT)
old=git('show','558b497ba9ab4bd5464274571923959e628cbc03:generic_chess/core/search_runtime.py')
new=git('show',PIN+':generic_chess/core/search_runtime.py')
left=ast.parse(old);right=ast.parse(new)
frozen=ast.parse((B.parent/'task018/frozen_working_resolve.py').read_text(encoding='utf-8')).body[0]
getcls=lambda t:next(n for n in t.body if isinstance(n,ast.ClassDef) and n.name=='SearchPathRuntime')
cls=getcls(left);cls.body=[frozen if isinstance(n,ast.FunctionDef) and n.name==frozen.name else n for n in cls.body]
assert ast.dump(left,include_attributes=False)==ast.dump(right,include_attributes=False)
published=next(n for n in getcls(right).body if isinstance(n,ast.FunctionDef) and n.name==frozen.name)
assert ast.dump(published,include_attributes=False)==ast.dump(frozen,include_attributes=False)
paths=git('diff','--name-only','558b497ba9ab4bd5464274571923959e628cbc03',PIN,'--','generic_chess').decode().splitlines()
assert paths==['generic_chess/core/search_runtime.py'],paths
index=json.loads(git('show',PIN+':docs/research/data/compiled_effect_20261011.json'))
archive=git('show',PIN+':'+index['archive'])
assert hashlib.sha256(archive).hexdigest()==index['archive_sha256']
science=[]
with zipfile.ZipFile(io.BytesIO(archive)) as z:
 for name in ('compiled_effect_shared.py','compiled_effect_probe.py'):
  match=[v for v in index['members'] if v['path'].endswith('/'+name)]
  assert len(match)==1,(name,match)
  row=match[0];data=z.read(row['path']);assert hashlib.sha256(data).hexdigest()==row['sha256']
  (B/name).write_bytes(data)
  science.append({'path':row['path'],'sha256':row['sha256']})
out=dict(complete=True,primary_pin=PIN,published_runtime_sha256=hashlib.sha256(new).hexdigest(),whole_runtime_ast_matches_tested_Task018_substitution=True,frozen_resolve_ast_matches=True,product_changed_paths=paths,archive_sha256=index['archive_sha256'],scientific_source_members=science,scope='immutable source binding only; original failures retained; primary regression not independently run')
(B/'published_binding.json').write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8')
print(json.dumps(out,indent=2))
