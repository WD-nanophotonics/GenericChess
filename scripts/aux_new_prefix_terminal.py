"""One frozen offline two-ply terminal envelope over new published histories.
No Player/PN, generated games, training, or old experiment refill.
"""
from pathlib import Path
from copy import copy
import hashlib,json,time,traceback
from unittest.mock import patch
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.session.result import SessionStatus
from scripts.research_record import record_value,write_record
from scripts.leaper_microgames import role_stop_requested

BASE=Path('docs/research/data/aux_new_prefix_terminal_20261031')

class Limit(Exception):pass

def terminal_interval(session,actor):
    result=session.result
    if result.status in (SessionStatus.ONGOING,SessionStatus.NO_CONTEST):
        return [-1,1]
    if result.declaration_outcome in ('NO_CONTEST','RESTART'):
        return [-1,1]
    value=0 if result.winner is None else 1 if result.winner==actor else -1
    return [value,value]

def min_fold(intervals):
    return [min(x[0]for x in intervals),min(x[1]for x in intervals)] if intervals else [-1,1]

def max_fold(intervals):
    return [max(x[0]for x in intervals),max(x[1]for x in intervals)] if intervals else [-1,1]

def selected_regret(intervals,selected):
    root=max_fold(intervals)
    return [max(0,root[0]-selected[1]),max(0,root[1]-selected[0])]

def decode(raw,session):
    matches=[a for a in session.legal_actions()if record_value(a)==raw]
    if len(matches)!=1:raise ValueError('literal action absent/ambiguous')
    return matches[0]

def run():
    plan=json.loads((BASE/'plan.json').read_bytes())
    with(BASE/'execution-start.json').open('x',encoding='utf-8')as f:
        json.dump({'start_unix':time.time(),'plan_sha256':hashlib.sha256((BASE/'plan.json').read_bytes()).hexdigest(),'producer_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()},f)
    start=time.perf_counter();paid=0;rows=[];reason='complete';compiled={}
    real=GameSession.submit
    def guard():
        if time.perf_counter()-start>=plan['caps']['execution_seconds']:raise Limit('TIME_CAP')
        if paid>=plan['caps']['submit_attempts_all_including_prefix_PV']:raise Limit('SUBMIT_CAP')
        if paid%128==0 and role_stop_requested():raise Limit('USER_STOP')
    def submit(session,a):
        nonlocal paid
        guard();paid+=1
        return real(session,a)
    def save():
        write_record(BASE/'observed.json',{'rows':rows,'reason':reason,'planned_contexts':len(plan['contexts']),'not_started':plan['contexts'][len(rows):],'submit_attempts':paid,'seconds':time.perf_counter()-start,'Player_calls':0,'PN_calls':0,'new_games':0,'training_updates':0,'internal_trial_transition_count':'UNKNOWN; direct Session.submit attempts only'})
    try:
        with patch.object(GameSession,'submit',submit):
            for context in plan['contexts']:
                guard()
                out={'source_path':context['source_path'],'root_index':context['root_index'],'prefix':context['prefix'],'family':context['family'],'root_actions':[],'status':'RUNNING'}
                rows.append(out)
                root=plan['roots'][str(context['root_index'])]
                if context['root_index']not in compiled:
                    compiled[context['root_index']]=compile_legacy_ruleset_for_semantic_execution(ruleset_from_dict(root['RuleSet']))
                c=compiled[context['root_index']]
                assert c.ruleset_fingerprint==root['fingerprint'] and not c.declarations
                session=GameSession.replay(c,deserialize_game_record(json.dumps(context['record'])))
                assert session.result.status is SessionStatus.ONGOING
                actor=session.state.position.side_to_move
                actions=session.legal_actions();before=(session.state,session.to_record())
                d=context['decision'];selected=decode(d['action'],session)
                assert d['choice_kind']=='ACTION' and d['principal_variation'][0]==d['action']
                pv=copy(session)
                for raw in d['principal_variation']:pv.submit(decode(raw,pv))
                out.update(actor=actor,root_legal_count=len(actions),selected_action=record_value(selected),pv_plies=len(d['principal_variation']),pv_terminal=record_value(pv.result),selected_bounds=[-1,1],root_bounds=[-1,1],selected_regret_bounds=[0,2],record=context['record'])
                # Every root choice and every legal defense; no depth3 expansion.
                for action in actions:
                    guard();child=copy(session);child.submit(action)
                    entry={'action':record_value(action),'after_action_result':record_value(child.result),'bounds':terminal_interval(child,actor),'reply_count':0,'reply_terminal_counts':{},'terminal_witnesses':[],'complete':False}
                    out['root_actions'].append(entry)
                    if child.result.status is SessionStatus.ONGOING:
                        replies=child.legal_actions();entry['legal_reply_count']=len(replies)
                        values=[]
                        for reply in replies:
                            guard();grand=copy(child);grand.submit(reply)
                            value=terminal_interval(grand,actor);values.append(value);entry['reply_count']+=1
                            key=grand.result.status.value
                            entry['reply_terminal_counts'][key]=entry['reply_terminal_counts'].get(key,0)+1
                            if grand.result.status is not SessionStatus.ONGOING:
                                entry['terminal_witnesses'].append({'reply':record_value(reply),'result':record_value(grand.result),'value_bounds':value})
                        entry['bounds']=min_fold(values)
                    entry['complete']=True
                    assert (session.state,session.to_record())==before
                assert len(out['root_actions'])==len(actions)
                chosen=next(x for x in out['root_actions']if x['action']==record_value(selected))
                out.update(status='COMPLETE',selected_bounds=chosen['bounds'],root_bounds=max_fold([x['bounds']for x in out['root_actions']]),selected_regret_bounds=selected_regret([x['bounds']for x in out['root_actions']],chosen['bounds']))
                save()
                print(context['source_path'],out['root_bounds'],out['selected_bounds'],out['selected_regret_bounds'],'paid',paid,flush=True)
    except Limit as e:
        reason=str(e)
        if rows and rows[-1]['status']=='RUNNING':rows[-1]['status']='PARTIAL'
    except BaseException:
        reason='FAILED';save();raise
    save()
    print('END',reason,paid,time.perf_counter()-start,flush=True)

if __name__=='__main__':run()
