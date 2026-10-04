"""Frozen finite-reference closure/path diagnostic, not a material estimator."""
from dataclasses import replace
from fractions import Fraction
import hashlib
import json
from pathlib import Path
from random import Random
import sys
from time import monotonic

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from generic_chess.core.declarations import DeclarationAssessment
from generic_chess.core.pieces import Piece
from generic_chess.core.position import Hands, HistoryRecord
from generic_chess.core.semantic_executor import semantic_engine_for, _semantic_public_action
from generic_chess.core.transition import initial_state
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from generic_chess.rules.western_chess import build_western_chess_ruleset
from scripts.audit_resource_mode_feasibility import canonical_choice
from scripts.owned_service_reward import binding_reward, public_child_reward, continuation_prediction
from scripts.owned_tag_trace import trace_tag
from scripts.public_goal_intervals import PublicGame
from scripts.resource_mode_context import resource_ledger, owned_mode_mass

PROTOCOL = 'docs/research/OWNED_H2_PATH_PROTOCOL.md'
PROTOCOL_SHA = '4855c2ad2808c4ba946218b6caaee697606662e132a053334be2c5efe421f8d6'
INPUT = 'docs/research/data/resource_mode_correction_20261004.json'
INPUT_SHA = 'd8c207f33e2951cee2645fbbbad59db5c9eed7040c8ab2f4842729250e6ebaa9'


def restore_root(compiled, row):
    initial = initial_state(compiled)
    position = replace(initial.position,
                       board=tuple(None if p is None else Piece(*p) for p in row['board']),
                       hands=tuple(Hands(tuple(sorted(h.items()))) for h in row['hands']),
                       side_to_move=0, aux_state=tuple((tuple(k), v) for k, v in row['aux_state']))
    state = replace(initial, position=position, ply_count=row['ply_count'],
                    history=tuple(HistoryRecord(**h) for h in row['history']),
                    repetition_counts=tuple(tuple(item) for item in row['repetition_counts']))
    engine = semantic_engine_for(compiled)
    state = replace(state, terminal_status=engine.terminal_result(position, state.ply_count,
                     state.repetition_counts, state.history))
    tag = {**row['tag'], 'board': {int(k): Fraction(v) for k, v in row['tag']['board'].items()},
           'held': Fraction(row['tag']['held']), 'lost': Fraction(row['tag']['lost'])}
    resource_ledger(compiled, position, row['game'], full_chess=True)
    if owned_mode_mass(position, tag, compiled.support.type_metadata) != {tuple(row['mode']): 1}:
        raise ValueError('restored tag does not match frozen root mode')
    return state, tag


class DiagnosticLimit(Exception):
    pass


def audit():
    started = monotonic(); enumerated = 0; transitions = 0; rows = []; refs = []; reason = None
    def checkpoint():
        if monotonic()-started >= 15:
            raise DiagnosticLimit('15-second H2 diagnostic cap')
    for path, expected in ((PROTOCOL, PROTOCOL_SHA), (INPUT, INPUT_SHA)):
        if hashlib.sha256((ROOT/path).read_bytes()).hexdigest() != expected:
            raise ValueError('frozen H2 input changed')
    source = json.loads((ROOT/INPUT).read_text(encoding='utf-8'))
    for ledger in (source['original_source_sha256'], source['sha256']):
        for path, expected in ledger.items():
            if hashlib.sha256((ROOT/path).read_bytes()).hexdigest() != expected:
                raise ValueError('root qualification source changed')

    def tick():
        nonlocal enumerated
        checkpoint(); enumerated += 1
        if enumerated > 5000:
            raise DiagnosticLimit('5000 total enumeration cap')

    def choices(compiled, state, tag):
        game = PublicGame(compiled); engine = semantic_engine_for(compiled)
        if game.terminal(state).is_terminal:
            raise ValueError('cannot enumerate an ended service state')
        public = {}
        for action in game.actions(state, checkpoint):
            tick(); key = canonical_choice(action)
            if key in public:
                raise ValueError('duplicate public choice')
            public[key] = action
            if len(public) > 128:
                raise DiagnosticLimit('128 complete public choices/state cap')
        ordinary = {}; rewards = {}
        for runtime, binding in engine.iter_legal_action_bindings(state.position, checkpoint=checkpoint):
            tick(); key = canonical_choice(_semantic_public_action(engine, runtime))
            if key in ordinary:
                raise ValueError('duplicate semantic binding choice')
            ordinary[key] = (runtime, binding)
            rewards[key] = binding_reward(engine, state.position, runtime, binding, tag)
            if len(ordinary) > 128:
                raise DiagnosticLimit('128 complete binding choices/state cap')
        claims = {key for key, action in public.items() if isinstance(action, DeclarationAssessment)}
        if ordinary.keys() != public.keys()-claims or not public:
            raise ValueError('complete binding/public choice mismatch')
        rewards.update(dict.fromkeys(claims, Fraction(0)))
        mean = sum(rewards.values(), Fraction(0))/len(public)
        return public, ordinary, rewards, mean

    try:
        compiled_games = {'chess': compile_ruleset_for_execution(build_western_chess_ruleset()),
                          'shogi': compile_ruleset_for_execution(build_standard_shogi_ruleset())}
        roots = []; reference = {'chess': {}, 'shogi': {}}
        for row in source['strata']:
            checkpoint(); compiled = compiled_games[row['game']]
            state, tag = restore_root(compiled, row)
            table = choices(compiled, state, tag)
            if set(table[0]) != set(row['canonical_choices']):
                raise ValueError('restored root choices differ from frozen complete table')
            mode = tuple(row['mode']); reference[row['game']][mode] = table[3]
            refs.append({'game': row['game'], 'mode': mode, 'g': str(table[3]),
                         'choices': len(table[0]), 'reward_sum': str(sum(table[2].values(), Fraction(0))),
                         'nonzero_choices': {key: str(q) for key, q in table[2].items() if q}})
            roots.append((row, compiled, state, tag, table))
        for index, (root_row, compiled, state, tag, table) in enumerate(roots):
            checkpoint(); game = PublicGame(compiled); engine = semantic_engine_for(compiled)
            rng = Random(20261004201+index)
            row = {'game': root_row['game'], 'mode': root_row['mode'], 'seed': 20261004201+index,
                   'steps': [], 'complete': False, 'current_reward': '0', 'sampled_second_reward': '0'}
            rows.append(row); endpoint = None
            for ply in range(4):
                checkpoint()
                if ply == 2:
                    mass = owned_mode_mass(state.position, tag, compiled.support.type_metadata)
                    interval = continuation_prediction(mass, reference[root_row['game']])
                    actual = table[3]
                    row.update(second_expected_reward=str(actual),
                               prediction_interval=[str(q) for q in interval],
                               residual_interval=[str(actual-interval[1]), str(actual-interval[0])],
                               surviving_mode_mass={str(m): str(q) for m, q in mass.items()})
                key = rng.choice(sorted(table[0])); action = table[0][key]
                step = {'ply': ply, 'choice': key, 'complete_choices': len(table[0]),
                        'reward': str(table[2][key]), 'parent_history_length': len(state.history)}
                row['steps'].append(step)
                if isinstance(action, DeclarationAssessment):
                    game.terminal(game.successor(state, action))
                    endpoint = 'declared_service_claim_endpoint'; step['claim_outcome'] = action.outcome
                    break
                if transitions >= 24:
                    raise DiagnosticLimit('24 public materialization cap')
                child = game.successor(state, action); transitions += 1; checkpoint()
                runtime, binding = table[1][key]
                controlled = public_child_reward(state.position, child.position, action, tag, compiled.support.type_metadata)
                if controlled != table[2][key]:
                    raise AssertionError('semantic/public-child capture reward mismatch')
                new_tag = trace_tag(engine, state.position, child.position, runtime, binding, tag)
                resource_ledger(compiled, child.position, root_row['game'])
                if len(child.history) != len(state.history)+1:
                    raise ValueError('actual child history did not advance')
                step.update(child_history_length=len(child.history), tag_lost=str(new_tag['lost']),
                            held_mass=str(new_tag['held']), terminal=str(child.terminal_status))
                if ply == 0:
                    row['current_reward'] = str(controlled)
                if ply == 2:
                    row['sampled_second_reward'] = str(controlled)
                state, tag = child, new_tag
                if game.terminal(state).is_terminal:
                    endpoint = 'terminal_service_endpoint'; break
                if tag['lost'] == 1:
                    endpoint = 'ownership_loss'; break
                if ply != 3:
                    table = choices(compiled, state, tag)
            if 'residual_interval' not in row:
                if endpoint is None:
                    raise ValueError('missing H2 continuation observation')
                row.update(second_expected_reward='0', prediction_interval=['0', '0'],
                           residual_interval=['0', '0'], surviving_mode_mass={})
            row.update(complete=True, endpoint=endpoint, final_history_length=len(state.history))
        checkpoint()
    except DiagnosticLimit as exc:
        reason = str(exc)
    paths = [PROTOCOL, INPUT, 'scripts/audit_owned_h2_paths.py', 'scripts/owned_service_reward.py',
             'scripts/resource_mode_context.py', 'scripts/owned_tag_trace.py',
             'scripts/public_goal_intervals.py', 'generic_chess/core/semantic_executor.py',
             'generic_chess/core/transition.py', 'generic_chess/core/declarations.py']
    return {'complete': len(rows) == 6 and all(r['complete'] for r in rows),
            'scope': 'finite-reference sampled H2 closure/path diagnostic; no population prior or goal label',
            'reference': refs, 'paths': rows, 'enumerated_choices': enumerated,
            'public_transitions': transitions, 'stop_reason': reason,
            'elapsed_seconds': monotonic()-started,
            'sha256': {p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths}}


if __name__ == '__main__':
    result = audit()
    if len(sys.argv) > 1:
        (ROOT/sys.argv[1]).write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8', newline='\n')
    print(json.dumps({k: v for k, v in result.items() if k not in ('reference', 'paths', 'sha256')}, indent=2))
    print(json.dumps([{k: v for k, v in r.items() if k != 'nonzero_choices'} for r in result['reference']], indent=2))
    print(json.dumps([{k: v for k, v in r.items() if k != 'steps'} for r in result['paths']], indent=2))
