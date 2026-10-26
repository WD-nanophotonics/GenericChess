"""Offline action-value identification on fixed published Leaper returns.

This consumer does not instantiate a Player or fill missing search slots. It
binds diagnostic Action dataclasses to literal Core actions and keeps one WDL
variable for each full-context/action. Search scores/PVs are never WDL labels.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from fractions import Fraction
import gzip
import hashlib
from itertools import combinations
import json
import math
from pathlib import Path
import time

from generic_chess.core.actions import action_to_dict
from scripts.leaper_truth_compatibility import bind_context, digest, bound_same_context_pairs
from scripts.qualify_primary_leaper_sources import read_checked
from scripts.research_record import record_value

SOURCE_COMMIT = 'fd7d7eacbdc2741e766f26b67b0f54018a998aa7'
MANIFEST_SHA256 = 'b093b65db5fc742063237fda234a0c6f42c614ffca799051d0550f6a1afa7747'
PHASES = {
    'phase1': {'arms': ('baseline', 'scan_hint'), 'depths': (1, 4), 'seconds': 10},
    'phase2': {'arms': ('original', 'record_only', 'work_order'), 'depths': (4, 6), 'seconds': 20},
}


def literal_contexts(packet):
    """Bind every source context and its diagnostic-to-canonical action map."""
    contexts = {}
    maps = {}
    for row in packet['rows']:
        key = row['id']
        if key in contexts:
            raise ValueError('duplicate source context ID')
        context = bind_context(row['RuleSet'], row['record'])
        if context.identity['ruleset_fingerprint'] != row['fingerprint']:
            raise ValueError('source fingerprint differs')
        if record_value(context.session.state) != row['root']:
            raise ValueError('full source state differs')
        if record_value(context.session.to_record()) != row['record']:
            raise ValueError('full source record differs')
        if context.identity['ply'] != row['prefix_length']:
            raise ValueError('source clock differs')
        if type(row['terminal']) is not bool or row['terminal']:
            raise ValueError('expected ongoing source context')
        if context.identity['terminal']['status'] != 'ongoing':
            raise ValueError('source Session already ended')
        action_map = {digest(record_value(a)): action_to_dict(a)
                      for a in context.session.legal_actions()}
        source_actions = [digest(a) for a in row['legal_actions']]
        if len(source_actions) != len(set(source_actions)) or set(source_actions) != set(action_map):
            raise ValueError('source legal frontier differs')
        contexts[key] = context
        maps[key] = action_map
    if not contexts:
        raise ValueError('empty input contexts')
    identities = [digest(c.identity) for c in contexts.values()]
    if len(set(identities)) != len(identities):
        raise ValueError('duplicate full contexts need explicit planned weights')
    return contexts, maps


def qualify_returns(rows, phase, contexts, action_maps):
    """Missing/failed returns remain slots; malformed returned claims reject.

    Completion, call-budget eligibility, legality and quality are separate.
    A returned legal action from an incomplete iteration is still an actual
    selected action, but cannot support a same-completed-depth comparison.
    """
    spec = PHASES[phase]
    expected = {(case, depth, arm) for case in contexts
                for depth in spec['depths'] for arm in spec['arms']}
    qualified = {}
    slot_numbers = set()
    planned_slots = {}
    for i, case in enumerate(contexts):
        for depth in spec['depths']:
            arms = list(spec['arms'])
            if phase == 'phase1':
                if not (i+depth)%2:
                    arms.reverse()
            else:
                shift = (i+depth)%len(arms)
                arms = arms[shift:]+arms[:shift]
            for arm in arms:
                planned_slots[(case, depth, arm)] = len(planned_slots)
    for row in rows:
        if type(row['requested_depth']) is not int:
            raise ValueError('requested depth must be integer')
        key = (row['case_id'], row['requested_depth'], row['arm'])
        if key not in expected:
            raise ValueError('return outside frozen planned context/depth/arm')
        if key in qualified:
            raise ValueError('duplicate planned return')
        slot = row['slot']
        if type(slot) is not int or slot < 0 or slot >= len(expected) or slot in slot_numbers:
            raise ValueError('invalid/duplicate planned slot number')
        if slot != planned_slots[key]:
            raise ValueError('slot does not match frozen rotation schedule')
        slot_numbers.add(slot)
        if row['status'] not in {'RETURNED','ERROR','NOT_RUN','INELIGIBLE_RETAINED'}:
            raise ValueError('unrecognized source return status')
        entry = {'slot': slot, 'source_status': row['status'], 'action': None,
                 'completion_eligible': False, 'nominal_outer_limit_diagnostic': False}
        if row['status'] == 'RETURNED':
            case, depth, _ = key
            fp = row.get('input_fingerprint', row.get('fingerprint'))
            if fp != contexts[case].identity['ruleset_fingerprint']:
                raise ValueError('returned fingerprint differs')
            decision = row['decision']
            action_key = digest(decision.get('action'))
            if action_key not in action_maps[case]:
                raise ValueError('returned selected action is not literal legal action')
            if decision.get('choice_kind') != 'ACTION' or decision.get('declaration') is not None:
                raise ValueError('unsupported selected choice')
            pv = decision['principal_variation']
            if pv and pv[0] != decision['action']:
                raise ValueError('saved PV does not start with selected action')
            if row.get('root_unchanged') is not True or row.get('pv_legal') is not True:
                raise ValueError('source return lacks basic replay qualification')
            completed = decision['completed_depth']
            if type(completed) is not int or completed < 0 or completed > depth:
                raise ValueError('invalid completed depth')
            elapsed = row['outer_seconds']
            if type(elapsed) not in (int, float) or not math.isfinite(elapsed) or elapsed < 0:
                raise ValueError('invalid full-call elapsed time')
            entry.update(action=action_maps[case][action_key],
                         completion_eligible=completed == depth and decision['termination_reason'] == 'completed_depth',
                         nominal_outer_limit_diagnostic=elapsed <= spec['seconds'],
                         completed_depth=completed, outer_seconds=elapsed,
                         saved_score=decision['score'], saved_pv_length=len(pv),
                         PV_scope='SOURCE_LEGALITY_CLAIM' if pv else 'EMPTY_NO_CONTINUATION_SUPPLIED',
                         score_authority='HEURISTIC_SEARCH_OUTPUT_NOT_WDL',
                         execution_input_authority='PUBLISHED_DRIVER_INPUT_BINDING_CLAIM;TARGET_CONTEXT_REPLAY_CHECKED',
                         timing_scope='Outer elapsed <= nominal INNER search limit is descriptive only; no new formal timing qualification')
        qualified[key] = entry
    for key in expected - qualified.keys():
        qualified[key] = {'slot': None, 'source_status': 'MISSING', 'action': None,
                          'completion_eligible': False, 'nominal_outer_limit_diagnostic': False}
    return qualified


def summarize_comparison(contexts, metadata, qualified, baseline, candidate, baseline_depth, candidate_depth):
    """Equal planned source-context weights, plus explicit rule/family groups.

    The root-side value refers to ONE selected action followed by minimax play,
    not the policies' future play. Missing slots contribute the full [-2,2].
    """
    result = []
    totals = Counter()
    for case, context in contexts.items():
        before = qualified[(case, baseline_depth, baseline)]
        after = qualified[(case, candidate_depth, candidate)]
        pair = {'baseline_action': before['action'], 'candidate_action': after['action']}
        bounds = bound_same_context_pairs(context, [], [pair])
        same = before['action'] is not None and before['action'] == after['action']
        eligible = before['completion_eligible'] and after['completion_eligible']
        timed = before['nominal_outer_limit_diagnostic'] and after['nominal_outer_limit_diagnostic']
        # Recompute each eligibility estimand without dropping its planned slot.
        qualified_pair = pair if eligible else {}
        timing_pair = pair if eligible and timed else {}
        completed_bounds = bound_same_context_pairs(context, [], [qualified_pair])
        timing_bounds = bound_same_context_pairs(context, [], [timing_pair])
        m = metadata[case]
        row = dict(case_id=case, full_context_sha256=digest(context.identity),
                   observed_single_decision_defined=before['action'] is not None and after['action'] is not None,
                   missing_slot_scope='A missing/failed return has no observed legal-action value; [-2,2] bounds possible legal completions, never an assigned WDL or protocol utility',
                   rule_fingerprint=context.identity['ruleset_fingerprint'],
                   family=m['family'], board_size=m['n'], actor=context.identity['side_to_move'],
                   baseline=before, candidate=after, same_action=same,
                   completed_pair=eligible, nominal_outer_limit_pair=eligible and timed,
                   actual_choice_bounds=bounds['mean_improvement_bounds'],
                   completed_depth_bounds=completed_bounds['mean_improvement_bounds'],
                   nominal_outer_limit_bounds=timing_bounds['mean_improvement_bounds'],
                   action_quality='UNKNOWN_NO_MATCHING_TRUTH')
        result.append(row)
        totals['planned_pairs'] += 1
        totals['matched_legal_pairs'] += int(before['action'] is not None and after['action'] is not None)
        totals['same_action_pairs'] += int(same)
        totals['changed_action_pairs'] += int(before['action'] is not None and after['action'] is not None and not same)
        totals['completed_pairs'] += int(eligible)
        totals['nominal_outer_limit_pairs'] += int(eligible and timed)
    def average(rows, field):
        return [str(sum((Fraction(r[field][j]) for r in rows), Fraction()) / len(rows)) for j in (0, 1)]
    def group_by(field):
        groups = defaultdict(list)
        for row in result:
            groups[str(row[field])].append(row)
        return [dict(group=key, planned_pairs=len(rows),
                     mean_bounds=average(rows, 'actual_choice_bounds'),
                     same_actions=sum(r['same_action'] for r in rows))
                for key, rows in sorted(groups.items())]
    return dict(baseline=baseline, candidate=candidate,
                baseline_depth=baseline_depth, candidate_depth=candidate_depth,
                counts=dict(totals), mean_bounds=average(result, 'actual_choice_bounds'),
                completed_depth_mean_bounds=average(result, 'completed_depth_bounds'),
                nominal_outer_limit_mean_bounds=average(result, 'nominal_outer_limit_bounds'),
                by_full_rule=group_by('rule_fingerprint'), by_family=group_by('family'),
                rows=result, qualification='EXACT_ARITHMETIC_OVER_UNLABELLED_FULL_CONTEXT_ACTIONS',
                scope='Fixed planned source contexts; interval outer bounds, no IID/confidence/strength/holdout claim. Comparison depths remain explicit.')


def analyze(packet, phase_rows):
    contexts, maps = literal_contexts(packet)
    metadata = {r['id']: r for r in packet['rows']}
    phase_results = {}
    for phase, rows in phase_rows.items():
        qualified = qualify_returns(rows, phase, contexts, maps)
        spec = PHASES[phase]
        comparisons = [summarize_comparison(contexts, metadata, qualified, a, b, depth, depth)
                       for a, b in combinations(spec['arms'], 2) for depth in spec['depths']]
        # Descriptive depth sensitivity on the source baseline; never a new
        # algorithm comparison and never a score-based claim of improvement.
        base = spec['arms'][0]
        depth = summarize_comparison(contexts, metadata, qualified, base, base, *spec['depths'])
        phase_results[phase] = dict(planned_returns=len(qualified), observed_returns=len(rows),
                                   statuses=dict(Counter(r['source_status'] for r in qualified.values())),
                                   same_depth_comparisons=comparisons,
                                   baseline_depth_diagnostic=depth)
    return dict(source_commit=SOURCE_COMMIT, status='PASS',
                available_source_status='AVAILABLE_SOURCE_NOT_ASSIGNED',
                contexts=len(contexts), rules=len({c.identity['ruleset_fingerprint'] for c in contexts.values()}),
                unlabelled_legal_actions=sum(len(c.legal_actions) for c in contexts.values()),
                phases=phase_results, new_Player_calls=0, new_solver_calls=0, new_games=0,
                scope='Saved fixed-depth choices only, not equal-wall algorithm quality. Complete planned denominators retained. Same actions imply equal single-decision values, not optimality.')


def load_source(directory):
    directory = Path(directory)
    manifest_bytes = (directory/'manifest.json').read_bytes()
    if hashlib.sha256(manifest_bytes).hexdigest() != MANIFEST_SHA256:
        raise ValueError('manifest is not the fixed published source revision')
    manifest = json.loads(manifest_bytes)
    def read(name):
        return read_checked(directory/name, name, manifest)
    packet = read('prepared-v2/inputs.json.gz')
    decoded = gzip.decompress((directory/'prepared-v2/inputs.json.gz').read_bytes())
    input_hash = hashlib.sha256(decoded).hexdigest()
    rows = {}
    for phase, spec in PHASES.items():
        freeze = read(phase+'-frozen.json.gz')
        frozen_hash = freeze['inputs_sha256'] if phase == 'phase1' else freeze['input_sha256']
        if frozen_hash != input_hash or tuple(freeze['requested_depths']) != spec['depths']:
            raise ValueError('frozen input bytes/depths differ')
        planned = len(packet['rows']) * len(spec['arms']) * len(spec['depths'])
        if freeze.get('planned_Player_slots', freeze.get('max_attempts')) != planned:
            raise ValueError('frozen planned slot count differs')
        rows[phase] = read(phase+'/queries.json.gz')
        summary = read(phase+'/summary.json.gz')
        if summary['slots'] != planned or summary['attempts'] != len(rows[phase]):
            raise ValueError('source summary planned/actual slot count differs')
        if Counter(r['status'] for r in rows[phase]) != summary['statuses']:
            raise ValueError('source summary status counts differ')
    return packet, rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    tick = time.perf_counter()
    packet, rows = load_source(args.source)
    result = analyze(packet, rows)
    result['analysis_seconds'] = time.perf_counter()-tick
    args.output.parent.mkdir(parents=True, exist_ok=True)
    result['source_manifest_sha256'] = MANIFEST_SHA256
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False)+'\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in result.items() if k != 'phases'}))


if __name__ == '__main__':
    main()