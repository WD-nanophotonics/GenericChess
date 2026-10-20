"""Independent source/hash/replay audit for the rule1 mechanism-active pool."""
from __future__ import annotations
import hashlib,json,sys,subprocess
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT))
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.session.session import GameSession
from results.dev_aux.task2621.fixed_scale import FixedScaleSessionEnv
OUT=ROOT/'results/dev_aux/task2626/rule1-root-pools-audit-v2.json'
POOL=ROOT/'results/dev_aux/task2626/rule1-root-pools.json'
PREP=ROOT/'results/dev_aux/task2626/prepare_rule1_roots.py'
TRAIN_RANGE=(5_200_000,5_700_000);EVAL_RANGE=(6_200_000,6_350_000)
SEED_RULE=2_433_001
PREP_SOURCE_AT_LAUNCH_SHA256='9e6ad19fafbe5444a9c92f9a6f34f007a3e5dfde06f7586e9d816c3509ca1f25'
def sha(b):return hashlib.sha256(b).hexdigest()
def canon(v):return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
def row_records(row):
 for k in ('record_before','record_after','initial_record','final_record','record'):
  r=row.get(k)
  if isinstance(r,dict):yield r
def walk(v):
 if isinstance(v,dict):
  if isinstance(v.get('ruleset_fingerprint'),str) and isinstance(v.get('actions'),list):yield v
  for x in v.values():yield from walk(x)
 elif isinstance(v,list):
  for x in v:yield from walk(x)
def main():
 pool_raw=POOL.read_bytes();pool=json.loads(pool_raw);candidate=pool['candidate'];rule_path=ROOT/candidate['path'];raw_rule=rule_path.read_bytes()
 if candidate.get('path')!='results/dev_aux/task2433/rules-1.json' or candidate.get('index')!=1:
  raise ValueError('candidate fixed-order rule identity mismatch')
 if sha(raw_rule)!=candidate['sha256']:raise ValueError('candidate rule hash mismatch')
 compiled=compile_ruleset_for_execution(ruleset_from_dict(json.loads(raw_rule)));fingerprint=GameSession(compiled).to_record().ruleset_fingerprint
 if fingerprint!=candidate['ruleset_fingerprint']:raise ValueError('candidate ruleset fingerprint mismatch')
 prior=set();sources=[]
 for rec in pool['selection_inputs']['history_sources']:
  if rec.get('mode') in ('ALL_16_PREFIT_ROOTS','FIXED_ORDER_WITNESS','DISTINCT_RULE_CONTROL','SCREENED_FAMILY_RANGE') or rec.get('path')=='results/dev_aux/task2626/task2433-variant-screen.json':continue
  if rec.get('mode')=='RG_EXACT_FINGERPRINT_SCAN':
   paths=rec['searched_paths'];current_missing=[p for p in rec['missing_paths'] if (ROOT/p).exists()]
   if current_missing or any(not (ROOT/p).is_file() for p in paths) or sha(canon(paths))!=rec['searched_path_list_sha256']:
    raise ValueError('fixed-fingerprint search path list changed')
   scan=subprocess.run(['rg','-F','-l','--no-ignore','--',fingerprint,*paths],cwd=ROOT,capture_output=True,check=False)
   if scan.returncode not in (0,1):raise ValueError('exact-fingerprint search failed during audit')
   matches=sorted(x.replace('\\','/') for x in scan.stdout.decode('utf-8').splitlines())
   if matches!=rec['matched_paths'] or scan.returncode!=rec['rg_exit_code']:
    raise ValueError('candidate fingerprint matching files changed after pool prep')
   sources.append({'mode':'RG_EXACT_FINGERPRINT_SCAN','searched_paths':len(paths),'missing_paths':len(current_missing),
    'matched_paths':matches,'fingerprint':fingerprint,'rg_exit_code':scan.returncode});continue
  path=ROOT/rec['path']
  if rec.get('mode')=='READ_JSON_RECORDS_ONLY':
   raw=path.read_bytes()
   if sha(raw)!=rec['sha256']:raise ValueError(f"manifest hash changed: {rec['path']}")
   count=0
   for r in walk(json.loads(raw)):
    if r.get('ruleset_fingerprint')==fingerprint:prior.add(canon(r));count+=1
   if count!=rec['candidate_record_occurrences']:raise ValueError(f"manifest occurrence mismatch: {rec['path']}")
   sources.append({'path':rec['path'],'mode':'JSON_RECORDS','occurrences':count,'sha256':sha(raw)});continue
  if rec['status']=='MISSING':
   if path.exists():raise ValueError(f"source appeared after preparation: {rec['path']}")
   sources.append({'path':rec['path'],'status':'MISSING'});continue
  h=hashlib.sha256();rows=occ=0
  with path.open('rb') as f:
   for line in f:
    h.update(line)
    if not line.strip():continue
    rows+=1
    try:row=json.loads(line)
    except json.JSONDecodeError:continue
    for r in row_records(row):
     if r.get('ruleset_fingerprint')==fingerprint:prior.add(canon(r));occ+=1
  if h.hexdigest()!=rec['sha256'] or rows!=rec['rows'] or occ!=rec['candidate_record_occurrences']:
   raise ValueError(f"history source receipt mismatch: {rec['path']}")
  sources.append({'path':rec['path'],'status':'READ','rows':rows,'occurrences':occ,'sha256':h.hexdigest()})

 pre_path=ROOT/'results/dev_aux/task2433/inputs.json';pre_raw=pre_path.read_bytes();pre=json.loads(pre_raw)
 pre_cand=[r['record'] for r in pre if r['record'].get('ruleset_fingerprint')==fingerprint]
 pre_rec=next(x for x in pool['selection_inputs']['history_sources'] if x.get('mode')=='ALL_16_PREFIT_ROOTS')
 if sha(pre_raw)!=pre_rec['sha256'] or len(pre)!=pre_rec['records'] or len(pre_cand)!=pre_rec['candidate_record_occurrences']:
  raise ValueError('task2433 prefit records differ from preparation')
 prior.update(canon(r) for r in pre_cand)
 probe_rec=next(x for x in pool['selection_inputs']['history_sources'] if x.get('mode')=='SCREENED_FAMILY_RANGE')
 probe_path=ROOT/probe_rec['path'];probe_raw=probe_path.read_bytes();probe=json.loads(probe_raw)
 if sha(probe_raw)!=probe_rec['sha256'] or probe.get('rule_sha256')!=candidate['sha256'] or probe.get('family_limit')!=10000 or probe['counts']['same_owner_all_three']!=probe_rec['same_owner_eligible']:
  raise ValueError('outcome-blind family screen receipt changed')
 if any(probe_rec['screened_family_range'][0]<=r['family']<probe_rec['screened_family_range'][1]
        for r in pool['training_roots']+pool['evaluation_roots']):
  raise ValueError('selected roots overlap previously screened family indices')
 sources.append({'mode':'SCREENED_FAMILY_RANGE','path':probe_rec['path'],'sha256':sha(probe_raw),
  'screened_family_range':probe_rec['screened_family_range']})
 screen_path=ROOT/'results/dev_aux/task2626/task2433-variant-screen.json';screen_raw=screen_path.read_bytes()
 screen_rec=next(x for x in pool['selection_inputs']['history_sources']
  if x.get('mode')=='FIXED_ORDER_WITNESS' or x.get('path')=='results/dev_aux/task2626/task2433-variant-screen.json')
 if sha(screen_raw)!=screen_rec['sha256']:raise ValueError('variant screen changed')
 witness=next(x for x in json.loads(screen_raw)['records'] if x['index']==1)['witness']['record']
 if sha(canon(witness))!=screen_rec['selected_witness_full_record_sha256'] or len(witness['actions'])!=screen_rec['selected_witness_plies']:
  raise ValueError('selected rule1 witness record changed')
 prior.add(canon(witness))
 ctl_path=ROOT/'results/dev_aux/task2411/inputs.json';ctl_raw=ctl_path.read_bytes();ctl=json.loads(ctl_raw)
 ctl_rec=next(x for x in pool['selection_inputs']['history_sources'] if x.get('mode')=='DISTINCT_RULE_CONTROL')
 if sha(ctl_raw)!=ctl_rec['sha256'] or len(ctl)!=ctl_rec['records']:raise ValueError('task2411 control receipt mismatch')
 ctl_records=[x['record'] for x in ctl]
 if any(x.get('ruleset_fingerprint')==fingerprint for x in ctl_records):raise ValueError('task2411 control shares candidate fingerprint')

 splits={};keys={};totals=Counter();replayed=0;unlock_action_availability={}
 for name,rows,n,family_range in [('training',pool['training_roots'],120,TRAIN_RANGE),('evaluation',pool['evaluation_roots'],16,EVAL_RANGE)]:
  if pool[name].get('family_range')!=list(family_range) or pool[name].get('selected')!=n:
   raise ValueError(f'{name}: frozen family range or selected-count metadata mismatch')
  local=set();families=set();unlock_roots=[]
  for row in rows:
   rec=row['record'];key=canon(rec)
   if row.get('rule_index')!=1 or row.get('generator_seed')!=SEED_RULE:
    raise ValueError(f'{name}: fixed-order index or generator seed mismatch')
   if type(row.get('family')) is not int or not family_range[0]<=row['family']<family_range[1]:
    raise ValueError(f'{name}: family index outside its frozen split range')
   if row['family'] in families:raise ValueError(f'{name}: duplicate family index')
   families.add(row['family'])
   if sha(key)!=row['record_sha256'] or key in local:raise ValueError(f'{name}: hash or duplicate error')
   if rec.get('ruleset_fingerprint')!=fingerprint or key in prior:raise ValueError(f'{name}: rule mismatch or exact prior exposure')
   if len(rec['actions'])!=8:raise ValueError(f'{name}: non-eight-ply root')
   typed=deserialize_game_record(json.dumps(rec));session=GameSession.replay(compiled,typed);env=FixedScaleSessionEnv(session)
   if session.to_record()!=typed or env.terminal() is not None:raise ValueError(f'{name}: replay/terminal mismatch')
   if list(env.features())!=row['features'] or [list(c) for c in env.names]!=row['channels']:raise ValueError(f'{name}: feature receipt mismatch')
   pos=session.state.position;rh=sum(k for h in pos.hands for t,k in h.counts if t=='R')
   rb=sum(1 for p in pos.board if p is not None and p.current_type_id=='R')
   pr=sum(1 for p in pos.board if p is not None and p.base_type_id=='P' and p.current_type_id=='R')
   owner=row['same_owner']
   owner_rh=sum(k for t,k in pos.hands[owner].counts if t=='R')
   owner_rb=sum(1 for p in pos.board if p is not None and p.owner==owner and p.current_type_id=='R')
   owner_pr=sum(1 for p in pos.board if p is not None and p.owner==owner and p.base_type_id=='P' and p.current_type_id=='R')
   if (owner_rh,owner_rb,owner_pr)!=(row['R_hand_count'],row['R_board_count'],row['promoted_P_count']) or min(owner_rh,owner_rb,owner_pr)<1:
    raise ValueError(f'{name}: mechanism feature excitation mismatch')
   if any(getattr(action,'pattern_id','').endswith('_hand_R_unlocks_rook_quiet') for action in session.legal_actions()):
    unlock_roots.append(row['family'])
   local.add(key);replayed+=1;totals.update({'R_hand_root':1,'R_board_root':1,'promoted_P_root':1,'R_hand_total':rh,'R_board_total':rb,'promoted_P_total':pr})
  if len(local)!=n:raise ValueError(f'{name}: wrong pool size')
  splits[name]=len(local);keys[name]=local
  unlock_action_availability[name]={'roots_with_legal_hand_R_unlocks_rook_quiet':len(unlock_roots),'sample_families':unlock_roots[:8],
   'interpretation':'Diagnostic only; root eligibility remains based on same-owner R-hand/R-board/promoted-P feature counts, and this availability check is not action usage.'}
 if keys['training']&keys['evaluation']:raise ValueError('train/evaluation full-history intersection')
 result={'status':'PASS_SOURCE_HASH_FULL_HISTORY_REPLAY_MECHANISM_FEATURE_AND_SPLIT_AUDIT',
  'pool_sha256':sha(pool_raw),'candidate_rule_sha256':candidate['sha256'],'candidate_fingerprint':fingerprint,
  'preparation_script_sha256':sha(PREP.read_bytes()),'audit_script_sha256':sha(Path(__file__).read_bytes()),
  'preparation_source_at_launch_sha256':PREP_SOURCE_AT_LAUNCH_SHA256,
  'preparation_source_provenance':'Session77036 began before a single metadata-only FIXED_ORDER_WITNESS field was added to the producer receipt. The launch-source hash is reconstructed by reversing that unique field addition from the current file; root ranges, candidate test, selection criteria and generation code are unchanged.',
  'verified_history_source_count':len(sources),'prior_unique_candidate_histories':len(prior),
  'task2433_prefit_roots':len(pre),'task2433_exact_candidate_prefit_roots':len(pre_cand),
  'task2433_screen_witness_plies':len(witness['actions']),'task2411_control_roots':len(ctl_records),
  'training_roots':splits['training'],'evaluation_roots':splits['evaluation'],'exact_train_evaluation_overlap':0,
  'replayed_roots':replayed,'mechanism_feature_totals':dict(totals),'unlock_action_availability':unlock_action_availability,
  'scope':'Exact full records in enumerated evidence only; no descendant-state, transposition or distributional independence claim.',
  'source_audit':sources}
 with OUT.open('xb') as f:f.write(json.dumps(result,indent=2,sort_keys=True,ensure_ascii=False).encode()+b'\n')
 print(json.dumps({k:v for k,v in result.items() if k!='source_audit'},indent=2))
if __name__=='__main__':main()
