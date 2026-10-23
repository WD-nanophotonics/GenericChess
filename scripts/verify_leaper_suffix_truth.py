"""Independent action/transition enumeration of COMPLETE suffix results only.

Uses public legal_actions/apply_action instead of the producer successor
stream. No partial/unstarted root is finished or relabelled by verification.
"""
import argparse
from collections import Counter
import time

from generic_chess.core.movegen import legal_actions
from generic_chess.core.transition import apply_action
from generic_chess.core.actions import action_from_dict
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution as compile_rule
from scripts.leaper_cooperative_certificate import root_session
from scripts.leaper_explorer_truth import load, save, digest
from scripts.leaper_microgames import role_stop_requested


def verify(truth,result,*,seconds=300):
    if digest(truth)!=result['spec']['source_truth_digest']:
        raise ValueError('source truth mismatch')
    start=time.perf_counter();counts=Counter();last_stop=0.;rows=[]
    def walk(state,c):
        nonlocal last_stop
        now=time.perf_counter()
        if now-start>=seconds:raise RuntimeError('VERIFICATION_CAP_UNKNOWN')
        if now-last_stop>=.2:
            last_stop=now
            if role_stop_requested():raise RuntimeError('USER_STOP')
        counts['nodes']+=1
        if state.terminal_status.is_terminal:
            counts['terminals']+=1;t=state.terminal_status
            v=0 if t.winner is None else 1 if t.winner==0 else -1
            return {v},v
        found=set();values=[]
        for action in legal_actions(state,c):
            counts['edges']+=1
            future,value=walk(apply_action(state,action,c),c)
            found.update(future);values.append(value)
        if not values:raise ValueError('ongoing state without legal action')
        return found,(max if state.position.side_to_move==0 else min)(values)
    for q in result['rows']:
        if q['status']!='COMPLETE':continue
        c=compile_rule(ruleset_from_dict(truth['rules'][q['fingerprint']]))
        r,s=root_session(truth,q['id'],c);before=counts.copy()
        future,value=walk(s.state,c)
        if sorted(future)!=q['terminal_outcomes_player0'] or value!=q['wdl_player0']:
            raise ValueError('outcome/minimax mismatch')
        if (future=={0})!=q['universal_draw'] or bool(future-{0})!=q['cooperative_decisive']:
            raise ValueError('property mismatch')
        if counts['nodes']-before['nodes']!=q['nodes'] or counts['edges']-before['edges']!=q['edges']:
            raise ValueError('work census mismatch')
        if q['witness'] is not None:
            _,check=root_session(truth,q['id'],c)
            for action in q['witness']:check.submit(action_from_dict(action))
            if check.result.winner is None:raise ValueError('invalid cooperative witness')
        rows.append(dict(id=q['id'],verified=True,terminal_outcomes_player0=sorted(future),
                         wdl_player0=value,nodes=q['nodes'],edges=q['edges']))
    return dict(verified=True,counts=dict(counts),rows=rows,seconds=time.perf_counter()-start,
                result_digest=digest(result),scope='Only COMPLETE producer roots; partial and unstarted roots remain untouched. Shared Core authority, independent enumeration path; not an independently implemented rules engine.')


if __name__=='__main__':
    cli=argparse.ArgumentParser();cli.add_argument('--truth',required=True);cli.add_argument('--result',required=True);cli.add_argument('--output',required=True)
    args=cli.parse_args();r=verify(load(args.truth),load(args.result));save(args.output,r)
    print(__import__('json').dumps(r))
