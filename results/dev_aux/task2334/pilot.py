"""Frozen policy-only actual W-L pilot; no price fit or fixed learner adoption."""
from pathlib import Path
from dataclasses import asdict,fields
import json,time,hashlib,datetime
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import serialize_game_record,deserialize_game_record
from generic_chess.session.result import SessionStatus
from scripts.generic_session_phase_player import PhaseLimits
from scripts.generic_session_proof_player import commit_session_decision
from results.dev_aux.task2210.player import PaidGraphPhasePlayer
from results.dev_aux.task2153.stop_evidence import EvidenceStopReader
from results.dev_aux.task2175.receipt import choice_value
from results.dev_aux.task2181.run import encode as graph_encode
from results.dev_aux.task2048.portable_certificate import encode as tree_encode
OUT=Path('results/dev_aux/task2334')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(name,v):
 with(OUT/name).open('x',encoding='utf-8')as f:json.dump(v,f,indent=2)
def run():
 assert not(OUT/'started.json').exists()
 if not Path('results/dev_aux/task2260/result.json').exists():raise RuntimeError('Actualprefixproofqualification required first')
 p=json.loads((OUT/'plan.json').read_text());assert sha(p['input'])==p['input_sha']and sha(OUT/'slots.json')==p['slots_sha']
 for name,h in p['pins'].items():assert sha(name)==h
 roots={r['index']:r for r in json.loads(Path(p['input']).read_text())};slots=json.loads((OUT/'slots.json').read_text());began=time.perf_counter();deadline=began+p['one_cap_seconds'];stop=EvidenceStopReader(Path.cwd())
 save('started.json',dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),plan_sha=sha(OUT/'plan.json')));games=[];status='COMPLETE';decisions=0;certificates=0
 def cancel():stop();return time.perf_counter()>=deadline
 with(OUT/'games.jsonl').open('x',encoding='utf-8')as gf,(OUT/'decisions.jsonl').open('x',encoding='utf-8')as df,(OUT/'certificates.jsonl').open('x',encoding='utf-8')as cf:
  for slot in slots:
   if cancel():status='PARTIAL_GLOBAL_CAP';break
   start=time.perf_counter();root=roots[slot['root']];c=compile_ruleset_for_execution(deserialize_ruleset(Path(root['rules']).read_text()));s=GameSession.replay(c,deserialize_game_record(json.dumps(root['record'])))
   assert hashlib.sha256(repr(s.state).encode()).hexdigest()==root['state_sha']
   definition=deserialize_ruleset(Path(root['rules']).read_text());anchors={t.type_id for t in definition.piece_types if t.is_anchor}
   def material(pos,target,ratio):
    value=sum((1 if pc.owner==target else-1)*(ratio if pc.current_type_id=='R'else 1.)for pc in pos.board if pc is not None and pc.current_type_id not in anchors)
    value+=sum((1 if owner==target else-1)*count for owner,hand in enumerate(pos.hands)for type_id,count in hand.counts if type_id not in anchors)
    return float(value)
   cfg=p['candidate'];limits=PhaseLimits(proof_nodes=cfg['proof_nodes'],proof_seconds=cfg['proof_seconds'],verification_nodes=cfg['verification_nodes'],verification_seconds=cfg['verification_seconds'],normal_seconds=cfg['normal_seconds'])
   foe=p['opponents'][slot['opponent']];candidate=PaidGraphPhasePlayer(c,lambda pos,t:material(pos,t,slot['ratio']),limits=limits,max_depth=cfg['normal_depth'],proof_depth=cfg['proof_depth'],graph_positions=cfg['graph_positions'],graph_edges=cfg['graph_edges'],graph_enabled=slot['arm']=='LOW_ONLY_INCREMENTAL',proof_enabled=slot['arm']=='LOW_ONLY_INCREMENTAL')
   foe=p['opponents'][slot['opponent']];opponent=PaidGraphPhasePlayer(c,lambda pos,t:material(pos,t,foe['ratio']),limits=PhaseLimits(proof_nodes=foe['proof_nodes'],proof_seconds=foe['proof_seconds'],verification_nodes=foe['verification_nodes'],verification_seconds=foe['verification_seconds'],normal_seconds=foe['normal_seconds']),max_depth=cfg['normal_depth'],proof_depth=cfg['proof_depth'],graph_enabled=True)
   candidate.graph_search=__import__('results.dev_aux.task2273.incremental_adapted',fromlist=['prove_incremental_graph']).prove_incremental_graph
   attempted_regimes=set();players={slot['candidate_color']:candidate,1-slot['candidate_color']:opponent};counts={};end='HORIZON_UNFINISHED';moves=0
   for ply in range(p['H']):
    if s.result.status is not SessionStatus.ONGOING:end='ACTUAL_TERMINAL';break
    if cancel():end='GLOBAL_CAP_UNFINISHED';status='PARTIAL_GLOBAL_CAP';break
    side=s.state.position.side_to_move;player=players[side];nodes=cfg['normal_nodes']if side==slot['candidate_color']else foe['normal_nodes'];before=time.perf_counter()
    regime='LOW'if sum(pc is not None for pc in s.state.position.board)+sum(n for h in s.state.position.hands for _,n in h.counts)<=4 else'HIGH'
    is_candidate=side==slot['candidate_color'];attempt=is_candidate and slot['arm']=='LOW_ONLY_INCREMENTAL' and regime=='LOW' and regime not in attempted_regimes and candidate.cursor is None
    if attempt:attempted_regimes.add(regime)
    caller=p['candidate_proof_caller_seconds']if attempt else p['step_seconds']
    d=player.choose(s,max_nodes=nodes,seconds=min(caller,max(0.,deadline-time.perf_counter())),cancel=cancel,allow_new_proof=attempt if is_candidate else True)
    elapsed=time.perf_counter()-before;normal=None if d.normal_receipt is None else {f.name:(choice_value(v)if f.name=='choice'else v)for f in fields(d.normal_receipt)for v in[getattr(d.normal_receipt,f.name)]}
    row=dict(regime=regime,new_proof_attempt=attempt,caller_seconds=caller,slot=slot['slot'],ply=ply,side=side,is_candidate=side==slot['candidate_color'],root_record=json.loads(serialize_game_record(s.to_record())),root_state_sha=hashlib.sha256(repr(s.state).encode()).hexdigest(),choice=choice_value(d.choice),source=d.source,exit_cause=d.exit_cause,proof_reason=d.proof_reason,raw_proofs=d.raw_proofs,verification_receipts=d.verification_receipts,phase_limits=d.phase_limits,normal_receipt=normal,reported_seconds=d.seconds,measured_seconds=elapsed,admission_seconds=d.admission_seconds,fallback_admission_seconds=d.fallback_admission_seconds,proof_seconds=d.proof_seconds,verification_seconds=d.verification_seconds,normal_seconds=d.normal_seconds,tree_visits=d.proof_nodes,graph_positions=d.graph_positions,graph_expanded=d.graph_expanded,graph_transitions=d.graph_transitions,graph_verifier_visits=d.graph_verifier_visits,tree_verifier_visits=d.tree_verifier_visits,normal_visits=d.search_nodes,proof_rank=d.proof_rank)
    df.write(json.dumps(row)+'\n');df.flush();decisions+=1;counts[d.source]=counts.get(d.source,0)+1
    if d.source in('VERIFIED_GRAPH_STRATEGY','VERIFIED_FULL_HISTORY_STRATEGY'):
     cur=player.cursor;cert=cur.certificate;cf.write(json.dumps(dict(slot=slot['slot'],ply=ply,side=side,kind=player.cursor_kind,root_record=json.loads(serialize_game_record(s.to_record())),certificate=graph_encode(cert)if player.cursor_kind=='GRAPH'else tree_encode(cert.tree)))+'\n');cf.flush();certificates+=1
    if d.choice is None:end='NO_CHOICE_UNFINISHED';break
    if cancel():end='GLOBAL_CAP_UNFINISHED';status='PARTIAL_GLOBAL_CAP';break
    commit_session_decision(s,d,players.values(),cancel=cancel);moves+=1
   if s.result.status is not SessionStatus.ONGOING:end='ACTUAL_TERMINAL'
   terminal=end=='ACTUAL_TERMINAL';winner=s.result.winner;outcome=('D'if winner is None else'W'if winner==slot['candidate_color']else'L')if terminal else'U'
   game=dict(slot,ending=end,outcome=outcome,reward=None if not terminal else 0 if winner is None else 1 if winner==slot['candidate_color']else-1,actual_status=s.result.status.value,winner=winner,plies=moves,record=json.loads(serialize_game_record(s.to_record())),sources=counts,seconds=time.perf_counter()-start)
   games.append(game);gf.write(json.dumps(game)+'\n');gf.flush();print(json.dumps(dict(slot=slot['slot'],root=slot['root'],arm=slot['arm'],outcome=outcome,plies=moves,seconds=game['seconds'])),flush=True)
   if status!='COMPLETE':break
 save('completion.json',dict(status=status,games=len(games),expected_games=p['expected_games'],missing=p['expected_games']-len(games),seconds=time.perf_counter()-began,decisions=decisions,certificates=certificates,outcomes={x:sum(g['outcome']==x for g in games)for x in'WLDU'},scope=p['scope']))
if __name__=='__main__':import sys;{'run':run}[sys.argv[1]]()
