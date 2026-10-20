"""Outcome-blind mechanism-active pool for first task2433 rule variant with legal P-to-R witness."""
from __future__ import annotations
import datetime,hashlib,json,sys,time,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT))
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.session.session import GameSession
from results.dev_aux.task2621.fixed_scale import FixedScaleSessionEnv
from results.dev_aux.task2606.train import prefix
from tools.local_agent.environment import require_identity
OUT=ROOT/'results/dev_aux/task2626'
POOL=OUT/'rule1-root-pools.json'
RULE=ROOT/'results/dev_aux/task2433/rules-1.json';RULE_REL=RULE.relative_to(ROOT).as_posix()
TRAIN_RANGE=range(5_200_000,5_700_000);EVAL_RANGE=range(6_200_000,6_350_000)
SEED_RULE=2433001;PREFIX_PLIES=8;TRAIN_N=120;EVAL_N=16
HARD_SECONDS=6_600.0
STATUS=OUT/'rule1-root-preparation-status-v3.json'
HISTORY_FILES=(
 'results/dev_aux/task2525/queries.jsonl','results/dev_aux/task2525/episodes.jsonl',
 'results/dev_aux/task2565/generic/queries.jsonl','results/dev_aux/task2565/generic/games.jsonl',
 'results/dev_aux/task2565/generic/eval-queries.jsonl','results/dev_aux/task2565/generic/eval-games.jsonl',
 'results/dev_aux/task2606/queries.jsonl','results/dev_aux/task2606/games.jsonl','results/dev_aux/task2606/eval-queries.jsonl','results/dev_aux/task2606/eval-games.jsonl',
 'results/dev_aux/task2608/eval-queries.jsonl','results/dev_aux/task2608/eval-games.jsonl',
 'results/dev_aux/task2609/eval-queries.jsonl','results/dev_aux/task2609/eval-games.jsonl',
 'results/dev_aux/task2610/eval-queries.jsonl','results/dev_aux/task2610/eval-games.jsonl','results/dev_aux/task2610/attempt-2/eval-queries.jsonl','results/dev_aux/task2610/attempt-2/eval-games.jsonl',
 'results/dev_aux/task2618/learner-comparison-v2/queries.jsonl','results/dev_aux/task2618/learner-comparison-v2/games.jsonl',
 'results/dev_aux/task2618/learner-comparison-v3/queries.jsonl','results/dev_aux/task2618/learner-comparison-v3/games.jsonl',
 'results/dev_aux/task2621/active-feature-probe/queries.jsonl','results/dev_aux/task2621/cost-scan/queries.jsonl','results/dev_aux/task2621/cost-scan/episodes.jsonl',
 'results/dev_aux/task2622/run/queries.jsonl','results/dev_aux/task2622/run/episodes.jsonl','results/dev_aux/task2623/run/queries.jsonl','results/dev_aux/task2623/run/episodes.jsonl',
 'results/dev_aux/task2625/run/queries.jsonl','results/dev_aux/task2625/run/episodes.jsonl','results/dev_aux/task2625/run/eval-queries.jsonl','results/dev_aux/task2625/run/eval-games.jsonl')
MANIFESTS=('results/dev_aux/task2607/root-candidates.json','results/dev_aux/task2609/root-manifest.json',
 'results/dev_aux/task2610/root-manifest.json','results/dev_aux/task2622/root-pools.json',
 'results/dev_aux/task2622/root-pools-v2.json','results/dev_aux/task2624/root-pools-v2.json')
def sha(raw):return hashlib.sha256(raw).hexdigest()
def canon(obj):return json.dumps(obj,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
def row_records(row):
 for k in ('record_before','record_after','initial_record','final_record','record'):
  r=row.get(k)
  if isinstance(r,dict):yield r
def walk_records(v):
 if isinstance(v,dict):
  if isinstance(v.get('ruleset_fingerprint'),str) and isinstance(v.get('actions'),list):yield v
  for x in v.values():yield from walk_records(x)
 elif isinstance(v,list):
  for x in v:yield from walk_records(x)
def save_status(value):
 tmp=STATUS.with_suffix('.tmp')
 tmp.write_text(json.dumps(value,indent=2,sort_keys=True,ensure_ascii=False)+'\n',encoding='utf-8')
 tmp.replace(STATUS)

def main():
 require_identity();OUT.mkdir(parents=True,exist_ok=True)
 if POOL.exists():raise FileExistsError('rule1 root pool is write-once')
 began=time.perf_counter();raw_rule=RULE.read_bytes();compiled=compile_ruleset_for_execution(ruleset_from_dict(json.loads(raw_rule)))
 if STATUS.exists():raise FileExistsError('a prior rule1 pool preparation status exists; inspect it before any continuation')
 save_status({'status':'PREPARING_OUTCOME_BLIND_POOL','started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
  'rule_sha256':sha(raw_rule),'train_family_range':[TRAIN_RANGE.start,TRAIN_RANGE.stop],
  'evaluation_family_range':[EVAL_RANGE.start,EVAL_RANGE.stop],'required_roots':{'training':TRAIN_N,'evaluation':EVAL_N},
  'prefix_plies':PREFIX_PLIES,'joint_feature_rate_prior':'7/9069 ongoing roots in fixed rule1 10k-family screen',
  'hard_cap_seconds':HARD_SECONDS,'outputs_written':False})
 fingerprint=GameSession(compiled).to_record().ruleset_fingerprint;prior=set();receipts=[];occ_total=0
 existing=[rel for rel in HISTORY_FILES if (ROOT/rel).is_file()]
 missing=[rel for rel in HISTORY_FILES if not (ROOT/rel).is_file()]
 scan=subprocess.run(['rg','-F','-l','--no-ignore','--',fingerprint,*existing],cwd=ROOT,capture_output=True,check=False)
 if scan.returncode not in (0,1):raise RuntimeError(f'exact-fingerprint rg scan failed ({scan.returncode}): {scan.stderr.decode(errors="replace")[:500]}')
 matched=sorted(x.replace('\\','/') for x in scan.stdout.decode('utf-8').splitlines())
 receipts.append({'mode':'RG_EXACT_FINGERPRINT_SCAN','fingerprint':fingerprint,
  'searched_paths':existing,'searched_path_list_sha256':sha(canon(existing)),
  'missing_paths':missing,'matched_paths':matched,'rg_exit_code':scan.returncode,
  'scope':'Exact candidate ruleset fingerprint occurrences in the enumerated prior JSONL streams; only matching files are parsed as full records.'})
 for rel in matched:
  path=ROOT/rel;h=hashlib.sha256();rows=occ=0
  with path.open('rb') as f:
   for line in f:
    h.update(line)
    if not line.strip():continue
    rows+=1
    try:row=json.loads(line)
    except json.JSONDecodeError:continue
    for r in row_records(row):
     if r.get('ruleset_fingerprint')==fingerprint:prior.add(canon(r));occ+=1
  receipts.append({'path':rel,'status':'READ_MATCHING_JSONL','bytes':path.stat().st_size,
   'sha256':h.hexdigest(),'rows':rows,'candidate_record_occurrences':occ});occ_total+=occ
 for rel in missing:receipts.append({'path':rel,'status':'MISSING','candidate_record_occurrences':0})
 for rel in MANIFESTS:
  path=ROOT/rel
  if not path.is_file():receipts.append({'path':rel,'status':'MISSING','candidate_record_occurrences':0});continue
  raw=path.read_bytes();n=0
  for r in walk_records(json.loads(raw)):
   if r.get('ruleset_fingerprint')==fingerprint:prior.add(canon(r));n+=1
  receipts.append({'path':rel,'status':'READ_JSON_RECORDS_ONLY','bytes':len(raw),'sha256':sha(raw),'candidate_record_occurrences':n});occ_total+=n

 pre_path=ROOT/'results/dev_aux/task2433/inputs.json';pre_raw=pre_path.read_bytes();prefit=json.loads(pre_raw)
 prefit_candidate=[r['record'] for r in prefit if r['record'].get('ruleset_fingerprint')==fingerprint]
 prior.update(canon(r) for r in prefit_candidate)
 receipts.append({'path':'results/dev_aux/task2433/inputs.json','mode':'ALL_16_PREFIT_ROOTS','sha256':sha(pre_raw),'bytes':len(pre_raw),'records':len(prefit),'candidate_record_occurrences':len(prefit_candidate)})
 probe_path=OUT/'rule1-feature-probe-v2.json';probe_raw=probe_path.read_bytes();probe=json.loads(probe_raw)
 if probe.get('rule_sha256')!=sha(raw_rule) or probe.get('family_limit')!=10000 or probe['counts']['same_owner_all_three']<1:raise ValueError('rule1 same-owner feature screen source/coverage differs')
 receipts.append({'path':'results/dev_aux/task2626/rule1-feature-probe-v2.json','mode':'SCREENED_FAMILY_RANGE','sha256':sha(probe_raw),
  'screened_family_range':[0,10000],'records_persisted':False,'same_owner_eligible':probe['counts']['same_owner_all_three'],
  'outcome_blind_exposure_note':'Every deterministic family index in the first 10,000 screen is excluded by the disjoint 5.2M/6.2M selection ranges.'})
 screen_path=OUT/'task2433-variant-screen.json';screen_raw=screen_path.read_bytes();screen=json.loads(screen_raw)
 selected_row=next(r for r in screen['records'] if r['index']==1)
 if selected_row['status']!='WITNESS_FOUND':raise ValueError('rule1 mechanism witness missing')
 witness=selected_row['witness']['record']
 if witness.get('ruleset_fingerprint')!=fingerprint:raise ValueError('fixed-index witness rule fingerprint mismatch')
 prior.add(canon(witness))
 receipts.append({'path':'results/dev_aux/task2626/task2433-variant-screen.json','mode':'FIXED_ORDER_WITNESS','sha256':sha(screen_raw),'selected_witness_full_record_sha256':sha(canon(witness)),'selected_witness_plies':len(witness.get('actions',[])),'candidate_record_occurrences':1})
 control_path=ROOT/'results/dev_aux/task2411/inputs.json';control_raw=control_path.read_bytes();controls=json.loads(control_raw)
 control_records=[r['record'] for r in controls]
 # Separate control rules have different full ruleset fingerprints.
 if any(r.get('ruleset_fingerprint')==fingerprint for r in control_records):raise ValueError('task2411 control unexpectedly matches rule1 fingerprint')
 receipts.append({'path':'results/dev_aux/task2411/inputs.json','mode':'DISTINCT_RULE_CONTROL','sha256':sha(control_raw),'records':len(control_records),'fingerprints':sorted({r.get('ruleset_fingerprint') for r in control_records})})

 def candidate(family):
  env=FixedScaleSessionEnv(GameSession(compiled));prefix(env,SEED_RULE,family,PREFIX_PLIES);rec=env.record()
  if len(rec.get('actions',[]))!=PREFIX_PLIES or env.terminal() is not None:return None
  env.replay();pos=env.session.state.position
  owner_data=[]
  for owner in (0,1):
   rhand=sum(n for base,n in pos.hands[owner].counts if base=='R')
   rboard=sum(1 for p in pos.board if p is not None and p.owner==owner and p.current_type_id=='R')
   prom=sum(1 for p in pos.board if p is not None and p.owner==owner and p.base_type_id=='P' and p.current_type_id=='R')
   if rhand and rboard and prom:owner_data.append((owner,rhand,rboard,prom))
  if not owner_data:return None
  owner,rhand,rboard,prom=owner_data[0]
  return rec,list(env.features()),[list(x) for x in env.names],owner,rhand,rboard,prom
 def select(families,count,excluded,label):
  selected=[];seen=set();tested=invalid=overlap=duplicate=unexcited=0
  for family in families:
   elapsed=time.perf_counter()-began
   if elapsed>=HARD_SECONDS:
    state={'status':'HARD_CAP_REACHED_NO_POOL','phase':label,'current_family':family,'tested_families':tested,
     'selected':len(selected),'invalid_terminal_or_unexcited':invalid,'prior_exact_history_rejections':overlap,
     'within_pool_duplicates':duplicate,'elapsed_seconds':elapsed,'outputs_written':False}
    save_status(state);print(json.dumps(state,sort_keys=True),flush=True)
    raise TimeoutError(f"{label} preparation reached cap after {tested} families; selected {len(selected)}/{count}")
   item=candidate(family);tested+=1
   if item is None:invalid+=1
   else:
    rec,features,channels,owner,rh,rb,pr=item;key=canon(rec)
    if key in excluded:overlap+=1
    elif key in seen:duplicate+=1
    else:
     seen.add(key);selected.append({'rule_index':1,'generator_seed':SEED_RULE,'family':family,'record':rec,'record_sha256':sha(key),
      'features':features,'channels':channels,'same_owner':owner,'R_hand_count':rh,'R_board_count':rb,'promoted_P_count':pr})
   if len(selected)==count:break
   if tested%25000==0:
    state={'status':'PREPARING_OUTCOME_BLIND_POOL','phase':label,'current_family':family,'tested_families':tested,
     'selected':len(selected),'invalid_terminal_or_unexcited':invalid,'prior_exact_history_rejections':overlap,
     'within_pool_duplicates':duplicate,'elapsed_seconds':elapsed,'outputs_written':False}
    save_status(state);print(json.dumps(state,sort_keys=True),flush=True)
  if len(selected)!=count:
   state={'status':'FAILED_POOL_SHORT_NO_POOL','phase':label,'current_family':families.stop-1,'tested_families':tested,
    'selected':len(selected),'required':count,'invalid_terminal_or_unexcited':invalid,
    'prior_exact_history_rejections':overlap,'within_pool_duplicates':duplicate,
    'elapsed_seconds':time.perf_counter()-began,'outputs_written':False}
   save_status(state);print(json.dumps(state,sort_keys=True),flush=True)
   raise RuntimeError(f"{label} pool short: {len(selected)}/{count} in {tested} families; invalid={invalid} overlap={overlap} duplicate={duplicate}")
  return selected,{'family_range':[families.start,families.stop],'selected':len(selected),'families_tested':tested,
   'invalid_terminal_or_unexcited':invalid,'prior_exact_history_rejections':overlap,'within_pool_duplicates':duplicate}
 training,tstat=select(TRAIN_RANGE,TRAIN_N,prior,'training')
 trainkeys={canon(x['record']) for x in training}
 evaluation,estat=select(EVAL_RANGE,EVAL_N,prior|trainkeys,'evaluation')
 result={'status':'OUTCOME_BLIND_MECHANISM_ACTIVE_ROOTS_PREPARED_NOT_REGISTERED',
  'candidate':{'path':RULE_REL,'index':1,'sha256':sha(raw_rule),'ruleset_fingerprint':fingerprint,
    'selection_reason':'First fixed-index task2433 ruleset after rule0 with a legal full-history P-to-R transition witness; no outcome/search/model fields.'},
  'selection_inputs':{'history_sources':receipts,'prior_unique_exact_candidate_histories':len(prior),
    'task2433_prefit_root_count':len(prefit),'task2433_prefit_candidate_roots':len(prefit_candidate),
    'fixed_order_screen_sha256':sha(screen_raw),'fixed_order_witness_plies':len(witness['actions'])},
  'prefix_plies':PREFIX_PLIES,'feature_policy':'Every root is ongoing after8 plies and one same owner has an R in hand, a current-type R on board, and a P-base/R-current promoted piece; this enables that owner to use a hand-R-unlocking move and activates the promotion material channel. No auxiliary-state guard claim.',
  'training':tstat,'evaluation':estat,'training_roots':training,'evaluation_roots':evaluation,
  'exact_train_evaluation_overlap':0,'preparation_seconds':time.perf_counter()-began,
  'limitations':['Exact full-record exclusion covers only enumerated prior Generic streams, task2433 prefit roots and the saved mechanism witness. No transposition, descendant-state or distributional independence claim.',
    'The auxiliary bit is written/expired but no rule guard reads it; this panel does not test aux-conditioned decisions.',
    'Root selection uses legal feature activation, not a fitness label; selected histories are exposed development evidence after preparation.',
    'No registration, training or actual W/L/D evaluation is created by this file.']}
 raw=json.dumps(result,indent=2,sort_keys=True,ensure_ascii=False,allow_nan=False).encode()+b'\n'
 with POOL.open('xb') as f:f.write(raw)
 save_status({'status':'COMPLETE_PREPARED_NOT_REGISTERED','pool_sha256':sha(raw),
  'training_selected':len(training),'evaluation_selected':len(evaluation),
  'preparation_seconds':result['preparation_seconds'],'outputs_written':True})
 print(json.dumps({'status':result['status'],'training':tstat,'evaluation':estat,'prior_unique_histories':len(prior),
  'preparation_seconds':result['preparation_seconds'],'root_pool_sha256':sha(raw)},indent=2))
if __name__=='__main__':main()
