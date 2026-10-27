"""Independent published-return reader: no producer/Player/search/Native imports.
The supplied source is a private exact Git archive; output is derived evidence.
No original timing or internal search trace is recreated by this verifier.
"""
from __future__ import annotations
import argparse,gzip,hashlib,json,math,sys,time
from pathlib import Path
from collections import Counter
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from generic_chess.rules.schema import ruleset_from_dict,compute_fingerprint
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution
from generic_chess.session.serialization import deserialize_game_record,serialize_game_record
from generic_chess.session.session import GameSession
from scripts.research_record import record_value

EXCLUDED_TIMING_FIELDS=frozenset({"elapsed_seconds","time_to_first_legal_action",
 "time_to_first_completed_iteration","ordering_seconds","legal_generation_seconds",
 "evaluation_seconds","evaluation_profile_cache_hit","quiet_geometry_build_seconds"})

def load(p):
 raw=Path(p).read_bytes()
 return json.loads(gzip.decompress(raw) if str(p).endswith('.gz') else raw)

def digest(raw):return hashlib.sha256(raw).hexdigest()

def signature(d):return {k:v for k,v in d.items() if k not in EXCLUDED_TIMING_FIELDS}

def diagnostic_action(data,fingerprint):
 # The producer recorded a dataclass diagnostic, not GameRecord JSON. Convert
 # only its exact observed public semantic board shape, preserving IDs.
 expected={'pattern_id','geometry_id','actor_type_id','from_square','to_square','promotion_target_id'}
 if type(data) is not dict or set(data)!=expected:raise ValueError('unsupported diagnostic action shape')
 for key in ('from_square','to_square'):
  if type(data[key]) is not dict or set(data[key])!={'file','rank'}:raise ValueError('bad square shape')
 action=dict(kind='semantic_board',pattern_id=data['pattern_id'],geometry_id=data['geometry_id'],
  actor_type_id=data['actor_type_id'],promotion_target_id=data['promotion_target_id'],
  **{'from':[data['from_square']['file'],data['from_square']['rank']],
     'to':[data['to_square']['file'],data['to_square']['rank']]})
 wire=dict(schema_version=1,ruleset_fingerprint=fingerprint,resigned_by=None,actions=[action])
 return deserialize_game_record(json.dumps(wire)).actions[0]

def verify(source,inputs,output):
 output.mkdir(exist_ok=False,parents=True)
 began=time.perf_counter();cpu=time.process_time()
 manifest=load(source/'manifest.json');archive_checks=[]
 for entry in manifest['files']:
  p=source/entry['file'];assert p.is_file(),p
  assert digest(p.read_bytes())==entry['publication_sha256'],p
  archive_checks.append(entry['file'])
 assert len(archive_checks)==manifest['verified_copies']==83
 frozen=load(source/'boolean-experiment--frozen.json.gz')
 assert digest(inputs.read_bytes())==frozen['input_sha256']
 for name in ['generic_chess/core/semantic_executor.py','generic_chess/core/search_runtime.py',
              'generic_chess/rules/compiler.py','generic_chess/rules/ir.py']:
  assert (ROOT/name).read_text(encoding='utf-8')==frozen['sources'][name],name
 packet=load(inputs);cases=[r for r in packet['rows'] if r['prefix_length']==2]
 assert len(packet['rows'])==24 and len(cases)==12
 assert [r['id'] for r in cases]==frozen['case_ids']
 sessions={};roots=[]
 for row in cases:
  rule=ruleset_from_dict(row['RuleSet']);assert compute_fingerprint(rule)==row['fingerprint']
  compiled=compile_legacy_ruleset_for_semantic_execution(rule)
  record=deserialize_game_record(json.dumps(row['record']))
  session=GameSession.replay(compiled,record)
  assert record_value(session.state)==row['root'],row['id']
  assert session.result.status.value=='ongoing'
  assert session.state.ply_count==row['prefix_length']==2
  assert json.loads(serialize_game_record(session.to_record()))==row['record']
  actual=session.legal_actions()
  expected=[diagnostic_action(a,row['fingerprint']) for a in row['legal_actions']]
  assert len(actual)==len(set(expected)) and set(actual)==set(expected)
  sessions[row['id']]=(compiled,record,session)
  roots.append(dict(id=row['id'],fingerprint=row['fingerprint'],board_size=rule.board_size,
   history_entries=len(session.state.history),repetition_keys=len(session.state.repetition_counts),legal_actions=len(actual)))
 slots=load(source/'boolean-experiment--slots.json.gz');assert len(slots)==96
 frozen_slots=frozen['slots'];assert len(frozen_slots)==len(slots)
 for a,b in zip(frozen_slots,slots):
  for key in ['slot','case_id','depth','on']:assert a[key]==b[key],(key,a,b)
 # Explicitly separate published-case failures from the other co-published panel.
 boolean_failures=sorted(p.name for p in source.glob('boolean-experiment--*failure*'))
 assert not boolean_failures,boolean_failures
 returns=[];pv_plies=0;endings=Counter();per_root_record={}
 for number in range(48):
  raw=load(source/f'boolean-experiment--return-{number:03d}.json.gz');slot=slots[number]
  assert raw['slot']==slot['slot']==number and raw['status']==slot['status']=='RETURNED'
  for key in ['case_id','on','depth']:assert raw[key]==slot[key]
  assert raw['depth']==6
  d=raw['decision'];assert d==slot['decision']
  assert d['runtime_depth_balanced'] and d['runtime_pushes']==d['runtime_pops']
  assert slot['complete']==(d['completed_depth']==6)
  for key in ['outer_seconds','cpu_seconds']:assert slot[key]==raw[key]
  assert raw['Native_delta']['availability'].get('declines',0)==0
  if raw['on']:
   assert raw['boolean_metrics']['fallbacks']==0
   assert not raw['Native_delta']['availability'] and not raw['Native_delta']['check']
  else:assert raw['boolean_metrics'] is None
  assert d['native_legality_fallbacks']==d['native_legality_operational_failures']==0
  for name in ['outer_seconds','cpu_seconds','constructor_seconds']:
   assert type(raw[name]) in (int,float) and math.isfinite(raw[name]) and raw[name]>=0
  assert raw['outer_seconds']>=raw['constructor_seconds']
  for key in ['nodes','qnodes','completed_depth','runtime_pushes','runtime_pops']:
   assert type(d[key]) is int and d[key]>=0
  compiled,record,root=sessions[raw['case_id']]
  session=GameSession.replay(compiled,record)
  action=diagnostic_action(d['action'],record.ruleset_fingerprint)
  pv=tuple(diagnostic_action(a,record.ruleset_fingerprint) for a in d['principal_variation'])
  assert pv and pv[0]==action and action in root.legal_actions()
  for a in pv:
   assert session.result.status.value=='ongoing'
   session.submit(a);pv_plies+=1
  assert root.to_record()==record
  endings[session.result.status.value]+=1
  if raw['case_id'] in per_root_record and d['completed_depth']==6:
   assert session.to_record()==per_root_record[raw['case_id']]
  elif d['completed_depth']==6:per_root_record[raw['case_id']]=session.to_record()
  returns.append(dict(slot=number,case=raw['case_id'],on=raw['on'],depth=d['completed_depth'],
   reason=d['termination_reason'],result_source=d['result_source'],pv_length=len(pv),pv_terminal=session.result.status.value,
   root_binding='Exact frozen input hash + caseID + frozen/final slot join; not per-return before-record hash',
   postvalidation='Producer finalslot RETURNED/complete flag joined; current Core root/action/PV checks PASS',
   historical_session_unchanged='Not independently observable in saved return',
   all_iterative_attempts='UNKNOWN: no per-iteration/action event trace',
   Native_loaded_binary='Frozen producer hash declaration; no independent historical DLL observation',
   pv_final_ply=session.state.ply_count,nodes=d['nodes'],qnodes=d['qnodes'],
   outer_seconds=raw['outer_seconds'],cpu_seconds=raw['cpu_seconds'],
   saved_signature=signature(d)))
 groups=[]
 for start in range(0,48,4):
  g=returns[start:start+4];eligible=all(r['depth']==6 for r in g)
  same=len({json.dumps(r['saved_signature'],sort_keys=True) for r in g})==1
  eligible=eligible and same
  pair={k:sum(r[k] for r in g if r['on']) for k in ['outer_seconds','cpu_seconds']}
  baseline={k:sum(r[k] for r in g if not r['on']) for k in ['outer_seconds','cpu_seconds']}
  groups.append(dict(case=g[0]['case'],eligible=eligible,same_saved_nontiming_signature=same,
   on=pair,off=baseline))
 for r in slots[48:]:assert r['status']=='NOT_RUN'
 eligible=[g for g in groups if g['eligible']]
 ratios={k:sum(g['on'][k] for g in eligible)/sum(g['off'][k] for g in eligible) for k in ['outer_seconds','cpu_seconds']}
 summary=load(source/'boolean-experiment--summary.json.gz')
 assert len(eligible)==summary['6']['eligible_root_groups']==11
 assert abs(ratios['outer_seconds']-summary['6']['wall_ratio'])<1e-12
 assert abs(ratios['cpu_seconds']-summary['6']['cpu_ratio'])<1e-12
 result=dict(archive_files_hash_checked=len(archive_checks),roots=roots,returns=returns,groups=groups,
  PV_plies=pv_plies,PV_endings=dict(endings),ratios=ratios,not_run_D8=len(slots[48:]),
  source_input_sha256=digest(inputs.read_bytes()),source_commit='5e2002561f81892018c2076c13cf6eeaa26d84b9',
  public_source='docs/research/data/leaper_boolean_cost_20261027/',
  root_source=frozen['plan']['benchmark_source'],no_boolean_failure_files=True,
  frozen_slot_identities_checked=len(frozen_slots),
  missing_fields=['per-return before-record hash','per-iteration/scout/research event records','independent DLL/build source attestation'],
  private_original_bytes='Not read; only published hashes verified. Source-capsule2CRLF hashes reproducible from current unchanged files, no private-return reconstruction.',
  driver_sha256=digest(Path(__file__).read_bytes()),
  verifier_wall_seconds=time.perf_counter()-began,verifier_cpu_seconds=time.process_time()-cpu,
  limitations=['No new Player/search/game/build or timing rerun.',
   'Work counts and provider/fallback declarations are saved claims, not independently reconstructed search internals.',
   'Core replays establish current root/PV legality and full-history binding, not an historical executable or loaded DLL proof.',
   'The48raw D6 returns include2D5cancelled;48D8NOT_RUN remain missing, not draws or successful returns.',
   'No WDL/action optimality/strength or speedup follows from legal PVs.'])
 (output/'verification.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
 (output/'verifier.py').write_bytes(Path(__file__).read_bytes())
 print(json.dumps({k:v for k,v in result.items() if k not in ['roots','returns','groups']},indent=2))

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--inputs',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();verify(a.source,a.inputs,a.output)
