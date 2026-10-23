"""One bounded existential Core path probe, never a minimax or absence proof.

Inputs are existing complete histories. Position repeats along a proposed
path may be cut only in the admitted plain-Leaper scope; Core still executes
every edge with the actual prehistory, repetition and rule clock. A failed
bounded search is UNKNOWN. No graph cache, new rule/layout or Player is used.
"""
from __future__ import annotations

import argparse
import time

from generic_chess.core.actions import action_to_dict, action_from_dict
from generic_chess.core.transition import legal_successors
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution as compile_rule
from scripts.leaper_cooperative_certificate import root_session
from scripts.leaper_cooperative_truth import admit
from scripts.leaper_explorer_truth import load, save, digest, materialize
from scripts.leaper_microgames import role_stop_requested


def search(state, compiled, *, depth, nodes, seconds):
    """Iterative deepening with one shared budget; partial failure stays UNKNOWN."""
    if type(depth) is not int or not 0 <= depth <= 16:
        raise ValueError('depth must be 0..16')
    if type(nodes) is not int or not 1 <= nodes <= 100000:
        raise ValueError('nodes must be 1..100000')
    if type(seconds) not in (int, float) or not 0 < seconds <= 900:
        raise ValueError('seconds must be finite and 0 < seconds <= 900')
    started = time.perf_counter()
    stats = dict(expanded=0, generated_edges=0, terminal_draws=0,
                 repeated_path_positions=0, completed_depth=-1)
    last_stop = 0.

    def guard():
        nonlocal last_stop
        now = time.perf_counter()
        if now-started >= seconds:
            raise TimeoutError('TIME_CAP_UNKNOWN')
        if now-last_stop >= .2:
            last_stop = now
            if role_stop_requested():
                raise TimeoutError('USER_STOP')

    def visit(s, left, seen):
        guard()
        if s.terminal_status.is_terminal:
            if s.terminal_status.winner is not None:
                return [], s.terminal_status.winner
            stats['terminal_draws'] += 1
            return None
        if not left:
            return None
        if stats['expanded'] >= nodes:
            raise TimeoutError('NODE_CAP_UNKNOWN')
        stats['expanded'] += 1
        for ac, child in legal_successors(s, compiled):
            guard()
            stats['generated_edges'] += 1
            # Check decisive terminal BEFORE cycle pruning, just as Core does.
            if not child.terminal_status.is_terminal and child.position in seen:
                stats['repeated_path_positions'] += 1
                continue
            answer = visit(child, left-1, seen | {child.position})
            if answer is not None:
                path, winner = answer
                return [action_to_dict(ac)] + path, winner
        return None

    result = dict(status='DEPTH_CAP_UNKNOWN', cooperative_decisive=None,
                  universal_draw=None, witness=None, terminal_winner=None)
    try:
        for current_depth in range(depth+1):
            found = visit(state, current_depth, {state.position})
            if found is not None:
                path, winner = found
                result.update(status='WITNESS', cooperative_decisive=True,
                              universal_draw=False, witness=path, terminal_winner=winner)
                break
            stats['completed_depth'] = current_depth
    except TimeoutError as error:
        result['status'] = str(error)
    result.update(stats=stats, seconds=time.perf_counter()-started)
    return result


def run(folder, output):
    """Freeze the only missing original initial cooperation target, then try once."""
    from pathlib import Path
    p = Path(folder)
    original = load(p/'truth.json.gz')
    truth = materialize(original, load(p/'cooperative.json'), load(p/'observed-suffixes.json.gz'))
    candidates = sorted((r for r in truth['roots'] if r['ply'] == 0 and
                         r['cooperative_decisive'] is None), key=lambda r: r['id'])
    if not candidates:
        raise ValueError('no missing frozen initial cooperative target')
    row = candidates[0]
    out = Path(output)
    out.mkdir(parents=True, exist_ok=False)
    spec = dict(format='leaper-cooperative-path-probe-v1',
                question='Can the only still-unknown canonical initial cooperative property be witnessed without six-actor graph closure?',
                id=row['id'], fingerprint=row['fingerprint'], truth_digest=digest(original),
                materialized_digest=digest(truth), source_sha='c7e7b84101ee286a4d3bc98a19a33463afd2809d',
                selection='Lexicographically first original ply0 history still unknown after existing suffix/nonzero-WDL/certificate consequences; truth diagnosis only, never TRAIN/layout selection.',
                caps=dict(depth=12, nodes=100000, seconds=300),
                alternative='Keep UNKNOWN; no new graph or forward campaign. A literal Core path suffices for existential cooperation.',
                stop='One attempt under cumulative depth/node/time budget; any unfinished/negative search is UNKNOWN, no refill.',
                scope='Exposed initial history. A positive is not forced WDL, initial fork truth or policy probability.')
    save(out/'spec.json', spec)
    rule = ruleset_from_dict(truth['rules'][row['fingerprint']])
    compiled = compile_rule(rule)
    admit(rule, compiled)
    _, session = root_session(truth, row['id'], compiled)
    answer = search(session.state, compiled, **spec['caps'])
    save(out/'result.json', answer)
    if answer['witness'] is not None:
        # Separate literal Session replay; don't trust the path proposal.
        _, check = root_session(truth, row['id'], compiled)
        for raw in answer['witness']:
            check.submit(action_from_dict(raw))
        assert check.result.winner is not None
        assert check.result.winner == answer['terminal_winner']
        save(out/'verification.json', dict(verified=True, id=row['id'],
             core_edges=len(answer['witness']), winner=check.result.winner,
             result_digest=digest(answer), truth_digest=digest(original)))
    return answer


if __name__ == '__main__':
    cli=argparse.ArgumentParser()
    cli.add_argument('--folder', default='docs/research/data/leaper_explorer_truth_20261023')
    cli.add_argument('--output', required=True)
    args=cli.parse_args()
    print(__import__('json').dumps(run(args.folder,args.output)))
