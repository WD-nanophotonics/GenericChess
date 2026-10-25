"""Data-only full-record acceptance of existing Native service research.
Never imports experiment source capsules or issues Player/solver queries.
"""
from pathlib import Path
from collections import Counter,defaultdict
import json,hashlib
from scripts import leaper_design as L
from scripts.leaper_delayed_capture_witness import replay
from tools.local_agent.common import write_json

def lines(p):return [json.loads(s)for s in p.read_text(encoding='utf-8').splitlines()]if p.exists()else[]
def assess(d,partial=False):
 data=L.load(d/'inputs.json');plan=L.load(d/'fitness-plan.json');receipt=L.load(d/'fitness-receipt.json')if(d/'fitness-receipt.json').exists()else dict(status='RUNNING');rows=lines(d/'fitness-queries.jsonl');quality=lines(d/'quality.jsonl');games=lines(d/'games.jsonl')
 assert hashlib.sha256((d/'inputs.json').read_bytes()).hexdigest()==plan['inputs_sha256']
 assert [r['id']for r in rows]==list(range(len(rows)))
 assert [q['slot']for q in quality]==plan['slots'][:len(quality)]
 expected=[k+'-native'+str(color)for i,k in enumerate(plan['game_cases'])for color in((0,1)if i%2==0 else(1,0))]
 assert [g['game']for g in games]==expected[:len(games)]
 if not partial:assert receipt['status']=='CLOSED'and len(quality)==len(plan['slots'])and len(games)==24 and receipt['queries']==len(rows)
 byid={r['id']:r for r in rows};cases={c['key']:c for c in data['quality']['cases']};used=set();pairs=defaultdict(dict);totals=defaultdict(Counter);service=defaultdict(Counter);material=defaultdict(Counter);pvsteps=0;table=[]
 def root_inventory(s,rule):
  anchors={p.type_id for p in rule.piece_types if p.is_anchor};pieces=[p for p in s.state.position.board if p is not None]
  return 'two_unpromoted_anchors'if len(pieces)==2 and {p.owner for p in pieces}=={0,1} and all(p.current_type_id==p.base_type_id and p.current_type_id in anchors and not p.promoted for p in pieces) and not any(h.counts for h in s.state.position.hands) else'other_root'
 def consume(r,phase,stratum):
  assert r['id']not in used;used.add(r['id']);assert r['provider_present'];assert r['decision']['runtime_pushes']==r['decision']['runtime_pops']
  assert r['arm']in ('baseline','both')and r['enabled']==(r['arm']=='both')
  for group,m in r['provider_delta'].items():
   for k,v in m.items():assert v>=0;service[phase+':'+r['arm']+':'+group][k]+=v
  if r['arm']=='baseline':assert not r['provider_delta']['availability']and not r['provider_delta']['check']
  else:
   a=r['provider_delta']['availability'];c=r['provider_delta']['check'];assert a.get('declines',0)==0
   assert a.get('imports',0)+a.get('reused_imports',0)==a.get('queries',0)
   assert c.get('imports',0)==c.get('queries',0)
  mc=material[phase+':'+r['arm']+':'+stratum];mc['queries']+=1;mc['seconds']+=r['seconds'];mc['events']+=r['decision']['nodes']+r['decision']['qnodes']
  counter=totals[phase+':'+r['arm']];counter['queries']+=1;counter['seconds']+=r['seconds'];counter['setup_seconds']+=r['setup_seconds'];counter['reported_search_seconds']+=r['decision']['elapsed_seconds'];counter['events']+=r['decision']['nodes']+r['decision']['qnodes'];counter['time_censored']+=int(r['decision']['termination_reason']=='time_limit');counter['fallback']+=int(r['decision']['result_source']in ('fallback','legal_fallback','root_scan_fallback'))
 def validate(c,r,record):
  nonlocal pvsteps
  s=replay(c,record);assert r['before_record']==record and r['state_sha256']==L.state_sha(s.state)
  action=next(a for a in s.legal_actions()if L.record_value(a)==r['decision']['action'])
  for raw in r['decision']['principal_variation']:
   aa=[a for a in s.legal_actions()if L.record_value(a)==raw];assert len(aa)==1;s.submit(aa[0]);pvsteps+=1
  return action
 for q in quality:
  r=byid[q['query_id']];slot=q['slot'];assert r['label']==slot;assert r['arm']==slot['arm'];case=cases[slot['case']];c=L.compile_rule(L.ruleset_from_dict(data['quality']['rules'][case['rule_sha256']]));s=replay(c,case['record']);action=validate(c,r,case['record']);consume(r,slot['budget'],root_inventory(s,L.ruleset_from_dict(data['quality']['rules'][case['rule_sha256']])))
  labels={json.dumps(a['action'],sort_keys=True):a['truth']['value']*(1 if s.state.position.side_to_move==0 else -1)for a in case['labelled_actions']};assert set(labels)=={json.dumps(L.record_value(a),sort_keys=True)for a in s.legal_actions()}
  assert q['root_own_WDL']==max(labels.values())and q['chosen_own_WDL']==labels[json.dumps(L.record_value(action),sort_keys=True)]
  totals[slot['budget']+':'+r['arm']]['correct']+=q['root_own_WDL']==q['chosen_own_WDL'];pairs[(slot['case'],slot['budget'])][r['arm']]=(q,r)
 paircounts=defaultdict(Counter)
 for (key,budget),pp in pairs.items():
  if set(pp)!={'baseline','both'}:continue
  (qa,a),(qb,b)=pp['baseline'],pp['both'];assert a['profile']==b['profile']and a['tuning']==b['tuning']
  pc=paircounts[budget];pc['pairs']+=1;pc['repairs']+=qb['chosen_own_WDL']>qa['chosen_own_WDL'];pc['regressions']+=qb['chosen_own_WDL']<qa['chosen_own_WDL'];pc['action_changes']+=a['decision']['action']!=b['decision']['action'];pc['score_changes']+=a['decision']['score']!=b['decision']['score']
  table.append(dict(case=key,budget=budget,baseline_WDL=qa['chosen_own_WDL'],candidate_WDL=qb['chosen_own_WDL'],root_WDL=qa['root_own_WDL'],baseline_depth=a['decision']['completed_depth'],candidate_depth=b['decision']['completed_depth'],same_action=a['decision']['action']==b['decision']['action'],baseline_seconds=a['seconds'],candidate_seconds=b['seconds']))
 gc={c['key']:c for c in data['games']};outcomes=Counter();colorpairs=defaultdict(dict);invalid=[]
 for game in games:
  case=gc[game['case']];c=L.compile_rule(L.ruleset_from_dict(case['rule']));s=replay(c,case['record']);assert game['initial_record']==case['record'];rr=[r for r in rows if r['label'].get('game')==game['game']];assert len(rr)==len(game['events'])
  for event,r in zip(game['events'],rr):
   action=validate(c,r,L.record_value(s.to_record()));assert event['side']==s.state.position.side_to_move and event['candidate']==r['enabled']==(event['side']==game['candidate_color']);assert str(action)==event['action'];consume(r,'games_all',root_inventory(s,L.ruleset_from_dict(case['rule'])))
   if game['eligible']:
    # Same row may contribute to a separate descriptive eligible subtotal, not a second query.
    mc=material['games_eligible:'+r['arm']+':'+root_inventory(s,L.ruleset_from_dict(case['rule']))];mc['queries']+=1;mc['seconds']+=r['seconds'];mc['events']+=r['decision']['nodes']+r['decision']['qnodes']
    counter=totals['games_eligible:'+r['arm']];counter['queries']+=1;counter['seconds']+=r['seconds'];counter['events']+=r['decision']['nodes']+r['decision']['qnodes']
   if event['timing_invalid']:invalid.append(dict(game=game['game'],query_id=r['id'],arm=r['arm'],caller_seconds=event['elapsed_seconds'],row_seconds=r['seconds'],search_seconds=r['decision']['elapsed_seconds']))
   s.submit(action);assert s.state.ply_count==event['ply']
  assert L.record_value(s.to_record())==game['final_record']and L.record_value(s.result)==game['final_result']
  if game['outcome']['result']not in ('failed','unresolved'):assert s.result.status.value!='ongoing'
  outcomes['games']+=1;outcomes['eligible']+=game['eligible'];outcomes[game['outcome']['result']]+=1;colorpairs[game['case']][game['candidate_color']]=game['eligible']
 if not partial:assert used==set(byid),'Orphaned/missing query'
 return dict(status=receipt['status'],queries=len(rows),quality_rows=len(quality),totals={k:dict(v)for k,v in totals.items()},pairs={k:dict(v)for k,v in paircounts.items()},pairtable=table,provider_deltas={k:dict(v)for k,v in service.items()},root_inventory_cost={k:dict(v)for k,v in material.items()},games=dict(outcomes),eligible_color_pairs=sum(set(x)=={0,1}and all(x.values())for x in colorpairs.values()),timing_invalid=invalid,pv_steps=pvsteps,scope=plan['exposure'],timing_scope='row includes freshPlayer setup and choose; excludes imports/replay/recording/PV validation. Game service clock additionally includes save/ledger/PV replay; receipt includes whole batch. No fabricated setup0 for historical data.')
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--directory',type=Path,required=True);p.add_argument('--partial',action='store_true');a=p.parse_args();r=assess(a.directory,a.partial);write_json(a.directory/('partial-assessment.json'if a.partial else'assessment.json'),r);print({k:v for k,v in r.items()if k not in ('pairtable','timing_invalid')})
