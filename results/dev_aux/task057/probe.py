"""Five predeclared frontier controls; isolated process, no search/product writes."""
import ast, hashlib, json, subprocess, sys, time
from dataclasses import replace
from pathlib import Path
sys.path[:0]=[str(Path.cwd()),str(Path.cwd()/'tests/product'),str(Path.cwd()/'tests')]
from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.rules.schema import RuleTypeRef, ruleset_to_dict
from generic_chess.core.pieces import Piece
from generic_chess.core.semantic_executor import semantic_engine_for, _semantic_public_action
from generic_chess.ai.alphabeta.native_legality import NativeSemanticLegalityProvider
from generic_chess.native import compiler as nc
from test_f24c_mixed_mechanic_certification import _mixed_ruleset, _position
from scripts.research_record import record_value
B=Path(__file__).parent;decl=json.loads((B/'DECLARATION.json').read_bytes());REV=decl['source_pin']
def sha(b):return hashlib.sha256(b).hexdigest()
def git(p):return subprocess.check_output(['git','show',REV+':'+p])
sources={p:sha(git(p)) for p in ['generic_chess/native/compiler.py','generic_chess/_native/native_semantic_runtime.c','generic_chess/core/semantic_executor.py','tests/product/test_f24c_mixed_mechanic_certification.py']}
for p in sources:
 if p!='generic_chess/native/compiler.py':assert Path(p).read_bytes().replace(b'\r\n',b'\n')==git(p).replace(b'\r\n',b'\n'),p
fixed=git('generic_chess/native/compiler.py');tree=ast.parse(fixed)
node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='_sem_effect')
ns=dict(nc.__dict__);exec(compile(ast.Module(body=[node],type_ignores=[]),'<fixed _sem_effect>','exec'),ns)
original=nc._sem_effect;nc._sem_effect=ns['_sem_effect']
natives=list(Path('generic_chess').rglob('_native_core.cp312-win_amd64.pyd'));assert len(natives)==1,natives
binary={'path':str(natives[0]),'sha256':sha(natives[0].read_bytes())}
assert binary['sha256']=='2f97cfb8816bc963163207095bf40ac990169284cd0cfb2e7b545f0a6bf07bf1'
out={'complete':False,'source_pin':REV,'sources':sources,'auxiliary_checkout_source_hashes':{p:sha(Path(p).read_bytes()) for p in sources},'binary_source_identity_limit':'Installed binary hash matches recorded runtime, not proof it was built from either tracked C source.','native_binary':binary,'scope':decl['method'],'rows':[]};start=time.perf_counter()
try:
 for case in decl['cases']:
  ref=RuleTypeRef('explicit',case[9:]) if case.startswith('explicit_') else RuleTypeRef(case)
  rules=_mixed_ruleset();actions=[]
  for a in rules.semantic_actions:
   if a.name=='capture_B0_A0_leap':a=replace(a,effects=tuple(replace(e,piece_type_ref=ref) if e.kind=='remove' else e for e in a.effects))
   actions.append(a)
  rules=replace(rules,semantic_actions=tuple(actions));c=compile_semantic_ruleset(rules)
  pos=_position(c,[(1,1,Piece(0,'B0','B0')),(2,1,Piece(1,'A0','A0')),(0,0,Piece(0,'H0','H0')),(6,6,Piece(1,'H0','H0'))])
  engine=semantic_engine_for(c);provider=NativeSemanticLegalityProvider.try_create(c,strict=True);assert provider is not None
  before=record_value(pos);core={_semantic_public_action(engine,a):a for a in engine.legal_actions(pos)};pairs=provider(pos,0);native=dict(pairs)
  needle=lambda a:a.pattern_id.endswith('capture_B0_A0_leap') and a.from_square.file==1 and a.from_square.rank==1 and a.to_square.file==2 and a.to_square.rank==1
  core_capture=[a for a in core if needle(a)];native_capture=[a for a in native if needle(a)]
  attempted=[]
  for a in native_capture:
   sem,binding=native[a]
   try:child=engine._transition(pos,sem,binding);accepted=True;error=None
   except Exception as e:child=None;accepted=False;error={'type':type(e).__name__,'message':str(e)}
   attempted.append({'action':record_value(a),'core_transition_accepted':accepted,'error':error,'child':record_value(child)})
  assert record_value(pos)==before
  out['rows'].append({'case':case,'ruleset_fingerprint':c.ruleset_fingerprint,'ruleset':ruleset_to_dict(rules),'position':before,'provider_executable':provider.native_rules.native_executable,'core_count':len(core),'native_count':len(native),'core_capture':record_value(core_capture),'native_capture':record_value(native_capture),'core_only':record_value(list(set(core)-set(native))),'native_only':record_value(list(set(native)-set(core))),'same_complete_frontier':set(core)==set(native),'core_transition_for_native_capture':attempted,'root_unchanged':True})
  (B/'result.json').write_bytes((json.dumps(out,indent=2)+'\n').encode())
 out['complete']=True;out['elapsed_observation_seconds']=time.perf_counter()-start;(B/'result.json').write_bytes((json.dumps(out,indent=2)+'\n').encode())
 print(json.dumps([{k:r[k] for k in ['case','core_count','native_count','same_complete_frontier','core_transition_for_native_capture']} for r in out['rows']]))
finally:nc._sem_effect=original
