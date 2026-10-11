"""Static immutable source correspondence; no engine/test imports."""
import ast, copy, datetime, hashlib, json, subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
BASE='b4108a68a7ee06327be39cb3a222939644085a52'
PUBLISHED='558b497ba9ab4bd5464274571923959e628cbc03'
FILE='generic_chess/core/search_runtime.py'
def git(*args):
    return subprocess.check_output(['git',*args],cwd=ROOT)
def source(pin,path):
    return git('show',pin+':'+path)
dump=lambda t:ast.dump(t,include_attributes=False)
base=source(BASE,FILE);published=source(PUBLISHED,FILE)
candidate=copy.deepcopy(ast.parse(base))
cls=next(n for n in candidate.body if isinstance(n,ast.ClassDef) and n.name=='SearchPathRuntime')
push=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='push')
removed=0
for node in ast.walk(push):
    if isinstance(node,ast.BoolOp) and isinstance(node.op,ast.And):
        previous=len(node.values)
        node.values=[v for v in node.values if ast.unparse(v)!='rollback_frame.bridge_key is not None']
        removed+=previous-len(node.values)
assert removed==1
own=(ROOT/FILE).read_bytes()
assert dump(ast.parse(own))==dump(ast.parse(base))
assert dump(candidate)==dump(ast.parse(published))
changed=git('diff','--name-only',BASE,PUBLISHED,'--','generic_chess','scripts').decode().splitlines()
assert changed==['generic_chess/ai/alphabeta/native_legality.py',FILE]
result={'complete':True,'observed_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'baseline_pin':BASE,'published_pin':PUBLISHED,'removed_conjuncts':removed,
    'whole_runtime_ast_matches_independently_executed_candidate':True,
    'own_runtime_ast_matches_baseline':True,
    'git_blob_sha256':{'baseline':hashlib.sha256(base).hexdigest(),'published':hashlib.sha256(published).hexdigest()},
    'other_changed_product_paths':changed[:-1],
    'changed_test_paths':git('diff','--name-only',BASE,PUBLISHED,'--','tests').decode().splitlines(),
    'other_change':'NativeSemanticLegalityProvider.supports_position reads compiled.support.max_ply instead of compiled.max_ply',
    'scope':'source correspondence only; transfers existing finite Runtime candidate results; does not execute primary tests or validate Native provider change'}
(ROOT/'results/dev_aux/task011/published_correspondence.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
