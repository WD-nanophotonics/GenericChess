"""Static read-only comparison of primary working Runtime against tested candidate."""
import ast,copy,json,hashlib,datetime
from pathlib import Path
root=Path.cwd();primary=Path(r'C:\Users\wdai\Documents\ChatGPT\GenericChess 2')
own=root/'generic_chess/core/search_runtime.py';current=primary/'generic_chess/core/search_runtime.py'
left=ast.parse(own.read_text());right=ast.parse(current.read_text());candidate=copy.deepcopy(left)
cl=next(n for n in candidate.body if isinstance(n,ast.ClassDef) and n.name=='SearchPathRuntime')
push=next(n for n in cl.body if isinstance(n,ast.FunctionDef) and n.name=='push');removed=0
for n in ast.walk(push):
 if isinstance(n,ast.BoolOp) and isinstance(n.op,ast.And):
  size=len(n.values);n.values=[v for v in n.values if ast.unparse(v)!='rollback_frame.bridge_key is not None'];removed+=size-len(n.values)
assert removed==1
dump=lambda t:ast.dump(t,include_attributes=False)
result={'observed_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'pinned_own_base':'b4108a68a7ee06327be39cb3a222939644085a52','own_source_sha256':hashlib.sha256(own.read_bytes()).hexdigest(),'primary_working_source_sha256':hashlib.sha256(current.read_bytes()).hexdigest(),'entire_runtime_ast_matches_tested_candidate':dump(candidate)==dump(right),'primary_is_working_file_not_published_commit':True,'scope':'read-only source comparison; does not execute primary tests or certify other product files'}
assert result['entire_runtime_ast_matches_tested_candidate']
(root/'results/dev_aux/task008/primary_working_ast.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
