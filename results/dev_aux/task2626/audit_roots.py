"""Independent source-hash, full-history replay and split audit for task2626."""
from __future__ import annotations
import hashlib,json,sys
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT))
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.session.session import GameSession
from results.dev_aux.task2621.fixed_scale import FixedScaleSessionEnv

POOL=ROOT/'results/dev_aux/task2626/root-pools.json'
OUT=ROOT/'results/dev_aux/task2626/root-pools-audit-v2.json'

def sha(b):return hashlib.sha256(b).hexdigest()
def canon(v):return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
def records(row):
 for k in ('record_before','record_after','initial_record','final_record','record'):
  r=row.get(k)
  if isinstance(r,dict):yield r
def walk(v):
 if isinstance(v,dict):
  if isinstance(v.get('ruleset_fingerprint'),str) and isinstance(v.get('actions'),list):yield v
  for c in v.values():yield from walk(c)
 elif isinstance(v,list):
  for c in v:yield from walk(c)

def main():
 pool=json.loads(POOL.read_text(encoding='utf-8'));candidate=pool['candidate']
 rule_path=ROOT/candidate['path'];raw=rule_path.read_bytes()
 if sha(raw)!=candidate['sha256']:raise ValueError('candidate rule hash changed')
 comp=compile_ruleset_for_execution(ruleset_from_dict(json.loads(raw)))
 fingerprint=GameSession(comp).to_record().ruleset_fingerprint
 if fingerprint!=candidate['ruleset_fingerprint']:raise ValueError('candidate fingerprint changed')
 prior=set();source_receipts=[]
 for receipt in pool['selection_inputs']['history_sources']:
  if receipt.get('status')=='MISSING':
   if (ROOT/receipt['path']).exists():raise ValueError(f"source appeared after preparation: {receipt['path']}")
   source_receipts.append({'path':receipt['path'],'status':'MISSING'});continue
  if receipt.get('status')!='READ':continue
  path=ROOT/receipt['path']
  if receipt['status']=='MISSING':
   if path.exists():raise ValueError(f"source appeared after pool preparation: {receipt['path']}")
   continue
  h=hashlib.sha256();occ=0;rows=0
  with path.open('rb') as stream:
   for line in stream:
    h.update(line)
    if not line.strip():continue
    rows+=1
    try:row=json.loads(line)
    except json.JSONDecodeError:continue
    for rec in records(row):
     if rec.get('ruleset_fingerprint')==fingerprint:prior.add(canon(rec));occ+=1
  if h.hexdigest()!=receipt['sha256'] or rows!=receipt['rows'] or occ!=receipt['candidate_record_occurrences']:
   raise ValueError(f"source receipt mismatch: {receipt['path']}")
  source_receipts.append({'path':receipt['path'],'rows':rows,'matching_occurrences':occ,'sha256':h.hexdigest()})
 for receipt in pool['selection_inputs']['history_sources']:
  if receipt.get('mode')!='READ_JSON_RECORDS_ONLY':continue
  path=ROOT/receipt['path'];raw=path.read_bytes()
  if sha(raw)!=receipt['sha256']:raise ValueError(f"manifest source hash changed: {receipt['path']}")
  occ=0
  for rec in walk(json.loads(raw)):
   if rec.get('ruleset_fingerprint')==fingerprint:prior.add(canon(rec));occ+=1
  if occ!=receipt['candidate_record_occurrences']:raise ValueError(f"manifest count mismatch: {receipt['path']}")
  source_receipts.append({'path':receipt['path'],'record_occurrences':occ,'sha256':sha(raw)})

 task2433_path=ROOT/'results/dev_aux/task2433/inputs.json';pre_raw=task2433_path.read_bytes()
 prefit=json.loads(pre_raw);prefit_exact=[r['record'] for r in prefit if r['record'].get('ruleset_fingerprint')==fingerprint]
 if len(prefit)!=pool['candidate']['task2433_prefit_roots'] or len(prefit_exact)!=pool['candidate']['candidate_prefit_matches']:
  raise ValueError('task2433 prefit root exposure receipt mismatch')
 prior.update(canon(r['record']) for r in prefit if r['record'].get('ruleset_fingerprint')==fingerprint)
 if canon(prefit_exact[0]) not in prior:raise ValueError('task2433 exact prefit root missing from excluded set')

 control_path=ROOT/'results/dev_aux/task2411/inputs.json';control_raw=control_path.read_bytes()
 cr=pool['selection_inputs']['task2411_control']
 if sha(control_raw)!=cr['sha256']:raise ValueError('task2411 control hash changed')
 controls=json.loads(control_raw);control_records=[r['record'] for r in controls]
 if len(control_records)!=cr['records']:raise ValueError('task2411 record count changed')
 if any(r.get('ruleset_fingerprint')==fingerprint for r in control_records):raise ValueError('task2411 control unexpectedly shares candidate fingerprint')

 splits={};all_keys={};features=Counter();replayed=0
 for name,rows,expected in [('training',pool['training_roots'],120),('evaluation',pool['evaluation_roots'],16)]:
  local=set();
  for row in rows:
   rec=row['record'];key=canon(rec)
   if sha(key)!=row['record_sha256'] or key in local:raise ValueError(f'{name}: bad hash or duplicate')
   if rec.get('ruleset_fingerprint')!=fingerprint or key in prior:raise ValueError(f'{name}: rule mismatch or exposed history')
   if len(rec.get('actions',[]))!=8:raise ValueError(f'{name}: wrong prefix length')
   typed=deserialize_game_record(json.dumps(rec))
   sess=GameSession.replay(comp,typed)
   env=FixedScaleSessionEnv(sess)
   if sess.to_record()!=typed or env.terminal() is not None:raise ValueError(f'{name}: replay mismatch or terminal root')
   if list(env.features())!=row['features'] or [list(x) for x in env.names]!=row['channels']:
    raise ValueError(f'{name}: feature/channel mismatch')
   pos=sess.state.position
   rh=sum(n for hand in pos.hands for base,n in hand.counts if base=='R')
   p=sum(1 for piece in pos.board if piece and piece.base_type_id=='P' and piece.current_type_id=='P')
   if rh!=row['active_R_hand_count'] or p!=row['live_P_on_board_count'] or not rh or not p:
    raise ValueError(f'{name}: declared R/P feature excitation invalid')
   local.add(key);replayed+=1
   features['R_hand_roots']+=int(rh>0);features['P_board_roots']+=int(p>0)
   features['R_hand_count']+=rh;features['P_board_count']+=p
  if len(rows)!=expected:raise ValueError(f'{name}: wrong root count')
  splits[name]=len(local);all_keys[name]=local
 if all_keys['training']&all_keys['evaluation']:raise ValueError('train/evaluation exact-history overlap')
 result={'status':'PASS_SOURCE_HASH_FULL_HISTORY_REPLAY_FEATURE_AND_SPLIT_AUDIT',
  'root_pools_sha256':sha(POOL.read_bytes()),'candidate_rule_sha256':candidate['sha256'],
  'candidate_fingerprint':fingerprint,'verified_history_source_count':len(source_receipts),
  'prior_unique_candidate_histories':len(prior),'task2433_prefit_roots':len(prefit),
  'task2433_exact_candidate_prefit_roots':len(prefit_exact),'task2411_control_records':len(control_records),
  'training_roots':splits['training'],'evaluation_roots':splits['evaluation'],
  'exact_train_evaluation_overlap':0,'replayed_roots':replayed,'feature_totals':dict(features),
  'scope':'Exact complete records in enumerated evidence only; no transposition, descendant-state, or distributional independence claim.',
  'source_audit':source_receipts}
 rawout=json.dumps(result,indent=2,sort_keys=True,ensure_ascii=False).encode()+b'\n'
 with OUT.open('xb') as f:f.write(rawout)
 print(json.dumps({k:v for k,v in result.items() if k!='source_audit'},indent=2))
if __name__=='__main__':main()
