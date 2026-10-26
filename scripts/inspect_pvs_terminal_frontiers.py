"""Bounded one-step inspection on all supplied PVS played-prefix contexts."""
from collections import Counter
import argparse,gzip,hashlib,json,time
from pathlib import Path
from generic_chess.core.actions import action_to_dict
from generic_chess.session.serialization import deserialize_game_record
from scripts.leaper_terminal_frontier import terminal_frontier
from scripts.leaper_truth_compatibility import bind_context,_child_context,digest
from scripts.qualify_pvs_source_intake import git_bytes,BASE,INPUT,COMMIT
from scripts.research_record import record_value


def inspect(max_contexts=10000,max_seconds=120):
    started=time.perf_counter();manifest=json.loads(git_bytes(BASE+'manifest.json'))
    raw=git_bytes(BASE+'pilot/games.json.gz');member=manifest['members']['pilot/games.json']
    if hashlib.sha256(raw).hexdigest()!=member['gzip_sha256']:raise ValueError('PVS compressed source differs')
    unpacked=gzip.decompress(raw)
    if hashlib.sha256(unpacked).hexdigest()!=member['original_sha256']:raise ValueError('PVS original source differs')
    games=json.loads(unpacked);inputs=git_bytes(INPUT)
    packet=json.loads(gzip.decompress(inputs));rows={r['id']:r for r in packet['rows']}
    if hashlib.sha256(inputs).hexdigest()!='dc471719ad6720f97be01b0a052cdc14728dfdab29dbe4b8bdb8a0785fb9dd93':
        raise ValueError('input differs from qualified source')
    cache={};queries=[];counts=Counter();complete=True;halt=None
    for game in games:
        row=rows[game['case_id']]
        if row['record']!=game['initial_record']:raise ValueError('initial full record differs')
        ctx=bind_context(row['RuleSet'],row['record']);session=ctx.session
        actual=deserialize_game_record(json.dumps(game['final_record'])).actions
        for query in game['queries']:
            if len(queries)>=max_contexts or time.perf_counter()-started>=max_seconds:
                complete=False;halt='CONTEXT_OR_WALL_CAP';break
            if digest(record_value(session.to_record()))!=query['record_before_sha256']:
                raise ValueError('actual query prefix hash differs')
            key=digest(ctx.identity)
            if key not in cache:
                result=terminal_frontier(ctx);cache[key]=result
                counts['new_hypothetical_Core_successors']+=result['new_hypothetical_Core_successors']
                counts['Core_terminal_children']+=result['Core_terminal_children']
            result=cache[key]
            move=actual[query['ply_before']]
            if record_value(move)!=query['decision']['action']:raise ValueError('diagnostic actual action differs')
            canonical=action_to_dict(move)
            selected=next(r for r in result['action_bounds']if r['action']==canonical)
            child=next(r for r in result['children']if r['action']==canonical)
            actor=session.state.position.side_to_move
            actor_root=result['root_WDL_outer_bounds']
            if actor!=result['value_seat']:actor_root=[-actor_root[1],-actor_root[0]]
            queries.append(dict(query_id=query['query_id'],game_id=game['game_id'],case_id=game['case_id'],
                family=game['family'],policy_ON=query['on'],timing_eligible=query['timing_eligible'],context_sha256=key,
                actual_action=canonical,actual_action_bounds=selected,actual_actor_root_WDL_bounds=actor_root,
                terminal_children=result['Core_terminal_children'],ordinary_legal_actions=result['ordinary_legal_actions'],
                actual_child_truth=child['truth']))
            if selected['regret_bounds'][0]>0:counts['selected_action_proved_suboptimal_exposures']+=1
            if selected['regret_bounds'][1]==0:counts['selected_action_proved_WDL_optimal_exposures']+=1
            counts['exact_root_WDL_exposures']+=actor_root[0]==actor_root[1]
            counts['source_queries']+=1
            session.submit(move)
            if digest(record_value(session.state))!=child['state_sha256']:
                raise ValueError('actual Session child differs from hypothetical Core')
            if digest(record_value(session.to_record()))!=query['record_after_sha256']:
                raise ValueError('actual child record hash differs')
            if session.result.status.value=='ongoing':ctx=_child_context(session,ctx)
        if not complete:break
        if record_value(session.to_record())!=game['final_record']:raise ValueError('final source record differs')
    return dict(status='COMPLETE'if complete else'PARTIAL',halt=halt,source_commit=COMMIT,
        source_games_sha256=hashlib.sha256(raw).hexdigest(),input_sha256=hashlib.sha256(inputs).hexdigest(),
        planned_saved_game_queries=sum(len(g['queries'])for g in games),inspected_queries=len(queries),
        distinct_full_contexts=len(cache),contexts=cache,queries=queries,counts=dict(counts),
        seconds=time.perf_counter()-started,max_seconds=max_seconds,max_contexts=max_contexts,
        new_Player_calls=0,new_played_games=0,complete_game_solver_calls=0,
        scope='New depth-one Core successor/terminal checks explicitly counted. Full supplied PVS prefix denominator, exact rules/history and actual Session/Core child equality; no deeper solve, heuristic leaf labels, training start selection, TT quotient or strength claim.')


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True)
    p.add_argument('--max-seconds',type=float,default=120);p.add_argument('--max-contexts',type=int,default=10000)
    a=p.parse_args();result=inspect(a.max_contexts,a.max_seconds);a.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items()if k not in ('contexts','queries')}))
if __name__=='__main__':main()
