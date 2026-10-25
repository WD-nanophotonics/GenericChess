"""Data-only acceptance reader for the frozen research draw study, no queries."""
import argparse,hashlib,json
from pathlib import Path
from collections import Counter,defaultdict
from scripts import leaper_design as L
from scripts.leaper_delayed_capture_witness import replay
from generic_chess.core.actions import action_from_dict
from scripts.leaper_draw_observer import rule_gate,inventory
from tools.local_agent.common import write_json

def lines(p):return [json.loads(x)for x in p.read_text(encoding='utf-8').splitlines()]if p.exists()else[]
def assess(d,partial=False):
 plan=L.load(d/'plan.json');data=L.load(d/'inputs.json');rows=lines(d/'queries.jsonl');qr=lines(d/'quality.jsonl');games=lines(d/'games.jsonl')
 receipt=L.load(d/'receipt.json')if(d/'receipt.json').exists()else{'status':'RUNNING'}
 expected_games=[f'{key}-draw{color}'for i,key in enumerate(plan['game_cases'])for color in((0,1)if i%2==0 else(1,0))]
 assert [g['game']for g in games]==expected_games[:len(games)]
 used_ids=set()
 assert hashlib.sha256((d/'inputs.json').read_bytes()).hexdigest()==plan['inputs_sha256']
 if not partial:assert receipt['status']=='CLOSED' and len(qr)==len(plan['slots'])and len(games)==24 and receipt['queries']==len(rows)
 assert [r['id']for r in rows]==list(range(len(rows)))
 assert [r['slot']for r in qr]==plan['slots'][:len(qr)]
 byid={r['id']:r for r in rows};cases={c['key']:c for c in data['quality']['cases']};pairs=defaultdict(dict);counts=defaultdict(Counter);pvsteps=0
 for q in qr:
  r=byid[q['query_id']];used_ids.add(r['id']);slot=q['slot'];assert r['label']==slot and r['enabled']==slot['enabled']
  if slot['case']=='canonical-control':
   case=data['canonical'];rd=case['rule'];record=case['record']
  else:
   case=cases[slot['case']];rd=data['quality']['rules'][case['rule_sha256']];record=case['record']
  c=L.compile_rule(L.ruleset_from_dict(rd));s=replay(c,r['before_record']);assert r['before_record']==record and L.state_sha(s.state)==r['state_sha256']
  action=next(a for a in s.legal_actions()if L.record_value(a)==r['decision']['action'])
  if slot['case']=='canonical-control':
   chosen='bad_proved_opponent_WIN'if action==action_from_dict(case['bad_action'])else'safe_proved_DRAW'if action==action_from_dict(case['safe_action'])else'UNKNOWN_other_action';assert chosen==q['chosen_certificate']
  else:
   labels={json.dumps(a['action'],sort_keys=True):a['truth']['value']*(1 if s.state.position.side_to_move==0 else -1)for a in case['labelled_actions']}
   assert set(labels)=={json.dumps(L.record_value(a),sort_keys=True)for a in s.legal_actions()}
   assert labels[json.dumps(L.record_value(action),sort_keys=True)]==q['chosen_own_WDL']
   assert q['root_own_WDL']==max(labels.values())
  for raw in r['decision']['principal_variation']:
   found=[a for a in s.legal_actions()if L.record_value(a)==raw];assert len(found)==1;s.submit(found[0]);pvsteps+=1
  key=(slot['case'],slot['budget']);assert slot['enabled']not in pairs[key];pairs[key][slot['enabled']]=(q,r)
 pairtable=[]
 for (key,budget),g in pairs.items():
  if set(g)!={False,True}:continue
  (qa,a),(qb,b)=g[False],g[True];assert a['profile']==b['profile']and a['tuning']==b['tuning']
  counter=counts[budget];counter['pairs']+=1
  for name,q,r in [('baseline',qa,a),('candidate',qb,b)]:
   counter[name+'_seconds']+=r['seconds'];counter[name+'_events']+=r['decision']['nodes']+r['decision']['qnodes'];counter[name+'_time_censored']+=int(r['decision']['termination_reason']=='time_limit');counter[name+'_fallback']+=int(r['decision']['completed_depth']==0)
   if'root_own_WDL'in q:counter[name+'_correct']+=q['root_own_WDL']==q['chosen_own_WDL']
  row=dict(case=key,budget=budget,baseline_seconds=a['seconds'],candidate_seconds=b['seconds'],same_action=a['decision']['action']==b['decision']['action'],candidate_cutoffs=b['policy_counts'].get('cutoffs',0))
  if'chosen_own_WDL'in qa:
   counter['repairs']+=qb['chosen_own_WDL']>qa['chosen_own_WDL'];counter['regressions']+=qb['chosen_own_WDL']<qa['chosen_own_WDL'];row.update(baseline=qa['chosen_own_WDL'],candidate=qb['chosen_own_WDL'],root=qa['root_own_WDL'])
  else:row.update(baseline=qa['chosen_certificate'],candidate=qb['chosen_certificate'])
  pairtable.append(row)
 gc={c['key']:c for c in data['games']};gamecounts=Counter();querycost=defaultdict(Counter);eligiblecost=defaultdict(Counter);colorpairs=defaultdict(dict);materialcost=defaultdict(Counter)
 for game in games:
  case=gc[game['case']];rule=L.ruleset_from_dict(case['rule']);c=L.compile_rule(rule);anchor=rule_gate(rule);initial=case['record'];assert game['initial_record']==initial
  final=replay(c,game['final_record']);assert L.record_value(final.result)==game['final_result']
  assert game['final_record']['actions'][:len(initial['actions'])]==initial['actions']
  if game['outcome']['result'] not in ('failed','unresolved'):
   assert final.result.status.value!='ongoing','caller-censored isnot a completed game'
  assert final.state.ply_count==len(game['final_record']['actions'])
  if game['outcome']['result'] not in ('failed','unresolved'):
   assert len(game['events'])==game['outcome']['plies']-len(initial['actions'])
  gamecounts['games']+=1;gamecounts['eligible']+=int(game['eligible']);gamecounts[game['outcome']['result']]+=1;colorpairs[game['case']][game['candidate_color']]=game['eligible']
  rr=[r for r in rows if isinstance(r['label'],dict)and r['label'].get('game')==game['game']]
  assert len(rr)==len(game['events'])
  actual=replay(c,initial)
  for event,r in zip(game['events'],rr):
   assert r['id'] not in used_ids; used_ids.add(r['id'])
   assert r['before_record']==L.record_value(actual.to_record())
   assert event['side']==actual.state.position.side_to_move
   assert event['candidate']==r['enabled']==(event['side']==game['candidate_color'])
   stratum='root_twoK'if inventory(actual.state.position,anchor)else'other_root'
   arm='candidate'if r['enabled']else'baseline'
   for cohort in ('all','eligible')if game['eligible']else('all',):
    mc=materialcost[cohort+':'+arm+':'+stratum];mc['queries']+=1;mc['seconds']+=r['seconds'];mc['events']+=r['decision']['nodes']+r['decision']['qnodes']
   action=next(a for a in actual.legal_actions()if L.record_value(a)==r['decision']['action'])
   assert str(action)==event['action']
   actual.submit(action)
   assert event['ply']==actual.state.ply_count
   a='candidate'if r['enabled']else'baseline';querycost[a]['queries']+=1;querycost[a]['seconds']+=r['seconds'];querycost[a]['events']+=r['decision']['nodes']+r['decision']['qnodes'];querycost[a]['cutoffs']+=r['policy_counts'].get('cutoffs',0)
   if game['eligible']:
    eligiblecost[a]['queries']+=1;eligiblecost[a]['seconds']+=r['seconds'];eligiblecost[a]['events']+=r['decision']['nodes']+r['decision']['qnodes'];eligiblecost[a]['cutoffs']+=r['policy_counts'].get('cutoffs',0)
  assert L.record_value(actual.to_record())==game['final_record']
 if not partial: assert used_ids==set(byid),'orphaned ormissing query rows'
 return dict(status=receipt['status'],queries=len(rows),quality_rows=len(qr),quality_budgets={k:dict(v)for k,v in counts.items()},pairs=pairtable,games=dict(gamecounts),gamequerycost={k:dict(v)for k,v in querycost.items()},eligible_gamequerycost={k:dict(v)for k,v in eligiblecost.items()},eligible_color_pairs=sum(set(v)=={0,1}and all(v.values())for v in colorpairs.values()),game_material_cost={k:dict(v)for k,v in materialcost.items()},quality_pv_steps=pvsteps,scope='MatchedPVStrue arms/fullrecords.64exposedcorrelatedoneRuleSet pluscanonical and6game rules, no independentholdout/Elo/classstrength. CanonicalotheractionsUNKNOWN. Timingcensors/ineligibles retained; eventsnotdistinctstates. Frozencontrols unchanged.')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--directory',type=Path,required=True);p.add_argument('--partial',action='store_true');a=p.parse_args();r=assess(a.directory,a.partial);write_json(a.directory/('partial-assessment.json'if a.partial else'assessment.json'),r);print({k:r[k]for k in ['status','queries','quality_rows','quality_budgets','games','gamequerycost','eligible_gamequerycost','eligible_color_pairs','game_material_cost','quality_pv_steps']})
