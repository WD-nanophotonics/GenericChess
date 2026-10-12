import json,time,hashlib
from pathlib import Path
R=Path.cwd();O=R/'results/dev_aux/task311';O.mkdir(exist_ok=False);start=time.monotonic();CT='$dev_aux_constant_telemetry_v1';ST='$dev_aux_sparse_telemetry_v1'
def hook(d):
 if set(d)=={CT}:z=d[CT];return [z['value'] for _ in range(z['count'])]
 if set(d)=={ST}:
  z=d[ST];rr=[z['default'] for _ in range(z['count'])];seen=set()
  for i,v in z['entries']:assert type(i) is int and 0<=i<len(rr) and i not in seen;seen.add(i);rr[i]=v
  return rr
 return d
def canonical(x):return json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()
X=json.loads((R/'results/dev_aux/task310/result.json').read_bytes(),object_hook=hook);B=json.loads((R/'results/dev_aux/task289/result.json').read_bytes(),object_hook=hook);assert X['complete'] and X['actual_new_queries']==107 and X['actual_total_queries']==139
entries=[json.loads(line,object_hook=hook) for line in (R/'results/dev_aux/task310/queries.jsonl').read_bytes().splitlines()];assert len(entries)==139
for i,z in enumerate(entries):
 assert z['sequence']==i and hashlib.sha256(canonical(z['record'])).hexdigest()==z['raw_sha256'];rr=next(q for q in X['calls'] if q['root']==z['game']['root'] and q['color']==z['game']['color']);assert z['record']==rr['search_records'][z['record']['ply']]
def strip(v):
 if isinstance(v,dict):return {k:strip(z) for k,z in v.items() if 'elapsed' not in k and k not in ('seconds','wall_seconds')}
 if isinstance(v,list):return [strip(z) for z in v]
 return v
for z in X['calls']:
 ref=next(q for q in B['calls'] if q['root']==z['root'] and q['color']==z['color'] and q['opponent']=='unit');assert strip(z)==strip(ref)
# Both baselines fullyqualified by independent290/298; aggregatewithoutmixing oldrulepilot.
rand=json.loads((R/'results/dev_aux/task293/summary.json').read_bytes());perm=json.loads((R/'results/dev_aux/task297/result.json').read_bytes());tags=[z['outcome'] for z in perm['calls']];alltags=[z['outcome'] for z in B['calls']]+tags
out=dict(complete=True,independent_journal_hash_checks=139,all_4matched_non_time_games_equal=True,actual_new_recovery_queries=107,prior309_actual_persisted_queries=32,reused_pending_queries=1,recovery_game_counts=dict(prior_completed=1,new_completed=3,total=4),actual_persisted_new_Native_queries=124+1235+1233+8+204+32+107,additional_failed294_queries='UNKNOWN_notpersisted, do notclaimexacttotal',actual_complete_games=72,baseline64_repetition5_outcomes={k:alltags.count(k) for k in ('win','loss','draw','unknown')},permutation32_outcomes={k:tags.count(k) for k in ('win','loss','draw','unknown')},sparse_append_actual_bytes=X['total_write_bytes']['sparse_append'],legacy_growing_prefix_actual_bytes=X['total_write_bytes']['legacy_prefix'],actual_IO_seconds=X['record_io_seconds'],seconds=time.monotonic()-start,scope='Independentobjecthook decoder ofbothcodecformats; everyquery hash andallscientificnon-timefields matches qualified289. 4recordinggames duplicateinputs, notextraIIDscience. Countsinclude72physicalcompletedgames; failedD4partialattemptexcludedfromcompletegames/calltotalunknown. Root64finitegoal37W0L27U (notfinalWDL orpopulationconfidence).')
(O/'audit.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps(out,indent=2))