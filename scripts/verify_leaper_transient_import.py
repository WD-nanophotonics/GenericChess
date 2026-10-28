"""Saved-data verifier for the finite transient-import assessment: zero Player."""
from __future__ import annotations
import argparse,gzip,json,hashlib,statistics
from pathlib import Path
from generic_chess.rules.schema import ruleset_from_dict,compute_fingerprint
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.session.session import GameSession
from scripts.research_record import record_value,write_record
from scripts.verify_leaper_pvs_quality_pilot import action

TIMING={'elapsed_seconds','time_to_first_legal_action','time_to_first_completed_iteration','ordering_seconds','legal_generation_seconds','evaluation_seconds','evaluation_profile_cache_hit','quiet_geometry_build_seconds'}
def load(p):
 p=Path(p)
 if not p.exists():p=Path(str(p)+'.gz')
 raw=p.read_bytes();return json.loads(gzip.decompress(raw) if str(p).endswith('.gz') else raw)
def verify(folder,output):
 f=load(folder/'frozen.json');p=f['plan'];data=Path(p['benchmark_source']).read_bytes();assert hashlib.sha256(data).hexdigest()==f['input_sha256']==p['input_sha256']
 supplement=load(folder.parent/'source-byte-supplement.json')['files']
 for name,text in f['sources'].items():
  exact=supplement[name]['original_utf8'];assert hashlib.sha256(exact.encode()).hexdigest()==f['source_hashes'][name]==supplement[name]['sha256']
  assert exact.replace('\r\n','\n')==text,'normalizedcapsule differsfrompinnedoriginalbytes'
 assert f['binary']['sha256']==p['binary_sha256']
 roots={r['id']:r for r in json.loads(gzip.decompress(data))['rows'] if r['prefix_length']==2}
 slots=load(folder/'slots.json');assert len(slots)==96 and [s['slot'] for s in slots]==list(range(96))
 observed={int(x.name.removesuffix('.gz').removesuffix('.json').split('-')[-1]) for x in folder.glob('return-*.json*')};associated=set();pvs=0;reports=[];contexts={}
 for cid,row in roots.items():
  rules=ruleset_from_dict(row['RuleSet']);assert compute_fingerprint(rules)==row['fingerprint']
  c=compile_legacy_ruleset_for_semantic_execution(rules);s=GameSession.replay(c,deserialize_game_record(json.dumps(row['record'])))
  contexts[cid]=(c,s)
 for slot in slots:
  if slot['status']!='RETURNED':continue
  index=slot['slot'];associated.add(index);r=load(folder/f'return-{index:03d}.json');assert r['slot']==index and r['case_id']==slot['case_id'] and r['depth']==slot['depth'] and r['on']==slot['on']
  assert r['decision']==slot['decision'] and r['transient_imports_active']==r['on']
  assert r['outer_seconds']==slot['outer_seconds'] and r['cpu_seconds']==slot['cpu_seconds']
  d=r['decision'];assert slot['complete']==(d['completed_depth']==r['depth'])
  assert d['runtime_depth_balanced'] and d['native_legality_fallbacks']==d['native_legality_operational_failures']==0
  assert r['Native_delta']['availability'].get('declines',0)==0
  c,s=contexts[r['case_id']];chosen=action(d['action'],s);pv=GameSession.replay(c,s.to_record())
  if d['principal_variation']:assert d['principal_variation'][0]==d['action']
  for a in d['principal_variation']:pv.submit(action(a,pv));pvs+=1
  reports.append(dict(slot=index,case=r['case_id'],depth=r['depth'],on=r['on'],completed=d['completed_depth'],PV_plies=len(d['principal_variation']),outer=r['outer_seconds'],cpu=r['cpu_seconds']))
 assert associated==observed,'missing/orphan savedreturns'
 groups=[]
 for i in range(0,96,4):
  g=slots[i:i+4];ok=all(s['status']=='RETURNED' and s['complete'] for s in g)
  if ok:assert len({json.dumps({k:v for k,v in s['decision'].items() if k not in TIMING},sort_keys=True) for s in g})==1
  a=[s for s in g if s['on']];b=[s for s in g if not s['on']]
  groups.append(dict(case=g[0]['case_id'],depth=g[0]['depth'],eligible=ok,wall_on=sum(s.get('outer_seconds',0) for s in a) if ok else None,wall_off=sum(s.get('outer_seconds',0) for s in b) if ok else None,cpu_on=sum(s.get('cpu_seconds',0) for s in a) if ok else None,cpu_off=sum(s.get('cpu_seconds',0) for s in b) if ok else None))
 result=dict(returns=len(reports),literal_PV_plies=pvs,complete_roots=len(contexts),groups=groups,rows=reports,not_run=sum(s['status']=='NOT_RUN' for s in slots),failed=sum(s['status']=='FAILED' for s in slots),new_Player=0,new_solver=0,new_games=0,limits='Independent savedreader,not independent timing orheldoutstrength. Non-target depths andNOT_RUN fixed;scopeonlyonecandidate.')
 for depth in (6,8):
  eligible=[g for g in groups if g['depth']==depth and g['eligible']]
  result[str(depth)]=dict(eligible=len(eligible),wall_ratio=sum(g['wall_on'] for g in eligible)/sum(g['wall_off'] for g in eligible) if eligible else None,root_median=statistics.median(g['wall_on']/g['wall_off'] for g in eligible) if eligible else None,cpu_ratio=sum(g['cpu_on'] for g in eligible)/sum(g['cpu_off'] for g in eligible) if eligible and all(g['cpu_off']>0 for g in eligible) else None)
 original=load(folder/'summary.json')
 for depth in ('6','8'):
  assert result[depth]['eligible']==original[depth]['eligible_root_groups']
  assert result[depth]['wall_ratio']==original[depth]['wall_ratio'] and result[depth]['cpu_ratio']==original[depth]['cpu_ratio']
 write_record(output,result);print(json.dumps({k:result[k] for k in ['returns','literal_PV_plies','not_run','failed','6','8']}))
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--folder',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);a=parser.parse_args();verify(a.folder,a.output)
