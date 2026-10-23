"""Portable reader for saved-history Bellman bounds and literal path proofs."""
from pathlib import Path
from collections import Counter
import argparse,hashlib,time
from scripts.leaper_explorer_truth import load,save,digest,rule_targets
from scripts.leaper_saved_child_bounds import current_truth,propagate,verify as verify_edges
from scripts.leaper_path_constraints import constrain,recorded_edges
from scripts.leaper_saved_suffix_transfer import verify as verify_suffix,apply as suffix_apply,barrier_diagnostics
from scripts.leaper_observed_path_proofs import verify as verify_observed,apply as observed_apply
from scripts.leaper_truth_views import initial_history_view
from scripts.leaper_episode_exposure import run as episodes


def verify_critical_cases(before,after,packet,context):
    """Two new natural events: check literal tactical scope and actual outcome."""
    import json
    from copy import copy
    from generic_chess.core.actions import action_from_dict
    from generic_chess.rules.schema import ruleset_from_dict
    from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution as compile_rule
    from generic_chess.session.session import GameSession
    from generic_chess.session.serialization import deserialize_game_record
    from scripts.leaper_cooperative_certificate import root_session
    from scripts.leaper_saved_child_bounds import edge
    if packet['input_digest']!=digest(before)or packet['saved_child_truth_digest']!=digest(after):
        raise ValueError('critical source mismatch')
    roots={r['id']:r for r in after['roots']};old={r['id']:r for r in before['roots']};stats=Counter()
    for q in packet['new_record_actions']:
        r=roots[q['id']];c=compile_rule(ruleset_from_dict(after['rules'][r['fingerprint']]))
        _,s=root_session(after,r['id'],c);actor=s.state.position.side_to_move
        record=after['records'][q['record_id']]
        if record['actions'][q['ply']]!=q['chosen_action']or q['actor']!=actor:raise ValueError('critical record action mismatch')
        if r['wdl_bounds']!=[1,1]or old[r['id']]['wdl_bounds']!=q['before_root_bounds']:raise ValueError('critical root bound mismatch')
        choice=next(a['wdl_bounds']for a in r['action_bounds']if a['action']==q['chosen_action'])
        if choice!=q['chosen_bounds']or choice[1]>=r['wdl_bounds'][0]:raise ValueError('not a certified guarantee loss')
        ac=action_from_dict(q['chosen_action']);ch=copy(s);ch.submit(ac)
        if digest(edge(s.state,ac,ch.state))!=digest(q['chosen_core_child']):raise ValueError('chosen child mismatch')
        winners=0
        for item in q['better_core_children']:
            ac=action_from_dict(item['action']);ch=copy(s);ch.submit(ac)
            if digest(edge(s.state,ac,ch.state))!=digest(item):raise ValueError('better child mismatch')
            winners+=ch.state.terminal_status.winner==actor
        if not winners or q['immediate_winning_action_exists']is not True:raise ValueError('not an immediate-win opportunity')
        final=GameSession.replay(c,deserialize_game_record(json.dumps(record)))
        if final.result.status.value!=q['actual_terminal']or final.result.winner!=q['actual_winner']:
            raise ValueError('critical actual outcome mismatch')
        refs=context['records'][q['record_id']]
        if [ref['queries'][q['ply']]for ref in refs]!=q['source_queries']or len(refs)!=q['reference_count']:
            raise ValueError('critical source reference mismatch')
        stats['record_actions']+=1;stats['immediate_win_opportunities']+=1;stats['reference_count']+=len(refs)
    return dict(verified=True,counts=dict(stats),scope='Actual same-record RNG choices and literal immediate-win alternatives;no deeper-than-FLOOR,price,learning,E0 or independent-reference claim.')


def verify(directory, *, parents=True, diagnostics=True):
    start=time.perf_counter();p=Path(directory).resolve();root=p.parents[3]
    manifest=load(p/'manifest.json')
    for section,base in (('files',p),('sources',root)):
        for name,expected in manifest[section].items():
            path=(base/name).resolve()
            if not path.is_relative_to(base):raise ValueError('manifest path outside root')
            raw=path.read_bytes()
            if expected.get('normalization')=='git_text_lf':raw=raw.replace(b'\r\n',b'\n')
            if len(raw)!=expected['bytes']or hashlib.sha256(raw).hexdigest()!=expected['sha256']:
                raise ValueError('manifest mismatch:'+name)
    parent=p.parent/'leaper_explorer_truth_20261023';followup=p.parent/'leaper_explorer_followup_20261023'
    previous=None
    if parents:
        from scripts.verify_leaper_explorer_followup import verify as previous_reader
        previous=previous_reader(followup)
    t=current_truth(parent,followup);local=load(p/'edges.json.gz')
    edge_receipt=verify_edges(t,local);u,changes=propagate(t,local)
    if changes!=load(p/'changes.json.gz'):raise ValueError('saved-child changes mismatch')
    diag=None
    if diagnostics:
        recorded=load(p/'recorded-edges.json.gz');actual=recorded_edges(u)
        if actual['rows']!=recorded['rows']or actual['counts']!=recorded['counts']:
            raise ValueError('recorded edge provenance mismatch')
        _,path_changes,statistics=constrain(u,recorded,local)
        if path_changes!=load(p/'path-changes.json.gz'):raise ValueError('path constraint result mismatch')
        diag=dict(recorded_counts=actual['counts'],path_changes=len(path_changes),constraint_statistics=statistics)
    proposals=load(p/'suffix-proposals.json.gz');raw=load(p/'suffix-proofs.json.gz');short=load(p/'shortened-proofs.json.gz')
    raw_receipt=verify_suffix(u,proposals,raw);short_receipt=verify_suffix(u,proposals,short)
    if barrier_diagnostics(u,raw,short)!=load(p/'barriers.json'):raise ValueError('repetition barrier mismatch')
    v=suffix_apply(u,short);op=load(p/'observed-proposals.json.gz');proofs=load(p/'observed-proofs.json.gz')
    observed_receipt=verify_observed(v,op,proofs);w=observed_apply(v,proofs)
    summary=load(p/'final-summary.json')
    if summary['final_truth_digest']!=digest(w):raise ValueError('final truth mismatch')
    if t['mu_ids']!=w['mu_ids']or t['records']!=w['records']or t['rules']!=w['rules']:
        raise ValueError('evaluation support/rules/records changed')
    if rule_targets(w)!=load(p/'final-rule-targets.json'):raise ValueError('rule target mismatch')
    if initial_history_view(w)!=load(p/'final-initial-view.json.gz'):raise ValueError('initial view mismatch')
    ep=episodes(w,load(parent/'source-context.json.gz'))
    if ep!=load(p/'final-episodes.json.gz'):raise ValueError('episode result mismatch')
    if summary['exact_wdl']!=sum(r['wdl_bounds'][0]==r['wdl_bounds'][1]for r in w['roots']):
        raise ValueError('WDL count mismatch')
    props={k:dict(Counter(str(r[k])for r in w['roots']))for k in ('wdl_fork','cooperative_decisive','universal_draw')}
    if summary['properties']!=props:raise ValueError('property count mismatch')
    metadata=load(p/'metadata-support.json');derived={}
    from collections import defaultdict
    for name,view in (('original_initial10',initial_history_view(w)),('saved_distinct_histories',w)):
        groups=defaultdict(list)
        for r in view['roots']:groups[view['rules'][r['fingerprint']]['board_size'],r['actors']].append(r)
        rows=[]
        for (size,actors),rs in sorted(groups.items()):
            properties={}
            for prop in ('wdl_fork','cooperative_decisive'):
                counts=Counter(str(r[prop])for r in rs);n=len(rs)
                properties[prop]=dict(counts=dict(counts),prevalence_bounds=[counts['True']/n,(counts['True']+counts['None'])/n])
            rows.append(dict(board_size=size,actors=actors,denominator=len(rs),distinct_rules=len({r['fingerprint']for r in rs}),properties=properties))
        derived[name]=dict(denominator=len(view['roots']),metadata_classes=len(groups),rows=rows)
    if metadata['truth_digest']!=digest(w)or metadata['reports']!=derived:raise ValueError('metadata support mismatch')
    critical_receipt=verify_critical_cases(t,u,load(p/'new-critical-cases.json'),load(parent/'source-context.json.gz'))
    minimal=load(p/'minimal-fork-result.json')
    if (minimal['spec']['input_digest']!=digest(w)or minimal['status']!='UNKNOWN'
            or minimal['certificate']is not None or minimal['initial_fork']is not None):
        raise ValueError('closed minimal diagnostic must not supply a truth label')
    return dict(verified=True,files=len(manifest['files']),sources=len(manifest['sources']),parent=previous,
                edges=edge_receipt,diagnostics=diag,raw_suffix=raw_receipt,shortened_suffix=short_receipt,
                observed_paths=observed_receipt,final_truth_digest=digest(w),properties=props,
                critical_cases=critical_receipt,metadata_classes={k:v['metadata_classes']for k,v in derived.items()},seconds=time.perf_counter()-start,
                scope='Full-history/actual-Core proof checks on identical frozen support. Imported baseline labels retain earlier qualifications; incomplete observed edgebooks and failed paths prove no absence. No E0/baseline predictions, FP/FN, population calibration, new rule campaign or learner speed claim.')


if __name__=='__main__':
    cli=argparse.ArgumentParser();cli.add_argument('--directory',default='docs/research/data/leaper_explorer_saved_paths_20261023')
    cli.add_argument('--skip-parents',action='store_true');cli.add_argument('--skip-diagnostics',action='store_true');cli.add_argument('--output',required=True)
    a=cli.parse_args();r=verify(a.directory,parents=not a.skip_parents,diagnostics=not a.skip_diagnostics);save(a.output,r)
    print(__import__('json').dumps({k:r[k]for k in ('verified','files','sources','final_truth_digest','seconds')}))
