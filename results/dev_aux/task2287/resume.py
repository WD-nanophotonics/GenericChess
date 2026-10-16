"""Frozen stronger-normal resource transfer, no refit or DEV profile selection."""
from pathlib import Path
import json,time,hashlib,importlib
from collections import Counter
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import serialize_game_record,deserialize_game_record
from generic_chess.session.result import SessionStatus
from scripts.generic_session_proof_player import commit_session_decision
from results.dev_aux.task2153.stop_evidence import EvidenceStopReader
OUT=Path('results/dev_aux/task2287')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(n,v):
 with(OUT/n).open('x',encoding='utf-8')as f:json.dump(v,f,indent=2)
def run():
 assert not(OUT/'resume-started.json').exists();p=json.loads((OUT/'plan.json').read_text());assert sha(OUT/'transfer.py')==p['source_sha']
 assert sha(OUT/'inputs.json')==p['inputs_sha'] and json.loads(Path('results/dev_aux/task2286/result.json').read_text())['queries']==320
 recovery=json.loads((OUT/'runtime-recovery.json').read_text());import datetime
 begin=time.perf_counter();oldstart=datetime.datetime.fromisoformat(recovery['original_start_conservative_utc']);remaining=max(0.,p['one_cap_seconds']-(datetime.datetime.now(datetime.timezone.utc)-oldstart).total_seconds());deadline=begin+remaining;stop=EvidenceStopReader(Path.cwd());save('resume-started.json',dict(original_start=recovery['original_start_conservative_utc'],remaining_seconds=remaining,no_clock_reset=True));games=[json.loads(x)for x in(OUT/'games.jsonl').read_text().splitlines()];decisions=sum(1 for _ in(OUT/'moves.jsonl').open());status='COMPLETE_EXCEPT_INTERRUPTED_SLOT';planned_slot=-1
 def cancel():stop();return time.perf_counter()>=deadline
 with(OUT/'games.jsonl').open('a',encoding='utf-8')as gf,(OUT/'moves.jsonl').open('a',encoding='utf-8')as mf:
  for seed in p['seeds']:
   task=seed
   module=importlib.import_module('results.dev_aux.task2282.study');guide=module.Guide();roots=json.loads((OUT/'inputs.json').read_text())['roots'];base=dict(priority_seed=seed,normal_depth=3)
   for root in roots:
    for foe in p['opponent_prices']:
     for role in p['candidate_colors']:
      profiles=p['profiles']if(root['family']+role)%2==0 else list(reversed(p['profiles']))
      for ratio in profiles:
       planned_slot+=1
       if planned_slot<=recovery['interrupted_slot']:continue
       if cancel():status='PARTIAL_GLOBAL_CAP';break
       start=time.perf_counter();slot=planned_slot;c=compile_ruleset_for_execution(deserialize_ruleset(Path(root['rules']).read_text()));s=GameSession.replay(c,deserialize_game_record(json.dumps(root['record'])));players=[module.GuidedPlayer(c,ratio if side==role else foe,guide,dict(base,normal_seconds=p['candidate'if side==role else'opponent']['normal_seconds']))for side in(0,1)];moves=0;reason='H_UNFINISHED'
       for ply in range(p['H']):
        if s.result.status is not SessionStatus.ONGOING:reason='ACTUAL_RULE_TERMINAL';break
        if cancel():reason='GLOBAL_CAP_UNFINISHED';status='PARTIAL_GLOBAL_CAP';break
        side=s.state.position.side_to_move;cfg=p['candidate'if side==role else'opponent'];before=hashlib.sha256(repr(s.state).encode()).hexdigest();d=players[side].choose(s,max_nodes=cfg['normal_nodes'],seconds=min(cfg['step_seconds'],max(0.,deadline-time.perf_counter())),cancel=cancel)
        row=dict(slot=slot,context=task,family=root['family'],ratio=ratio,opponent_ratio=foe,candidate_color=role,ply=ply,side=side,is_candidate=side==role,source=d.source,seconds=d.seconds,normal_visits=d.search_nodes,normal_depth=None if d.normal_receipt is None else d.normal_receipt.completed_depth,exit_cause=d.exit_cause,root_state_sha=before)
        if d.choice is None:reason='NO_CHOICE_UNFINISHED';row['after_state_sha']=before;mf.write(json.dumps(row)+'\n');mf.flush();decisions+=1;break
        if cancel():reason='GLOBAL_CAP_UNFINISHED';status='PARTIAL_GLOBAL_CAP';break
        commit_session_decision(s,d,players,cancel=cancel);moves+=1;row['after_state_sha']=hashlib.sha256(repr(s.state).encode()).hexdigest();mf.write(json.dumps(row)+'\n');mf.flush();decisions+=1
       terminal=s.result.status is not SessionStatus.ONGOING;outcome='U'if not terminal else'D'if s.result.winner is None else'W'if s.result.winner==role else'L';reward=None if not terminal else 0 if s.result.winner is None else 1 if s.result.winner==role else-1
       g=dict(slot=slot,context=task,family=root['family'],ratio=ratio,opponent_ratio=foe,candidate_color=role,outcome=outcome,reward=reward,reason='ACTUAL_RULE_TERMINAL'if terminal else reason,status=s.result.status.value,winner=s.result.winner,moves=moves,seconds=time.perf_counter()-start,record=json.loads(serialize_game_record(s.to_record())));games.append(g);gf.write(json.dumps(g)+'\n');gf.flush()
       if len(games)%32==0:print(json.dumps(dict(games=len(games),context=task,seconds=time.perf_counter()-begin)),flush=True)
       if status not in('COMPLETE','COMPLETE_EXCEPT_INTERRUPTED_SLOT'):break
      if status not in('COMPLETE','COMPLETE_EXCEPT_INTERRUPTED_SLOT'):break
     if status not in('COMPLETE','COMPLETE_EXCEPT_INTERRUPTED_SLOT'):break
    if status not in('COMPLETE','COMPLETE_EXCEPT_INTERRUPTED_SLOT'):break
   if status not in('COMPLETE','COMPLETE_EXCEPT_INTERRUPTED_SLOT'):break
 save('completion.json',dict(status=status,games=len(games),expected_games=p['expected_games'],missing=p['expected_games']-len(games),decisions=decisions,seconds=time.perf_counter()-begin,original_elapsed_seconds=(datetime.datetime.now(datetime.timezone.utc)-oldstart).total_seconds(),unknown_interrupted_slots=[recovery['interrupted_slot']],original_deadline_not_reset=True,WLDU=dict(Counter(g['outcome']for g in games)),scope=p['scope']))
if __name__=='__main__':import sys;{'run':run}[sys.argv[1]]()
