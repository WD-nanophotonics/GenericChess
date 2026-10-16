from pathlib import Path
from copy import copy
import sys,json,time,hashlib
R=Path.cwd();P=R/'.local_agent/alias-teacher-20261016';sys.path[:0]=[str(R),str(P)]
from core_teacher import SearchMetadataAdapter,compile_legacy_ruleset_for_semantic_execution,deserialize_ruleset,deserialize_game_record,GameSession,record_value
from generic_chess.native.compiler import compile_native_semantic_rules
from generic_chess.native.adapter import pack_semantic_search_position
from generic_chess.native.semantic import dynamic_features
from generic_chess.learning.nonlinear import semantic_state_features
from generic_chess.core.transition import apply_action
plan=dict(question='Does measured dynamic-input dominance persist at public root/oneply states separately from dense packing?',cases=json.loads((P/'finite-teacher-plan.json').read_bytes())['cases'],children_per_root=8,repetitions=2,whole_seconds=45,expected_seconds=8,selection='SHA256dependency20261016|canonicalaction before new timings, no label selection',scope='Component calls only, nosearch/game/fit or productedit. Existingfullroots andalreadycheckedchildren, notpopulation/leafmix estimate. No result licenses omittingdynamicfeatures orchangingtrainedfunctional.')
(P/'input-dependency-plan.json').write_text(json.dumps(plan,indent=2)+'\n');rows=[];start=time.perf_counter()
for case in plan['cases']:
 d=json.loads((P/case['root']).read_bytes());c0=compile_legacy_ruleset_for_semantic_execution(deserialize_ruleset(json.dumps(d['ruleset'])));c=SearchMetadataAdapter(ir=c0.ir,_legacy_compiled=c0._legacy_compiled,support=c0.support);n=compile_native_semantic_rules(c);s=GameSession.replay(c,deserialize_game_record(json.dumps(d['game_record'])));aa=sorted(s.legal_actions(),key=lambda a:hashlib.sha256(('dependency20261016|'+json.dumps(record_value(a),sort_keys=True)).encode()).hexdigest())[:8]
 states=[(None,s)]
 for a in aa:
  child=copy(s);child.submit(a);states.append((a,child))
 for a,ss in states:
  state=ss.state
  if time.perf_counter()-start>45:raise RuntimeError('whole cap; partial preserved, noextend')
  measurements=[];vals=[]
  for rep in range(2):
   t=time.perf_counter();packed=pack_semantic_search_position(c,n,ss);pack=time.perf_counter()-t;t=time.perf_counter();v=dynamic_features(n,packed);dynamic=time.perf_counter()-t;t=time.perf_counter();f=semantic_state_features(state.position,c,v);features=time.perf_counter()-t;vals.append(v);measurements.append(dict(pack_seconds=pack,dynamic_seconds=dynamic,dense_input_seconds=features,dimension=len(f)))
  assert vals[0]==vals[1];rows.append(dict(seed=case['seed'],board=case['board'],action=record_value(a),state_sha256=hashlib.sha256(json.dumps(record_value(state),sort_keys=True).encode()).hexdigest(),dynamic_values=vals[0],measurements=measurements));(P/'input-dependency-progress.json').write_text(json.dumps(dict(complete=False,rows=rows)))
x=dict(complete=True,rows=rows,seconds=time.perf_counter()-start,search_queries=0,games=0,scope=plan['scope']);(P/'input-dependency-results.json').write_text(json.dumps(x,indent=2)+'\n');print('INPUT_DEPENDENCY',len(rows),x['seconds'])
