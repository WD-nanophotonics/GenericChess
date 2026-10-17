"""Qualify measured baseline reuse by exact driver normalization and Core states."""
from pathlib import Path
from copy import deepcopy
import ast,json,time,hashlib
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from results.dev_aux.task2392.reader import SharedDeleteStopReader
from results.dev_aux.task2397.material import material as semantic_material
OUT=Path('results/dev_aux/task2459')
class Baseline(ast.NodeTransformer):
 def visit_Constant(self,n):return ast.copy_location(ast.Constant('results/dev_aux/task2441'),n)if n.value=='results/dev_aux/task2461'else n
 def visit_Name(self,n):return ast.copy_location(ast.Constant(1.),n)if n.id=='N_hand'else n
 def visit_FunctionDef(self,n):
  if n.name=='material':
   assert n.args.args[-1].arg=='N_hand'and len(n.args.defaults)==1;n.args.args=n.args.args[:-1];n.args.defaults=[]
  return self.generic_visit(n)
 def visit_IfExp(self,n):
  n=self.generic_visit(n)
  return n.body if ast.dump(n.body)==ast.dump(n.orelse)else n
 def visit_Call(self,n):
  if isinstance(n.func,ast.Name)and n.func.id=='material'and len(n.args)==5:
   last=n.args[-1];assert isinstance(last,ast.Subscript)and isinstance(last.slice,ast.Constant)and last.slice.value=='N_hand';n.args=n.args[:-1]
  return self.generic_visit(n)
def run():
 stop=SharedDeleteStopReader(Path.cwd());t=time.perf_counter();old=Path('results/dev_aux/task2441');new=Path('results/dev_aux/task2461');tree=ast.parse((old/'pilot.py').read_text());newtree=ast.parse((new/'pilot.py').read_text());normal=Baseline().visit(deepcopy(newtree));assert ast.dump(tree)==ast.dump(normal),'DriverdiffbeyondNhandcallbackandOUT';p=json.loads((old/'plan.json').read_text());q=json.loads((new/'plan.json').read_text());keys=['candidate','opponents','H','step_seconds','candidate_step_seconds','candidate_proof_caller_seconds'];assert all(p[k]==q[k]for k in keys);assert json.loads((old/'inputs.json').read_text())==json.loads((new/'inputs.json').read_text());ledger=json.loads((new/'baseline-reuse.json').read_text());games=[json.loads(x)for x in(old/'games.jsonl').read_text().splitlines()];ds=[json.loads(x)for x in(old/'decisions.jsonl').read_text().splitlines()];roots=json.loads((old/'inputs.json').read_text());observations=0;prepaid=0.
 for row in ledger:
  stop();g=next(g for g in games if g['slot']==row['source_slot']);assert g['root']==row['family']and g['candidate_color']==row['role']and(g['ratio'],g['hand_ratio'])==(.75,.75)and g['reward']==row['reward']and g['record']==row['record'];prepaid+=g['seconds'];root=roots[row['family']];definition=deserialize_ruleset(Path(root['rules']).read_text());c=compile_ruleset_for_execution(definition);anchors={x.type_id for x in definition.piece_types if x.is_anchor};funcs=[]
  for tr in(tree,newtree):
   node=deepcopy(next(n for n in ast.walk(tr)if isinstance(n,ast.FunctionDef)and n.name=='material'));module=ast.Module(body=[node],type_ignores=[]);ns=dict(semantic_material=semantic_material,definition=definition,anchors=anchors);exec(compile(ast.fix_missing_locations(module),'actual_material_callback','exec'),ns);funcs.append(ns['material'])
  for d in ds:
   if d['slot']!=g['slot']:continue
   stop();s=GameSession.replay(c,deserialize_game_record(json.dumps(d['root_record'])));assert d['normal_receipt']is None or d['normal_receipt']['completed_depth']==3;assert dict(d['phase_limits'])['total_seconds']==d['caller_seconds'];
   for side in(0,1):assert funcs[0](s.state.position,side,.75,.75)==funcs[1](s.state.position,side,.75,.75,1.);observations+=1
 result=dict(status='PASS_ONCE_ONLY_BASELINE_REUSE_AT_NHAND1',driver_AST_equal_under_Nhand1=True,behavioral_config_keys=keys,reused_games=len(ledger),actual_state_side_callback_equalities=observations,prepaid_game_seconds=prepaid,seconds=time.perf_counter()-t,scope='Eightqualified2441TRAINanchor(.75,.75)/Nhand1 measuredgames reusedONCE asnewscalarlearnerbaseline; SAMEfullrules/starts/foe/proof/gates/strictD3/phaseceilings. ActualnormalizedwholeproducerASTequalatNhand1exceptoutputfolder, alldrivercontractkeys equal; actualCorestatesandcallbacks checked. MetadataextraNhandfieldnotnewoutcomes. Thisdoesnotguaranteereexecutionunderwallbudgetsidentical; notnew8games/newreplication/noextraweights. No newsearch/fitness/oldcapextension.')
 (OUT/'reuse-result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
if __name__=='__main__':run()
