"""Independent actual public replay of all forced-action continuations."""
from pathlib import Path
import json,hashlib,time
from collections import defaultdict,Counter
from dataclasses import asdict
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record,serialize_game_record
from generic_chess.session.result import SessionStatus
from scripts.generic_proof_rnb_bridge import actor_state,uci
from scripts.generic_royal_actor import RoyalActor
from scripts.generic_win_proof import _same_state
O=Path('results/dev_aux/task1914');P=Path('results/dev_aux/task1911')
def read(p):return json.loads(Path(p).read_text())
def lines(p):return [json.loads(s) for s in Path(p).read_text().splitlines()]
def digest(s):return hashlib.sha256(repr(s).encode()).hexdigest()
def rd(s):return {**asdict(s.result),'status':s.result.status.value}
def main():
 begin=time.perf_counter();plan=read(P/'run-plan.json');completion=read(P/'completion.json');games=lines(P/'games.jsonl');moves=lines(P/'moves.jsonl');events=lines(P/'run/transport.jsonl');groups=defaultdict(list)
 for m in moves:groups[m['slot']].append(m)
 assert completion['status']=='COMPLETE' and completion['completed']==len(games)==len(plan['slots'])==22 and completion['source_unchanged'];c=compile_ruleset_for_execution(deserialize_ruleset(Path(plan['rules']).read_text()));actor=RoyalActor(4);bindings=[];proofgames=proofsteps=tailgames=tailmoves=0;causes=Counter();outcomes=Counter();pairs=defaultdict(dict);allnative=[]
 for frozen,g in zip(plan['slots'],games):
  assert all(g[k]==v for k,v in frozen.items());s=GameSession.replay(c,deserialize_game_record(json.dumps(frozen['start_record'])));assert digest(s.state)==frozen['start_state_sha'];parents=read('results/dev_aux/task1910/result.json')['pairs'][g['pair']];a=next(x for x in parents['alternatives'] if x['ratio']==g['origin_ratio']);assert a['child_record']==frozen['start_record'] and a['action']==g['forced_action'];assert s.to_record().actions[-1]==deserialize_game_record(json.dumps(a['child_record'])).actions[-1]
  owners=set();tail=False;steps=groups[g['slot']];assert len(steps)==g['moves']
  for ply,m in enumerate(steps):
   assert m['ply']==ply and m['side']==s.state.position.side_to_move and digest(s.state)==m['before_state_sha'] and m['budget']==4096;assert s.result.status is SessionStatus.ONGOING
   assert m['proof_nodes']<=16384 and m['verification_nodes']<=16384
   assert m['phase_limits']==dict(normal_nodes=4096,proof_nodes=16384,verification_nodes=16384,total_seconds=2.75,proof_seconds=1.5,verification_seconds=.5,normal_seconds=.1)
   if m['source']=='PROOF':assert ply<48;owners.add(m['side']);proofsteps+=1
   if ply>=48:assert m['tail'] and m['source']!='PROOF' and m['proof_nodes']==m['verification_nodes']==0 and any(v is not None and 0<v<=64 for v in m['before_ranks']);tail=True;tailmoves+=1
   else:assert not m['tail']
   if m['source']=='EXTERNAL_SEARCH':
    initial=GameSession(c,s.to_record().initial_setup_key);command='position fen '+actor.fen(actor_state(initial.state))+(' moves '+' '.join(uci(a) for a in s.to_record().actions) if s.to_record().actions else '');bindings.append((command,repr(s.to_record()),m))
   front=dict(actor.moves(actor_state(s.state)));assert set(front)==set(uci(a) for a in s.legal_actions());r=json.loads(serialize_game_record(s.to_record()));r['actions'].append(m['choice']);act=deserialize_game_record(json.dumps(r)).actions[-1];assert uci(act) in front;s.submit(act);assert actor_state(s.state)==front[uci(act)] and digest(s.state)==m['after_state_sha'] and rd(s)==m['result']
   for before,after in zip(m['before_ranks'],m['after_ranks']):
    if before is not None and before>0:assert after is not None and 0<=after<before
   causes[m['exit_cause']]+=1
  actual=GameSession.replay(c,deserialize_game_record(json.dumps(g['record'])));assert _same_state(s.state,actual.state) and _same_state(s.result,actual.result) and rd(s)==g['result'] and digest(s.state)==g['final_state_sha'];outcome='UNKNOWN' if s.result.status is SessionStatus.ONGOING else 'DRAW' if s.result.winner is None else 'WIN' if s.result.winner==g['candidate_side'] else 'LOSS';assert g['outcome']==outcome and g['finite_event_score']==(1 if outcome=='WIN' else -1 if outcome=='LOSS' else 0)
  if owners:assert len(owners)==1 and s.result.winner==next(iter(owners));proofgames+=1
  if tail:assert s.result.status is not SessionStatus.ONGOING;tailgames+=1
  assert tail==g['tail'];outcomes[outcome]+=1;pairs[g['pair']][g['origin_ratio']]=g
 intent=[e for e in events if e['event']=='INTENT'];choices=[e for e in events if e['event']=='CHOICE'];sent=[e for e in events if e['event']=='SENT'];profiles=[e for e in events if e['event']=='PROFILE'];clears=[e for e in events if e['event']=='CLEAR'];assert len(bindings)==len(intent)==len(choices)==len(sent)==len(profiles)==len(clears)==completion['native_go']
 for q,((command,record,m),i,ch,se,profile,clear) in enumerate(zip(bindings,intent,choices,sent,profiles,clears)):
  assert q==i['query']==ch['query']==se['query'] and i['position']==command and i['root_record']==record and i['R']==ch['R']==profile['values']==clear['values']==[720]*4 and ch['reported_nodes']==m['search_nodes'] and ch['requested_nodes']==4096
  action=deserialize_game_record(json.dumps({'schema_version':1,'ruleset_fingerprint':c.ruleset_fingerprint,'actions':[m['choice']],'resigned_by':None})).actions[0];assert ch['move']==uci(action)
  assert any('DEV_AUX leafRNBP 720 720 720 720 nativeP 720 nativeR 720 nativeN 720 nativeB 720 captureP 720 captureR 720 captureN 720 captureB 720' in x for x in profile['ack'])
 results=[]
 for n,pair in sorted(pairs.items()):
  a,b=pair[2.],pair[4.];results.append(dict(pair=n,family=a['family'],role=a['candidate_side'],origin2_action=a['forced_action'],origin4_action=b['forced_action'],outcomes=[a['outcome'],b['outcome']],scores=[a['finite_event_score'],b['finite_event_score']],delta=b['finite_event_score']-a['finite_event_score'],moves=[a['moves'],b['moves']],old_wholepolicy_outcomes=read('results/dev_aux/task1910/result.json')['pairs'][n]['old_wholepolicy_outcomes']))
 out=dict(status='PASS_ALL22_ACTUAL_CONTINUATIONS',games=22,moves=len(moves),native_bindings=len(bindings),proof_games=proofgames,proof_steps=proofsteps,tail_games=tailgames,tail_moves=tailmoves,outcomes=dict(outcomes),cells={str(r):dict(outcomes=dict(Counter(g['outcome'] for g in games if g['origin_ratio']==r)),net=sum(g['finite_event_score'] for g in games if g['origin_ratio']==r)) for r in (2.,4.)},pairs=results,exit_causes=dict(causes),seconds=time.perf_counter()-begin,scope='EXPOSED11pairedfirstactions; samefixedUNIT7204096normal16kproofBOTHafterforcedmove, H48additional/actualmaxply96. Not learning4vs2, not oldpolicystrength/freshvalidation, no independently randomized price trial. Changedoldopponent64->4096/nobank for BOTH newalternatives. UNKNOWNseparate; only actualterminals reward.')
 with (O/'result.json').open('x') as f:json.dump(out,f,indent=2)
 print(json.dumps(out))
if __name__=='__main__':main()
