"""Complete actual actors on two unchanged frozen boards; not type values."""
from collections import Counter
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

from generic_chess.core.actions import action_to_dict
from generic_chess.core.lazy_transitions import iter_legal_successor_handles
from generic_chess.core.pieces import Piece
from generic_chess.core.position import Hands
from generic_chess.core.semantic_executor import semantic_engine_for
from generic_chess.core.transition import initial_state
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from scripts.audit_exchange_custody import custody, synthetic_state
from scripts.audit_f24f_western_chess_perft import standard_engine, position_from_fen
from scripts.audit_secured_exchange_common_context import Budget, task_success

PROTOCOL = ROOT / 'docs/research/ACTUAL_ACTOR_ENUMERATION_PROTOCOL.md'
PROTOCOL_SHA = '93da6368545c317b4baf2331d6c4aefa5caa9b6fc5f51900e3c4d38493b73f1b'
INPUT = ROOT / 'docs/research/data/nonterminal_physical_support_20261003.json'
INPUT_SHA = '801cb8ca48817d4c411eed74e106e76f9cc93b3452234f26b54e20b8874148fc'


def inventory(position):
    return Counter((p.owner, p.base_type_id, p.current_type_id, p.promoted)
                   for p in position.board if p is not None)


def all_actor_labels(compiled, position, budget):
    budget.checkpoint()
    initial = initial_state(compiled).position
    if inventory(position) != inventory(initial) or position.hands != (Hands.empty(), Hands.empty()):
        raise ValueError('actual initial board inventory and empty hands required')
    if position.side_to_move != 0:
        raise ValueError('acting owner must be zero')
    engine = semantic_engine_for(compiled)
    if any(engine.in_check(position, owner, checkpoint=budget.checkpoint) for owner in (0, 1)):
        raise ValueError('quiet actual root required')
    state = synthetic_state(compiled, position)
    if state.terminal_status.is_terminal:
        raise ValueError('nonterminal actual root required')
    anchors = {tid for tid, item in compiled.support.type_metadata.items() if item.is_anchor}
    baseline = custody(position, anchors)
    actors = {square: {'source': [square % compiled.board_size, square // compiled.board_size],
                       'type': p.current_type_id, 'actions': []}
              for square, p in enumerate(position.board)
              if p is not None and p.owner == 0 and p.current_type_id not in anchors}
    for handle in iter_legal_successor_handles(state, compiled, checkpoint=budget.checkpoint):
        source = getattr(handle.action, 'from_square', None)
        square = None if source is None else source.rank * compiled.board_size + source.file
        if square not in actors:
            continue
        child = budget.child(state, handle, compiled)
        count = 0; success = True; refutation = None
        if child.terminal_status.is_terminal:
            success = task_success(child, anchors, baseline)
        else:
            for reply in iter_legal_successor_handles(child, compiled, checkpoint=budget.checkpoint):
                after = budget.child(child, reply, compiled); count += 1
                if not task_success(after, anchors, baseline):
                    success = False
                    if refutation is None:
                        refutation = {'action': action_to_dict(reply.action),
                                      'custody_delta': custody(after.position, anchors) - baseline,
                                      'terminal': after.terminal_status.status.value}
            if count == 0:
                raise ValueError('empty nonterminal replies; incomplete actual-actor evidence')
        actors[square]['actions'].append({'action': action_to_dict(handle.action),
                                         'reply_count': count, 'success': success,
                                         'first_refutation': refutation})
    rows = list(actors.values())
    for row in rows:
        row['success'] = int(any(a['success'] for a in row['actions']))
    types = {}
    for kind in sorted({row['type'] for row in rows}):
        group = [row for row in rows if row['type'] == kind]
        successful = sum(row['success'] for row in group)
        types[kind] = {'count': len(group), 'successful': successful,
                       'marked_actor_mean': str(Fraction(successful, len(group)))}
    budget.checkpoint()
    return {'actors': rows, 'types': types, 'actor_success_count': sum(row['success'] for row in rows),
            'reconstructed_count': str(sum((item['count'] * Fraction(item['marked_actor_mean'])
                                            for item in types.values()), Fraction()))}


def audit(budget=None):
    if hashlib.sha256(PROTOCOL.read_bytes()).hexdigest() != PROTOCOL_SHA:
        raise ValueError('frozen actual-actor protocol changed')
    if hashlib.sha256(INPUT.read_bytes()).hexdigest() != INPUT_SHA:
        raise ValueError('frozen physical evidence changed')
    budget = budget or Budget()
    frozen = json.loads(INPUT.read_text())['roots']
    chess, _ = standard_engine()
    shogi = compile_ruleset_for_execution(build_standard_shogi_ruleset())
    roots = []
    for game, compiled in (('chess', chess), ('shogi', shogi)):
        budget.checkpoint()
        row = next(row for row in frozen if row['game'] == game)
        template = position_from_fen('8/8/8/8/8/8/8/8 w - - 0 1', compiled) if game == 'chess' else initial_state(compiled).position
        position = replace(template, board=tuple(None if p is None else Piece(*p) for p in row['physical_board']),
                           hands=(Hands.empty(), Hands.empty()), side_to_move=0)
        roots.append({'game': game, 'physical_board': row['physical_board'],
                      **all_actor_labels(compiled, position, budget)})
    return {'protocol_sha256': PROTOCOL_SHA, 'input_sha256': INPUT_SHA,
            'program_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'complete': True, 'roots': roots, 'materialized_transitions': budget.transitions,
            'elapsed_seconds': monotonic() - budget.started}


if __name__ == '__main__':
    result = audit()
    if len(sys.argv) > 1:
        Path(sys.argv[1]).write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps({**{k: v for k, v in result.items() if k != 'roots'},
                      'roots': [{k: v for k, v in row.items() if k not in ('actors', 'physical_board')}
                                for row in result['roots']]}, indent=2))
