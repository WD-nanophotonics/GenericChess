"""Literal exposure/PV audit of the already published24Leaper games.

No Player calls, new games, WDL solving, off-policy value estimates or candidate
selection. Full GameRecord prefixes identify contexts; boards never merge them.
"""
from collections import Counter, defaultdict
import argparse
from fractions import Fraction
import gzip
import hashlib
import json
import math
from pathlib import Path
import time

from generic_chess.core.actions import action_to_dict
from generic_chess.session.session import GameSession
from scripts.leaper_truth_compatibility import Context, digest, bound_same_context_pairs
from scripts.research_record import record_value
from scripts.score_published_leaper_choices import literal_contexts, load_source, SOURCE_COMMIT
from scripts.qualify_primary_leaper_sources import read_checked


def audit_exposure(packet, games, raw_returns, plan, executed, *, verify_pvs=True, progress=None):
    contexts, _ = literal_contexts(packet)
    source_rows = {r['id']: r for r in packet['rows']}
    by_full_context = {}
    positions = defaultdict(set)
    game_rows = []
    query_rows = []
    ids = set()
    game_ids = set()
    pv_cache = {}
    counts = Counter()
    expected_game_slots = [(case, seat) for case in executed['root_ids'] for seat in (0, 1)]
    if len(games) != plan['games'] or len(expected_game_slots) != plan['games']:
        raise ValueError('saved game/frozen planned denominator differs')
    for game in games:
        game_id = game['game_id']
        if type(game_id) is not int or game_id in game_ids or not 0 <= game_id < len(expected_game_slots):
            raise ValueError('invalid/duplicate game slot')
        game_ids.add(game_id)
        case = game['case_id']
        if type(game['long_seat']) is not int or game['long_seat'] not in (0,1):
            raise ValueError('game policy seat is not integer0/1')
        if expected_game_slots[game_id] != (case, game['long_seat']):
            raise ValueError('game source slot/swap schedule differs')
        if game['fingerprint'] != contexts[case].identity['ruleset_fingerprint']:
            raise ValueError('game rule fingerprint differs')
        initial = source_rows[case]
        horizon=contexts[case].session.compiled.max_ply
        if type(horizon)is not int or horizon<=contexts[case].identity['ply']:
            raise ValueError('finite positive remaining rule horizon required')
        if game['initial_record'] != initial['record']:
            raise ValueError('game initial full record differs')
        session = GameSession.replay(contexts[case].session.compiled, contexts[case].session.to_record())
        if session.compiled.declarations:
            raise ValueError('declaration choices outside this source exposure scope')
        started = counts.copy()
        timing_ok = True
        for query in game['queries']:
            qid = query['query_id']
            if type(qid) is not int or qid in ids or str(qid) not in raw_returns:
                raise ValueError('query ID duplicate/missing original')
            ids.add(qid)
            original = raw_returns[str(qid)]
            if hashlib.sha256(original['original_utf8'].encode('utf-8')).hexdigest() != original['sha256']:
                raise ValueError('original return bytes hash differs')
            returned = json.loads(original['original_utf8'])
            if any(query.get(k) != v for k, v in returned.items()):
                raise ValueError('validated query changes original returned fields')
            if set(query)-set(returned) != {'validated_root_unchanged', 'pv_legal', 'record_after_sha256'}:
                raise ValueError('unexpected validation/source query fields')
            before = record_value(session.to_record())
            before_hash = digest(before)
            state = record_value(session.state)
            if query['record_before_sha256'] != before_hash:
                raise ValueError('actual full incoming record hash differs')
            if query['case_id'] != case or query['game_id'] != game_id:
                raise ValueError('query belongs to a different game/context')
            if type(query['seat']) is not int or type(query['ply_before']) is not int:
                raise ValueError('query source clock/seat must be integers')
            if query['ply_before'] != session.state.ply_count or query['seat'] != session.state.position.side_to_move:
                raise ValueError('query source clock/seat differs')
            policy = 'long' if query['seat'] == game['long_seat'] else 'short'
            seconds = plan['policies'][policy]['seconds']
            if query['policy'] != policy or query['requested_seconds'] != seconds:
                raise ValueError('source resource policy differs')
            for field in ('choose_wall_seconds','choose_cpu_seconds'):
                value=query[field]
                if type(value) not in (int,float) or not math.isfinite(value) or value<0:
                    raise ValueError('query has invalid actual cost')
            timing = query['choose_wall_seconds'] <= seconds+max(0.025, 0.10*seconds)
            if type(query['timing_eligible']) is not bool or query['timing_eligible'] != timing:
                raise ValueError('source timing qualification differs')
            timing_ok &= timing
            if query['validated_root_unchanged'] is not True or query['pv_legal'] is not True:
                raise ValueError('query is not source replay-qualified')
            legal = session.legal_actions()
            amap = {digest(record_value(a)): a for a in legal}
            if not amap or session.result.status.value != 'ongoing':
                raise ValueError('query without an ongoing ordinary move frontier')
            decision = query['decision']
            action_key = digest(decision['action'])
            if decision['choice_kind'] != 'ACTION' or decision['declaration'] is not None or action_key not in amap:
                raise ValueError('query selected choice outside exact legal frontier')
            action = amap[action_key]
            canonical = action_to_dict(action)
            pv = decision['principal_variation']
            if pv and pv[0] != decision['action']:
                raise ValueError('PV head differs from saved selected move')
            identity = dict(ruleset_fingerprint=game['fingerprint'], record_sha256=before_hash,
                            state_sha256=digest(state), history_sha256=digest(state['history']),
                            ply=state['ply_count'], side_to_move=query['seat'],
                            terminal=record_value(session.result))
            full_key = digest(identity)
            if full_key not in by_full_context:
                by_full_context[full_key] = {'context': Context(None, identity, tuple(action_to_dict(a) for a in legal)),
                                             'queries': []}
            elif by_full_context[full_key]['context'].legal_actions != tuple(action_to_dict(a) for a in legal):
                raise ValueError('same full context has different literal frontier')
            positions[(game['fingerprint'], digest(state['position']))].add(full_key)
            pv_key = (full_key, digest(pv))
            if verify_pvs and pv_key not in pv_cache:
                replay = GameSession.replay(session.compiled, session.to_record())
                for move in pv:
                    matches = [a for a in replay.legal_actions() if record_value(a) == move]
                    if len(matches) != 1:
                        raise ValueError('saved PV continuation not a literal legal move')
                    replay.submit(matches[0])
                    counts['unique_PV_plies_replayed'] += 1
                pv_cache[pv_key] = dict(length=len(pv), final_session_result=record_value(replay.result))
                counts['unique_saved_PV_entries_checked'] += 1
                counts['unique_nonempty_saved_PVs_replayed'] += int(bool(pv))
            counts['saved_PV_occurrence_plies'] += len(pv)
            counts['empty_PV_returns'] += int(not pv)
            item = dict(query_id=qid, game_id=game_id, case_id=case, policy=policy,
                        full_context_sha256=full_key, record_before_sha256=before_hash,
                        state_sha256=identity['state_sha256'], ply=identity['ply'], actor=query['seat'],
                        position_sha256=digest(state['position']),
                        repetition_counts_sha256=digest(state['repetition_counts']),
                        legal_frontier_sha256=digest(sorted((action_to_dict(a)for a in legal),key=digest)),
                        remaining_rule_plies=session.compiled.max_ply-state['ply_count'],
                        legal_actions=len(legal), forced_action=len(legal)==1,
                        action=canonical, timing_eligible=timing, completed_depth=decision['completed_depth'],
                        PV_plies=len(pv), PV_status='SUPPLIED_LEGAL_LINE' if pv else 'EMPTY_NO_CONTINUATION_SUPPLIED', rule_fingerprint=game['fingerprint'],
                        quality='FORCED_MOVE_REGRET_ZERO' if len(legal)==1 else 'UNKNOWN_ACTION_QUALITY',
                        minimax_value='UNLABELLED')
            by_full_context[full_key]['queries'].append(item)
            query_rows.append(item)
            session.submit(action)
            if digest(record_value(session.to_record())) != query['record_after_sha256']:
                raise ValueError('saved query after-record hash differs')
            counts['saved_actual_actions_replayed'] += 1
            counts['forced_decisions' if len(legal)==1 else 'multi_action_decisions'] += 1
            counts['timing_eligible_decisions'] += int(timing)
        if record_value(session.to_record()) != game['final_record']:
            raise ValueError('full final record differs')
        if record_value(session.result) != game['Session_result'] or record_value(session.state.terminal_status) != game['Core_terminal']:
            raise ValueError('saved terminal result differs')
        if session.result.status.value in ('ongoing', 'no_contest') or game['status'] != 'TERMINAL':
            raise ValueError('unresolved saved game endpoint')
        if type(game['timing_eligible']) is not bool or game['timing_eligible'] != timing_ok:
            raise ValueError('game timing qualification differs')
        game_rows.append(dict(game_id=game_id, case_id=case, long_seat=game['long_seat'],
                              actual_moves=len(game['queries']), timing_eligible=timing_ok,
                              forced_decisions=counts['forced_decisions']-started['forced_decisions'],
                              multi_action_decisions=counts['multi_action_decisions']-started['multi_action_decisions'],
                              result=record_value(session.result)))
        if progress:
            progress(dict(completed_games=len(game_rows), counts=dict(counts)))
    if ids != {int(k) for k in raw_returns} or ids != set(range(len(ids))):
        raise ValueError('unbound original returns or missing query IDs')
    matched = []
    for key, node in by_full_context.items():
        policies = defaultdict(list)
        for query in node['queries']:
            policies[query['policy']].append(query)
        # These deterministic source games have at most one observation of
        # either budget per exact prefix. Reject accidental replication.
        if any(len(v)>1 for v in policies.values()):
            raise ValueError('repeated source policy observation requires explicit weighting')
        if set(policies) == {'long', 'short'}:
            short, long = policies['short'][0], policies['long'][0]
            result = bound_same_context_pairs(node['context'], [], [dict(baseline_action=short['action'],candidate_action=long['action'])])
            matched.append(dict(full_context_sha256=key, case_id=short['case_id'],
                                short_query=short['query_id'], long_query=long['query_id'],
                                same_action=short['action']==long['action'],
                                both_timing_eligible=short['timing_eligible'] and long['timing_eligible'],
                                single_decision_difference_bounds=result['mean_improvement_bounds'],
                                legal_actions=len(node['context'].legal_actions)))
    counts.update(saved_games=len(games), unique_full_decision_contexts=len(by_full_context),
                  matched_long_short_contexts=len(matched),
                  matched_same_action=sum(r['same_action'] for r in matched),
                  matched_changed_action=sum(not r['same_action'] for r in matched),
                  position_groups_with_multiple_full_contexts=sum(len(v)>1 for v in positions.values()))
    qbyid={q['query_id']:q for q in query_rows}
    initial_pairs=[r for r in matched if qbyid[r['short_query']]['ply']==source_rows[r['case_id']]['prefix_length']]
    if len(initial_pairs)!=len(executed['root_ids']):
        raise ValueError('planned initial source root pair missing')
    first_mean=[str(sum((Fraction(r['single_decision_difference_bounds'][j])for r in initial_pairs),Fraction())/len(initial_pairs))for j in (0,1)]
    initial=dict(planned_source_contexts=len(executed['root_ids']),same_actions=sum(r['same_action']for r in initial_pairs),changed_actions=sum(not r['same_action']for r in initial_pairs),mean_single_decision_bounds=first_mean,context_ids=executed['root_ids'],scope='Fixed12source gameplay roots only, not24input contexts or equal-time algorithms. Current and prior TT budget protocol bundled; not policy continuation value.')
    prefix_rows=prefix_stopping_diagnostics(games,matched,query_rows)
    aliases=history_alias_diagnostics(query_rows)
    contrasts=terminal_outcome_contrasts(games,prefix_rows,query_rows)
    return dict(status='PASS',source_commit=SOURCE_COMMIT,counts=dict(counts),games=game_rows,
                prefix_stopping_diagnostics=prefix_rows,
                history_alias_diagnostics=aliases,
                initial_resource_choice_comparison=initial,
                terminal_outcome_contrasts=contrasts,
                matched_prefix_contexts=matched,queries=query_rows,
                source_population_status='EXPOSED_DETERMINISTIC_RESOURCE_CONTROL_TRAJECTORIES',
                unmatched_prefix_scope='Unmatched queries have no counterfactual action observation. Shared-prefix pairs are trajectory-dependent descriptive support, not a preplanned or IID quality sample.',
                scope='All recorded actual actions and supplied PVs checked; terminal game outcomes stay factual, not root/action minimax labels. No off-policy policy-value estimate, new labels/solver/Player/game.',
                new_Player_calls=0,new_solver_calls=0,new_games=0)


def prefix_stopping_diagnostics(games, matched, queries):
    """Exact-record overlap ends after the first differing actual move.

    This is a data identity, not a probabilistic stopping-time correction.
    More agreement delays divergence and mechanically adds overlap rows.
    """
    by_case=defaultdict(list)
    qmap={r['query_id']:r for r in queries}
    for game in games:by_case[game['case_id']].append(game)
    result=[]
    for case,pair in sorted(by_case.items()):
        if len(pair)!=2 or {g['long_seat']for g in pair}!={0,1}:
            raise ValueError('missing full color-pair source denominator')
        a,b=pair
        left=[qmap[q['query_id']]['action']for q in a['queries']]
        right=[qmap[q['query_id']]['action']for q in b['queries']]
        common=0
        for x,y in zip(left,right):
            if x!=y:break
            common+=1
        diverged=common<min(len(left),len(right))
        if not diverged and len(left)!=len(right):
            raise ValueError('equal prefix has inconsistent terminal length')
        actual=[r for r in matched if r['case_id']==case]
        expected=common+int(diverged)
        if len(actual)!=expected or sum(not r['same_action']for r in actual)!=int(diverged):
            raise ValueError('observed overlap violates exact-record prefix identity')
        result.append(dict(case_id=case,game_ids=[a['game_id'],b['game_id']],
                           common_actual_move_prefix=common,observed_matched_contexts=len(actual),
                           divergence_observed=diverged,changed_action_contexts=int(diverged),
                           interpretation='Trajectory-dependent prefix support; not independent matched quality trials'))
    return result


def history_alias_diagnostics(queries):
    """Measure observed lower-information aliases; infer no WDL difference."""
    groups=defaultdict(list)
    for q in queries:
        key=(q['rule_fingerprint'],q['position_sha256'],q['ply'],q['legal_frontier_sha256'])
        groups[key].append(q)
    examples=[];count=0;distinct_counts=0
    for key,rows in groups.items():
        if len({r['full_context_sha256']for r in rows})<2:continue
        count+=1
        count_variation=len({r['repetition_counts_sha256']for r in rows})>1
        distinct_counts+=int(count_variation)
        if len(examples)<8:
            first=rows[0]
            second=next(r for r in rows if r['full_context_sha256']!=first['full_context_sha256'])
            examples.append(dict(first_query=first['query_id'],second_query=second['query_id'],
                                 fingerprint=key[0],position_sha256=key[1],absolute_ply=key[2],
                                 same_legal_frontier=True,different_full_records=True,
                                 repetition_count_maps_differ=count_variation,
                                 action_equal=first['action']==second['action']))
    return dict(same_position_clock_frontier_groups_with_distinct_full_records=count,
                groups_with_distinct_repetition_count_maps=distinct_counts,examples=examples,
                scope='Observed aliasing only: no WDL difference or permission to merge histories. Conservative record identity can distinguish semantically equivalent histories.')


def terminal_outcome_contrasts(games,prefix_rows,qualified_queries):
    """Conditional finite-game regret lower bound, never a local WDL label.

    For V*(h) measured at fixed seat0, every signed step change has magnitude
    equal to that acting player's minimax regret. Telescoping two terminal
    paths from the same full prefix gives sum(regrets on both suffixes) >=
    |terminal0-terminal1|. Different outcomes therefore require some
    nonoptimal action in the suffix union, without identifying which action.
    With policy colors swapped, subtracting fixed-seat terminal outcomes also
    gives EXACT total short-policy actor regret minus long-policy actor regret.
    This re-expresses the SAME source outcome contrast, not independent evidence.
    The caller must first replay both complete paths and qualify finite,
    deterministic, zero-sum, rule-terminal semantics (no caller cutoffs).
    """
    by_case=defaultdict(list)
    for game in games:by_case[game['case_id']].append(game)
    qindex={q['query_id']:q for q in qualified_queries}
    rows=[]
    for prefix in prefix_rows:
        pair=by_case[prefix['case_id']]
        if len(pair)!=2 or {g['long_seat']for g in pair}!={0,1}:
            raise ValueError('terminal contrast requires exactly swapped policy seats')
        a=next(g for g in pair if g['long_seat']==0)
        b=next(g for g in pair if g['long_seat']==1)
        if a['fingerprint']!=b['fingerprint'] or a['initial_record']!=b['initial_record']:
            raise ValueError('terminal contrast has different initial full contexts')
        values=[]
        for game in (a,b):
            core=game['Core_terminal'];session=game['Session_result']
            if core['status']in ('ongoing','no_contest') or session['status']!=core['status'] or session['winner']!=core['winner']:
                raise ValueError('terminal contrast requires actual rule outcomes')
            if any(session.get(k)is not None for k in ('resigned_by','declaration_id','declared_by','declaration_outcome')):
                raise ValueError('external Session ending is not a rule-terminal contrast')
            winner=core['winner']
            if winner is not None and (type(winner)is not int or winner not in (0,1)):
                raise ValueError('invalid terminal winner seat')
            values.append(0 if winner is None else 1 if winner==0 else -1)
        signed_gap=values[0]-values[1]
        difference=abs(signed_gap)
        common=prefix['common_actual_move_prefix']
        actual_common=0
        for left,right in zip(a['queries'],b['queries']):
            if qindex[left['query_id']]['action']!=qindex[right['query_id']]['action']:break
            actual_common+=1
        if common!=actual_common:
            raise ValueError('terminal contrast prefix does not match actual selected actions')
        eligible=all(g['timing_eligible']for g in (a,b))
        suffixes=[q['query_id']for g in (a,b)for q in g['queries'][common:]]
        excess='short'if signed_gap>0 else'long'if signed_gap<0 else None
        candidates=[qid for qid in suffixes if qindex[qid]['policy']==excess and not qindex[qid]['forced_action']]if excess else []
        if difference and not candidates:
            raise ValueError('outcome contrast lacks any non-forced excess-policy suffix decision')
        rows.append(dict(case_id=prefix['case_id'],game_ids=prefix['game_ids'],
                         terminal_values_fixed_seat0=values,absolute_outcome_difference=difference,
                         both_games_timing_eligible=eligible,
                         short_minus_long_total_actor_regret=signed_gap,
                         excess_regret_policy=excess or'NONE_IDENTIFIED',
                         excess_policy_nonforced_suffix_candidates=candidates,
                         candidate_count=len(candidates),
                         excess_regret_policy_nonoptimal_decisions_lower_bound=(difference+1)//2,
                         total_actor_regret_lower_bound=difference,
                         nonoptimal_suffix_decisions_lower_bound=int(difference>0),
                         suffix_query_union=suffixes,local_action_labels=0,root_WDL='UNKNOWN',
                         conclusion='EXISTS_NONOPTIMAL_SUFFIX_DECISION'if difference else'NO_POSITIVE_LOWER_BOUND',
                         scope='Conditional on verified finite deterministic WDL game; mathematical lower bound only. Equal outcomes do not prove zero regret; actors/actions and policy strength are unidentified.'))
    return dict(rows=rows,planned_color_pairs=len(rows),
                differing_outcome_pairs=sum(r['absolute_outcome_difference']>0 for r in rows),
                timing_eligible_color_pairs=sum(r['both_games_timing_eligible']for r in rows),
                timing_eligible_differing_outcome_pairs=sum(r['both_games_timing_eligible']and r['absolute_outcome_difference']>0 for r in rows),
                short_minus_long_total_actor_regret=sum(r['short_minus_long_total_actor_regret']for r in rows),
                timing_eligible_short_minus_long_total_actor_regret=sum(r['short_minus_long_total_actor_regret']for r in rows if r['both_games_timing_eligible']),
                source_action_WDL_labels_created=0)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();tick=time.perf_counter()
    packet,_=load_source(args.source)
    manifest=json.loads((args.source/'manifest.json').read_bytes())
    def read(name):return read_checked(args.source/name,name,manifest)
    inputs=[read(name)for name in ('population-games/games.json.gz','population-games/returns.json.gz','population-budget-frozen.json.gz','population-games/executed-source.json.gz')]
    result=audit_exposure(packet,*inputs,progress=lambda r:print(json.dumps(r),flush=True))
    result['analysis_seconds']=time.perf_counter()-tick
    args.output.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items()if k not in ('queries','games','matched_prefix_contexts')}))


if __name__=='__main__':main()