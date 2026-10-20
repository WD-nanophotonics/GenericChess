from pathlib import Path
from collections import Counter
import datetime,hashlib,json,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[3]))
from results.dev_aux.task2492.adapters import ChessEnv
from results.dev_aux.task2565.train import prefix,model
TASK=Path('results/dev_aux/task2616');ROOT=Path.cwd()
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def canon(x):return json.dumps(x,sort_keys=True,separators=(',',':'))
# Reuse only fixed, already frozen Chess TD and finite-WDL endpoints from task2568.
base=Path('results/dev_aux/task2568'); bp=json.loads((base/'plan.json').read_text()); br=json.loads((base/'result.json').read_text())
assert bp['domain']=='chess' and bp['foe']==[1.0]*5 and bp['depth']==2 and bp['prefix_plies']==8
assert bp['nodes_per_arm']==1_000_000 and bp['nodes_per_game']==25_000 and bp['nodes_per_query']==8192
seeds=[1977,8173,27182,31415]
models={}
for a in br['arms']:
 if a['method'] in ('TD','WDL'):
  assert a['seed'] not in models.setdefault(a['method'],{})
  assert a['nodes']==1_000_000
  models[a['method']][a['seed']]=a
assert set(models)=={'TD','WDL'} and all(set(v)==set(seeds) for v in models.values())
for seed in seeds:
 r=__import__('random').Random(seed); expected=[1.0]+[r.uniform(.5,1.5) for _ in range(4)]
 assert models['TD'][seed]['initial']==models['WDL'][seed]['initial']==expected
# Index all prior full starting histories on registered standard-Chess evaluation panels.
old_roots={};old_sources=[]
for plan_path in sorted(Path('results/dev_aux').rglob('eval-plan.json')):
 p=json.loads(plan_path.read_text(encoding='utf-8'))
 if p.get('domain')!='chess' or 0 not in p.get('rules',[]):continue
 games=plan_path.parent/'eval-games.jsonl'
 if not games.exists():continue
 n=0
 for line in games.open(encoding='utf-8-sig'):
  row=json.loads(line);rec=row.get('initial_record')
  if rec is None:continue
  key=canon(rec);old_roots.setdefault(key,[]).append({'source':games.as_posix(),'slot':row.get('slot')});n+=1
 old_sources.append({'plan':plan_path.as_posix(),'plan_sha256':sha(plan_path),'games':games.as_posix(),'games_sha256':sha(games),'rows':n})
# Add every possible eight-ply training start under the frozen max_games schedule.
train_root_ids=range(bp['training_family_offset'],bp['training_family_offset']+(bp['max_games']+1)//2)
train_roots={}
for family in train_root_ids:
 e=ChessEnv();prefix(e,0,family,bp['prefix_plies']);rec=e.record()
 if len(rec['moves'])==bp['prefix_plies']:
  train_roots[canon(rec)]=family
# Exact full records are the disjointness unit. The candidate generation is outcome-blind.
selected=[];seen=set();examined=[]
for family in range(700001,710001):
 e=ChessEnv();prefix(e,0,family,bp['prefix_plies']);rec=e.record()
 if len(rec['moves'])!=bp['prefix_plies']:continue
 key=canon(rec)
 examined.append(family)
 if key in seen or key in old_roots or key in train_roots:continue
 seen.add(key);selected.append({'family':family,'record':rec,'record_sha256':hashlib.sha256(key.encode()).hexdigest()})
 if len(selected)==32:break
assert len(selected)==32
# Four endpoints x four frozen model seeds x 32 roots x both colors = 1024 matched slots.
slots=[]
for item in selected:
 for seed in seeds:
  for color in (0,1):
   for endpoint in ('initial','TD','WDL','TreeStrap'):
    slots.append([0,seed,item['family'],color,endpoint,'uniform'])
root_manifest={'status':'FROZEN_OUTCOME_BLIND_CHESS_ROOTS','prefix_plies':8,'unit':'exact complete ChessEnv record (initial FEN plus ordered UCI history)','count':len(selected),'roots':selected,'prior_eval_unique_records':len(old_roots),'possible_train_unique_records':len(train_roots),'possible_train_root_sha256s':sorted(hashlib.sha256(k.encode()).hexdigest() for k in train_roots),'candidate_families_examined':examined}
(TASK/'root-manifest.json').write_text(json.dumps(root_manifest,indent=2,sort_keys=True)+'\n')
# Cost estimates are source-bound projections, not strength claims or runtime guarantees.
cost_scan=Path('results/dev_aux/task2612/attempt-4/result.json')
if not cost_scan.exists(): cost_scan=Path('results/dev_aux/task2612/attempt-4/arms.jsonl')
scan_json=None
scan_rows=[]
if cost_scan.suffix=='.json':scan_json=json.loads(cost_scan.read_text())
else:scan_rows=[json.loads(x) for x in cost_scan.read_text().splitlines() if x]
if scan_json and 'arms' in scan_json:scan_rows=scan_json['arms']
tree_rows=[x for x in scan_rows if x.get('method') in ('TreeStrap','tree')]
if not tree_rows:tree_rows=[x for x in scan_rows if x.get('learner')=='TreeStrap']
# Bound estimate from the frozen comparison already in task2614 (same TrainingSearch implementation).
prev=json.loads(Path('results/dev_aux/task2568/design-costs.json').read_text())
eval_seconds=prev['components']['2568_EVAL_seconds']+prev['components']['2570_EVAL_seconds'];eval_slots=prev['panels']['2568']['executed']+prev['panels']['2570']['executed']
eval_mean=eval_seconds/eval_slots
# The later task2612 scan used a different AlphaBeta adapter; retain only its conservative recorded whole-run cost as an upper engineering proxy.
scan_seconds=111.982;scan_nodes=800_000;tree_projection=scan_seconds*(4_000_000/scan_nodes)
eval_projection=eval_mean*len(slots)
setup_audit_reserve=600
new_expected=tree_projection+eval_projection+setup_audit_reserve
# Sunk historical producer cost is shown separately; don't use it as the single-run preassessment threshold.
result={'task':'DEV_AUX2616','status':'REGISTERED_BEFORE_NEW_TREE_TRAINING_OR_EVALUATION','registered_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'question':'Under the same fixed-foe Chess TrainingSearch, initialization, 1M nodes/seed and fresh matched evaluation roots, does TreeStrap differ in actual terminal W/L from the already frozen TDLeaf and finite one-coordinate WDL endpoints?','reuse':{'TD_and_WDL':'Frozen task2568 endpoints reused without retraining or outcome-based selection; their source run used the same TrainingSearch, exact initial seed values, fixed uniform foe and 1M nodes/seed.','TreeStrap':'Only newly trained endpoint; same seed initial values and task2568 Chess training recipe.'},'conditions':{'domain':'standard Chess through python-chess complete game rules','seeds':seeds,'initialization':'task2568 fixed Random(seed), pawn coefficient=1, four other coefficients uniform[0.5,1.5]','training':{'node_budget_per_seed_both_actors':1_000_000,'depth':bp['depth'],'q_limit':bp.get('q_limit',2),'H':bp['H'],'nodes_per_game':bp['nodes_per_game'],'nodes_per_query':bp['nodes_per_query'],'seconds_per_query':bp['seconds_per_query'],'fixed_foe':bp['foe'],'opening_prefix_plies':bp['prefix_plies'],'max_games_per_seed':bp['max_games'],'method':'TreeStrap on candidate-color complete TrainingSearch receipts only; incomplete receipts censored; all candidate+foe nodes paid'},'evaluation':{'slots':len(slots),'roots':len(selected),'endpoints':['initial','TD','WDL','TreeStrap'],'colors':[0,1],'foe':'uniform','depth':bp['depth'],'q_limit':bp.get('q_limit',2),'H':bp['H'],'node_budget_per_slot_both_sides':20_000,'max_nodes_per_query':8192,'seconds_per_query':2.0,'global_hard_cap_seconds':3600,'unknown':'Censored. Paired interval retains known rewards and ranges only UNKNOWN endpoint rewards over [-1,+1].'},'root_disjointness':'Exact ChessEnv complete record; new 8-ply roots exclude all registered Chess eval-game starts and all 5,000 possible TreeStrap training-family starts under the frozen prefix recipe.'},'cost_estimate':{'basis':'task2612 attempt-4 shared learner cost 800k nodes/111.982s scaled to 4M nodes; task2568 TrainingSearch evaluation mean from 768 completed slots scaled to 1,024; 600s setup/audit reserve. These are estimates, not a strength forecast.','tree_4m_nodes_expected_seconds':tree_projection,'eval_seconds_per_slot_historical_mean':eval_mean,'new_1024_slot_eval_expected_seconds':eval_projection,'setup_audit_reserve_seconds':setup_audit_reserve,'incremental_expected_seconds':new_expected,'incremental_expected_minutes':new_expected/60,'threshold':'Expected new execution is under 120m; no Dot preassessment required. Frozen search/eval caps remain unchanged once started; preserve any missing/UNKNOWN slots.'},'slot_count':len(slots),'sources':{'task2568_plan_sha256':sha(base/'plan.json'),'task2568_result_sha256':sha(base/'result.json'),'task2568_design_costs_sha256':sha('results/dev_aux/task2568/design-costs.json'),'task2568_search_sha256':bp['pins']['results/dev_aux/task2504/search.py'],'task2568_learning_sha256':bp['pins']['results/dev_aux/task2492/learning.py'],'task2612_cost_scan_sha256':sha(cost_scan),'task2568_prior_eval_panels':old_sources}}
result['budget']={'expected_new_run_seconds':new_expected,'expected_new_run_minutes':new_expected/60,'hard_cap_seconds':1200+3600+600,'historical_baseline_producer_seconds':prev['listed_producer_seconds'],'historical_plus_incremental_expected_seconds':prev['listed_producer_seconds']+new_expected}
# Add a self-contained eval plan, immutable registration, and started-style source/plan pins before any run.
eval_plan={'task':'DEV_AUX2616','status':'FROZEN_NOT_STARTED','domain':'chess','rules':[0],'seeds':seeds,'endpoints':['initial','TD','WDL','TreeStrap'],'foes':['uniform'],'slots':slots,'root_manifest_sha256':sha(TASK/'root-manifest.json'),'prefix_plies':8,'depth':bp['depth'],'q_limit':bp.get('q_limit',2),'H':bp['H'],'nodes_per_query':8192,'seconds_per_query':2.0,'node_budget_per_slot_both_actors':20_000,'global_cap_seconds':3600,'unknown_policy':'censored with endpoint-specific [-1,+1] completion interval','scope':'finite fixed-policy comparison only; no population or broad learning claim'}
(TASK/'eval-plan.json').write_text(json.dumps(eval_plan,indent=2,sort_keys=True)+'\n')
result['sources']['root_manifest_sha256']=sha(TASK/'root-manifest.json');result['sources']['eval_plan_sha256']=sha(TASK/'eval-plan.json')
result['sources']['prepare_script_sha256']=sha(Path(__file__))
result['budget']['expected_new_run_seconds']=new_expected
result['budget']['expected_new_run_minutes']=new_expected/60
result['budget']['hard_cap_seconds']=1200+3600+600
result['budget']['historical_baseline_producer_seconds']=prev['listed_producer_seconds']
result['budget']['historical_plus_incremental_expected_seconds']=prev['listed_producer_seconds']+new_expected
(TASK/'plan.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
reg={'task':'DEV_AUX2616','status':'REGISTERED_PRE_RUN','science':'OPEN','registered_at_utc':result['registered_at_utc'],'plan_sha256':sha(TASK/'plan.json'),'eval_plan_sha256':sha(TASK/'eval-plan.json'),'root_manifest_sha256':sha(TASK/'root-manifest.json'),'no_training_yet':True,'no_evaluation_yet':True}
(TASK/'registration.json').write_text(json.dumps(reg,indent=2,sort_keys=True)+'\n')
print(json.dumps({'status':result['status'],'roots':len(selected),'old_eval_roots':len(old_roots),'training_roots':len(train_roots),'slots':len(slots),'tree_projection_s':tree_projection,'eval_projection_s':eval_projection,'new_expected_s':new_expected,'new_expected_min':new_expected/60,'historical_plus_expected_min':(prev['listed_producer_seconds']+new_expected)/60,'old_eval_panels':len(old_sources),'plan_sha256':sha(TASK/'plan.json'),'eval_plan_sha256':sha(TASK/'eval-plan.json')},indent=2))




