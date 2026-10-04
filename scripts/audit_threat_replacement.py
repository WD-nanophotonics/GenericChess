"""A removed intrinsic attack edge need not produce net protection."""
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import sys
from time import monotonic

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from generic_chess.core.actions import action_source_square, action_target_square, action_to_dict
from generic_chess.core.coordinates import Square
from generic_chess.core.movegen import iter_legal_actions
from generic_chess.core.semantic_executor import semantic_engine_for
from generic_chess.core.transition import apply_action
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.western_chess import build_western_chess_ruleset
from scripts.audit_exchange_custody import synthetic_state
from scripts.audit_f24f_western_chess_perft import position_from_fen
from scripts.audit_physical_placement_sampling import serialize_board
from scripts.intrinsic_action_events import collect_intrinsic_board_events

PROTOCOL = 'docs/research/THREAT_REPLACEMENT_WITNESS_PROTOCOL.md'
PROTOCOL_SHA = '6993b9b71aa6c8fb92000b907841bf9f0a86bcb238c87d3fc91e812a4e656819'
FENS = {'replacement': '3r3k/8/8/8/8/1b1R4/8/K2N4 w - - 0 1',
        'control': '7k/8/8/8/8/1b1R4/8/K2N4 w - - 0 1'}


def intrinsic_sources(compiled, position, owner, target, ledger):
    """Read board-removal eligibility with full occupancy, excluding dynamic safety."""
    victim = position.board[target]
    if victim is None or victim.owner == owner:
        raise ValueError('enemy protected entity required')
    sources = set()
    for source, piece in enumerate(position.board):
        if piece is None or piece.owner != owner:
            continue
        audit = ledger(piece.current_type_id)
        if not audit['coverage_complete']:
            raise ValueError('unsupported intrinsic semantics')
        for key, cubes in audit['events'].items():
            if key[0] != owner or key[2] != source or not any(s == target for s, _ in key[5]):
                continue
            def holds(cube):
                for square, allowed in cube:
                    occupying = position.board[square]
                    label = 'empty' if occupying is None else 'own' if occupying.owner == owner else 'enemy'
                    if label not in allowed:
                        return False
                return True
            if any(holds(cube) for cube in cubes):
                sources.add(source)
    return sorted(sources)


def audit():
    started = monotonic()

    def checkpoint():
        if monotonic() - started > 10:
            raise TimeoutError('10-second physical witness cap')

    if hashlib.sha256((ROOT / PROTOCOL).read_bytes()).hexdigest() != PROTOCOL_SHA:
        raise ValueError('frozen witness protocol changed')
    compiled = compile_ruleset_for_execution(build_western_chess_ruleset())
    engine = semantic_engine_for(compiled)

    @lru_cache(maxsize=None)
    def ledger(type_id):
        checkpoint()
        return collect_intrinsic_board_events(compiled, type_id, max_candidates=100_000)

    transitions = 0
    def chosen(state, source, target):
        actions = []
        total = 0
        for action in iter_legal_actions(state, compiled, checkpoint=checkpoint):
            total += 1
            if total > 128:
                raise RuntimeError('public choice cap exceeded')
            if action_source_square(action) == source and action_target_square(action) == target:
                actions.append(action)
        if len(actions) != 1:
            raise ValueError('unique declared public action missing')
        return actions[0], total

    def child(state, action):
        nonlocal transitions
        checkpoint()
        if transitions >= 3:
            raise RuntimeError('three-transition cap exceeded')
        transitions += 1
        result = apply_action(state, action, compiled)
        checkpoint()
        return result

    rows = {}
    for name, fen in FENS.items():
        state = synthetic_state(compiled, position_from_fen(fen, compiled))
        if state.terminal_status.is_terminal or any(engine.in_check(state.position, o) for o in (0, 1)):
            raise ValueError('fixture must be ongoing with neither anchor checked')
        before = intrinsic_sources(compiled, state.position, 1, 3, ledger)
        if before != [17] or not engine.is_square_attacked(state.position, 3, 1):
            raise AssertionError('expected bishop-only pre-capture threat absent')
        action, choices = chosen(state, Square(3, 2), Square(1, 2))
        after_state = child(state, action)
        if after_state.position.board[3] != state.position.board[3]:
            raise AssertionError('protected entity changed')
        after = intrinsic_sources(compiled, after_state.position, 1, 3, ledger)
        expected = [59] if name == 'replacement' else []
        if after != expected or bool(after) != engine.is_square_attacked(after_state.position, 3, 1):
            raise AssertionError('compiled/public pseudo-exposure mismatch')
        row = {'fen': fen, 'capture': action_to_dict(action), 'legal_root_choices': choices,
               'before_sources': before, 'after_sources': after,
               'removed_edge_opportunity': 1, 'exposure_delta': int(bool(before)) - int(bool(after)),
               'before_board': serialize_board(state.position), 'after_board': serialize_board(after_state.position),
               'history_lengths': [len(state.history), len(after_state.history)]}
        if name == 'replacement':
            reply, replies = chosen(after_state, Square(3, 7), Square(3, 0))
            lost = child(after_state, reply)
            if lost.position.board[3] is None or lost.position.board[3].owner != 1:
                raise AssertionError('replacement reply did not remove protected token')
            row.update(replacement_reply=action_to_dict(reply), legal_reply_choices=replies,
                       reply_board=serialize_board(lost.position), reply_history_length=len(lost.history))
        rows[name] = row
    paths = [PROTOCOL, 'scripts/audit_threat_replacement.py', 'scripts/intrinsic_action_events.py',
             'generic_chess/rules/western_chess.py', 'generic_chess/rules/compiler.py',
             'generic_chess/core/semantic_executor.py', 'generic_chess/core/transition.py']
    checkpoint()
    return {'complete': True, 'scope': 'hand-built physical exposure witness, not deployment/WDL',
            'ruleset_fingerprint': compiled.ruleset_fingerprint, 'public_transitions': transitions,
            'sha256': {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in paths},
            'fixtures': rows, 'elapsed_seconds': monotonic() - started}


if __name__ == '__main__':
    result = audit()
    if len(sys.argv) > 1:
        Path(sys.argv[1]).write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps({'complete': result['complete'], 'public_transitions': result['public_transitions'],
                     'elapsed_seconds': result['elapsed_seconds'],
                     'fixtures': {n: {k: v for k, v in r.items() if 'board' not in k}
                                  for n, r in result['fixtures'].items()}}, indent=2))
