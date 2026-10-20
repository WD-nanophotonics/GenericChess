"""Outcome-blind successor pool; exact-history inventory is hash-pinned first."""
from __future__ import annotations
import datetime,hashlib,json,sys,time,gzip
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'.local_agent/devaux_pydeps'));sys.path.insert(0,str(ROOT))
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.session.session import GameSession
from results.dev_aux.task2621.fixed_scale import FixedScaleSessionEnv
from results.dev_aux.task2606.train import prefix
from tools.local_agent.environment import require_identity
OUT=ROOT/'results/dev_aux/task2627'
POOL=OUT/'rule15-successor-root-pools.json'
INVENTORY=OUT/'source-inventory-v2.json'
COST_BOUND=OUT/'successor-cost-bound.json'
RULE=ROOT/'results/dev_aux/task2433/rules-15.json';RULE_REL=RULE.relative_to(ROOT).as_posix()
TRAIN_RANGE=range(140_000,260_000);EVAL_RANGE=range(280_000,300_000)
SEED_RULE=2433017;PREFIX_PLIES=8;TRAIN_N=120;EVAL_N=16
HARD_SECONDS=180.0
STATUS=OUT/'successor-root-preparation-status.json'
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
 if POOL.exists():raise FileExistsError('rule15 root pool is write-once')
 if (TRAIN_RANGE.start,TRAIN_RANGE.stop)==(10_000,110_000) or (EVAL_RANGE.start,EVAL_RANGE.stop)==(120_000,140_000):raise ValueError('successor ranges must be new')
 if max(TRAIN_RANGE.start,120_000)<min(TRAIN_RANGE.stop,140_000) or max(EVAL_RANGE.start,10_000)<min(EVAL_RANGE.stop,110_000):raise ValueError('successor range overlaps an old registered range')
 prior_attempts=[];prior_elapsed=0.0
 if STATUS.exists():
  previous=json.loads(STATUS.read_text(encoding='utf-8'))
  if previous.get('status')!='FAILED_INPUT_REPLAY_NO_POOL' or previous.get('outputs_written') is not False:
   raise FileExistsError('a prior rule15 pool preparation status exists; inspect it before any continuation')
  prior_attempts=previous.get('prior_attempts',[])+[{k:v for k,v in previous.items() if k!='prior_attempts'}]
  prior_elapsed=float(previous.get('elapsed_seconds',0.0))
  if prior_elapsed>=HARD_SECONDS:raise TimeoutError('cumulative preparation cap already exhausted; no pool written')
 began=time.perf_counter();raw_rule=RULE.read_bytes();compiled=compile_ruleset_for_execution(ruleset_from_dict(json.loads(raw_rule)))
 bound_raw=COST_BOUND.read_bytes();bound=json.loads(bound_raw)
 if bound.get('status')!='PREPARATION_COST_BOUND_BEFORE_SUCCESSOR_POOL' or bound['candidate_rule']['sha256']!=sha(raw_rule):raise ValueError('source-bound pre-pool cost record mismatch')
 if bound['cost_bound_seconds']['conservative_total']>min(bound['cost_bound_seconds']['all_in_hard_cap'],bound['cost_bound_seconds']['chat_assessment_threshold']):raise ValueError('successor experiment exceeds the existing authorized budget')
 save_status({'status':'PREPARING_OUTCOME_BLIND_POOL','started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
  'rule_sha256':sha(raw_rule),'train_family_range':[TRAIN_RANGE.start,TRAIN_RANGE.stop],
  'evaluation_family_range':[EVAL_RANGE.start,EVAL_RANGE.stop],'required_roots':{'training':TRAIN_N,'evaluation':EVAL_N},
  'prefix_plies':PREFIX_PLIES,'joint_feature_rate_prior':'455/9433 ongoing roots in source-pinned rule15 seed2433016 10k-family screen',
    'hard_cap_seconds':HARD_SECONDS,'cumulative_prior_attempt_seconds':prior_elapsed,'prior_attempts':prior_attempts,
    'cost_bound_sha256':sha(bound_raw),'outputs_written':False})
 fingerprint=GameSession(compiled).to_record().ruleset_fingerprint;prior=set();receipts=[];occ_total=0
 inv_raw=INVENTORY.read_bytes();inv=json.loads(inv_raw)
 if inv.get('status')!='DYNAMIC_EXACT_HISTORY_INVENTORY_ONLY_NO_ROOTS_WRITTEN' or inv['candidate']['ruleset_fingerprint']!=fingerprint:
  raise ValueError('dynamic exact-history inventory status/fingerprint mismatch')
 for source in inv['matched_sources']:
  path=ROOT/source['path'];raw_hash=hashlib.sha256()
  with path.open('rb') as stream:
   for block in iter(lambda:stream.read(1024*1024),b''):raw_hash.update(block)
  if raw_hash.hexdigest()!=source['sha256']:raise ValueError(f"source changed after inventory: {source['path']}")
  count=0
  if source['record_occurrences']:
   if path.suffix.lower()=='.jsonl':
    with path.open('rb') as stream:
     for line in stream:
      if fingerprint.encode() not in line:continue
      row=json.loads(line)
      for record in walk_records(row):
       encoded=canon(record);prior.add(encoded);count+=1
   else:
    for record in walk_records(json.loads(path.read_text(encoding='utf-8'))):
     if record.get('ruleset_fingerprint')!=fingerprint:continue
     encoded=canon(record);prior.add(encoded);count+=1
  if count!=source['record_occurrences']:raise ValueError(f"record occurrence count changed: {source['path']}")
  receipts.append({'path':source['path'],'sha256':source['sha256'],'record_occurrences':count,
   'unique_records_in_file':source['unique_records_in_file'],'status':'SOURCE_HASH_AND_RECORD_COUNT_MATCH'})
 if sorted(sha(record) for record in prior)!=inv['unique_record_sha256']:
  raise ValueError('reconstructed exact-history set differs from dynamic inventory')
 if inv['matched_compressed_sources']:
  raise ValueError('compressed exact-history sources need explicit selector support before preparation')
 receipts.append({'path':INVENTORY.relative_to(ROOT).as_posix(),'sha256':sha(inv_raw),
  'enumerated_plain_files':inv['enumeration']['plain_files'],'enumerated_compressed_files':inv['enumeration']['compressed_files'],
  'matched_plain_files':inv['enumeration']['matched_plain_files'],'matched_compressed_files':len(inv['matched_compressed_sources']),
  'unique_exact_histories':len(prior),'mode':'HASH_PINNED_DYNAMIC_EXACT_HISTORY_INVENTORY'})
 occ_total=sum(source['record_occurrences'] for source in inv['matched_sources'])+sum(source['record_occurrences'] for source in inv['matched_compressed_sources'])

 pre_path=ROOT/'results/dev_aux/task2433/inputs.json';pre_raw=pre_path.read_bytes();prefit=json.loads(pre_raw)
 prefit_candidate=[r['record'] for r in prefit if r['record'].get('ruleset_fingerprint')==fingerprint]
 prior.update(canon(r) for r in prefit_candidate)
 receipts.append({'path':'results/dev_aux/task2433/inputs.json','mode':'ALL_16_PREFIT_ROOTS','sha256':sha(pre_raw),'bytes':len(pre_raw),'records':len(prefit),'candidate_record_occurrences':len(prefit_candidate)})
 attempts_path=ROOT/'results/dev_aux/task2433/generation-attempts.json';attempts_raw=attempts_path.read_bytes();attempts=json.loads(attempts_raw)
 receipts.append({'path':'results/dev_aux/task2433/generation-attempts.json','mode':'GENERATION_ATTEMPT_HISTORY','sha256':sha(attempts_raw),'attempts':len(attempts),'outcomes_used':False})
 probe_path=ROOT/'results/dev_aux/task2626/rule15-feature-probe-seed2433016.json';probe_raw=probe_path.read_bytes();probe=json.loads(probe_raw)
 if probe.get('rule_sha256')!=sha(raw_rule) or probe.get('seed_identity')!=2433016 or probe.get('family_range')!=[0,10000] or probe['counts']['same_owner_all_three']<1:raise ValueError('rule15 same-owner feature screen source/coverage differs')
 receipts.append({'path':'results/dev_aux/task2626/rule15-feature-probe-seed2433016.json','mode':'SCREENED_FAMILY_RANGE','sha256':sha(probe_raw),
  'generator_seed_identity':probe['seed_identity'],'screened_family_range':probe['family_range'],'records_persisted':False,'same_owner_eligible':probe['counts']['same_owner_all_three'],
  'outcome_blind_exposure_note':'Every deterministic family index in [0,10000) for seed2433016 is exposed; future candidate roots use the distinct seed2433017 and disjoint registered ranges.'})
 screen_path=ROOT/'results/dev_aux/task2626/task2433-unvisited-variant-screen.json';screen_raw=screen_path.read_bytes();screen=json.loads(screen_raw)
 selected_row=next(r for r in screen['records'] if r['index']==15)
 if selected_row['status']!='WITNESS_FOUND':raise ValueError('rule15 mechanism witness missing')
 witness=selected_row['witness']['record']
 if witness.get('ruleset_fingerprint')!=fingerprint:raise ValueError('rule15 witness rule fingerprint mismatch')
 prior.add(canon(witness))
 receipts.append({'path':'results/dev_aux/task2626/task2433-unvisited-variant-screen.json','mode':'FIXED_ORDER_WITNESS','sha256':sha(screen_raw),'selected_witness_full_record_sha256':sha(canon(witness)),'selected_witness_plies':len(witness.get('actions',[])),'candidate_record_occurrences':1})
 reply_path=ROOT/'results/dev_aux/task2626/task2433-variant-unlock-one-reply.json';reply_raw=reply_path.read_bytes();reply=json.loads(reply_raw)
 reply15=next(r for r in reply['records'] if r['index']==15)
 receipts.append({'path':'results/dev_aux/task2626/task2433-variant-unlock-one-reply.json','mode':'ONE_REPLY_MECHANISM_CONTINUATION','sha256':sha(reply_raw),'opponent_legal_replies':reply15['opponent_legal_replies'],'replies_with_legal_unlock':len(reply15['replies_with_legal_unlock']),'outcomes_read':reply['outcomes_read'],'search_expanded':reply['search_expanded']})
 control_path=ROOT/'results/dev_aux/task2411/inputs.json';control_raw=control_path.read_bytes();controls=json.loads(control_raw)
 control_records=[r['record'] for r in controls]
 # Separate control rules have different full ruleset fingerprints.
 if any(r.get('ruleset_fingerprint')==fingerprint for r in control_records):raise ValueError('task2411 control unexpectedly matches rule15 fingerprint')
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
   elapsed=prior_elapsed+time.perf_counter()-began
   if elapsed>=HARD_SECONDS:
    state={'status':'HARD_CAP_REACHED_NO_POOL','phase':label,'current_family':family,'tested_families':tested,
     'selected':len(selected),'invalid_terminal_or_unexcited':invalid,'prior_exact_history_rejections':overlap,
     'within_pool_duplicates':duplicate,'elapsed_seconds':elapsed,'outputs_written':False,'prior_attempts':prior_attempts}
    save_status(state);print(json.dumps(state,sort_keys=True),flush=True)
    raise TimeoutError(f"{label} preparation reached cap after {tested} families; selected {len(selected)}/{count}")
   item=candidate(family);tested+=1
   if item is None:invalid+=1
   else:
    rec,features,channels,owner,rh,rb,pr=item;key=canon(rec)
    if key in excluded:overlap+=1
    elif key in seen:duplicate+=1
    else:
     seen.add(key);selected.append({'rule_index':15,'generator_seed':SEED_RULE,'family':family,'record':rec,'record_sha256':sha(key),
      'features':features,'channels':channels,'same_owner':owner,'R_hand_count':rh,'R_board_count':rb,'promoted_P_count':pr})
   if len(selected)==count:break
   if tested%25000==0:
    state={'status':'PREPARING_OUTCOME_BLIND_POOL','phase':label,'current_family':family,'tested_families':tested,
     'selected':len(selected),'invalid_terminal_or_unexcited':invalid,'prior_exact_history_rejections':overlap,
      'within_pool_duplicates':duplicate,'elapsed_seconds':elapsed,'outputs_written':False,'prior_attempts':prior_attempts}
    save_status(state);print(json.dumps(state,sort_keys=True),flush=True)
  if len(selected)!=count:
   state={'status':'FAILED_POOL_SHORT_NO_POOL','phase':label,'current_family':families.stop-1,'tested_families':tested,
    'selected':len(selected),'required':count,'invalid_terminal_or_unexcited':invalid,
    'prior_exact_history_rejections':overlap,'within_pool_duplicates':duplicate,
     'elapsed_seconds':prior_elapsed+time.perf_counter()-began,'outputs_written':False,'prior_attempts':prior_attempts}
   save_status(state);print(json.dumps(state,sort_keys=True),flush=True)
   raise RuntimeError(f"{label} pool short: {len(selected)}/{count} in {tested} families; invalid={invalid} overlap={overlap} duplicate={duplicate}")
  return selected,{'family_range':[families.start,families.stop],'selected':len(selected),'families_tested':tested,
   'invalid_terminal_or_unexcited':invalid,'prior_exact_history_rejections':overlap,'within_pool_duplicates':duplicate}
 training,tstat=select(TRAIN_RANGE,TRAIN_N,prior,'training')
 trainkeys={canon(x['record']) for x in training}
 evaluation,estat=select(EVAL_RANGE,EVAL_N,prior|trainkeys,'evaluation')
 result={'status':'OUTCOME_BLIND_MECHANISM_ACTIVE_ROOTS_PREPARED_NOT_REGISTERED',
  'candidate':{'path':RULE_REL,'index':15,'sha256':sha(raw_rule),'ruleset_fingerprint':fingerprint,
    'selection_reason':'First fixed-index task2433 ruleset after rule0 with a legal full-history P-to-R transition witness; no outcome/search/model fields.'},
  'selection_inputs':{'history_sources':receipts,'prior_unique_exact_candidate_histories':len(prior),
    'task2433_prefit_root_count':len(prefit),'task2433_prefit_candidate_roots':len(prefit_candidate),
    'fixed_order_screen_sha256':sha(screen_raw),'fixed_order_witness_plies':len(witness['actions']),
    'dynamic_inventory_sha256':sha(inv_raw),'cost_bound_sha256':sha(bound_raw)},
  'prefix_plies':PREFIX_PLIES,'feature_policy':'Every root is ongoing after8 plies and one same owner has an R in hand, a current-type R on board, and a P-base/R-current promoted piece; this enables that owner to use a hand-R-unlocking move and activates the promotion material channel. No auxiliary-state guard claim.',
  'training':tstat,'evaluation':estat,'training_roots':training,'evaluation_roots':evaluation,
   'exact_train_evaluation_overlap':0,'preparation_seconds':prior_elapsed+time.perf_counter()-began,
  'limitations':['Exact full-record exclusion covers dynamically discovered current DEV_AUX results JSON/JSONL and compressed JSONL/JSON sources plus task2433 prefit roots and the saved mechanism witness. No transposition, descendant-state or distributional independence claim.',
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
