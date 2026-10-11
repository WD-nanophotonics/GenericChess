"""Audit new shared-template completed records, never rerun timing."""
import ast,hashlib,json,math
from pathlib import Path
B=Path(__file__).parent
P=Path('C:/Users/wdai/Documents/ChatGPT/GenericChess 2/.local_agent/availability-core-20261011')
mapping={'compiled-effect-shared-control.json':'frozen_control.json','shared-template-slot.json':'frozen_slot.json','shared-template-decision.json':'frozen_cost_analysis.json',
 'shared-template-declaration.json':'frozen_declaration.json','shared_template_control.py':'frozen_control_producer.py',
 'compiled_effect_shared.py':'frozen_shared.py','compiled_effect_probe.py':'frozen_dependency.py'}
hashes={}
for src,dest in mapping.items():
 target=B/dest
 data=target.read_bytes() if target.exists() else (P/src).read_bytes()
 if not target.exists():target.write_bytes(data)
 hashes[dest]=hashlib.sha256(data).hexdigest()
assert (B/'frozen_shared.py').read_bytes()==(B.parent/'task025/compiled_effect_shared.py').read_bytes()
assert (B/'frozen_dependency.py').read_bytes()==(B.parent/'task025/compiled_effect_probe.py').read_bytes()
# Reuse already reviewed arithmetic procedure; new inputs/output belong here.
source=(B.parent/'task022/cost_record_audit.py').read_text(encoding='utf-8')
ns={'__file__':str(B/'new_shared_cost_audit.py')}
exec(compile(source,'<retained arithmetic procedure with new frozen inputs>','exec'),ns)
out=json.loads((B/'cost_record_audit.json').read_text(encoding='utf-8'))
assert sum(r['warm_ratio']>1 for r in out['rows'] if r['condition']=='fixed')==7
assert next(r['warm_ratio'] for r in out['rows'] if r['condition']=='completed')>1
v=json.loads((B/'frozen_control.json').read_text(encoding='utf-8'))
assert all(r['metadata']['templates']==(6 if r['root'].startswith('chess') else 3) for r in v['setup'])
producer=ast.parse((B/'frozen_control_producer.py').read_text(encoding='utf-8'))
imports=[ast.unparse(n) for n in ast.walk(producer) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='module']
assert any('compiled_effect_shared.py' in n for n in imports)
out.update(candidate='new shared exact Task025 bytes, not first per-pattern candidate',input_hashes=hashes,
 reuses_arithmetic_procedure_only=True,new_engine_invocations=0,
 all_declared_roots_included=sorted(r['root'] for r in out['rows'] if r['condition']=='fixed'),
 verdict='DEFER remains supported by supplied finite records;4newpositive+56callback and Task028invalid semantic success do not cancel7adverse warm roots.',
 declaration_status='frozen declaration retains pre-execution Prepared label; actual complete control/slot records establish executed status separately')
(B/'shared_cost_audit.json').write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8')
print('New shared hash identical Task025;64fixed+4completed+8setup;7of8fixed warm adverse; all paired arithmetic and non-time metadata pass.')
