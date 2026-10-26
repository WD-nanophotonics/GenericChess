"""Root-subtree work ordering: frozen research source variants, no product patch."""
from __future__ import annotations
import argparse,ast,hashlib,json,time,types,sys
from pathlib import Path
from datetime import datetime,timezone
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.ai.limits import SearchLimits
from scripts.research_record import record_value,write_record
from scripts.leaper_root_scan_hint_trial import BASE
import generic_chess.ai.alphabeta.player as player_module

ORDER='''    if ply == 0 and ctx.use_ordering and ROOT_WORK_STATE["previous"]:
        ordered_actions = list(ordered_actions)
        original_rank = {a: i for i, a in enumerate(ordered_actions)}
        tt_hint = entry.best_action if entry is not None else None
        ordered_actions.sort(key=lambda a: (
            a != tt_hint, -ROOT_WORK_STATE["previous"].get(a, 0), original_rank[a]))
        ROOT_WORK_STATE["orders"].append({
            "depth": depth, "tt_hint": str(tt_hint),
            "actions": [str(a) for a in ordered_actions],
            "previous_work": {str(a): v for a, v in ROOT_WORK_STATE["previous"].items()}})

'''

def transformed_source(reorder):
    source=BASE.read_bytes().decode('utf-8').replace('\r\n','\n')
    replacements=[
      ('    original_alpha = alpha\n', (ORDER if reorder else '')+'    original_alpha = alpha\n'),
      ('    for move_index, action in enumerate(ordered_actions):\n', '    for move_index, action in enumerate(ordered_actions):\n        if ply == 0:\n            root_work_before = ctx.stats.nodes + ctx.stats.qnodes\n'),
      ('        # A completed root child can already prove a win even if a later\n', '        if ply == 0:\n            ROOT_WORK_STATE["current"][action] = ctx.stats.nodes + ctx.stats.qnodes - root_work_before\n        # A completed root child can already prove a win even if a later\n'),
      ('        prev_score = best.score if best is not None else None\n', '        ROOT_WORK_STATE["current"] = {}\n        ROOT_WORK_STATE["last_started_depth"] = depth\n        prev_score = best.score if best is not None else None\n'),
      ("        _set_result_provenance(stats, 'main_iteration', ctx)\n", '        ROOT_WORK_STATE["previous"] = dict(ROOT_WORK_STATE["current"])\n        ROOT_WORK_STATE["iterations"].append({"depth": depth, "root_work": {str(a): v for a, v in ROOT_WORK_STATE["current"].items()}})\n'+"        _set_result_provenance(stats, 'main_iteration', ctx)\n")]
    for old,new in replacements:
        assert source.count(old)==1,old
        source=source.replace(old,new)
    ast.parse(source);return source

def module(reorder):
    name='generic_chess.ai.alphabeta._root_work_'+str(reorder)
    mod=types.ModuleType(name);mod.__package__='generic_chess.ai.alphabeta';mod.__file__='<frozen-root-work-research>'
    mod.ROOT_WORK_STATE={'previous':{},'current':{},'iterations':[],'orders':[]};sys.modules[name]=mod
    exec(compile(transformed_source(reorder),mod.__file__,'exec'),mod.__dict__);return mod

def observed_state(mod):
    return {'iterations':mod.ROOT_WORK_STATE['iterations'],'orders':mod.ROOT_WORK_STATE['orders'],
            'last_started_depth':mod.ROOT_WORK_STATE.get('last_started_depth'),
            'last_iteration_completed_children_work':{str(a):n for a,n in mod.ROOT_WORK_STATE['current'].items()}}

def run(inputs,plan_file,output):
    assert not output.exists();output.mkdir(parents=True);plan=json.loads(plan_file.read_bytes());rows=json.loads(inputs.read_bytes())['rows']
    mods={'record_only':module(False),'work_order':module(True)};results=[];attempts=0;halt=None;start=datetime.now(timezone.utc).isoformat();tick=time.perf_counter()
    write_record(output/'executed-source.json',{'driver':Path(__file__).read_bytes().decode(),'base_source':BASE.read_bytes().decode(),'record_source':transformed_source(False),'order_source':transformed_source(True),'inputs_sha256':hashlib.sha256(inputs.read_bytes()).hexdigest(),'plan_sha256':hashlib.sha256(plan_file.read_bytes()).hexdigest()})
    for i,row in enumerate(rows):
     for depth in plan['requested_depths']:
      arms=list(plan['arms']);shift=(i+depth)%len(arms);arms=arms[shift:]+arms[:shift];pair=[]
      for arm in arms:
       result={'slot':len(results),'case_id':row['id'],'requested_depth':depth,'arm':arm,'fingerprint':row['fingerprint']}
       if halt or time.perf_counter()-tick>=plan['max_batch_seconds'] or attempts>=plan['max_attempts']:
        result.update(status='NOT_RUN',reason=halt or 'batch_cap');results.append(result);continue
       attempts+=1;t0=time.perf_counter();cpu=time.process_time();utc0=datetime.now(timezone.utc).isoformat();original=player_module.run_root_search
       try:
        c=compile_legacy_ruleset_for_semantic_execution(ruleset_from_dict(row['RuleSet']));s=GameSession.replay(c,deserialize_game_record(json.dumps(row['record'])));before=s.to_record();setup=time.perf_counter()-t0
        player=AlphaBetaPlayer(c,use_disk_cache=False,tuning=SearchTuning(use_pvs=True),use_native_semantic_legality=True,use_native_semantic_availability=True,use_native_semantic_check=True);constructor=time.perf_counter()-t0-setup
        if arm in mods:
         mod=mods[arm];mod.ROOT_WORK_STATE={'previous':{},'current':{},'iterations':[],'orders':[]};player_module.run_root_search=mod.run_root_search
        decision=player.choose_action(s,SearchLimits(max_depth=depth,max_nodes=plan['per_call_max_nodes'],max_time_seconds=plan['per_call_seconds'],quiescence_max_depth=4,quiescence_hard_max_depth=8))
        player_module.run_root_search=original
        result.update(status='RETURNED',decision=record_value(decision),started_at=utc0,ended_at=datetime.now(timezone.utc).isoformat(),outer_seconds=time.perf_counter()-t0,cpu_seconds=time.process_time()-cpu,setup_seconds=setup,constructor_seconds=constructor,root_work=observed_state(mods[arm]) if arm in mods else None)
        write_record(output/f'return-{result["slot"]:03d}.json',result)
        assert s.to_record()==before,'root mutation'
        if decision.action is not None:assert decision.action in s.legal_actions(),'illegal action'
        pv=GameSession.replay(c,before)
        for a in decision.principal_variation:pv.submit(a)
        result.update(root_unchanged=True,pv_legal=True)
       except Exception as e:
        result.update(status='FAILED',error_type=type(e).__name__,error=str(e),started_at=utc0,ended_at=datetime.now(timezone.utc).isoformat(),outer_seconds=time.perf_counter()-t0,cpu_seconds=time.process_time()-cpu);halt='execution_or_record_failure'
       finally:player_module.run_root_search=original
       results.append(result);pair.append(result);write_record(output/'queries.json',results)
      complete=[r for r in pair if r['status']=='RETURNED' and r['decision']['completed_depth']==depth]
      if len({r['decision']['score']for r in complete})>1:halt='complete_value_mismatch';write_record(output/'mismatch.json',complete)
      write_record(output/'progress.json',{'slots':len(results),'attempts':attempts,'seconds':time.perf_counter()-tick,'halt':halt})
    summary={'started_at':start,'ended_at':datetime.now(timezone.utc).isoformat(),'seconds':time.perf_counter()-tick,'slots':len(results),'attempts':attempts,'halt':halt,'statuses':{s:sum(r['status']==s for r in results)for s in sorted({r['status']for r in results})},'games':0,'new_solver':0}
    write_record(output/'summary.json',summary);print(json.dumps(summary))

if __name__=='__main__':
 p=argparse.ArgumentParser(__doc__);p.add_argument('--inputs',type=Path,required=True);p.add_argument('--plan',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();run(a.inputs,a.plan,a.output)
