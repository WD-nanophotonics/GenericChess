"""Source and finite-record audit only; no engine invocation or timing rerun."""
import ast,hashlib,json,subprocess
from pathlib import Path
B=Path(__file__).parent
ROOT=B.resolve().parents[2]
P=Path('C:/Users/wdai/Documents/ChatGPT/GenericChess 2/.local_agent/physical-publication-20261011')
PIN='c87ed1f36497276eb966bb186c81baabaa897114'
def digest(data):return hashlib.sha256(data).hexdigest()
source=subprocess.check_output(['git','show',PIN+':generic_chess/core/semantic_executor.py'],cwd=ROOT)
own=(ROOT/'generic_chess/core/semantic_executor.py').read_bytes()
assert ast.dump(ast.parse(source),include_attributes=False)==ast.dump(ast.parse(own),include_attributes=False)
inputs={}
for name in ('physical_profile.py','physical-profile.json','analysis.json','declaration.json','declaration-correction.json'):
 dest=B/name
 data=dest.read_bytes() if dest.exists() else (P/name).read_bytes()
 if not dest.exists():dest.write_bytes(data)
 inputs[name]=digest(data)
record=json.loads((B/'physical-profile.json').read_text(encoding='utf-8'))
assert record['complete'] and len(record['rows'])==2
def clean(v):
 if isinstance(v,dict):return {k:clean(x) for k,x in v.items() if 'seconds' not in k and not k.startswith('time_') and k!='wall'}
 if isinstance(v,list):return [clean(x) for x in v]
 return v
plain,observed=record['rows']
assert clean(plain['decision'])==clean(observed['decision'])
assert clean(plain['stats'])==clean(observed['stats'])
assert observed['root_multiset_restored'] and plain['root_multiset_restored']
assert observed['counts']=={'transitions':93824,'copies':93824,'freezes':93824}
components=observed['components']
assert sum(x.get('trials',0)+x.get('transitions',0) for x in components.values())==93824
assert sum(x.get('trials',0) for k,x in components.items() if 'terminal_runtime' in k)==50946
assert sum(x.get('trials',0) for k,x in components.items() if 'terminal_initial' in k)==1
assert sum(x.get('transitions',0) for k,x in components.items() if 'formal_push' in k)==42877
totals={n:sum(x.get(n,0) for x in components.values()) for n in ('copy','freeze','trans')}
analysis=json.loads((B/'analysis.json').read_text(encoding='utf-8'))
assert totals==analysis['totals']
tree=ast.parse(source)
cls={n.name:n for n in tree.body if isinstance(n,ast.ClassDef)}
transition=next(n for n in cls['SemanticEngine'].body if isinstance(n,ast.FunctionDef) and n.name=='_transition')
init=next(n for n in cls['_WorkingPosition'].body if isinstance(n,ast.FunctionDef) and n.name=='__init__')
freeze=next(n for n in cls['_WorkingPosition'].body if isinstance(n,ast.FunctionDef) and n.name=='to_position')
assert any(isinstance(n,ast.Assign) and ast.unparse(n)=='aux = dict(position.aux_state)' for n in transition.body)
ret=transition.body[-1];assert isinstance(ret,ast.Return)
assert ast.unparse(ret.value.args[0])=='tuple(sorted(aux.items()))'
assert sum(isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='_WorkingPosition' for n in ast.walk(transition))==1
assert sum(isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='to_position' for n in ast.walk(transition))==1
assert not any(isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='_transition' for f in (transition,init,freeze) for n in ast.walk(f))
out={'complete':True,'pin':PIN,'executor_sha256':digest(source),'inputs_sha256':inputs,
 'reused_primary_execution':True,'independent_new_engine_calls':0,
 'counts':observed['counts'],'consumer_counts':{'terminal_initial':1,'terminal_runtime':50946,'formal_push':42877},
 'totals':totals,'observed_choose_wall':observed['wall'],
 'small_copy_freeze_scope':'init includes board and two hands copies, not aux=dict in transition; to_position includes board/hands freeze and Position validation, not caller aux tuple/sort argument',
 'larger_transition_scope':'all those aux operations lie inside timed saved transition; total physical transition cannot be equated to exclusive copy/freeze',
 'stage_scope':'component sums include session initialization while wall denominator times choose; separate session numerator before ratios',
 'decision':'No source/record omission overturns DEFER on this frozen caller; do not call4.14% complete copy/freeze, do not call11.5% universal upper bound or causal speedup. C internals and S3/S4 checks remain excluded.',
 'limits':'Counters increment finally on attempts; this completed record has equal counts but not a general proof every counted attempt publishes a child. Source audit and record arithmetic, not independently rerun primary performance.'}
(B/'coverage_audit.json').write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8')
print(json.dumps(out,indent=2))
