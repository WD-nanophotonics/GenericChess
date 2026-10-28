"""Consume frozen endpoint inputs: bounded complete two-ply Core preflight.

First-ply terminal rejects whole panel. Second-ply terminal counts are descriptive
and NEVER used to replace/filter roots. UNKNOWN/incomplete stops later phases.
No Player/solver query and no outcome-selected replacement.
"""
import hashlib,json,time
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution
from generic_chess.rules.schema import ruleset_from_dict,compute_fingerprint
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.session.session import GameSession
from generic_chess.core.attacks import is_in_check
from generic_chess.core.actions import action_to_dict
from scripts.leaper_opening_capacity import opening_escape_capacity
from scripts.leaper_ordinary_geometry import ordinary_leap_geometry
from scripts.research_record import record_value,write_record
from tools.local_agent.common import read_json

class StopPreflight(Exception):pass

def run(input_path,plan_path,out):
    out=Path(out)
    if out.exists():raise FileExistsError(out)
    out.mkdir(parents=True);raw=Path(input_path).read_bytes();data=json.loads(raw);plan=json.loads(Path(plan_path).read_text());assert hashlib.sha256(raw).hexdigest()==plan['input_sha256'];rows=data['rows'];assert len(rows)==16 and not data['rejected'];tick=time.perf_counter();cpu=time.process_time();transitions=0;results=[];current=None;reason=None
    def checkpoint(root_tick):
        flags=read_json(Path('.local_agent/rollout.json'))
        if any(flags.get(k) for k in ('user_paused','stopped','research_stopped','stop_requested')):raise StopPreflight('scoped_stop')
        if transitions>=plan['preflight']['Core_transitions']:raise StopPreflight('Core_transition_cap')
        if time.perf_counter()-tick>plan['preflight']['whole_seconds']-2:raise StopPreflight('batch_dispatch_reserve')
        if time.perf_counter()-root_tick>plan['preflight']['root_seconds']-2:raise StopPreflight('root_dispatch_reserve')
        if datetime.now(timezone.utc)>=datetime.fromisoformat(plan['whole_deadline_utc']):raise StopPreflight('whole_deadline')
    try:
        for row in rows:
            rt=time.perf_counter();checkpoint(rt);current={'id':row['id'],'status':'STARTED','first_actions':[]};results.append(current);write_record(out/'progress.json',{'results':results,'transitions':transitions})
            rule=ruleset_from_dict(row['RuleSet']);assert compute_fingerprint(rule)==row['fingerprint'];c=compile_legacy_ruleset_for_semantic_execution(rule);session=GameSession.replay(c,deserialize_game_record(json.dumps(row['record'])));initial=session.to_record()
            if session.state.terminal_status.is_terminal:raise StopPreflight('initial_terminal')
            if any(is_in_check(session.state.position,owner,c) for owner in (0,1)):raise StopPreflight('initial_check')
            if getattr(c,'declarations',()):raise StopPreflight('declarations_outside_frozen_domain')
            current['declarations']='EXCLUDED:compiled declarations empty;ordinary strict IR/support/no effects contract checked';geometry=ordinary_leap_geometry(c);current['ordinary_contract']=geometry is not None
            if geometry is None:raise StopPreflight('ordinary_IR_UNKNOWN')
            capacity=opening_escape_capacity(session.state,c);current['capacity']=capacity
            if capacity['status']!='SUFFICIENT_ONE_PLY_REPLY':raise StopPreflight('capacity_UNKNOWN')
            actions=session.legal_actions();current['root_actions']=len(actions)
            if not actions:raise StopPreflight('no_root_actions')
            for action in actions:
                checkpoint(rt);child=GameSession.replay(c,initial);child.submit(action);transitions+=1
                branch={'action':action_to_dict(action),'child_record':record_value(child.to_record()),'first_terminal':record_value(child.state.terminal_status),'reply_counts':{},'reply_actions':[],'status':'STARTED'};current['first_actions'].append(branch)
                if child.state.terminal_status.is_terminal:raise StopPreflight('first_ply_terminal')
                replies=child.legal_actions();counts=Counter();child_record=child.to_record()
                for reply in replies:
                    checkpoint(rt);leaf=GameSession.replay(c,child_record);leaf.submit(reply);transitions+=1;t=leaf.state.terminal_status
                    label=('CONTINUE' if not t.is_terminal else 'DRAW' if t.winner is None else 'ROOT_WIN' if t.winner==0 else 'REPLY_WIN');counts[label]+=1;branch['reply_actions'].append({'action':action_to_dict(reply),'terminal':record_value(t)})
                branch.update(reply_counts=dict(counts),reply_count=len(replies),status='COMPLETE');assert sum(counts.values())==len(replies)
                write_record(out/(row['id']+'.json'),current)
            assert session.to_record()==initial;current.update(status='COMPLETE',seconds=time.perf_counter()-rt);write_record(out/(row['id']+'.json'),current);print(row['id'],len(actions),sum(x['reply_count'] for x in current['first_actions']),round(current['seconds'],3),flush=True)
    except (StopPreflight,Exception) as exc:
        reason=type(exc).__name__+':'+str(exc)
        if current is not None:current.update(status='STOPPED_UNKNOWN',reason=reason);write_record(out/(current['id']+'.json'),current)
    summary={'status':'PASS_TWO_PLY_PREFLIGHT_ONLY' if reason is None and len(results)==16 and all(r['status']=='COMPLETE' for r in results) else 'STOP_NO_Player','reason':reason,'transitions':transitions,'roots':[{'id':r['id'],'status':r['status'],'first_actions_completed':sum(b['status']=='COMPLETE' for b in r['first_actions'])} for r in results],'NOT_RUN':[r['id'] for r in rows[len(results):]],'seconds':time.perf_counter()-tick,'cpu_seconds':time.process_time()-cpu,'Player_calls':0,'games':0,'claim':'finite2ply legal/terminal distribution only;no WDL/difficulty/equalservice or strength;no replacement'}
    write_record(out/'summary.json',summary);print(json.dumps(summary));return summary
