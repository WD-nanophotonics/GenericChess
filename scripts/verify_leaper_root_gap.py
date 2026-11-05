"""Saved full records and root-bound traces; no Player/producer calls."""
from pathlib import Path
from collections import Counter
import json,hashlib
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution
from generic_chess.rules.schema import ruleset_from_dict,compute_fingerprint
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.ai.evaluation.config import MATE_THRESHOLD

def make_session(row):
 rules=ruleset_from_dict(row["RuleSet"]);assert compute_fingerprint(rules)==row["fingerprint"]
 c=compile_legacy_ruleset_for_semantic_execution(rules)
 s=GameSession.replay(c,deserialize_game_record(json.dumps(row["record"])))
 assert not s.state.terminal_status.is_terminal
 return c,s
from scripts.verify_leaper_pvs_quality_pilot import action
from scripts.research_record import record_value,write_record

def verify(base,out):
 b=Path(base);f=json.loads((b/'frozen.json').read_text());assert hashlib.sha256((b/'inputs.json').read_bytes()).hexdigest()==f['input_sha256']
 rows=json.loads((b/'inputs.json').read_text())['rows'];returns=[json.loads(p.read_text()) for p in sorted(b.glob('return-*.json'))]
 assert len(returns)==32 and {r['slot'] for r in returns}==set(range(32))
 rejections=Counter();events=boundrows=plies=0;pairs=[]
 for ri,row in enumerate(rows):
  c,s=make_session(row);legal=[record_value(a) for a in s.legal_actions()]
  pair=[next(r for r in returns if r['root']==ri and r['on']==on) for on in (False,True)]
  for r in pair:
   assert r['record_before']==record_value(s.to_record()) and r['timing_eligible'] and r['wall_seconds']<=1.1
   d=r['decision'];assert d['runtime_depth_balanced'];action(d['action'],s)
   pv=type(s).replay(c,s.to_record())
   for raw in d['principal_variation']:pv.submit(action(raw,pv));plies+=1
   trace=d['root_gap_trace'];assert r['on'] or not trace
   previous=None;applied=0
   for e in trace:
    events+=1;candidate=None
    if previous is not None and previous['completed'] and not previous['selective'] and previous['depth']>=2 and previous['ordinary_phase'] and not previous['neutral'] and len(previous['rows'])>=2:
     selected=[x for x in previous['rows'] if x['action']==previous['best_action']]
     if len(selected)==1:
      win=selected[0];other=[x for x in previous['rows'] if x['action']!=previous['best_action']]
      if win['bound'] in ('EXACT','LOWER') and abs(win['score'])<MATE_THRESHOLD and all(x['bound'] in ('EXACT','UPPER') and x['score']<win['score'] for x in other):candidate=win['action']
    if e['depth']>=64:candidate=None
    assert e['target']==candidate and e['selective']==(candidate is not None)
    assert e['applied']<=1
    seen=[]
    for x in e['rows']:
     boundrows+=1;assert x['action'] in legal and x['action'] not in seen;seen.append(x['action'])
     assert x['child_depth']==e['depth']-1+int(x['action']==candidate)
     expected='UPPER' if x['score']<=x['alpha'] else 'LOWER' if x['score']>=x['beta'] else 'EXACT'
     assert x['bound']==expected
    if e['completed']:assert len(seen)==len(legal)
    if not e['completed']:rejections['incomplete']+=1
    elif e['selective']:rejections['selective_not_self_reused']+=1
    elif not e['ordinary_phase'] or e['depth']<2:rejections['firstQreserve_or_D1']+=1
    else:
     best=next((x for x in e['rows'] if x['action']==e['best_action']),None)
     if best is None:rejections['no_typed_best']+=1
     elif any(x['action']!=e['best_action'] and x['score']>=best['score'] for x in e['rows']):rejections['alternative_upper_not_strictly_below']+=1
     else:rejections['strict_separation_or_other_guard']+=1
    applied+=e['applied'];previous=e
   assert applied==d['root_gap_extensions']
  off,on=pair
  same=(off['decision']['action'],off['decision']['declaration'],off['decision']['choice_kind'])==(on['decision']['action'],on['decision']['declaration'],on['decision']['choice_kind'])
  pairs.append(dict(root=ri,family=row['family'],same_complete_choice=same,relative_action_value_interval=[0,0] if same else [-2,2]))
 summary=dict(status='PASS_SAVED_FULL_RECORD_TRACE',returns=len(returns),pairs=pairs,Core_PV_plies=plies,root_attempts=events,bound_rows=boundrows,trace_classification=dict(rejections),newPlayer=0,newPN=0,limits='shared Core replay,not independent rulesengine;finite returned-bound semantics only,not trueWDL;no archive-source execution')
 write_record(out,summary);return summary
if __name__=='__main__':
 import sys;print(json.dumps(verify(sys.argv[1],sys.argv[2])))
