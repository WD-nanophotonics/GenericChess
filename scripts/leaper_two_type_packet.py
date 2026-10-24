"""Data-only public reader: decode exact JSON documents, never execute capsules."""
from pathlib import Path
import argparse,gzip,json,hashlib,time
from scripts.leaper_two_type_qualify import analyze,qualify_game
from scripts import leaper_design as L
from scripts.leaper_component_qualify import qualify_game as qualify_component
from tools.local_agent.common import write_json

def read_packet(packet,manifest):
 raw=packet.read_bytes();m=L.load(manifest);assert hashlib.sha256(raw).hexdigest()==m['packet_sha256'];data=json.loads(gzip.decompress(raw));docs=data['documents'];assert set(docs)==set(m['documents'])
 for name,text in docs.items():
  b=text.encode('utf-8');assert len(b)==m['documents'][name]['bytes'] and hashlib.sha256(b).hexdigest()==m['documents'][name]['sha256']
 return docs


def contact_frontiers(world,raw):
 from scripts.leaper_two_type_forward import profiles
 c=L.compile_rule(L.ruleset_from_dict(world['rule']));total=0
 def score(ss,e):
  if ss.state.terminal_status.is_terminal:return 0 if ss.result.winner is None else 1000000000 if ss.result.winner==0 else -1000000000
  v=e.evaluate(ss.state);return v if ss.state.position.side_to_move==0 else -v
 for r in raw['rows']:
  e,_,_=profiles(c,r['B']);ss=L.GameSession.replay(c,L.deserialize_game_record(json.dumps(r['initial_record'])));assert r['initial_record']==world['roots'][r['root']]['record'];legal=ss.legal_actions();assert len(legal)==len(r['arms'])
  assert {json.dumps(L.record_value(a),sort_keys=True)for a in legal}=={json.dumps(x['action'],sort_keys=True)for x in r['arms']}
  for arm in r['arms']:
   z=L.GameSession.replay(c,ss.to_record());z.submit(L.match_action(z,arm['action']));assert L.record_value(z.to_record())==arm['record'] and score(z,e)==arm['D1']
   replies=[] if z.state.terminal_status.is_terminal else z.legal_actions();assert len(replies)==len(arm['replies'])
   assert {json.dumps(L.record_value(a),sort_keys=True)for a in replies}=={json.dumps(x['action'],sort_keys=True)for x in arm['replies']}
   for q in arm['replies']:
    zz=L.GameSession.replay(c,z.to_record());zz.submit(L.match_action(zz,q['action']));assert L.record_value(zz.to_record())==q['record'] and score(zz,e)==q['value'];total+=1
   assert arm['D2']==(min(x['value']for x in arm['replies'])if arm['replies']else arm['D1'])
  k='D'+str(r['depth']);best=max(x[k]for x in r['arms']);assert r['best_score']==best and r['best_actions']==[x['action']for x in r['arms']if x[k]==best];assert r['decision']['action']in r['best_actions'] and r['decision']['score']==best
  pv=L.GameSession.replay(c,ss.to_record())
  for a in r['decision']['principal_variation']:pv.submit(L.match_action(pv,a))
 return dict(status='PASS',rows=len(raw['rows']),reply_occurrences=total,scope='Repeated retained arrays not unique states; no new Player calls.')

def qualify(packet,manifest,output):
 tick=time.perf_counter();docs=read_packet(packet,manifest);j=lambda name:json.loads(docs[name]);world=j('two-type/inputs.json');reg=j('two-type/registration.json');res=j('two-type/results.json');result=analyze(world,reg,res,lambda i:j(f'two-type/game-{i:03d}.json'))
 assert hashlib.sha256(docs['two-type/inputs.json'].encode()).hexdigest()==reg['input_sha256']
 assert hashlib.sha256(docs['source/leaper_two_type_forward.py'].encode()).hexdigest()==reg['source_sha256']
 geo=[];georeg=j('geometry/plan.json');execution=j('geometry/execution.json')
 assert hashlib.sha256(docs['source/leaper_two_type_geometry.py'].encode()).hexdigest()==georeg['source_sha256']==execution['source_sha256']
 for x in execution['slots']:
  i=x['root'];r=qualify_game(world,j(f'geometry/game-{i:03d}.json'),reg);assert r['value']==x['value'];geo.append(dict(root=i,**r))
 contact_world=j('contact/inputs.json');contact_reg=j('contact/registration.json');contact_res=j('contact/results.json')
 contact=analyze(contact_world,contact_reg,contact_res,lambda i:j(f'contact/game-{i:03d}.json'))
 assert hashlib.sha256(docs['contact/inputs.json'].encode()).hexdigest()==contact_reg['input_sha256']
 assert contact_reg['source_sha256']==reg['source_sha256']
 contact_cost=qualify_game(contact_world,j('contact/cost.json'),contact_reg)
 frontier=contact_frontiers(contact_world,j('contact/frontier-raw.json'))
 basis=qualify_game(j('cost-basis/inputs.json'),j('cost-basis/game.json'),reg)
 disclosure=j('cost-basis/repetition-disclosure.json');repeat=j(f"two-type/game-{disclosure['formal_index']:03d}.json");assert j('cost-basis/game.json')['final_record']==repeat['final_record']
 assert j('cost-basis/inputs.json')['rule']==world['rule']
 cw=j('component/world.json');explore=[]
 for x in j('component/exploratory-results.json')['slots']:
  r=qualify_component(cw,j('component/'+x['receipt']));assert r['value']==x['value'];explore.append(dict(actual_policy=x['actual_policy'],seed=x['seed'],**r))
 cost=qualify_component(cw,j('component/default-cost.json'))
 for name in ('left','right'):
  witness=j('legal-regions/result.json')['witness'][name];c=L.compile_rule(L.ruleset_from_dict(world['rule']));s=L.GameSession.replay(c,L.deserialize_game_record(json.dumps(witness['record'])));assert L.state_sha(s.state)==witness['state_sha256']
 nextpv=0
 nc=L.compile_rule(L.ruleset_from_dict(contact_world['rule']))
 for r in j('next/returns.json')['rows']:
  ns=L.GameSession.replay(nc,L.deserialize_game_record(json.dumps(r['initial_record'])))
  assert r['decision']['action']in [L.record_value(a)for a in ns.legal_actions()]
  for a in r['decision']['principal_variation']:ns.submit(L.match_action(ns,a));nextpv+=1
 out=dict(next_queries=6,next_PV_plies=nextpv,status='PASS',documents=len(docs),formal=result,contact=contact,contact_cost=contact_cost,contact_frontier=frontier,cost_basis=basis,geometry=geo,exploratory_component=explore,component_cost=cost,seconds=time.perf_counter()-tick,new_Player_queries=0,source_capsule_executions=0,scope='Exact UTF8 capsules and literal shared-Core fullhistory/PV qualification; data only, not independently executed search or an independent engine.')
 write_json(output,out);print('PACKET PASS',len(docs),'formal',result['games'],'geometry',len(geo),'seconds',out['seconds'],flush=True);return out
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--packet',type=Path,required=True);ap.add_argument('--manifest',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args();qualify(a.packet,a.manifest,a.output)
