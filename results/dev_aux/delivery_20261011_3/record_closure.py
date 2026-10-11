"""Scientific dependency closure without engine imports or experiment replay."""
import ast,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];B=ROOT/'results/dev_aux'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
checks=[]
def bind(report,field,target):
 v=json.loads((B/report).read_bytes());expected=v[field]
 actual=sha(B/target);assert actual==expected,(report,field,target,actual,expected)
 checks.append(dict(report=report,field=field,target=target,sha256=actual))
for report,field in [('task027/coverage_audit.json','inputs_sha256'),('task030/shared_cost_audit.json','input_hashes')]:
 v=json.loads((B/report).read_bytes())
 for name,expected in v[field].items():
  target=(B/report).parent/name;actual=sha(target);assert actual==expected,(report,name)
  checks.append(dict(report=report,field=field+'.'+name,target=str(target.relative_to(B)),sha256=actual))
for item in [
 ('task032/native_transport_scope.json','profile_input_sha256','task032/frozen_residual_profile.json'),
 ('task034/selection_work.json','reused_query_record_sha256','task033/rank_merge.json'),
 ('task036/iterator_priming.json','input_sha256','task034/selection_work.json'),
 ('task038/retrieval_law.json','input_sha256','task037/multirow_contract.json'),
 ('task039/blocked_ray.json','candidate_raw_sha256','task033/candidate_function.py'),
 ('task040/deferred_square.json','shared_source_sha256','task025/compiled_effect_shared.py'),
 ('task041/checkpoint_provenance.json','fixture_source_sha256','task040/deferred_square.py')]:
 bind(*item)
# inspect.getsource's method hash is an LF source-method hash, not module bytes.
module=(ROOT/'generic_chess/core/semantic_executor.py').read_text()
cls=next(n for n in ast.parse(module).body if isinstance(n,ast.ClassDef) and n.name=='SemanticEngine')
fn=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='is_square_attacked')
logical=''.join(module.splitlines(keepends=True)[fn.lineno-1:fn.end_lineno])
expected=json.loads((B/'task033/rank_merge.json').read_bytes())['baseline_executor_sha256']
assert hashlib.sha256(logical.encode()).hexdigest()==expected
parsed=[]
for i in range(27,42):
 for path in sorted((B/('task%03d'%i)).iterdir()):
  if path.suffix=='.py':ast.parse(path.read_text(encoding='utf-8'));parsed.append(str(path.relative_to(B)))
  elif path.suffix=='.json':json.loads(path.read_bytes());parsed.append(str(path.relative_to(B)))
out=dict(complete=True,engine_imports_or_experiment_replays=0,raw_byte_bindings=checks,
 baseline_method_source=dict(field='baseline_executor_sha256',meaning='inspect.getsource original method LF text including class indentation',sha256=expected),
 syntactic_files_checked=len(parsed),parsed_paths=parsed,
 limits='Syntax parsing includes retained failed fixture scripts; it is not passing execution of those scripts. JSON parsing is not a claim that every declaration executed. Existing scientific controls supply execution evidence. Module source is checked without import.')
Path(__file__).with_name('record_closure.json').write_bytes((json.dumps(out,indent=2)+'\n').encode())
print('closure:',len(checks),'raw SHA bindings and original method logical source; syntax/JSON:',len(parsed),'files; no engine reruns')
