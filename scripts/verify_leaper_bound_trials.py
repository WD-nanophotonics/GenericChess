"""Saved root-driver/Q-bound trials; no Player,PN or producer execution."""
from pathlib import Path
from collections import Counter
import json,hashlib
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution
from generic_chess.rules.schema import ruleset_from_dict,compute_fingerprint
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from scripts.research_record import record_value,write_record
from scripts.verify_leaper_pvs_quality_pilot import action

def verify_trials(base,out,kind):
 b=Path(base);f=json.loads((b/'frozen.json').read_text());assert hashlib.sha256((b/'inputs.json').read_bytes()).hexdigest()==f['input_sha256']
 rows=json.loads((b/'inputs.json').read_text())['rows'];returns=[json.loads(p.read_text()) for p in sorted(b.glob('return-*.json'))];assert len(returns)==32 and {r['slot'] for r in returns}==set(range(32))
 pairs=[];plies=passes=0;reasons=Counter();changed_completed=set()
 for ri,row in enumerate(rows):
  rules=ruleset_from_dict(row['RuleSet']);assert compute_fingerprint(rules)==row['fingerprint'];c=compile_legacy_ruleset_for_semantic_execution(rules);s=GameSession.replay(c,deserialize_game_record(json.dumps(row['record'])))
  pair=[next(r for r in returns if r['root']==ri and r['on']==on) for on in (False,True)]
  for r in pair:
   d=r['decision'];assert r['record_before']==record_value(s.to_record()) and d['runtime_depth_balanced'] and r['wall_seconds']<=1.1 and r['timing_eligible'];action(d['action'],s);reasons[d['termination_reason']]+=1
   pv=GameSession.replay(c,s.to_record())
   for raw in d['principal_variation']:pv.submit(action(raw,pv));plies+=1
   if kind=='mtdf':
    trace=d['mtdf_trace'];assert r['on'] or not trace
    last=None
    for e in trace:
     lower,upper=-10**12,10**12;value=e['guess'];witness=None
     for step in e['passes']:
      beta=value+1 if value==lower else value;assert step['beta']==beta;value=step['score'];passes+=1
      if value<beta:upper=min(upper,value)
      else:lower=max(lower,value);witness=step
      assert lower<=upper
     assert e['lower']==lower and e['upper']==upper
     if e['completed']:
      assert lower==upper and witness is not None and witness['score']==lower;last=(e,witness)
    if d['result_source']=='main_iteration_mtdf':
     assert last is not None;event,w=last
     assert d['completed_depth']==event['depth'] and d['score']==w['score'] and d['action']==w['best_action'] and d['declaration']==w['declaration']
    if d['termination_reason']=='mtdf_pass_limit':assert d['completed_depth']==0 and len(trace[0]['passes'])==256 and not trace[0]['completed']
   else:
    assert d['mtdf_passes']==0 and not d['mtdf_trace']
    assert 0<=d['soft_q_strict_upper_returns']<=d['soft_q_bound_returns']
    if r['on']:assert d['soft_q_strict_upper_returns']>0
    else:assert d['soft_q_bound_returns']==d['soft_q_strict_upper_returns']==0
  off,on=pair;same=(off['decision']['action'],off['decision']['declaration'],off['decision']['choice_kind'])==(on['decision']['action'],on['decision']['declaration'],on['decision']['choice_kind'])
  if not same and on['decision']['completed_depth']>0:changed_completed.add(row['family'])
  pairs.append(dict(root=ri,family=row['family'],same_complete_choice=same,relative_action_value_interval=[0,0] if same else [-2,2]))
 result=dict(status='PASS_SAVED_TYPED_CHOICES',kind=kind,returns=32,pairs=pairs,Core_PV_plies=plies,mtdf_returned_passes=passes,reasons=dict(reasons),changed_with_completed_iteration_families=sorted(changed_completed),newPlayer=0,newPN=0,limits='sharedCoreliteralreplay;differentchoicesremainUNKNOWN;no capsule execution/fitnessrefill')
 write_record(out,result);return result

def verify_semantic(base,out):
 b=Path(base);f=json.loads((b/'frozen.json').read_text());assert hashlib.sha256((b/'inputs.json').read_bytes()).hexdigest()==f['inputs_sha256'];qs=[json.loads(p.read_text()) for p in sorted(b.glob('query-*.json'))];assert len(qs)==448 and all(q['status']=='RETURNED' for q in qs);cross=main=bound=0
 for ri in range(32):
  references=[]
  for runtime in (False,True):
   group=[q for q in qs if q['input']==ri and q['runtime']==runtime and q['kind'].startswith('q-')]
   wide=[q for q in group if q['kind']=='q-wide'];assert len(wide)==2 and wide[0]['score']==wide[1]['score'];value=wide[0]['score'];references.append(value)
   for q in group:
    if q['kind']=='q-null':
     a,z,v=q['alpha'],q['beta'],q['score'];assert value<=v if v<=a else value>=v if v>=z else value==v;bound+=1
  assert references[0]==references[1];cross+=1
  root=[q for q in qs if q['input']==ri and q['kind']=='main'];assert len(root)==2 and root[0]['score']==root[1]['score'];main+=1
 r=dict(status='PASS_SAVED_FINITE_BOUNDS',returns=448,cross_Core_runtime_wideQ_pairs=cross,wide_main_pairs=main,null_bound_returns=bound,newCore=0,newPlayer=0,limits='originalreferencesfromsameCoreandfiniteQ;not universalproof/strength/speed;allzeroUTCintervalsuncredited')
 write_record(out,r);return r
if __name__=='__main__':
 import sys
 print(json.dumps(verify_semantic(sys.argv[2],sys.argv[3]) if sys.argv[1]=='semantic' else verify_trials(sys.argv[2],sys.argv[3],sys.argv[1])))
