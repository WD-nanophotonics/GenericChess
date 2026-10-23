"""One-ply exact bounds/cardinality on existing unresolved complete histories.

Core terminal children and singleton legal-action sets are claim-sufficient
facts. An ongoing child is [-1,1], never DRAW. No additional ply is searched,
no old proof cap is refilled, and no forward game or training start is made.
"""
from __future__ import annotations
from collections import Counter
from copy import deepcopy
from pathlib import Path
import argparse
import json
import time

from generic_chess.core.actions import action_to_dict,action_from_dict
from generic_chess.core.transition import legal_successors
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution as compile_rule
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from scripts.leaper_design import state_sha
from scripts.leaper_explorer_truth import load,save,digest,materialize
from scripts.leaper_explorer_supplement import apply_supplement
from scripts.leaper_microgames import role_stop_requested


def derive(children):
    if not children:raise ValueError('ongoing root must have legal actions')
    bounds=[c['wdl_bounds']for c in children]
    low=max(b[0]for b in bounds);high=max(b[1]for b in bounds)
    fork=False if len(children)==1 or all(b==bounds[0]and b[0]==b[1]for b in bounds)else (
         True if max(b[0]for b in bounds)>min(b[1]for b in bounds)else None)
    decisive=any(c['terminal_winner']is not None for c in children)
    all_draw=all(c['terminal']!='ongoing'and c['terminal']!='no_contest'and c['terminal_winner']is None for c in children)
    return dict(wdl_bounds=[low,high],wdl_fork=fork,
                cooperative_decisive=True if decisive else False if all_draw else None,
                universal_draw=False if decisive else True if all_draw else None)


def inspect_state(state,c):
    children=[];mover=state.position.side_to_move
    for ac,ch in legal_successors(state,c):
        t=ch.terminal_status
        value=None if not t.is_terminal or t.status.value=='no_contest'else (
              0 if t.winner is None else 1 if t.winner==mover else -1)
        children.append(dict(action=action_to_dict(ac),child_id=state_sha(ch),
                    terminal=t.status.value,terminal_winner=t.winner,
                    wdl_bounds=[-1,1]if value is None else[value,value]))
    return children,derive(children)


def apply_layer(truth,layer):
    if layer['input_digest']!=digest(truth):raise ValueError('local bound source mismatch')
    result=deepcopy(truth);by_id={r['id']:r for r in result['roots']};seen=set()
    for q in layer['rows']:
        if q['id']in seen:raise ValueError('duplicate local root')
        seen.add(q['id']);r=by_id[q['id']]
        if r['fingerprint']!=q['fingerprint']:raise ValueError('local rule mismatch')
        expected=derive(q['children'])
        if expected!=q['derived']:raise ValueError('local bound derivation mismatch')
        lo=max(r['wdl_bounds'][0],expected['wdl_bounds'][0]);hi=min(r['wdl_bounds'][1],expected['wdl_bounds'][1])
        if lo>hi:raise ValueError('local bounds contradict source')
        r['wdl_bounds']=[lo,hi]
        r['action_bounds']=[dict(action=k['action'],wdl_bounds=k['wdl_bounds'])for k in q['children']]
        for prop in ('wdl_fork','cooperative_decisive','universal_draw'):
            if expected[prop]is None:continue
            if r[prop]is not None and r[prop]!=expected[prop]:raise ValueError('local property contradiction')
            r[prop]=expected[prop]
        r['original_truth_basis']=r.get('truth_basis');r['truth_basis']='actual_Core_oneply_terminal_or_cardinality'
    result['local_truth_digest']=digest(layer)
    return result


def run(folder,supplement,output):
    p=Path(folder);out=Path(output);out.mkdir(parents=True,exist_ok=False)
    raw=load(p/'truth.json.gz');base=materialize(raw,load(p/'cooperative.json'),load(p/'observed-suffixes.json.gz'))
    truth=apply_supplement(base,load(supplement));by_id={r['id']:r for r in truth['roots']}
    target={r['id']for r in truth['roots']if r['wdl_bounds'][0]!=r['wdl_bounds'][1]or r['wdl_fork']is None}
    spec=dict(question='Can literal one-ply terminal choices/single legal actions close missing WDL/fork truth before any deeper proof?',
        input_digest=digest(truth),selected=sorted(target),caps=dict(seconds=180,depth=1),
        selection='All remaining unresolved saved histories, no new rule/layout or output-based exclusion.',
        stop='One source-record pass and one complete legal successor set per target, no second ply, UNKNOWN on incomplete read, no cap refill.')
    save(out/'spec.json',spec)
    started=time.perf_counter();seen=set();rows=[];counts=Counter();status='COMPLETE'
    compiled={fp:compile_rule(ruleset_from_dict(rule))for fp,rule in truth['rules'].items()}
    try:
        for rid,record in truth['records'].items():
            c=compiled[record['ruleset_fingerprint']]
            s=GameSession.replay(c,deserialize_game_record(json.dumps(record|dict(actions=[]))))
            for action in record['actions']:
                if time.perf_counter()-started>=180:raise TimeoutError('TIME_CAP_UNKNOWN')
                if role_stop_requested():raise TimeoutError('USER_STOP')
                hid=state_sha(s.state)
                if hid in target and hid not in seen:
                    r=by_id[hid];children,derived=inspect_state(s.state,c)
                    counts['queried_histories']+=1;counts['core_edges']+=len(children)
                    counts['singleton_legal_histories']+=len(children)==1
                    counts['immediate_winning_choices']+=sum(k['terminal_winner']==s.state.position.side_to_move for k in children)
                    if (derived['wdl_bounds']!=r['wdl_bounds']or any(
                        derived[prop]is not None and r[prop]is None for prop in ('wdl_fork','cooperative_decisive','universal_draw'))):
                        rows.append(dict(id=hid,fingerprint=r['fingerprint'],children=children,derived=derived))
                    seen.add(hid)
                s.submit(action_from_dict(action))
    except TimeoutError as error:status=str(error)
    layer=dict(format='leaper-local-truth-v1',input_digest=digest(truth),spec=spec,
          rows=rows,counts=dict(counts),status=status,unqueried=sorted(target-seen),seconds=time.perf_counter()-started,
          scope='Actual Core local bounds only. Singleton forkFALSE does not solve WDL. Immediate WIN is a real terminal proof. Unknown ongoing children retain[-1,1]. No deep solver, game, policy prediction or training.')
    save(out/'layer.json.gz',layer)
    updated=apply_layer(truth,layer)
    summary=dict(status=status,counts=dict(counts),changed_histories=len(rows),
          wdl_bounds=dict(Counter(str(r['wdl_bounds'])for r in updated['roots'])),
          properties={prop:dict(Counter(str(r[prop])for r in updated['roots']))for prop in ('wdl_fork','cooperative_decisive','universal_draw')},
          seconds=layer['seconds'],unqueried=len(layer['unqueried']),updated_digest=digest(updated))
    save(out/'summary.json',summary)
    return summary


def verify_layer(truth,layer):
    """Recheck changed roots by public action enumeration/application."""
    from generic_chess.core.transition import apply_action
    from scripts.leaper_cooperative_certificate import root_session
    if digest(truth)!=layer['input_digest']:raise ValueError('local source mismatch')
    by_id={r['id']:r for r in truth['roots']};compiled={};stats=Counter()
    for q in layer['rows']:
        r=by_id[q['id']];fp=r['fingerprint']
        if fp not in compiled:compiled[fp]=compile_rule(ruleset_from_dict(truth['rules'][fp]))
        _,s=root_session(truth,q['id'],compiled[fp]);mover=s.state.position.side_to_move
        actual=[]
        for ac in s.legal_actions():
            ch=apply_action(s.state,ac,compiled[fp]);t=ch.terminal_status
            v=None if not t.is_terminal or t.status.value=='no_contest'else(0 if t.winner is None else 1 if t.winner==mover else -1)
            actual.append(dict(action=action_to_dict(ac),child_id=state_sha(ch),terminal=t.status.value,
                               terminal_winner=t.winner,wdl_bounds=[-1,1]if v is None else[v,v]))
        if digest(actual)!=digest(q['children'])or derive(actual)!=q['derived']:
            raise ValueError('local Core certificate mismatch')
        stats['roots']+=1;stats['legal_edges']+=len(actual)
        stats['exact_terminal_action_labels']+=sum(k['wdl_bounds'][0]==k['wdl_bounds'][1]for k in actual)
    # This also rejects duplicated claims and contradictory source labels.
    apply_layer(truth,layer)
    return dict(verified=True,counts=dict(stats),layer_digest=digest(layer),
                scope='Changed roots only, by independent public legal_actions/apply_action enumeration through the same Core. Reported full-pass cost is a producer receipt, not independently replayed timing.')


if __name__=='__main__':
    cli=argparse.ArgumentParser();cli.add_argument('--folder',default='docs/research/data/leaper_explorer_truth_20261023');cli.add_argument('--supplement',required=True);cli.add_argument('--output',required=True)
    args=cli.parse_args();print(json.dumps(run(args.folder,args.supplement,args.output)))
