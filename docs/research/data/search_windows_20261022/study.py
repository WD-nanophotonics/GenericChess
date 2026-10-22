"""Frozen staged-vs-default utility experiment; existing Core and runner only."""
import json,random,time,traceback
from pathlib import Path
from dataclasses import replace
from scripts.research_record import record_value,write_record
from generic_chess.generation.config import GeneratorConfig
from generic_chess.generation.generator import generate_game
from generic_chess.rules.schema import ruleset_to_dict
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution
from generic_chess.session.session import GameSession
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.ai.benchmark.runner import play_game,RunConfig,_timing_invalid
from generic_chess.ai.benchmark.profiles import profile_by_name
ROOT=Path('.local_agent/pvs-20261022/staged-utility')
protocol=json.loads((ROOT/'registration.json').read_text())
assert not (ROOT/'results.json').exists()
tick=time.perf_counter();out={'protocol':protocol,'worlds':[],'failures':[],'slots':[{'slot':2*i+o,'seed':c['seed'],'owner':o,'status':'not_started','utility_interval':[-1,1]} for i,c in enumerate(protocol['configs']) for o in (0,1)],'new_queries':0,'analytical_BB_games_executed':0};contexts={}
write_record(ROOT/'results.json',out)
for cfg in protocol['configs']:
 if time.perf_counter()-tick>=900:break
 stage='generation';start=time.perf_counter()
 try:
  g=generate_game(GeneratorConfig(**cfg));stage='compile_and_capture';c=compile_legacy_ruleset_for_semantic_execution(g.ruleset);s=GameSession(c)
  out['worlds'].append({'seed':cfg['seed'],'config':cfg,'rule':ruleset_to_dict(g.ruleset),'generation_report':record_value(g.generation_report),'initial_record':record_value(s.to_record()),'initial_state':record_value(s.state),'setup_seconds':time.perf_counter()-start})
  write_record(ROOT/'inputs.json',{'protocol':protocol,'worlds':out['worlds'],'failures':out['failures']});contexts[cfg['seed']]=c
 except Exception as exc:
  out['failures'].append({'seed':cfg['seed'],'stage':stage,'type':type(exc).__name__,'message':str(exc),'traceback':traceback.format_exc()})
  for slot in out['slots']:
   if slot['seed']==cfg['seed']:slot.update(status='setup_failed',failure=str(exc))
 write_record(ROOT/'results.json',out);print('SETUP',cfg['seed'],cfg['seed'] in contexts,round(time.perf_counter()-start,3),flush=True)
class Censored(Exception):pass
class Recorder:
 def __init__(self,player,label,row,path):self.inner=player;self.label=label;self.row=row;self.path=path;self.latest=None
 def choose_action(self,session,limits):
  self.latest=session;self.row['current_record']=record_value(session.to_record());write_record(self.path,self.row)
  if time.perf_counter()-tick>=900:raise Censored('predeclared whole-experiment cap, no next query')
  actual=replace(limits,max_depth=4,quiescence_max_depth=0,quiescence_hard_max_depth=0)
  root_ply=session.state.ply_count;actor=session.state.position.side_to_move;start=time.perf_counter();d=self.inner.choose_action(session,actual);elapsed=time.perf_counter()-start
  q={'root_ply':root_ply,'actor':actor,'policy':self.label,'actual_limits':record_value(actual),'decision':record_value(d),'seconds':elapsed,'applied':False};self.row['queries'].append(q);out['new_queries']+=1;write_record(self.path,self.row)
  return d
blocks=list(protocol['configs']);rng=random.Random(protocol['shuffle_seed']);rng.shuffle(blocks);order=[]
for cfg in blocks:
 owners=[0,1];rng.shuffle(owners)
 for owner in owners:order.append(next(s['slot'] for s in out['slots'] if s['seed']==cfg['seed'] and s['owner']==owner))
out['execution_order']=order;write_record(ROOT/'results.json',out)
config=RunConfig(control=profile_by_name('baseline'),candidate=profile_by_name('staged_picker'),suite=(),seconds=1,nodes=4096,max_plies=96)
for index in order:
 if time.perf_counter()-tick>=900:break
 slot=out['slots'][index];seed=slot['seed']
 if seed not in contexts:continue
 c=contexts[seed];initial=GameSession(c);path=ROOT/f'game-{index:03d}.json';row={**slot,'status':'running','initial_record':record_value(initial.to_record()),'queries':[],'failure':None};write_record(path,row);slot.update(status='running',receipt=path.name);write_record(ROOT/'results.json',out)
 candidate=Recorder(AlphaBetaPlayer(c,use_disk_cache=False,tuning=SearchTuning(use_staged_move_picker=True)),'staged',row,path)
 control=Recorder(AlphaBetaPlayer(c,use_disk_cache=False),'baseline',row,path);start=time.perf_counter();outcome=None;events=[];stop=None
 try:
  outcome,events=play_game(c,(),str(seed),str(index),slot['owner'],candidate,control,config)
 except Censored as exc:stop='batch_cap';row['censor']=str(exc)
 except Exception as exc:stop='error';row['failure']={'type':type(exc).__name__,'message':str(exc),'traceback':traceback.format_exc()}
 session=candidate.latest or control.latest or initial;record=session.to_record();fallback=any(q['decision']['result_source'] in {'fallback','legal_fallback','root_scan_fallback'} or q['decision']['termination_reason']=='fallback' for q in row['queries']);timing=any(_timing_invalid(q['seconds'],1) for q in row['queries']);operational=any(q['decision']['native_legality_operational_failures'] for q in row['queries']);fallback=fallback or bool(outcome and (outcome.candidate_fallback or outcome.control_fallback));timing=timing or bool(outcome and (outcome.candidate_timing_invalid or outcome.control_timing_invalid));eligible=not(row['failure'] or fallback or timing or operational or bool(outcome and outcome.result=='failed'))
 raw=outcome.result if outcome else 'unresolved';v={'candidate_win':1,'candidate_loss':-1,'rule_draw':0}.get(raw);utility=[v,v] if eligible and v is not None else [-1,1]
 for q in row['queries']:
  k=q['root_ply']
  if k<len(record.actions):q['applied']=record_value(record.actions[k])==q['decision']['action']
 row.update(status='finished',final_record=record_value(record),final_state=record_value(session.state),raw_terminal=record_value(session.state.terminal_status),raw_result=raw,runner_outcome=record_value(outcome),move_events=record_value(events),eligible=eligible,fallback=fallback,timing_invalid=timing,operational_failure=bool(operational),utility_interval=utility,stop_reason=stop or ('rule_terminal' if session.state.terminal_status.is_terminal else 'game_ply_cap'),wall_seconds=time.perf_counter()-start);row.pop('current_record',None);write_record(path,row)
 slot.update(status='finished',utility_interval=utility,raw_result=raw,eligible=eligible,stop_reason=row['stop_reason'],queries=len(row['queries']),plies=len(record.actions),wall_seconds=row['wall_seconds']);out.update(wall_seconds=time.perf_counter()-tick);write_record(ROOT/'results.json',out);print('GAME',index,seed,slot['owner'],raw,utility,len(record.actions),round(row['wall_seconds'],3),round(out['wall_seconds'],3),flush=True)
out.update(wall_seconds=time.perf_counter()-tick,unexecuted_games=sum(s['status']!='finished' for s in out['slots']));write_record(ROOT/'results.json',out);print('DONE',out['new_queries'],out['unexecuted_games'],round(out['wall_seconds'],3),flush=True)
