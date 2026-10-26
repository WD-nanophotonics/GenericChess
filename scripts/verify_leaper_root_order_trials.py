"""Independent saved-data checks for root ordering trials; never runs Players."""
from pathlib import Path
from collections import Counter,defaultdict
import argparse,json,hashlib,copy,gzip
from generic_chess.rules.schema import ruleset_from_dict,compute_fingerprint
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.session.session import GameSession
from scripts.research_record import record_value

def original_bytes(p):
 p=Path(p)
 return p.read_bytes() if p.exists() else gzip.decompress(Path(str(p)+'.gz').read_bytes())
def load(p):return json.loads(original_bytes(p))
def digest(p):return hashlib.sha256(original_bytes(p)).hexdigest()

def verify_inputs(inputs):
 data=load(inputs);rows=data['rows'];assert len(rows)==24
 cache={};root_actions={}
 for row in rows:
  rr=ruleset_from_dict(row['RuleSet']);assert compute_fingerprint(rr)==row['fingerprint'];c=compile_legacy_ruleset_for_semantic_execution(rr)
  session=GameSession.replay(c,deserialize_game_record(json.dumps(row['record'])));assert record_value(session.to_record())==row['record'];assert record_value(session.state)==row['root']
  assert len(row['record']['actions'])==row['prefix_length']==session.state.ply_count
  assert session.state.position.side_to_move==row['prefix_length']%2
  actions=session.legal_actions();assert len({str(a)for a in actions})==len(actions)
  cache[row['id']]=(c,session.to_record());root_actions[row['id']]={str(a)for a in actions}
 assert len({r['fingerprint']for r in rows})==12
 return rows,cache,root_actions

def recover_action(raw,session):
 matches=[a for a in session.legal_actions() if record_value(a)==raw]
 assert len(matches)==1,"saved complete action has no unique legal match"
 return matches[0]

def verify_rows(rows,planned,cache,root_actions,depths,arms):
 assert len(rows)==len(planned)
 expected_slots=[(case,depth,arm)for case,depth,arm in planned]
 assert [(r['case_id'],r['requested_depth'],r['arm'])for r in rows]==expected_slots,'missing/changed scheduled slots'
 pv_count=0;groups=defaultdict(dict);conserved=0;rank_checks=0
 for r in rows:
  assert r['slot']==rows.index(r)
  groups[(r['case_id'],r['requested_depth'])][r['arm']]=r
  if r['status']!='RETURNED':continue
  assert r['root_unchanged'] and r['pv_legal'];d=r['decision'];c,record=cache[r['case_id']]
  session=GameSession.replay(c,record)
  # Standalone research dataclass actions differ from GameRecord wire actions.
  # Recover only a unique FULL serialized legal action, never coordinate projection.
  if d['action'] is not None:
   a=recover_action(d['action'],session)
  for raw in d['principal_variation']:
   session.submit(recover_action(raw,session));pv_count+=1
  rw=r.get('root_work')
  if rw is None:continue
  iterations=rw['iterations'];assert [it['depth']for it in iterations]==list(range(1,d['completed_depth']+1))
  for it in iterations:
   assert set(it['root_work'])<=root_actions[r['case_id']]
   assert all(type(n)is int and n>=1 for n in it['root_work'].values())
  if rw['last_started_depth']==d['completed_depth'] and d['result_source']=='main_iteration':
   work=sum(sum(it['root_work'].values())for it in iterations)+len(iterations)+d['root_scan_nodes']
   assert work==d['nodes']+d['qnodes'],'root-child budget-event accounting failed';conserved+=1
  for order in rw['orders']:
   assert order['depth']>1 and set(order['actions'])==root_actions[r['case_id']]
   assert len(order['actions'])==len(root_actions[r['case_id']])
   previous=[it['root_work']for it in iterations if it['depth']==order['depth']-1]
   assert len(previous)==1 and previous[0]==order['previous_work'],'non-complete previous iteration promoted'
   tt=order['tt_hint'];ordered=order['actions']
   if tt in root_actions[r['case_id']]:assert ordered[0]==tt;ordered=ordered[1:]
   counts=[order['previous_work'].get(a,0)for a in ordered];assert counts==sorted(counts,reverse=True),'root order violates descending work after TT';rank_checks+=1
 return {'queries':len(rows),'returned':sum(r['status']=='RETURNED'for r in rows),'literal_pv_plies_replayed':pv_count,'conserved_root_work_calls':conserved,'rank_events_checked':rank_checks},groups

def verify_source_capsule(caps,plan,phase):
 hashes=({'driver':plan['driver_sha256'],'base_source':plan['baseline_sha256'],
          'candidate_source':plan['candidate_sha256']} if phase==1 else
         {'driver':plan['source_hashes']['driver'],'base_source':plan['source_hashes']['baseline'],
          'record_source':plan['source_hashes']['record_source'],'order_source':plan['source_hashes']['order_source']})
 for key,expected in hashes.items():
  assert hashlib.sha256(caps[key].encode()).hexdigest()==expected,'executed source capsule hash mismatch'

def run(data):
 inputs=data/'prepared-v2/inputs.json';input_rows,cache,acts=verify_inputs(inputs);out={'status':'SAVED_DATA_VERIFIED','inputs':24,'full_rules':12,'phases':{},'new_Player':0,'new_solver':0,'new_games':0}
 for phase in [1,2]:
  p=data/f'phase{phase}';f=load(data/f'phase{phase}-frozen.json');rows=load(p/'queries.json');caps=load(p/'executed-source.json');assert caps['inputs_sha256']==digest(inputs);assert caps['plan_sha256']==digest(data/f'phase{phase}-frozen.json');verify_source_capsule(caps,f,phase)
  if phase==1:
   depths=[1,4];arms=['baseline','scan_hint'];planned=[]
   for i,rr in enumerate(input_rows):
    for depth in depths:
     for arm in arms if (i+depth)%2 else arms[::-1]:planned.append((rr['id'],depth,arm))
  else:
   depths=f['requested_depths'];arms=f['arms'];planned=[]
   for i,rr in enumerate(input_rows):
    for depth in depths:
     shift=(i+depth)%len(arms)
     for arm in arms[shift:]+arms[:shift]:planned.append((rr['id'],depth,arm))
  summary,groups=verify_rows(rows,planned,cache,acts,depths,arms)
  complete_groups=0;observer_parity=0
  for key,g in groups.items():
   complete=[r for r in g.values()if r['status']=='RETURNED' and r['decision']['completed_depth']==key[1]]
   assert len({r['decision']['score']for r in complete})<=1,'complete-score mismatch'
   complete_groups+=len(complete)==len(arms)
   if phase==2:
    a,b=g['original'],g['record_only']
    if all(r['status']=='RETURNED' and r['decision']['completed_depth']==key[1]for r in [a,b]):
     for field in ['action','score','principal_variation','nodes','qnodes','evaluation_calls','pvs_null_window_searches','pvs_researches','tt_probes','tt_hits','tt_cutoffs']:
      assert a['decision'][field]==b['decision'][field],'observer changes semantics/work'
     observer_parity+=1
  summary.update(complete_groups=complete_groups,observer_semantic_work_parity_pairs=observer_parity);out['phases'][str(phase)]=summary
 return out

if __name__=='__main__':
 p=argparse.ArgumentParser(__doc__);p.add_argument('--data',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();assert not a.output.exists();result=run(a.data);a.output.write_bytes((json.dumps(result,indent=2)+'\n').encode());print(json.dumps(result))
