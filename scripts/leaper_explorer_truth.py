"""Retrospective AUX truth inventory and strict offline E0 scoring.

Consumes existing closed canonical evidence. No new rules, games, search,
training, predictions or product defaults. Legacy labels retain their scope.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import gzip
import hashlib
import json
import math
from pathlib import Path
import re
import time

from generic_chess.rules.schema import ruleset_from_dict, compute_fingerprint
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution as compile_rule
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.core.actions import action_from_dict
from scripts.leaper_design import state_sha
from scripts.leaper_microgames import role_stop_requested

SOURCE = Path('docs/research/data/leaper_canonical_triage_20261022/evidence.json.gz')
PROPERTIES = ('wdl_fork', 'cooperative_decisive', 'universal_draw')


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                      ensure_ascii=False).encode()).hexdigest()


def load(path):
    blob = Path(path).read_bytes()
    return json.loads(gzip.decompress(blob) if str(path).endswith('.gz') else blob)


def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = (json.dumps(value, sort_keys=True, separators=(',', ':')) + '\n').encode()
    path.write_bytes(gzip.compress(raw, mtime=0) if str(path).endswith('.gz') else raw)


def family_key(masks):
    """Group renamed/swapped ordinary types and every layout of the same code.

    Conservatively also group board-size/clock variants of this code. All
    current inputs are 4x4/repeat4/max128; this is not generic canonicalization.
    """
    if len(masks) != 2 or any(type(x) is not int or not 1 <= x <= 31 for x in masks):
        raise ValueError('two canonical orbit masks required')
    return 'K3:' + ':'.join(map(str, sorted(masks)))


def make_freeze(source=SOURCE):
    p = load(source)
    masks = p['triage']['rule_masks']
    families = sorted({family_key(m) for m in masks.values()},
                      key=lambda k: digest(['AUX-E0-exposed-split-v1', k]))
    # Already read/public labels: this partition tests a future pipeline only.
    split = {k: 'calibration_exposed' if i < 6 else 'leaveout_exposed'
             for i, k in enumerate(families)}
    return dict(format='leaper-explorer-truth-freeze-v1',
                source_file=str(source).replace('\\', '/'),
                source_sha256=hashlib.sha256(Path(source).read_bytes()).hexdigest(),
                source_execution_sha=p['source_sha'],
                current_shared_source_sha='8f1f9e5f977e1baba0e5a3cd14d74b7ea0351130',
                families=split,
                fingerprints={fp: dict(masks=m, family=family_key(m), split=split[family_key(m)])
                              for fp, m in masks.items()},
                exposure='All legacy rules/labels exposed; no blind holdout or generalization claim.',
                mu='Uniform distinct ongoing full histories within each source rule; endogenous frozen trajectories, not initial-layout or policy IID sampling.',
                selection='All 369 distinct source records and all their ongoing queried histories; no truth-based exclusion.',
                witness_selection='Per family, lexicographically first full-history SHA in each of DRAW/nonstructural, WDL-fork, repeated/nonstructural categories. Diagnostic only, never TRAIN.',
                new_compute_caps=dict(seconds=900, graphs=30, selected_roots_per_family=3),
                stop='No original cap refill, new closure expansion, game or Player query. Unknown stays unknown. No E0 predictions are synthesized.')


def build(freeze, source=SOURCE):
    started = time.perf_counter()
    p = load(source)
    if hashlib.sha256(Path(source).read_bytes()).hexdigest() != freeze['source_sha256']:
        raise ValueError('source changed after freeze')
    rules = p['rules']
    compiled = {fp: compile_rule(ruleset_from_dict(rule)) for fp, rule in rules.items()}
    assert all(compute_fingerprint(ruleset_from_dict(rules[fp])) == fp for fp in rules)
    old_labels = {r[0]: r for r in p['roots']}
    roots, records, critical = {}, {}, []
    counts = Counter()
    for t in p['trajectories']:
        if role_stop_requested():
            raise RuntimeError('USER_STOP')
        record = t['record_header'] | dict(actions=[p['actions'][s[3]] for s in t['path'] if s[3] is not None])
        assert digest(record) == t['id']
        records[t['id']] = record
        fp = record['ruleset_fingerprint']
        s = GameSession(compiled[fp])
        position_visits = Counter()
        # Core's full state hash remains the identity; Position counts here
        # describe observed recurrence, not a history-equivalence quotient.
        for ply, label_index, actors, action_index in t['path']:
            assert s.state.ply_count == ply and not s.state.terminal_status.is_terminal
            hid = state_sha(s.state)
            position_visits[s.state.position] += 1
            old = old_labels.get(hid)
            assert (old is not None) == (label_index is not None)
            if old is not None:
                assert p['roots'][label_index] == old and old[2:4] == [ply, actors]
                assert p['fingerprints'][old[1]] == fp
            row = dict(id=hid, fingerprint=fp, ply=ply, actors=actors,
                       record_id=t['id'], prefix_actions=ply,
                       family=freeze['fingerprints'][fp]['family'],
                       split=freeze['fingerprints'][fp]['split'],
                       position_visits_in_prefix=position_visits[s.state.position],
                       max_repetition_count=max(n for _, n in s.state.repetition_counts),
                       rule_remaining=compiled[fp].max_ply-ply,
                       wdl_bounds=[-1, 1] if old is None else [old[4], old[4]],
                       graph_structural_deadzone=None if old is None else old[6],
                       wdl_fork=None if old is None else old[7],
                       cooperative_decisive=False if old is not None and old[6] else None,
                       universal_draw=True if old is not None and old[6] else None,
                       action_bounds=[] if old is None else [dict(action=p['actions'][b[0]], wdl_bounds=[b[1], b[1]]) for b in old[9]],
                       truth_basis='UNKNOWN_unresolved_original_caps' if old is None else 'legacy_complete_graph_scoped_history_rank_clock',
                       origins=[])
            root = roots.setdefault(hid, row)
            assert all(root[k] == row[k] for k in ('fingerprint', 'ply', 'wdl_bounds', 'max_repetition_count'))
            root['origins'].append(dict(record_id=t['id'], ply=ply, action_index=action_index))
            if old is not None and action_index is not None:
                chosen = next(b[1] for b in old[9] if b[0] == action_index)
                if chosen < old[4]:
                    # Fixed mover's observed eventual result, not a
                    # counterfactual policy estimate or proof of inevitability.
                    winner = t['terminal']['winner']
                    payoff = 0 if winner is None else 1 if winner == s.state.position.side_to_move else -1
                    critical.append(dict(id=hid, record_id=t['id'], ply=ply,
                                         root_wdl=old[4], chosen_wdl=chosen,
                                         actual_terminal=t['terminal']['status'],
                                         eventual_mover_payoff=payoff,
                                         better_than_chosen_guarantee=payoff > chosen))
            if action_index is not None:
                s.submit(action_from_dict(p['actions'][action_index]))
                counts['replayed_actions'] += 1
        assert s.result.status.value == t['terminal']['status'] and s.result.winner == t['terminal']['winner']
        counts['replayed_records'] += 1
    assert len(roots) == p['triage']['inventory']['unique_roots']
    assert sum(r['wdl_bounds'][0] == r['wdl_bounds'][1] for r in roots.values()) == len(old_labels)
    # Each hash is one unit in the explicitly retrospective mu; repeated visits
    # and duplicate record references never earn extra calibration weight.
    mus = {fp: digest(sorted(r['id'] for r in roots.values() if r['fingerprint'] == fp)) for fp in rules}
    for row in roots.values():
        row['mu_id'] = mus[row['fingerprint']]
    selected = {}
    for family in freeze['families']:
        rs = sorted((r for r in roots.values() if r['family'] == family), key=lambda r: r['id'])
        predicates = dict(draw_nonstructural=lambda r: r['wdl_bounds'] == [0, 0] and r['graph_structural_deadzone'] is False,
                          fork=lambda r: r['wdl_fork'] is True,
                          repeated_nonstructural=lambda r: r['position_visits_in_prefix'] > 1 and r['graph_structural_deadzone'] is False)
        selected[family] = {k: next((r['id'] for r in rs if test(r)), None) for k, test in predicates.items()}
    return dict(format='leaper-explorer-truth-v1', freeze=freeze, rules=rules,
                records=records, roots=sorted(roots.values(), key=lambda r:r['id']),
                mu_ids=mus, selected=selected, critical_observed=critical,
                counts=dict(counts), seconds=time.perf_counter()-started,
                scope='Existing labels are imported, not independently re-solved. Full records freshly replayed; public witnesses carry separate literal verification. No policy-attractor probability or blind test.')


def validate_probability_forecast(q):
    """Common provenance/cost/value checks, without inventing a prediction."""
    if not isinstance(q.get('source_sha'),str) or re.fullmatch('[0-9a-f]{40}',q['source_sha']) is None:
        raise ValueError('full prediction execution SHA required')
    cost=q.get('cost')
    if (not isinstance(cost,dict) or not cost or
        any(type(v) not in (int,float) or not math.isfinite(v) or v<0 for v in cost.values())):
        raise ValueError('prediction execution source and cost required')
    prob=q.get('probability')
    if type(prob) not in (int,float) or not math.isfinite(prob) or not 0<=prob<=1:
        raise ValueError('probability must be finite in [0,1]')
    return prob


def score(truth, predictions):
    """Finite forecast loss with explicit abstention and missing-truth bounds.

    A prediction is for one property at one exact full history under the named
    source mu. No fuzzy joins, default probability, duplicate vote or UNKNOWN=0.
    Whole-denominator bounds allow abstentions to have loss anywhere in [0,1].
    They measure missing evaluation, not the predictive loss of abstaining.
    """
    if predictions.get('format') != 'leaper-explorer-predictions-v1':
        raise ValueError('unsupported prediction format')
    roots = {r['id']: r for r in truth['roots']}
    seen, accepted_predictions, groups = set(), [], defaultdict(lambda: dict(predicted=0, known=0, tp=0, tn=0, fp=0, fn=0,
                                                   brier_known_sum=0., loss_lower=0., loss_upper=0.))
    for q in predictions['predictions']:
        prop = q['property']
        if prop not in PROPERTIES or q['id'] not in roots:
            raise ValueError('unknown property or history')
        r = roots[q['id']]
        if q['fingerprint'] != r['fingerprint'] or q['mu_id'] != r['mu_id']:
            raise ValueError('prediction rule/mu binding mismatch')
        prob=validate_probability_forecast(q)
        key = (q['id'], prop)
        if key in seen:
            raise ValueError('duplicate prediction')
        seen.add(key)
        accepted_predictions.append((r,prop,prob))
        g = groups[prop, r['split']]
        g['predicted'] += 1
        label = r[prop]
        if label is None:
            low, high = min(prob**2, (1-prob)**2), max(prob**2, (1-prob)**2)
        else:
            if type(label) is not bool:
                raise ValueError('truth must be boolean or unknown')
            low = high = (prob-int(label))**2
            g['known'] += 1
            g['brier_known_sum'] += low
            g[('t' if (prob >= .5) == label else 'f') + ('p' if prob >= .5 else 'n')] += 1
        g['loss_lower'] += low
        g['loss_upper'] += high
    output = []
    for prop in PROPERTIES:
        for split in sorted(set(r['split'] for r in roots.values())):
            rs = [r for r in roots.values() if r['split'] == split]
            g = groups[prop, split]
            n = len(rs)
            missing = n-g['predicted']
            output.append(dict(property=prop, split=split, denominator=n,
                               truth_known=sum(r[prop] is not None for r in rs),
                               abstained=missing, **g,
                               brier_known=None if not g['known'] else g['brier_known_sum']/g['known'],
                               whole_denominator_brier_bounds=None if not n else [g['loss_lower']/n, (g['loss_upper']+missing)/n]))
    selective=[];macro=[]
    for prop in PROPERTIES:
        for split in sorted(set(r['split']for r in roots.values())):
            split_roots=[r for r in roots.values()if r['split']==split]
            qs=[(r,p)for r,k,p in accepted_predictions if k==prop and r['split']==split]
            for threshold in(.5,.6,.7,.8,.9,1.):
                selected=[(r,p)for r,p in qs if max(p,1-p)>=threshold]
                known=[(r,p)for r,p in selected if r[prop]is not None]
                errors=sum((p>=.5)!=r[prop]for r,p in known)
                n=len(selected);unknown=n-len(known)
                selective.append(dict(property=prop,split=split,confidence_threshold=threshold,
                                      coverage=n/len(split_roots),accepted=n,known=len(known),unknown=unknown,
                                      conditional_error_bounds=None if not n else[errors/n,(errors+unknown)/n]))
            per_rule=[]
            for fp in sorted({r['fingerprint']for r in split_roots}):
                rr=[r for r in split_roots if r['fingerprint']==fp];qq=[(r,p)for r,p in qs if r['fingerprint']==fp]
                lo=hi=0.
                for r,p in qq:
                    if r[prop]is None:lo+=min(p*p,(1-p)**2);hi+=max(p*p,(1-p)**2)
                    else:v=(p-int(r[prop]))**2;lo+=v;hi+=v
                missing=len(rr)-len(qq)
                per_rule.append([lo/len(rr),(hi+missing)/len(rr)])
            macro.append(dict(property=prop,split=split,rules=len(per_rule),
                              equal_rule_whole_brier_bounds=[sum(x[j]for x in per_rule)/len(per_rule)for j in(0,1)]))
    return dict(format='leaper-explorer-score-v1', rows=output,selective=selective,macro=macro,
                note='FP/FN only count actual frozen predictions against known truth; no E0 supplied means no measured error. Known-only Brier is conditional on coverage. Loss bounds retain unknown truth and missing predictions. These are descriptive finite exposed-input diagnostics, not population calibration, IID confidence or unseen-rule generalization.')


def rule_targets(truth):
    """Uniform-history prevalence bounds, not rule-existence or opening truth.

    This denominator is useful for a future matching E0 predictor. It cannot
    calibrate PRIMARY's different initial-layout/policy mu by a fuzzy join.
    """
    result=[]
    for fp in sorted(truth['rules']):
        rs=[r for r in truth['roots']if r['fingerprint']==fp]
        assert rs
        row=dict(fingerprint=fp, family=rs[0]['family'], split=rs[0]['split'], mu_id=rs[0]['mu_id'],
                 denominator=len(rs), wdl_known=sum(r['wdl_bounds'][0]==r['wdl_bounds'][1]for r in rs),
                 wdl_unknown=sum(r['wdl_bounds'][0]!=r['wdl_bounds'][1]for r in rs), properties={})
        for prop in PROPERTIES:
            positives=sum(r[prop]is True for r in rs);negatives=sum(r[prop]is False for r in rs)
            unknown=len(rs)-positives-negatives
            row['properties'][prop]=dict(positive=positives,negative=negatives,unknown=unknown,
                                        prevalence_bounds=[positives/len(rs),(positives+unknown)/len(rs)])
        result.append(row)
    return result


def materialize(truth,cooperative,observed=None):
    """Add separately verified observer claims; retain imported source labels.

    Nonzero exact WDL already implies a cooperative decisive route. Zero WDL
    does not imply the contrary. Witness selection never changes the mu.
    """
    from copy import deepcopy
    if cooperative['source_truth_digest']!=digest(truth):
        raise ValueError('cooperative evidence input mismatch')
    out=deepcopy(truth);by_id={r['id']:r for r in out['roots']}
    for r in out['roots']:
        if r['wdl_bounds']in([-1,-1],[1,1]):
            r['cooperative_decisive']=True;r['universal_draw']=False
    for q in cooperative['rows']:
        r=by_id[q['id']]
        if r['cooperative_decisive']is not None and r['cooperative_decisive']!=q['cooperative_decisive']:
            raise ValueError('new observer contradicts imported WDL/closure')
        r['cooperative_decisive']=q['cooperative_decisive'];r['universal_draw']=q['universal_draw']
        r['cooperative_basis']='selected_history_distance_witness_or_potential'
    if observed is not None:
        if observed['truth_digest']!=digest(truth):raise ValueError('observed suffix input mismatch')
        for q in observed['positive']:
            r=by_id[q['id']]
            if r['cooperative_decisive']is False:raise ValueError('mate suffix contradicts no-decisive proof')
            r['cooperative_decisive']=True;r['universal_draw']=False
            r['cooperative_basis']='actual_complete_record_mate_suffix'
        out['observed_suffix_digest']=digest(observed)
    out['cooperative_evidence_digest']=digest(cooperative)
    return out


def observed_suffix_truth(truth,source=SOURCE):
    """A legal mate suffix certifies cooperative existence, never forced WDL.

    Reuses the already replayed complete-record census; no graph oracle or new
    game. The reference record's entire suffix is retained as a Core witness.
    """
    if hashlib.sha256(Path(source).read_bytes()).hexdigest()!=truth['freeze']['source_sha256']:
        raise ValueError('source capsule mismatch')
    p=load(source);terminals={t['id']:t['terminal']for t in p['trajectories']}
    positives=[];by_id={r['id']:r for r in truth['roots']}
    for r in truth['roots']:
        refs=[o for o in r['origins']if terminals[o['record_id']]['winner']is not None]
        if not refs:continue
        chosen=min(refs,key=lambda o:(len(truth['records'][o['record_id']]['actions'])-o['ply'],o['record_id']))
        assert r['graph_structural_deadzone']is not True
        record=truth['records'][chosen['record_id']]
        positives.append(dict(id=r['id'],record_id=chosen['record_id'],prefix_ply=chosen['ply'],
                              suffix_length=len(record['actions'])-chosen['ply'],terminal=terminals[chosen['record_id']]))
    return dict(format='leaper-observed-suffix-truth-v1',truth_digest=digest(truth),positive=positives,
                positive_WDL_unknown=sum(by_id[q['id']]['wdl_bounds']==[-1,1]for q in positives),
                scope='Existential full-history mate paths already contained in original frozen records. No new games, minimax labels, policy probabilities or E0 predictions.')


def build_context(truth,source):
    """Preserve PRIMARY's frozen controller/seed/cost provenance verbatim."""
    raw=Path(source).read_bytes();sha=hashlib.sha256(raw).hexdigest()
    if sha!='65cbda6e861249f04914511f5bcdd1e83233879c276236df7caac1f7d5c0b761':
        raise ValueError('source context packet mismatch')
    p=load(source);context=defaultdict(list)
    cols=['id','ply','actor','policy','legal_count','nodes','completed_depth','seconds']
    for item in p['games']:
        game=item['game'];rid=digest(game['final_record'])
        row={k:game[k]for k in ('slot','world','pair','role','repeat','policy_by_actor','rng_seeds','censor')}
        row['run']=item['run'];row['queries']=[]
        for q in game['queries']:
            decision=q.get('decision')or{}
            row['queries'].append([q['state_sha256'],q['root_ply'],q['actor'],q['policy'],q['legal_count'],
                                   decision.get('nodes',0),decision.get('completed_depth'),q['seconds']])
        context[rid].append(row)
    assert set(context)==set(truth['records'])
    return dict(format='leaper-explorer-source-context-v1',source_sha256=sha,
                source_sha='e8f4abf94bde7b6de1ab1a9acc3abfd24533c002',query_columns=cols,
                records=dict(context),registrations={k:v['registration']for k,v in p['runs'].items()},
                scope='Original frozen policy/seeds/cost provenance;not E0 predictions or new executions. Shared records can have different controller references.')


def observed_mechanisms(truth,cooperative,context):
    """Bind finite observed returns/exits and guarantee losses to real records.

    A repeated Position is not a cycle of complete histories or a probability
    of future entrapment. Exact policy-transition enumeration remains separate.
    """
    by_id={r['id']:r for r in truth['roots']};compiled={};loops=[]
    for q in cooperative['rows']:
        r=by_id[q['id']]
        if not q['cooperative_decisive']or r['position_visits_in_prefix']<2:continue
        fp=r['fingerprint']
        if fp not in compiled:compiled[fp]=compile_rule(ruleset_from_dict(truth['rules'][fp]))
        session=GameSession(compiled[fp]);record=truth['records'][r['record_id']]
        prefix=[];states=[]
        for action in record['actions'][:r['ply']]:
            prefix.append(session.state.position);states.append(state_sha(session.state));session.submit(action_from_dict(action))
        assert state_sha(session.state)==r['id']
        earlier=[i for i,p in enumerate(prefix)if p==session.state.position]
        assert earlier and all(states[i]!=r['id']for i in earlier)
        previous=earlier[-1];actual=context['records'][r['record_id']]
        loops.append(dict(id=r['id'],record_id=r['record_id'],previous_ply=previous,current_ply=r['ply'],
                          cycle_actions=record['actions'][previous:r['ply']],earlier_visits=len(earlier),
                          equal_position_different_history=True,actual_policy_context=[{k:v for k,v in row.items()if k!='queries'}for row in actual],
                          cooperative_exit=q['witness'],cooperative_terminal=q['terminal'],
                          limitation='Observed finite policy recurrence plus a legal cooperative exit;not a stationary full-history SCC, escape probability or opponent-forced exit.'))
    next_by_origin={(o['record_id'],o['ply']):r for r in truth['roots']for o in r['origins']}
    critical=[];counts=Counter()
    for q in truth['critical_observed']:
        ch=next_by_origin.get((q['record_id'],q['ply']+1))
        future_draw=(ch['graph_structural_deadzone']is True)if ch else q['chosen_wdl']==0
        category='closed_structural_draw'if ch and future_draw else 'actual_terminal_draw'if future_draw else 'not_established_all_future_draw'
        counts[category]+=1
        critical.append(q|dict(child_id=None if ch is None else ch['id'],
                               child_all_future_draw=True if future_draw else None,child_category=category))
    return dict(format='leaper-observed-mechanisms-v1',truth_digest=digest(truth),
                cooperative_digest=digest(cooperative),context_digest=digest(context),
                finite_exitable_returns=loops,critical=critical,
                counts=dict(critical_record_actions=len(critical),critical_unique_histories=len({r['id']for r in critical}),
                            actual_outperform_guarantee=sum(q['better_than_chosen_guarantee']for q in critical),
                            critical_children=dict(counts),finite_exitable_return_histories=len(loops)),
                scope='Posthoc finite witnesses on exposed endogenous records. Universal DRAW is only asserted from a closed structural child or actual draw terminal; all other universal-outcome classifications remain unknown.')


def sampling_law_summary(truth,context):
    """Posthoc prevalence bounds under explicitly different source laws."""
    laws={
        'uniform_distinct_ongoing_histories':{r['id']:1 for r in truth['roots']},
        'distinct_record_decision_visits':{r['id']:len(r['origins'])for r in truth['roots']},
        'reference_decision_visits':{r['id']:sum(len(context['records'][o['record_id']])for o in r['origins'])for r in truth['roots']},
        'one_frozen_initial_history_per_rule':{r['id']:int(r['ply']==0)for r in truth['roots']},
    }
    output=[]
    for name,weights in laws.items():
        n=sum(weights.values());row=dict(law=name,denominator=n,mu_id=digest(sorted((k,v)for k,v in weights.items()if v)),properties={})
        for prop in PROPERTIES:
            positive=sum(weights[r['id']]for r in truth['roots']if r[prop]is True)
            negative=sum(weights[r['id']]for r in truth['roots']if r[prop]is False)
            unknown=n-positive-negative
            row['properties'][prop]=dict(positive=positive,negative=negative,unknown=unknown,
                                        prevalence_bounds=[positive/n,(positive+unknown)/n])
        output.append(row)
    assert output[1]['denominator']==truth['counts']['replayed_actions']
    return dict(format='leaper-sampling-law-truth-v1',rows=output,
                scope='Finite source laws,not estimates of other initial/layout/policy distributions. Reference reuse and source controls deliberately alter weights; no independence or population interval follows.')


def main():
    cli = argparse.ArgumentParser()
    sub = cli.add_subparsers(dest='command', required=True)
    f = sub.add_parser('freeze'); f.add_argument('--output', required=True)
    b = sub.add_parser('build'); b.add_argument('--freeze', required=True); b.add_argument('--output', required=True)
    s = sub.add_parser('score'); s.add_argument('--truth', required=True); s.add_argument('--predictions', required=True); s.add_argument('--cooperative'); s.add_argument('--observed'); s.add_argument('--output', required=True)
    args = cli.parse_args()
    if args.command == 'freeze': result = make_freeze()
    elif args.command == 'build': result = build(load(args.freeze))
    else:
        truth=load(args.truth)
        if args.cooperative:truth=materialize(truth,load(args.cooperative),None if not args.observed else load(args.observed))
        result = score(truth, load(args.predictions))
    save(args.output, result)
    print(json.dumps(dict(output=args.output, format=result['format'], seconds=result.get('seconds'))))


if __name__ == '__main__':
    main()
