"""Actual saved composite capture/promotion/drop history and capture-only parity."""
from pathlib import Path
import ast,json,time,hashlib
from collections import Counter
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from results.dev_aux.task2354 import pilot
from results.dev_aux.task2376.material import features,material
from results.dev_aux.task2153.stop_evidence import EvidenceStopReader
OUT=Path('results/dev_aux/task2376')
def run():
 start=time.perf_counter();stop=EvidenceStopReader(Path.cwd());stop();folder=Path('results/dev_aux/task2315');definition=deserialize_ruleset((folder/'rules.json').read_text());compiled=compile_ruleset_for_execution(definition);anchors=frozenset(t.type_id for t in definition.piece_types if t.is_anchor);data=json.loads((folder/'result.json').read_text());row=next(r for r in data['rows']if r['setup']is None);other=next(r for r in data['rows']if r['setup']=='swapped_bases');initial=GameSession(compiled);capture=GameSession.replay(compiled,deserialize_game_record(json.dumps(row['prefixes'][0]['record'])));ready=GameSession.replay(compiled,deserialize_game_record(json.dumps(row['root_record'])));after=GameSession.replay(compiled,deserialize_game_record(json.dumps(row['actual_record'])));swapped=GameSession.replay(compiled,deserialize_game_record(json.dumps(other['root_record'])));assert after.result.status.value=='checkmate'and after.result.winner==0
 tree=ast.parse(Path('results/dev_aux/task2354/pilot.py').read_text(encoding='utf-8-sig'));fn=next(n for n in ast.walk(tree)if isinstance(n,ast.FunctionDef)and n.name=='material');ns={'anchors':anchors};exec(compile(ast.Module(body=[fn],type_ignores=[]),'actual_frozen_pilot_material','exec'),ns);old=ns['material'];probes=[]
 for ratio in(.5,1.,1.5,2.,3.):
  table={'R':ratio,'P':1.};values=[material(s.state.position,0,table,excluded_type_ids=anchors)for s in(initial,capture,ready,after,swapped)];assert values[1]==values[2]==values[3];assert values[1]-values[0]==3*ratio-1;assert values[2]-values[4]==ratio-1;old_delta=old(after.state.position,0,ratio)-old(ready.state.position,0,ratio);assert old_delta==ratio-1
  for s in(initial,capture,ready,after,swapped):assert material(s.state.position,1,table,excluded_type_ids=anchors)==-material(s.state.position,0,table,excluded_type_ids=anchors)
  probes.append(dict(probe_R=ratio,probe_P=1.,old_pure_Rdrop_delta=old_delta,new_pure_Rdrop_delta=values[3]-values[2],actual_capture_promotion_delta=values[1]-values[0],hand_R_vs_P_context_delta=values[2]-values[4]))
 # Missing and nonfinite values must not silently become quantity1/zero.
 controls={}
 for name,table in(('missing_active_R',{'P':1.}),('nonfinite_R',{'R':float('inf'),'P':1.})):
  try:material(ready.state.position,0,table,excluded_type_ids=anchors)
  except ValueError:controls[name]='REJECTED'
  else:raise AssertionError(name)
 # Replay real closed TRAIN trajectories; no search/newgame reward queries.
 f=Path('results/dev_aux/task2358');p=json.loads((f/'plan.json').read_text());roots={r['index']:r for r in json.loads(Path(p['input']).read_text())};compiled_cache={};states=0;score_comparisons=0
 for game in map(json.loads,(f/'games.jsonl').read_text().splitlines()):
  stop();r=roots[game['root']]
  if r['rules']not in compiled_cache:
   d=deserialize_ruleset(Path(r['rules']).read_text());compiled_cache[r['rules']]=(compile_ruleset_for_execution(d),frozenset(t.type_id for t in d.piece_types if t.is_anchor))
  c,exclude=compiled_cache[r['rules']];s=GameSession(c);record=deserialize_game_record(json.dumps(game['record']))
  for action in [None]+list(record.actions):
   stop()
   if action is not None:s.submit(action)
   assert not any(h.total()for h in s.state.position.hands)and all(pc is None or(pc.base_type_id==pc.current_type_id and not pc.promoted)for pc in s.state.position.board)
   for ratio in(.5,1.,1.5,2.,3.):
    table={'R':ratio,'N':1.}
    for target in(0,1):assert material(s.state.position,target,table,excluded_type_ids=exclude)==old(s.state.position,target,ratio);score_comparisons+=1
   states+=1
 result=dict(status='PASS_REAL_COMPOSITE_SEMANTIC_MATERIAL_AND_CAPTURE_ONLY_PARITY',probes=probes,controls=controls,coefficients={name:features(s.state.position,0,excluded_type_ids=anchors)for name,s in(('initial',initial),('captured_promoted',capture),('aux_expired',ready),('actual_Rdrop_mate',after),('actual_Phand_other',swapped))},old_frozen_function_ast=ast.dump(fn),source_old_material_sha=hashlib.sha256(Path('results/dev_aux/task2354/pilot.py').read_bytes()).hexdigest(),replayed_closed_TRAIN_games=160,replayed_positions=states,price_perspective_comparisons=score_comparisons,seconds=time.perf_counter()-start,scope='Opt-in future materialcallback, NOTactive2354/2362policychange/newlearning/pricefit. ProbeRvalues fromexistinggrid/P1 are arbitrarytestparameters, notlearned orhumanlabels. Existingcapture-only resultsunaffected. RealhandR->boardR inventoryconstant whileactualdropcheckmates; materialinvarianceNOTequalpositionalutility. Capture/promotion/handBASEvsboardCURRENT preserved; auxlegality remainsCore and isnotencodedascontextmaterialvalue. ExcludedtypeIDs callerexplicit; notall-generated-domainprice/modeladequacyclaim. AllclosedTRAINreplayedonly, no newproofs/games/reservedperformance reads.')
 with(OUT/'result.json').open('x')as fp:json.dump(result,fp,indent=2)
 print(json.dumps({k:v for k,v in result.items()if k not in('old_frozen_function_ast','coefficients','probes')}));print(json.dumps(probes))
if __name__=='__main__':run()
