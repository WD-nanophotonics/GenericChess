"""Frozen local-service count transfer; no material or global-task claim."""
from dataclasses import replace
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import sys
from time import monotonic

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from generic_chess.core.actions import action_from_dict
from generic_chess.core.pieces import Piece
from generic_chess.core.transition import apply_action, initial_state
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from scripts.local_capture_service import service_labels
from scripts.audit_exchange_custody import synthetic_state
from scripts.audit_f24f_western_chess_perft import standard_engine, position_from_fen
from scripts.audit_post_capture_scope import state_evidence
from scripts.audit_secured_exchange_common_context import Budget

INPUT = ROOT / 'docs/research/data/local_service_corpus_20261004.json'
INPUT_SHA = '9a884ed33633c070b4e5d045bf48617c8d5a34c82384b8354ff62d7c72224cc4'
PROTOCOL = ROOT / 'docs/research/LOCAL_SERVICE_VALIDATION_PROTOCOL.md'
PROTOCOL_SHA = '557648f17693906a176f0813fe250439c5115e74b1ecd3fdce4d44acfd07d567'
IMPLEMENTATION = ROOT / 'docs/research/LOCAL_SERVICE_LABEL_IMPLEMENTATION.md'
IMPLEMENTATION_SHA = 'dd7f2ca25ab6cfa29bf9a2e8f0b97a7f2ad381727605a783f9bb8d35c7ce419a'


def load_root(compiled, game, evidence):
    template = position_from_fen('8/8/8/8/8/8/8/8 w - - 0 1', compiled) if game == 'chess' else initial_state(compiled).position
    position = replace(template, board=tuple(None if p is None else Piece(*p) for p in evidence['physical_board']),
                       side_to_move=evidence['side_to_move'])
    state = synthetic_state(compiled, position)
    if state_evidence(state, compiled) != evidence:
        raise ValueError('full synthetic root evidence mismatch')
    return state


def count_risks(rows, coefficients, constant):
    if not rows:
        raise ValueError('empty deployment is not zero risk')
    predictions = [sum((n * coefficients[t] for t, n in row['counts'].items()), Fraction()) for row in rows]
    y = [row['actor_success_count'] for row in rows]
    risks = {name: sum(((target - prediction)**2 for target, prediction in zip(y, values)), Fraction()) / len(rows)
             for name, values in (('candidate', predictions), ('zero', [Fraction()] * len(rows)),
                                  ('constant', [constant] * len(rows)))}
    positive = risks['zero'] > 0 and risks['constant'] > 0
    passed = bool(any(coefficients.values()) and positive and all(
        risks['candidate'] <= Fraction(9, 10) * risks[b] for b in ('zero', 'constant')))
    return {'predictions': list(map(str, predictions)), 'risks': {k: str(v) for k, v in risks.items()},
            'positive_baseline_risks': positive, 'finite_gate_passed': passed}


def run(reference_output, budget=None):
    for path, expected in ((INPUT, INPUT_SHA), (PROTOCOL, PROTOCOL_SHA), (IMPLEMENTATION, IMPLEMENTATION_SHA)):
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError('frozen corpus or label protocol changed')
    corpus = json.loads(INPUT.read_text())
    if not corpus['complete']:
        raise ValueError('incomplete corpus cannot be labelled')
    budget = budget or Budget(seconds=30, transitions_limit=60_000)
    games = {'chess': standard_engine()[0], 'shogi': compile_ruleset_for_execution(build_standard_shogi_ruleset())}
    references = {}
    roots = 0
    for game, compiled in games.items():
        entry = corpus['games'][game]
        if len(entry['reference']) != 4:
            raise ValueError('frozen reference coverage changed')
        labels = []
        for evidence in entry['reference']:
            state = load_root(compiled, game, evidence)
            labels.append(service_labels(compiled, state, budget)); roots += 1
        n = entry['initial_counts']
        v = {t: sum(row['types'][t]['successful'] for row in labels) / Fraction(4 * count)
             for t, count in n.items()}
        constant = sum((n[t] * value for t, value in v.items()), Fraction())
        references[game] = {'labels': labels, 'coefficients': {t: str(value) for t, value in v.items()},
                            'constant': str(constant), 'nonzero_signal': any(v.values())}
    reference_data = {'input_sha256': INPUT_SHA, 'protocol_sha256': PROTOCOL_SHA,
                      'program_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                      'helper_sha256': hashlib.sha256((ROOT / 'scripts/local_capture_service.py').read_bytes()).hexdigest(),
                      'games': references, 'materialized_transitions': budget.transitions}
    budget.checkpoint()
    reference_output = Path(reference_output)
    reference_output.write_text(json.dumps(reference_data, indent=2) + '\n', encoding='utf-8', newline='\n')
    reference_hash = hashlib.sha256(reference_output.read_bytes()).hexdigest()
    result = {'input_sha256': INPUT_SHA, 'protocol_sha256': PROTOCOL_SHA,
              'implementation_sha256': IMPLEMENTATION_SHA, 'program_sha256': reference_data['program_sha256'],
              'helper_sha256': reference_data['helper_sha256'], 'reference_sha256': reference_hash, 'games': {}}
    for game, compiled in games.items():
        reference = references[game]
        if not reference['nonzero_signal']:
            result['games'][game] = {'deployment_labelled': False, 'finite_gate_passed': False,
                                     'reason': 'all-zero reference signal; deployment labels not read'}
            continue
        labels = []
        entry = corpus['games'][game]
        if len(entry['deployment']) != len(entry['initial_counts']):
            raise ValueError('deployment coverage changed')
        for deployment in entry['deployment']:
            selected = deployment['selected']
            parent = load_root(compiled, game, selected['parent'])
            budget.checkpoint()
            if budget.transitions >= budget.transitions_limit:
                raise RuntimeError('public replay transition cap')
            child = apply_action(parent, action_from_dict(selected['selected_action']), compiled)
            budget.transitions += 1
            if state_evidence(child, compiled) != selected['child']:
                raise ValueError('actual capture child evidence mismatch')
            labels.append({'victim_type': deployment['victim_type'], **service_labels(compiled, child, budget)})
            roots += 1
            if roots > 20:
                raise ValueError('frozen root cap')
        risks = count_risks(labels, {t: Fraction(v) for t, v in reference['coefficients'].items()}, Fraction(reference['constant']))
        result['games'][game] = {'deployment_labelled': True, 'labels': labels, **risks}
    budget.checkpoint()
    result.update({'reference_complete': True, 'all_deployment_labelled': all(r['deployment_labelled'] for r in result['games'].values()),
                   'finite_gate_passed': all(r['finite_gate_passed'] for r in result['games'].values()),
                   'roots_labelled': roots, 'materialized_transitions': budget.transitions,
                   'elapsed_seconds': monotonic() - budget.started})
    return result


if __name__ == '__main__':
    result = run(sys.argv[1])
    Path(sys.argv[2]).write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps({**{k: v for k, v in result.items() if k != 'games'},
                      'games': {g: {k: v for k, v in row.items() if k != 'labels'} for g, row in result['games'].items()}}, indent=2))
