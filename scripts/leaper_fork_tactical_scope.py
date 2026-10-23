"""Retrospective natural fork mechanisms; no new search/controller execution."""
from collections import Counter,defaultdict
import json,time
from fractions import Fraction

from generic_chess.core.actions import action_from_dict,action_to_dict
from generic_chess.core.transition import legal_successors
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution as compile_rule
from generic_chess.session.session import GameSession
from scripts.leaper_explorer_truth import digest
from scripts.leaper_design import state_sha
from scripts.leaper_microgames import role_stop_requested
from pathlib import Path
from scripts.leaper_explorer_truth import load


def source_truth():
    from scripts.leaper_saved_child_bounds import current_truth,propagate
    from scripts.leaper_saved_suffix_transfer import apply as suffix
    from scripts.leaper_observed_path_proofs import apply as observed
    p=Path('docs/research/data/leaper_explorer_saved_paths_20261023')
    t=current_truth('docs/research/data/leaper_explorer_truth_20261023','docs/research/data/leaper_explorer_followup_20261023')
    t,_=propagate(t,load(p/'edges.json.gz'));t=suffix(t,load(p/'shortened-proofs.json.gz'))
    return observed(t,load(p/'observed-proofs.json.gz'))


def mechanism(bounds,immediate):
    if bounds[0]!=bounds[1]:return 'nonexact_root'
    if bounds==[1,1]:return 'WIN_immediate_mate_available'if immediate else'WIN_no_immediate_mate'
    if bounds==[0,0]:
        if immediate:raise ValueError('DRAW fork cannot have immediate mate')
        return 'DRAW_avoid_LOSS'
    raise ValueError('exact LOSS cannot have distinct exact minimax action values')


def uniform_floor_bounds(root,immediate):
    """Exact conditional one-decision law of the existing FLOOR fallback.

    It selects an immediate winning terminal if present, otherwise a uniform
    legal action. Values are certified minimax action values/bounds, not played
    terminal utility, a new game run or search/learning performance.
    """
    lo,hi=root['wdl_bounds'];actions=root['action_bounds']
    if lo!=hi or not actions:raise ValueError('exact root and nonempty legal choices required')
    if immediate:
        if lo!=1:raise ValueError('terminal win contradicts root')
        return dict(action_WDL_mean=['1','1'],guarantee_gap_mean=['0','0'],lowering_probability=['0','0'])
    n=len(actions);bounds=[Fraction(sum(a['wdl_bounds'][i]for a in actions),n)for i in(0,1)]
    if bounds[1]>lo:raise ValueError('action exceeds exact root value')
    loss=[Fraction(sum(a['wdl_bounds'][1]<lo for a in actions),n),Fraction(sum(a['wdl_bounds'][0]<lo for a in actions),n)]
    return dict(action_WDL_mean=list(map(str,bounds)),guarantee_gap_mean=[str(lo-bounds[1]),str(lo-bounds[0])],lowering_probability=list(map(str,loss)))


def add_floor_summary(out,truth):
    from copy import deepcopy
    out=deepcopy(out)
    if digest(truth)!=out['truth_digest']:raise ValueError('wrong source truth for FLOOR bounds')
    roots={r['id']:r for r in truth['roots']}
    for row in out['histories']:
        row['conditional_FLOOR']=uniform_floor_bounds(roots[row['id']],bool(row['immediate_mate_actions']))
    summary={}
    for category in out['summary']:
        rows=[r for r in out['histories']if r['category']==category]
        summary[category]={k:[str(sum(Fraction(r['conditional_FLOOR'][k][i])for r in rows)/len(rows))for i in(0,1)]
                           for k in ('action_WDL_mean','guarantee_gap_mean','lowering_probability')}
    out['uniform_known_fork_mu_FLOOR']=summary
    out['FLOOR_scope']='Uniform across knownfork histories only; at each samehistory the existing FLOOR fallback is uniform over actuallegalactions unless an immediatemate exists. Descriptive one-decision minimax guarantee/probability bounds, not wholepolicy utility, deployment or causal price/depth benefit. Partialactionlabels remainintervals.'
    return out


def classify(truth,context,*,seconds=180):
    tick=time.perf_counter();forks={r['id']:r for r in truth['roots']if r['wdl_fork']is True}
    origins={(o['record_id'],o['ply']):r for r in truth['roots']for o in r['origins']}
    compiled={fp:compile_rule(ruleset_from_dict(r))for fp,r in truth['rules'].items()}
    physical={};events=[];cost=Counter();by_record={};columns=context['query_columns']
    for rid,record in truth['records'].items():
        if time.perf_counter()-tick>=seconds:raise RuntimeError('CLASSIFICATION_CAP_UNKNOWN')
        if role_stop_requested():raise RuntimeError('USER_STOP')
        s=GameSession(compiled[record['ruleset_fingerprint']]);refmeta=context['records'][rid]
        by_record[rid]=[]
        for ply,raw in enumerate(record['actions']):
            r=origins[rid,ply];hid=state_sha(s.state)
            if hid!=r['id']:raise ValueError('source complete-history binding mismatch')
            if hid in forks:
                if hid not in physical:
                    actor=s.state.position.side_to_move;win=[];children=[]
                    labels={digest(a['action']):a['wdl_bounds']for a in r['action_bounds']}
                    for ac,ch in legal_successors(s.state,s.compiled):
                        a=action_to_dict(ac);cost['Core_edges']+=1
                        children.append(a)
                        if ch.terminal_status.winner==actor:
                            if labels.get(digest(a))!=[1,1]:raise ValueError('terminal contradicts action truth')
                            win.append(a)
                    if {digest(a)for a in children}!=set(labels):raise ValueError('known fork legal set mismatch')
                    category=mechanism(r['wdl_bounds'],bool(win))
                    physical[hid]=dict(id=hid,fingerprint=r['fingerprint'],family=r['family'],
                        ply=r['ply'],actors=r['actors'],wdl_bounds=r['wdl_bounds'],category=category,
                        immediate_mate_actions=win,legal_actions=len(children),recorded_events=[])
                q=physical[hid];chosen=next(a['wdl_bounds']for a in r['action_bounds']if a['action']==raw)
                loss=chosen[1]<r['wdl_bounds'][0]
                equal=chosen[0]>=r['wdl_bounds'][1]
                # Same complete record may carry multiple controller protocol
                # references. Do not collapse their policy labels or count them
                # as independent games.
                policies=[]
                for ref in refmeta:
                    entries=[dict(zip(columns,x))for x in ref['queries']if x[1]==ply]
                    if len(entries)!=1 or entries[0]['id']!=hid:
                        raise ValueError('source policy reference mismatch')
                    policies.append(entries[0]['policy'])
                e=dict(record_id=rid,ply=ply,id=hid,category=q['category'],root=r['wdl_bounds'],chosen=chosen,
                    guarantee_loss=True if loss else False if equal else None,
                    policies=policies,reference_weight=len(refmeta))
                events.append(e);q['recorded_events'].append(len(events)-1);by_record[rid].append(len(events)-1)
            s.submit(action_from_dict(raw));cost['record_actions']+=1
        if not s.state.terminal_status.is_terminal:raise ValueError('source record incomplete')
        cost['records']+=1
    if set(physical)!=set(forks):raise ValueError('known fork not reached by source records')
    summary={};families={}
    for category in sorted({q['category']for q in physical.values()}):
        selected=[q for q in physical.values()if q['category']==category];es=[e for e in events if e['category']==category]
        losses=[e for e in es if e['guarantee_loss']is True]
        summary[category]=dict(distinct_histories=len(selected),record_actions=len(es),
            distinct_records=len({e['record_id']for e in es}),source_references=sum(e['reference_weight']for e in es),
            guarantee_loss_record_actions=len(losses),guarantee_loss_histories=len({e['id']for e in losses}),
            guarantee_loss_records=len({e['record_id']for e in losses}),
            policies=dict(Counter(p for e in es for p in e['policies'])),
            guarantee_loss_policies=dict(Counter(p for e in losses for p in e['policies'])))
    for family in sorted({q['family']for q in physical.values()}):
        families[family]=dict(Counter(q['category']for q in physical.values()if q['family']==family))
    return dict(format='leaper-fork-tactical-scope-v1',truth_digest=digest(truth),context_digest=digest(context),
        histories=sorted(physical.values(),key=lambda q:q['id']),events=events,summary=summary,families=families,
        cost=dict(cost),seconds=time.perf_counter()-tick,
        scope='Same frozen369records and known WDL fork roots, exact full-history replay and literal immediate terminal choices. Reference policies are endogenous correlated trajectories,not an intervention or independent win-rate sample. WIN without mate now means immediate-mate FLOOR has no positive terminal to find;it does not prove useful deeper search,price or learning. Earlier UNKNOWN histories still censor first-event times.')
