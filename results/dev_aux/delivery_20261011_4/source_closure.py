"""New-segment dependency/source closure, no engine imports or fixture replay."""
import ast,hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];B=Path(__file__).parent
base='b4108a68a7ee06327be39cb3a222939644085a52'
def sha(raw):return hashlib.sha256(raw).hexdigest()
sources=[]
for name in ('generic_chess/core/semantic_executor.py','generic_chess/rules/compiler.py','generic_chess/rules/ir.py','generic_chess/core/pieces.py','generic_chess/core/transition.py','generic_chess/core/actions.py','generic_chess/core/adjudication.py','generic_chess/rules/compiled.py'):
 raw=(ROOT/name).read_bytes()
 fixed=subprocess.check_output(['git','-C',str(ROOT),'show',base+':'+name])
 assert raw.replace(b'\r\n',b'\n')==fixed
 sources.append(dict(path=name,product_base=base,raw_sha256=sha(raw),git_blob_sha256=sha(fixed),
  exact_after_crlf_to_lf=True))
dependencies=[]
for folder,out in [('task043','hybrid_overlap.json'),('task044','frontier_recovery.json'),('task045','current_type_child.json'),('task046','termination_work.json'),('task047','s4_recovery.json'),('task048','public_core_history.json'),('task050','public_successors.json'),('task051','history_consumer.json'),('task052','drop_lifecycle.json'),('task053','carrier_fallback.json')]:
 path=ROOT/'results/dev_aux'/folder/out;data=json.loads(path.read_bytes());assert data['complete']
 mapping={'candidate_raw_sha256':'task033/candidate_function.py',
 'shared_source_sha256':'task025/compiled_effect_shared.py',
 'original_derivation_sha256':'task038/DERIVATION.md','iterator_counter_raw_sha256':'task046/iterator_counter.py'}
 if folder=='task044':mapping['fixture_source_sha256']='task040/deferred_square.py'
 if folder=='task047':mapping['fixture_source_sha256']='task044/frontier_recovery.py'
 if folder=='task048':mapping['fixture_source_sha256']='task045/current_type_child.py'
 if folder in ('task050','task051','task052','task053'):mapping['fixture_source_sha256']='task048/public_core_history.py'
 for field,dep in mapping.items():
  if field not in data:continue
  raw=(ROOT/'results/dev_aux'/dep).read_bytes()
  assert sha(raw)==data[field],(folder,field,dep)
  dependencies.append(dict(output=str(path.relative_to(ROOT)),field=field,input='results/dev_aux/'+dep,
   raw_sha256=sha(raw),exact=True))
syntax=[]
for i in range(43,55):
 for p in sorted((ROOT/'results/dev_aux'/('task%03d'%i)).iterdir()):
  if p.suffix=='.py':ast.parse(p.read_text(encoding='utf-8'));syntax.append(str(p.relative_to(ROOT)))
  if p.suffix=='.json':json.loads(p.read_bytes());syntax.append(str(p.relative_to(ROOT)))
assert len(dependencies)==15
out=dict(complete=True,scope='8 immutable product source pins;15 new output raw dependency bindings;new Python AST/JSON syntax, no engine or numeric witness rerun',
 sources=sources,dependencies=dependencies,parsed=syntax,
 limits='AST parsing retained unexecuted wrong-entry draft is not an execution pass. Hash binding proves bytes, not semantic completeness/performance or Dot execution.')
(B/'source_closure.json').write_bytes((json.dumps(out,indent=2)+'\n').encode())
print('source closure8pins/15dependencies/',len(syntax),'AST/JSON parses pass')
