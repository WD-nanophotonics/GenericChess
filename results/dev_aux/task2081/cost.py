"""Actual evaluator dispatch cost and an equivalent cheap material reference."""
from pathlib import Path
from collections import defaultdict
import json,time,statistics
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from results.dev_aux.task2063.campaign import evaluator
OUT=Path('results/dev_aux/task2081')
def run():
 p=json.loads(Path('results/dev_aux/task2076/plan.json').read_text());models=json.loads(Path('results/dev_aux/task2060/models.json').read_text());states=[]
 for case in p['cases']:
  c=compile_ruleset_for_execution(deserialize_ruleset(Path(case['rules']).read_text()));s=GameSession.replay(c,deserialize_game_record(json.dumps(case['record'])));states.append((s.state.position,case['expected_side']))
 material=evaluator(models['material']);kingpiece=evaluator(models['kingpiece']);w=models['material']
 def direct(pos,target):return 720*sum((1 if p.owner==target else -1)*(w[0]if p.current_type_id=='N'else w[1]if p.current_type_id=='B'else 0.)for p in pos.board if p is not None)
 for pos,target in states:
  for side in(0,1):assert abs(material(pos,side)-direct(pos,side))<1e-9
 funcs=dict(shared_feature_material=material,direct_material=direct,shared_feature_kingpiece=kingpiece);timings=defaultdict(list);sums={};reps=1000;start=time.perf_counter()
 for round in range(4):
  for name in(list(funcs)if round%2==0 else list(funcs)[::-1]):
   beg=time.perf_counter();checksum=0.
   for _ in range(reps):
    for pos,target in states:checksum+=funcs[name](pos,target)
   timings[name].append(time.perf_counter()-beg);sums[name]=checksum
 assert abs(sums['shared_feature_material']-sums['direct_material'])<1e-6
 result=dict(status='COMPLETE_PAIRED_COUNTERBALANCED_EVALUATOR_MICROCOST',states=len(states),calls_per_arm=4*reps*len(states),seconds={k:v for k,v in timings.items()},median_seconds_per_call={k:statistics.median(v)/(reps*len(states))for k,v in timings.items()},material_value_equivalent_all_cases_both_targets=True,seconds_total=time.perf_counter()-start,scope='Normal2063campaign intentionallyshares fullfeaturebuilder forALLmodels, so its materialbaselineisnot optimizedendtoendcost. Thisboundedmicrocost hasordinaryconcurrentloads; noexclusiveCPU/speedclaim or activepolicychange/automaticgame rerun.')
 (OUT/'result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
if __name__=='__main__':run()
