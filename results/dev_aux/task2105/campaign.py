"""Fresh actual W-L price learning plus candidate-only solver factorial.

No teacher reward, no quantity payoff, no fitting from DEV, no old cap restart.
OriginalPN opponent never changes across candidate solver/price conditions.
"""
from pathlib import Path
from dataclasses import asdict
from collections import Counter
import json,hashlib,time,datetime
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.session.session import GameSession
from generic_chess.session.result import SessionStatus
from generic_chess.session.serialization import serialize_game_record
from generic_chess.core.actions import action_to_dict
from scripts.generic_session_cached_phase_player import SessionCachedPhasePlayer
from scripts.generic_session_phase_player import PhaseLimits
from scripts.generic_session_proof_bank import SessionLogicalProofBank
from scripts.generic_session_proof_player import commit_session_decision
from scripts.generic_session_win_proof_batch_pn import prove_session_win_batch_pn
from scripts.generic_session_native_material import _load_transport
from scripts.generic_win_proof import _same_state
from results.dev_aux.task2068.teacher import CanonicalTeacher
from results.dev_aux.task2105.provider import TriggerProvider
OUT=Path('results/dev_aux/task2105')
def write(n,d):
 with (OUT/n).open('x',encoding='utf-8')as f:json.dump(d,f,indent=2)
def sha_state(s):return hashlib.sha256(repr(s).encode()).hexdigest()
def evaluate(ratio):
 def f(pos,target):
  return sum((1 if p.owner==target else-1)*720*(ratio if p.current_type_id=='N'else 1)for p in pos.board if p is not None and p.current_type_id!='K')
 return f

def selector(rows,initial,grid):
 score={r:sum(x['score']for x in rows if x['ratio']==r)/sum(x['ratio']==r for x in rows)for r in grid};index=grid.index(initial);trace=[initial]
 while True:
  adjacent=[i for i in(index-1,index+1)if 0<=i<len(grid)and score[grid[i]]>score[grid[index]]]
  if not adjacent:break
  index=adjacent[0];trace.append(grid[index])
 return dict(initial=initial,selected=grid[index],trace=trace,TRAIN_means={str(k):v for k,v in score.items()})

def reuse_role(old, candidate, logical):
 winner=old['result']['winner'];outcome='UNKNOWN'if old['outcome']=='UNKNOWN'else'DRAW'if winner is None else'WIN'if winner==candidate else'LOSS'
 return dict(old,logical_slot=logical,candidate_side=candidate,reused_from=old['logical_slot'],outcome=outcome,score=None if outcome=='UNKNOWN'else 1 if outcome=='WIN'else -1 if outcome=='LOSS'else 0)

def run():
 if (OUT/'started.json').exists():raise RuntimeError('Original2105cap already started; never restart')
 start=time.perf_counter();p=json.loads((OUT/'study-freeze.json').read_text(encoding='utf-8'));roots=json.loads((OUT/'inputs.json').read_text(encoding='utf-8'))['roots'];deadline=start+p['one_cap_seconds'];write('started.json',dict(started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),one_clock=True,cap_seconds=p['one_cap_seconds'],restart_forbidden=True))
 files=set(Path('generic_chess').rglob('*.py'))|set(Path('scripts').glob('*.py'))
 for task in [2068,2072,2086,2088,2097,2098,2099,2105]:files.update(f for f in Path(f'results/dev_aux/task{task}').glob('*')if f.suffix in('.py','.json')and f.name not in('started.json','source-pin.json','completion.json'))
 files.add(Path('results/dev_aux/task2098/labels.jsonl'));source={str(f):hashlib.sha256(f.read_bytes()).hexdigest()for f in sorted(files)};write('source-pin.json',source)
 transport=_load_transport();load=time.perf_counter();teacher=CanonicalTeacher('results/dev_aux/task2097','results/dev_aux/task2098','results/dev_aux/task2099');composite=TriggerProvider(teacher);teacherload=time.perf_counter()-load;compiled={r['family']:compile_ruleset_for_execution(deserialize_ruleset(Path(r['rules']).read_text(encoding='utf-8')))for r in roots};limits=PhaseLimits(proof_nodes=p['proof_nodes'],verification_nodes=p['verification_nodes'],proof_seconds=p['proof_seconds'],verification_seconds=p['verification_seconds'],normal_seconds=p['normal_seconds']);games=[];physical={};physical_count=0;move_count=0;status='COMPLETE';selected=None;devexpected=None
 def cancelled():
  transport.stop_check(Path.cwd());return time.perf_counter()>=deadline
 with (OUT/'games.jsonl').open('x',encoding='utf-8')as jf,(OUT/'moves.jsonl').open('x',encoding='utf-8')as mf:
  def game(root,ratio,candidate,policy,phase):
   nonlocal physical_count,move_count,status
   logical=len(games);identical=ratio==1 and policy=='TRIGGER';key=(root['family'],ratio,policy,0 if identical else candidate)
   if key in physical:
    old=physical[key];row=reuse_role(old,candidate,logical);games.append(row);jf.write(json.dumps(row)+'\n');jf.flush();return row
   c=compiled[root['family']];s=GameSession(c);players=[];pid=physical_count;physical_count+=1
   for side in(0,1):
    provider=composite
    players.append(SessionCachedPhasePlayer(c,evaluate(ratio if side==candidate else 1.),bank=SessionLogicalProofBank(provider,capacity=256),limits=limits,proof_enabled=True,max_depth=p['normal_depth'],proof_depth=p['proof_depth']))
   began=time.perf_counter();steps=0;reason='H_UNKNOWN'
   for ply in range(p['H']):
    if s.result.status is not SessionStatus.ONGOING:reason='ACTUAL_TERMINAL';break
    if cancelled():status='GLOBAL_CAP';reason='GLOBAL_CAP';break
    side=s.state.position.side_to_move;d=players[side].choose(s,max_nodes=p['normal_nodes'],seconds=p['step_seconds'],cancel=cancelled)
    if d.choice is None:reason=d.exit_cause;status='INCOMPLETE_OUTCOME';break
    before=sha_state(s.state);ranks=[None if x.cursor is None else x.cursor.node.rank for x in players];commit_session_decision(s,d,players,cancel=cancelled);replayed=GameSession.replay(c,s.to_record());assert _same_state(replayed.state,s.state)and _same_state(replayed.result,s.result)
    data=dict(physical_id=pid,logical_slot=logical,ply=ply,side=side,choice=action_to_dict(d.choice.action),source=d.source,proof_reason=d.proof_reason,exit_cause=d.exit_cause,proof_nodes=d.proof_nodes,verification_nodes=d.verification_nodes,fill_verification_nodes=d.fill_verification_nodes,search_nodes=d.search_nodes,seconds=d.seconds,proof_seconds=d.proof_seconds,normal_seconds=d.normal_seconds,phase_limits=dict(d.phase_limits),before_state_sha=before,after_state_sha=sha_state(s.state),before_ranks=ranks,after_ranks=[None if x.cursor is None else x.cursor.node.rank for x in players],result=dict(status=s.result.status.value,winner=s.result.winner));mf.write(json.dumps(data)+'\n');mf.flush();steps+=1;move_count+=1
    if s.result.status is not SessionStatus.ONGOING:reason='ACTUAL_TERMINAL';break
   result=s.result;outcome='UNKNOWN'if result.status is SessionStatus.ONGOING else'DRAW'if result.winner is None else'WIN'if result.winner==candidate else'LOSS';row=dict(logical_slot=logical,physical_id=pid,phase=phase,family=root['family'],ratio=ratio,candidate_side=candidate,candidate_policy=policy,opponent_ratio=1.,opponent_policy='TRIGGER',reused_from=None,outcome=outcome,score=None if outcome=='UNKNOWN'else 1 if outcome=='WIN'else -1 if outcome=='LOSS'else 0,moves=steps,reason=reason,seconds=time.perf_counter()-began,result=dict(status=result.status.value,winner=result.winner),record=json.loads(serialize_game_record(s.to_record())),final_state_sha=sha_state(s.state));physical[key]=row;games.append(row);jf.write(json.dumps(row)+'\n');jf.flush()
   if physical_count%16==0:print(json.dumps(dict(logical=len(games),physical=physical_count,moves=move_count,seconds=time.perf_counter()-start)),flush=True)
   return row
  for root in roots[:32]:
   for role in(0,1):
    order=p['ratios'][(root['family']+role)%5:]+p['ratios'][:(root['family']+role)%5]
    for ratio in order:
     if cancelled():status='GLOBAL_CAP';break
     row=game(root,ratio,role,'TRIGGER','TRAIN')
     if row['outcome']=='UNKNOWN':break
    if status!='COMPLETE':break
   if status!='COMPLETE':break
  train=[g for g in games if g['phase']=='TRAIN']
  if status=='COMPLETE'and len(train)==320 and all(g['score']is not None for g in train):
   selected=[selector(train,initial,p['ratios'])for initial in p['initial_ratio']];write('selector-lock.json',dict(status='LOCKED_BEFORE_ANY_DEV_GAME',selected=selected,source_TRAIN_games_sha=hashlib.sha256((OUT/'games.jsonl').read_bytes()).hexdigest()));prices=sorted({1.}|{s['selected']for s in selected});devexpected=16*2*len(prices)
   for root in roots[32:]:
    if status!='COMPLETE':break
    for role in(0,1):
     conditions=[(ratio,policy)for ratio in prices for policy in('TRIGGER',)];offset=(root['family']+role)%len(conditions);conditions=conditions[offset:]+conditions[:offset]
     for ratio,policy in conditions:
      if cancelled():status='GLOBAL_CAP';break
      row=game(root,ratio,role,policy,'DEV')
      if row['outcome']=='UNKNOWN':break
     if status!='COMPLETE':break
    if status!='COMPLETE':break
  else:selected=None
 if time.perf_counter()>=deadline:status='GLOBAL_CAP'
 unchanged=all(hashlib.sha256(Path(k).read_bytes()).hexdigest()==v for k,v in source.items());result=dict(status=status,logical_games=len(games),physical_games=physical_count,physical_moves=move_count,expected_TRAIN_logical=320,actual_TRAIN_logical=sum(g['phase']=='TRAIN'for g in games),expected_DEV_logical=devexpected,actual_DEV_logical=sum(g['phase']=='DEV'for g in games),selected=selected,outcomes=dict(Counter(g['outcome']for g in games)),seconds=time.perf_counter()-start,teacher_load_seconds=teacherload,source_unchanged=unchanged,scope='ActualruleW-L underfixedTRIGGERopponent; pricefactoronly/NEWresourcecontext, notpooledwith2100. Reusedidenticalbaselinephysicalrecords explicitlymarked, notindependentextra games. Singleoriginalcap/missingretained/noDEVselection.')
 write('completion.json',result);print(json.dumps(result),flush=True)
if __name__=='__main__':run()
