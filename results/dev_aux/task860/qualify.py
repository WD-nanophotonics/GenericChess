import json,sys,time,hashlib,re,os
from pathlib import Path
R=Path.cwd();O=R/'results/dev_aux/task861';O.mkdir(exist_ok=False)
for n in [360,364,381,509]:sys.path.insert(0,str(R/f'results/dev_aux/task{n}'))
import adapter as A
from warm_adapter import ControlledEngine
assert json.loads((R/'results/dev_aux/task839/result.json').read_bytes())['status']=='PASS_ALL64_QUERY_PV_AND_TRACE_MATERIAL_OBSERVATIONS';old=[json.loads(l) for l in (R/'results/dev_aux/task838/queries.jsonl').open(encoding='utf-8') if json.loads(l)['mode']=='original'];assert len(old)==32;plan=dict(status='FROZEN_BEFORE32_NEW_QUERIES',baseline_source='task838/queries.jsonl original32 fully839qualified',baseline_sha256=hashlib.sha256((R/'results/dev_aux/task838/queries.jsonl').read_bytes()).hexdigest(),new_executable_sha256=hashlib.sha256((R/'.local_agent/dualprice38/dual.exe').read_bytes()).hexdigest(),environment_leaf_override=False,scope='Samecold16positions2budgets; reusequalifiedoldoriginalcontrols exactinputs,32NEWqueries noENV. Comparebestmove/finalcp onlynotwalltime. Allactualmaterial/PVvalidate.')
(O/'plan.json').write_text(json.dumps(plan,indent=2),encoding='utf-8');A.EXE=R/'.local_agent/dualprice38/dual.exe';assert 'DEV_AUX_EVAL_VALUES' not in os.environ;pairs=[];start=time.monotonic()
with (O/'queries.jsonl').open('w',encoding='utf-8') as j:
 for a in old:
  e=ControlledEngine(a['weights'],None,'cold_per_query')
  try:q=e.search(a['initial_sfen'],a['history'],a['nodes_limit']);A.validate_search(q);q.update(case_index=a['case_index'],price_ack=e.prices);j.write(json.dumps(q)+'\n');j.flush();os.fsync(j.fileno())
  finally:e.close()
  info=lambda z:[l for l in z['lines'] if ' score ' in l][-1];value=lambda l:re.search(r' score (?:cp|mate) (-?\d+)',l).group(0);eqmove=a['bestmove']==q['bestmove'];eqscore=value(info(a))==value(info(q));pairs.append(dict(case_index=a['case_index'],nodes=a['nodes_limit'],bestmove_equal=eqmove,score_equal=eqscore,original_final=info(a),dual_final=info(q)));assert eqmove and eqscore,pairs[-1]
result=dict(status='PASS_ALL32_DUAL_NO_OVERRIDE_VS_QUALIFIED_ORIGINAL',actual_new_go=32,cached_comparison_controls=32,seconds=time.monotonic()-start,pairs=pairs);(O/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(result['status'],round(result['seconds'],3))
