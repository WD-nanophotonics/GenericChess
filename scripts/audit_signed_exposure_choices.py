"""Signed pseudo-exposure on two actual quiet children of the same root."""
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
from scripts.audit_threat_replacement import intrinsic_sources
from scripts.intrinsic_action_events import collect_intrinsic_board_events

PROTOCOL = 'docs/research/SIGNED_EXPOSURE_CHOICE_PROTOCOL.md'
PROTOCOL_SHA = '81549fbe93ba7c722aa762072db441b6f9077157b0f3a351ffc3edc98c9ede59'


def exposure_changes(compiled, before, after, owner, tracked, ledger):
    """Explicit surviving board entities; no implicit hand/identity matching."""
    if type(owner) is not int or owner not in (0, 1) or not tracked:
        raise ValueError('owner and explicit nonempty tracked identities required')
    old_squares, new_squares, result = set(), set(), {}
    for identity, (old, new) in tracked.items():
        if not isinstance(identity, str) or not identity or old in old_squares or new in new_squares:
            raise ValueError('distinct named physical entities required')
        if (type(old) is not int or type(new) is not int
                or not 0 <= old < len(before.board) or not 0 <= new < len(after.board)):
            raise ValueError('board-only tracked square required')
        old_piece, new_piece = before.board[old], after.board[new]
        if (old_piece is None or new_piece is None or old_piece.owner != owner
                or new_piece.owner != owner or old_piece.base_type_id != new_piece.base_type_id):
            raise ValueError('surviving same-owner/base physical entity required')
        if (compiled.support.type_metadata[old_piece.current_type_id].is_anchor
                or compiled.support.type_metadata[new_piece.current_type_id].is_anchor):
            raise ValueError('ordinary board entities only')
        old_squares.add(old); new_squares.add(new)
        first = intrinsic_sources(compiled, before, 1-owner, old, ledger)
        second = intrinsic_sources(compiled, after, 1-owner, new, ledger)
        result[identity] = {'before_square': old, 'after_square': new,
                            'before_type': old_piece.current_type_id,
                            'after_type': new_piece.current_type_id,
                            'before_sources': first, 'after_sources': second,
                            'signed_delta': int(bool(first))-int(bool(second))}
    # The caller must establish physical mapping from authoritative effects;
    # matching owner/base alone cannot authenticate two indistinguishable tokens.
    return result


def audit():
    started = monotonic()
    def checkpoint():
        if monotonic()-started > 10:
            raise TimeoutError('10-second signed-exposure cap')
    if hashlib.sha256((ROOT/PROTOCOL).read_bytes()).hexdigest() != PROTOCOL_SHA:
        raise ValueError('frozen signed-exposure protocol changed')
    compiled = compile_ruleset_for_execution(build_western_chess_ruleset())
    engine = semantic_engine_for(compiled)
    fen = '3r3k/8/8/8/8/3R4/8/K2N4 w - - 0 1'
    root = synthetic_state(compiled, position_from_fen(fen, compiled))
    if root.terminal_status.is_terminal or any(engine.in_check(root.position, o) for o in (0, 1)):
        raise ValueError('ongoing unchecked root required')
    @lru_cache(maxsize=None)
    def ledger(type_id):
        checkpoint()
        return collect_intrinsic_board_events(compiled, type_id, max_candidates=100_000)
    choices = []
    for action in iter_legal_actions(root, compiled, checkpoint=checkpoint):
        choices.append(action)
        if len(choices) > 128:
            raise RuntimeError('128-choice cap exceeded')
    rows = {}
    for name, destination in (('open', Square(4, 2)), ('screen', Square(3, 1))):
        actions = [a for a in choices if action_source_square(a) == Square(3, 2)
                   and action_target_square(a) == destination]
        if len(actions) != 1:
            raise ValueError('unique declared quiet choice missing')
        checkpoint()
        child = apply_action(root, actions[0], compiled)
        checkpoint()
        target = destination.rank*8 + destination.file
        # This frozen control contains unique own R and N, no hand/promotion
        # or multi-entity movement. Full public effects establish the mapping.
        if (child.position.board[3] != root.position.board[3]
                or child.position.board[target] != root.position.board[19]
                or child.position.board[19] is not None):
            raise AssertionError('declared public identity mapping failed')
        changes = exposure_changes(compiled, root.position, child.position, 0,
                                   {'protected': (3, 3), 'actor': (19, target)}, ledger)
        for row in changes.values():
            for position, prefix in ((root.position, 'before'), (child.position, 'after')):
                if bool(row[prefix+'_sources']) != engine.is_square_attacked(position, row[prefix+'_square'], 1):
                    raise AssertionError('independent pseudo-attack mismatch')
        expected = {'protected': -1, 'actor': 1} if name == 'open' else {'protected': 0, 'actor': 0}
        if {k: v['signed_delta'] for k, v in changes.items()} != expected:
            raise AssertionError('frozen signed-control expectation refuted')
        rows[name] = {'action': action_to_dict(actions[0]), 'entities': changes,
                      'aggregate_exposure_delta': sum(v['signed_delta'] for v in changes.values()),
                      'child_board': serialize_board(child.position),
                      'history_lengths': [len(root.history), len(child.history)]}
    paths = [PROTOCOL, 'scripts/audit_signed_exposure_choices.py', 'scripts/audit_threat_replacement.py',
             'scripts/intrinsic_action_events.py', 'generic_chess/rules/western_chess.py',
             'generic_chess/core/semantic_executor.py', 'generic_chess/core/transition.py']
    checkpoint()
    return {'complete': True, 'scope': 'same-root intrinsic exposure, not material/WDL',
            'fen': fen, 'root_board': serialize_board(root.position), 'legal_choices': len(choices),
            'public_transitions': 2, 'choices': rows,
            'sha256': {p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths},
            'elapsed_seconds': monotonic()-started}


if __name__ == '__main__':
    result = audit()
    if len(sys.argv) > 1:
        Path(sys.argv[1]).write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8', newline='\n')
    print(json.dumps({k: v for k, v in result.items() if k not in ('root_board', 'choices', 'sha256')}, indent=2))
