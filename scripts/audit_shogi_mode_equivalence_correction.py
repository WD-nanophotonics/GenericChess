"""Only the four unexecuted custody controls after metadata-interface failure."""
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

from generic_chess.core.actions import action_source_square, action_target_square
from generic_chess.core.coordinates import Square
from generic_chess.core.pieces import Piece
from generic_chess.core.semantic_executor import semantic_engine_for, _semantic_public_action
from generic_chess.core.transition import initial_state
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from scripts.audit_exchange_custody import synthetic_state
from scripts.audit_mode_equivalence import rotate
from scripts.audit_resource_mode_feasibility import canonical_choice
from scripts.owned_tag_trace import trace_tag
from scripts.public_goal_intervals import PublicGame

FAILED_SOURCE_SHA = '51495b04e3367a29d3a3db8f3e2663b20caf3b854bf33df78108f1da217b392f'


def audit():
    started = monotonic(); enumerated = 0; transitions = 0; rows = []
    def checkpoint():
        if monotonic()-started >= 8:
            raise TimeoutError('remaining conservative8-second correction cap')
    if hashlib.sha256((ROOT/'scripts/audit_mode_equivalence.py').read_bytes()).hexdigest() != FAILED_SOURCE_SHA:
        raise ValueError('first failure source must remain immutable')
    rules = build_standard_shogi_ruleset(); types = {p.type_id: p for p in rules.piece_types}
    if types['G'].movement_atoms != types['TP'].movement_atoms:
        raise ValueError('source Gold geometry equivalence missing')
    compiled = compile_ruleset_for_execution(rules); game = PublicGame(compiled); engine = semantic_engine_for(compiled)
    for owner in (0, 1):
        held = []
        for base, current in (('G', 'G'), ('P', 'TP')):
            checkpoint(); board = [None]*81
            board[0] = Piece(0, 'K', 'K'); board[80] = Piece(1, 'K', 'K')
            board[40] = Piece(0, 'R', 'R'); board[49] = Piece(1, base, current, base != current)
            position = replace(initial_state(compiled).position, board=tuple(board))
            if owner:
                position = rotate(position)
            state = synthetic_state(compiled, position); actions = {}; bindings = {}
            for action in game.actions(state, checkpoint):
                checkpoint(); enumerated += 1; key = canonical_choice(action)
                if key in actions or len(actions) >= 128 or enumerated > 1024:
                    raise ValueError('correction complete-choice cap/duplicate')
                actions[key] = action
            for runtime, binding in engine.iter_legal_action_bindings(position, checkpoint=checkpoint):
                checkpoint(); enumerated += 1; key = canonical_choice(_semantic_public_action(engine, runtime))
                if key in bindings or len(bindings) >= 128 or enumerated > 1024:
                    raise ValueError('correction binding cap/duplicate')
                bindings[key] = (runtime, binding)
            if actions.keys() != bindings.keys():
                raise ValueError('correction binding/public mismatch')
            target = Square(4, 5) if owner == 0 else Square(4, 3)
            matches = [key for key, action in actions.items() if action_source_square(action) == Square(4, 4)
                       and action_target_square(action) == target and getattr(action, 'promotion_target_id', None) is None]
            if len(matches) != 1 or transitions >= 4:
                raise ValueError('unique declared capture/four-transition cap')
            key = matches[0]; final = game.successor(state, actions[key]); transitions += 1; checkpoint()
            victim = 49 if owner == 0 else 31
            tag = {'owner': 1-owner, 'base': base, 'board': {victim: Fraction(1)}, 'held': 0, 'lost': 0}
            runtime, binding = bindings[key]
            lost = trace_tag(engine, position, final.position, runtime, binding, tag)
            hand = dict(final.position.hands[owner].items())
            if lost['lost'] != 1 or hand != {base: 1} or len(final.history) != 2:
                raise AssertionError('declared custody/history control refuted')
            rows.append({'owner': owner, 'victim_base': base, 'victim_current': current,
                         'choices': len(actions), 'capture': key, 'held_after': hand,
                         'victim_tag_lost': '1', 'history_length': len(final.history)})
            held.append(hand)
        if held != [{'G': 1}, {'P': 1}]:
            raise AssertionError('geometry-only merge conceals custody difference')
    paths = ['docs/research/MODE_EQUIVALENCE_PROTOCOL.md', 'docs/research/MODE_EQUIVALENCE_CORRECTION.md',
             'scripts/audit_mode_equivalence.py', 'scripts/audit_shogi_mode_equivalence_correction.py',
             'scripts/owned_tag_trace.py', 'generic_chess/rules/standard_shogi.py']
    return {'complete': True, 'scope': 'targeted previously-unexecuted Shogi custody controls only',
            'controls': rows, 'public_transitions': transitions, 'enumerated_choices': enumerated,
            'prior_chess_transitions': 112, 'combined_public_transitions': 112+transitions,
            'elapsed_seconds': monotonic()-started,
            'sha256': {p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths}}


if __name__ == '__main__':
    result = audit()
    if len(sys.argv) > 1:
        (ROOT/sys.argv[1]).write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8', newline='\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'sha256'}, indent=2))
