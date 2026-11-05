"""Saved full-policy game/PV acceptance; never rerun Player or source capsules."""
from pathlib import Path
from collections import Counter
import json,hashlib
from scripts.research_record import record_value,write_record
from scripts.leaper_pvs_quality_pilot import make_session
from scripts.verify_leaper_pvs_quality_pilot import action
from generic_chess.session.session import GameSession


def verify(base,output):
 b=Path(base);f=json.loads((b/'frozen.json').read_text(encoding='utf-8'))
 assert hashlib.sha256((b/'inputs.json').read_bytes()).hexdigest()==f['input_sha256']
 for name,h in f['sources'].items():assert hashlib.sha256((b/'frozen-source'/name).read_bytes()).hexdigest()==h
 inputs=json.loads((b/'inputs.json').read_text(encoding='utf-8'))['rows'];games=[json.loads(p.read_text(encoding='utf-8')) for p in sorted(b.glob('game-*.json'))]
 seen=set();PVplies=trajectory=0;accepted=[];source_counts=Counter();checking=Counter();work=Counter();times=Counter();literal=Counter();policy=None;timing_failures=[];native=Counter()
 for gi,g in enumerate(games):
  assert g['game']==gi and g['slot']==f['game_slots'][gi]
  c,s=make_session(inputs[g['slot']['family']]);eligible=True
  assert g['initial_record']==record_value(s.to_record())
  for ply,name in enumerate(g['returns']):
   assert name not in seen;seen.add(name)
   r=json.loads((b/name).read_text(encoding='utf-8'));d=r['decision'];actor=s.state.position.side_to_move;on=actor==g['slot']['ONseat']
   assert r['game']==gi and r['ply']==ply and r['actor']==actor and r['on']==on
   assert r['record_before']==record_value(s.to_record())
   tuning=dict(r['actual_tuning']);assert tuning.pop('use_capture_only_qsearch')==on
   if policy is None:policy=tuning
   assert tuning==policy and tuning['use_pvs']
   limits=r['actual_limits'];assert limits['max_nodes']==2000000 and limits['max_depth']==64 and limits['quiescence_max_depth']==4 and limits['quiescence_hard_max_depth']==8
   assert d['nodes']+d['qnodes']<=2000000 and d['runtime_depth_balanced']
   assert d['native_legality_fallbacks']==d['native_legality_operational_failures']==0
   native['legality_calls']+=d['native_legality_calls']
   for group,metrics in r['provider_delta'].items():
    for metric,value in metrics.items():native[group+'_'+metric]+=value
   assert r['provider_delta']['availability'].get('declines',0)==0
   # Calls can exceed successful queries when the checkpoint cancels between
   # attempt and completion. That is not a cache-hit or failure counter.
   assert d['choice_kind']=='ACTION' and d['action'] is not None
   eligible=eligible and r['wall_seconds']<=5.1
   if r['wall_seconds']>5.1:
    timing_failures.append(dict(return_path=name,game=gi,ply=ply,on=on,
      wall_seconds=r['wall_seconds'],CPU_seconds=r['cpu_seconds'],
      internal_choose_seconds=d['elapsed_seconds'],
      outer_minus_internal_seconds=r['wall_seconds']-d['elapsed_seconds'],
      termination_reason=d['termination_reason'],reused_Player=ply>=2,
      requested_max_time_seconds=limits['max_time_seconds']))
   pv=GameSession.replay(c,s.to_record())
   for a in d['principal_variation']:pv.submit(action(a,pv));PVplies+=1
   s.submit(action(d['action'],s));trajectory+=1
   source_counts[(on,d['result_source'])]+=1;checking[str(on)]+=d['checking_move_qactions'];work[str(on)]+=d['nodes']+d['qnodes'];times[str(on)]+=r['wall_seconds']
   if on:assert d['checking_move_qactions']==0
  terminal=s.result.status.value not in ('ongoing','no_contest')
  assert g['actual_terminal']==terminal and g['final_record']==record_value(s.to_record()) and g['literal_result']==record_value(s.result)
  value=None if not terminal or g['censor'] else 0 if s.result.winner is None else 1 if s.result.winner==g['slot']['ONseat'] else -1
  assert value==g['ONvalue'] and g['eligible']==(eligible and terminal and g['censor'] is None)
  literal[str(value)]+=1
  accepted.append(dict(game=gi,family=g['slot']['family'],ONseat=g['slot']['ONseat'],plies=len(g['returns']),eligible=g['eligible'],literal_ONvalue=value,result=record_value(s.result)))
 all_returns={p.name for p in b.glob('return-*.json')};orphans=sorted(all_returns-seen)
 known=[g['literal_ONvalue'] for g in accepted if g['eligible']];unknown=12-len(known);lo=sum(known)-unknown;hi=sum(known)+unknown
 pairs=[]
 for fam in range(6):
  gs=[g for g in accepted if g['family']==fam];qual=len(gs)==2 and all(g['eligible'] for g in gs)
  pairs.append(dict(family=fam,eligible=qual,ONnet=sum(g['literal_ONvalue'] for g in gs) if qual else None))
 success=len(games)==12 and not orphans and all(p['eligible'] for p in pairs) and sum(p['ONnet'] for p in pairs)>=2 and sum(p['ONnet']>0 for p in pairs)>=3
 result=dict(status='PASS_SAVED_GAME_ACCEPTANCE',games=len(games),queries=len(all_returns),accepted_queries=len(seen),orphan_returns=orphans,trajectory_Core_plies=trajectory,PV_Core_plies=PVplies,literal_outcomes=dict(literal),qualified_games=len(known),unknown_slots=unknown,ON_value_net_bounds=[lo,hi],ON_points_bounds=[(12+lo)/2,(12+hi)/2],pairs=pairs,success_gate=success,checking_move_qactions=dict(checking),budget_events=dict(work),service_wall_seconds=dict(times),result_sources=[dict(on=key[0],source=key[1],calls=v) for key,v in source_counts.items()],game_details=accepted,native_metrics=dict(native),native_limit='attempts/query/import/reusecountersareseparateandnotdisjoint;checkpoint-abortedattemptsnotproviderfaults',timing_failures=timing_failures,timing_interpretation='OuterwallendsbeforeJSONserialization;Playerinternalclockendsafterrun_root_searchbeforedecisionconstruction. Near-zeroouter-minus-internalrulesoutrecordwritingasobservedoverrunregion,notlocalizeNative/GC/CPUpreemption. WarmTTcontentsnotrecorded;cannotreconstructpastlivecachefromPVcounts.',newPlayer=0,newSolver=0,limits='finiteexposed6families;Core/PVvalidationnotindependentWDL;equalpercalllimitnotidenticalwholegamecost;remainingUNKNOWNnotDRAW;nominalQ4notuniformhorizon;no default/holdout/strengthclaim')
 write_record(output,result);return result
if __name__=='__main__':
 import sys;v=verify(sys.argv[1],sys.argv[2]);print(json.dumps({k:x for k,x in v.items() if k!='game_details'}))
