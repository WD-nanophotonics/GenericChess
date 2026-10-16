"""Fresh true-W-L learning over rule-derived price cells; no proxy reward."""
from pathlib import Path
from collections import Counter
import json,time,hashlib,datetime
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.session.session import GameSession
from generic_chess.session.result import SessionStatus
from generic_chess.session.serialization import serialize_game_record
from generic_chess.core.actions import action_to_dict
from results.dev_aux.task2136.legal_fallback import LegalFallbackPhasePlayer
from scripts.generic_session_phase_player import PhaseLimits
from scripts.generic_session_proof_bank import SessionLogicalProofBank
from scripts.generic_session_proof_player import commit_session_decision
from scripts.generic_win_proof import _same_state,_Interrupted
from results.dev_aux.task2068.teacher import CanonicalTeacher
from results.dev_aux.task2105.provider import TriggerProvider
from results.dev_aux.task2100.campaign import evaluate,selector,reuse_role,sha_state
from results.dev_aux.task2048.portable_certificate import encode
from results.dev_aux.task2122.decision_cells import support,boundaries
from results.dev_aux.task2131.stop_reader import ParsedStopReader
OUT=Path('results/dev_aux/task2149')
def write(name,value):
 with(OUT/name).open('x',encoding='utf-8')as f:json.dump(value,f,indent=2)
def run():
 if(OUT/'started.json').exists():raise RuntimeError('single600cap, neverrestart')
 start=time.perf_counter();p=json.loads((OUT/'plan.json').read_text(encoding='utf-8'));deadline=start+600;write('started.json',dict(started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),source_sha=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),cap_seconds=600));roots=json.loads((OUT/'inputs.json').read_text(encoding='utf-8'))['roots'];compiled={r['family']:compile_ruleset_for_execution(deserialize_ruleset(Path(r['rules']).read_text(encoding='utf-8')))for r in roots};load=time.perf_counter();teacher=CanonicalTeacher('results/dev_aux/task2093','results/dev_aux/task2094','results/dev_aux/task2095');load=time.perf_counter()-load;provider=TriggerProvider(teacher);stop=ParsedStopReader(Path.cwd());limits=PhaseLimits(proof_nodes=p['proof_nodes'],verification_nodes=p['verification_nodes'],proof_seconds=p['proof_seconds'],verification_seconds=p['verification_seconds'],normal_seconds=p['normal_seconds']);games=[];physical={};pidcount=movecount=0;status='COMPLETE';selected=None;devexpected=None
 def cancelled():stop();return time.perf_counter()>=deadline
 # Mechanical price-cell derivation; no teacher labels or fitness queried.
 points=boundaries(support(GameSession(compiled[0]).state.position,0));assert list(map(str,points))==['1/2','1','2'];last=0;grid=[]
 for b in points:grid.extend([(last+b)/2,b]);last=b
 grid.append(last+1);assert list(map(float,grid))==p['ratios'];write('price-cells.json',dict(positive_crossings=list(map(str,points)),representatives=list(map(str,grid)),fitness_queries=0))
 with(OUT/'decisions.jsonl').open('x',encoding='utf-8')as df,(OUT/'games.jsonl').open('x',encoding='utf-8')as jf,(OUT/'moves.jsonl').open('x',encoding='utf-8')as mf,(OUT/'certificates.jsonl').open('x',encoding='utf-8')as cf:
  def game(family,ratio,candidate,phase,foe):
   nonlocal pidcount,movecount,status
   logical=len(games);key=(family,foe,ratio,0 if ratio==foe else candidate)
   if key in physical:
    row=reuse_role(physical[key],candidate,logical);games.append(row);jf.write(json.dumps(row)+'\n');jf.flush();return row
   if cancelled():status='GLOBAL_CAP';return None
   pid=pidcount;pidcount+=1;c=compiled[family];s=GameSession(c);players=[LegalFallbackPhasePlayer(c,evaluate(ratio if side==candidate else foe),bank=SessionLogicalProofBank(provider,capacity=256),limits=limits,proof_enabled=True,max_depth=2,proof_depth=64)for side in(0,1)];began=time.perf_counter();steps=0;reason='H_UNKNOWN'
   for ply in range(96):
    if s.result.status is not SessionStatus.ONGOING:reason='ACTUAL_TERMINAL';break
    if cancelled():status='GLOBAL_CAP';reason=status;break
    side=s.state.position.side_to_move;d=players[side].choose(s,max_nodes=64,seconds=.75,cancel=cancelled)
    from results.dev_aux.task2139.receipt import decision_receipt
    df.write(json.dumps(decision_receipt(s,d,physical_id=pid,logical_slot=logical,ply=ply,candidate=candidate,limits=p))+'\n');df.flush()
    if d.choice is None:status='INCOMPLETE_OUTCOME';reason=d.exit_cause;break
    if d.source=='PROOF':
     cert=players[side].cursor.certificate;cf.write(json.dumps(dict(physical_id=pid,ply=ply,target=side,ruleset_fingerprint=cert.ruleset_fingerprint,root_record=json.loads(serialize_game_record(cert.root_record)),tree=encode(cert.tree)))+'\n');cf.flush()
    before=sha_state(s.state)
    try:commit_session_decision(s,d,players,cancel=cancelled)
    except _Interrupted:status='GLOBAL_CAP';reason='cancelled_before_commit';break
    replay=GameSession.replay(c,s.to_record());assert _same_state(replay.state,s.state)and replay.result==s.result
    row=dict(physical_id=pid,logical_slot=logical,ply=ply,side=side,is_candidate=side==candidate,choice=action_to_dict(d.choice.action),source=d.source,proof_reason=d.proof_reason,logical_status=d.logical_status,proof_nodes=d.proof_nodes,verification_nodes=d.verification_nodes,fill_verification_nodes=d.fill_verification_nodes,search_nodes=d.search_nodes,completed_depth=None if d.normal_receipt is None else d.normal_receipt.completed_depth,seconds=d.seconds,proof_seconds=d.proof_seconds,normal_seconds=d.normal_seconds,verification_seconds=d.verification_seconds,fill_verification_seconds=d.fill_verification_seconds,phase_limits=dict(d.phase_limits),before_state_sha=before,after_state_sha=sha_state(s.state),result=dict(status=s.result.status.value,winner=s.result.winner));mf.write(json.dumps(row)+'\n');mf.flush();steps+=1;movecount+=1
    if s.result.status is not SessionStatus.ONGOING:reason='ACTUAL_TERMINAL';break
   outcome='UNKNOWN'if s.result.status is SessionStatus.ONGOING else'DRAW'if s.result.winner is None else'WIN'if s.result.winner==candidate else'LOSS';g=dict(logical_slot=logical,physical_id=pid,phase=phase,family=family,ratio=ratio,candidate_side=candidate,candidate_policy='TRIGGER',opponent_ratio=foe,opponent_policy='TRIGGER',controller='2131+2136_CANCEL_LATCH',reused_from=None,outcome=outcome,score=None if outcome=='UNKNOWN'else 1 if outcome=='WIN'else -1 if outcome=='LOSS'else 0,moves=steps,reason=reason,seconds=time.perf_counter()-began,result=dict(status=s.result.status.value,winner=s.result.winner),record=json.loads(serialize_game_record(s.to_record())),final_state_sha=sha_state(s.state));physical[key]=g;games.append(g);jf.write(json.dumps(g)+'\n');jf.flush()
   if pidcount%32==0:print(json.dumps(dict(phase=phase,logical=len(games),physical=pidcount,moves=movecount,seconds=time.perf_counter()-start)),flush=True)
   if outcome=='UNKNOWN':status='INCOMPLETE_OUTCOME'
   return g
  for family in range(32):
   foes=p['TRAIN_foes']if family%2==0 else list(reversed(p['TRAIN_foes']))
   for foe in foes:
    for role in(0,1):
     off=(family+role)%7;order=p['ratios'][off:]+p['ratios'][:off]
     for ratio in order:
      if status!='COMPLETE':break
      game(family,ratio,role,'TRAIN',foe)
     if status!='COMPLETE':break
    if status!='COMPLETE':break
   if status!='COMPLETE':break
  train=[g for g in games if g['phase']=='TRAIN']
  if status=='COMPLETE'and len(train)==896 and all(g['score']is not None for g in train):
   totals={r:sum(g['score']for g in train if g['ratio']==r)for r in p['ratios']}
   maxima=[r for r in p['ratios']if totals[r]==max(totals.values())]
   chosen=1. if 1. in maxima else min(maxima)
   selected=dict(selected=chosen,TRAIN_sums={str(k):v for k,v in totals.items()},argmax=maxima,method=p['selection'])
   prices=sorted({1.,chosen});devexpected=16*2*len(prices)
   write('selector-lock.json',dict(status='LOCKED_BEFORE_ANY_DEV_GAME',selected=selected,prices=prices,source_TRAIN_games_sha=hashlib.sha256((OUT/'games.jsonl').read_bytes()).hexdigest()))
   for family in range(32,48):
    for role in(0,1):
     off=(family+role)%len(prices);order=prices[off:]+prices[:off]
     for ratio in order:
      if status!='COMPLETE':break
      game(family,ratio,role,'DEV',1.)
     if status!='COMPLETE':break
    if status!='COMPLETE':break
 result=dict(status=status,logical_games=len(games),physical_games=pidcount,moves=movecount,TRAIN_logical=len(train),DEV_logical=sum(g['phase']=='DEV'for g in games),expected_TRAIN_logical=896,expected_DEV_logical=devexpected,selected=selected,teacher_load_seconds=load,teacher_prepaid_seconds=p['teacher_prepaid_seconds'],seconds=time.perf_counter()-start,outcomes=dict(Counter(g['outcome']for g in games)),stop_actual_reads=stop.reads,stop_actual_parses=stop.parses,stop_bytes_read=stop.bytes_read,scope=p['question']);write('completion.json',result);print(json.dumps(result),flush=True)
if __name__=='__main__':run()
