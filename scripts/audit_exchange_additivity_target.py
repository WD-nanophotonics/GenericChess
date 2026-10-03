"""Joint eligibility, successful-actor count and custody are different targets."""
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

from generic_chess.core.actions import action_from_dict, action_to_dict
from generic_chess.core.lazy_transitions import iter_legal_successor_handles
from generic_chess.core.pieces import Piece
from generic_chess.core.semantic_executor import semantic_engine_for, iter_semantic_public_actions
from generic_chess.core.transition import apply_action
from scripts.audit_exchange_custody import custody, synthetic_state
from scripts.audit_f24f_western_chess_perft import standard_engine, position_from_fen
from scripts.audit_physical_placement_sampling import substituted
from scripts.audit_secured_exchange_common_context import Budget, task_success

PROTOCOL = ROOT / 'docs/research/EXCHANGE_ADDITIVITY_TARGET_PROTOCOL.md'
PROTOCOL_SHA = 'f55059aaafc798061e6d03ef3597c07c42604b9eaff3b122b0e89949cfe324de'
INPUT = ROOT / 'docs/research/data/nonterminal_physical_support_20261003.json'
INPUT_SHA = '801cb8ca48817d4c411eed74e106e76f9cc93b3452234f26b54e20b8874148fc'
SOURCES = ((3, 3), (0, 0))


def finite_targets(contexts):
    if sum((weight for weight, _ in contexts), Fraction()) != 1:
        raise ValueError('normalized finite measure required')
    if any(weight < 0 or len(flags) != 2 or any(type(flag) is not bool for flag in flags)
           for weight, flags in contexts):
        raise ValueError('two binary actor flags and nonnegative weights required')
    mean = lambda fn: sum((weight * fn(flags) for weight, flags in contexts), Fraction())
    a, b = mean(lambda flags: int(flags[0])), mean(lambda flags: int(flags[1]))
    union = mean(lambda flags: int(any(flags)))
    return {'A': str(a), 'B': str(b), 'union': str(union),
            'successful_actor_count': str(mean(lambda flags: sum(flags))),
            'A_union_increment_given_B': str(union - b), 'B_union_increment_given_A': str(union - a)}


def audit(budget=None):
    if hashlib.sha256(PROTOCOL.read_bytes()).hexdigest() != PROTOCOL_SHA:
        raise ValueError('additivity target protocol changed')
    if hashlib.sha256(INPUT.read_bytes()).hexdigest() != INPUT_SHA:
        raise ValueError('frozen nonterminal frame evidence changed')
    data = json.loads(INPUT.read_text()); frozen = next(row for row in data['roots'] if row['game'] == 'chess')
    budget = budget or Budget(seconds=10, transitions_limit=2000)
    compiled, _ = standard_engine(); engine = semantic_engine_for(compiled)
    frame = replace(position_from_fen('8/8/8/8/8/8/8/8 w - - 0 1', compiled),
                    board=tuple(None if p is None else Piece(*p) for p in frozen['physical_board']))
    position = substituted(frame, 'R', compiled); state = synthetic_state(compiled, position)
    anchors = {tid for tid, item in compiled.support.type_metadata.items() if item.is_anchor}
    baseline = custody(position, anchors); groups = {source: [] for source in SOURCES}
    for handle in iter_legal_successor_handles(state, compiled, checkpoint=budget.checkpoint):
        source = getattr(handle.action, 'from_square', None)
        key = None if source is None else (source.file, source.rank)
        if key not in groups:
            continue
        child = budget.child(state, handle, compiled); success = True; count = 0; refutation = None
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
                raise ValueError('empty nonterminal replies; incomplete target audit')
        groups[key].append({'action': action_to_dict(handle.action), 'reply_count': count,
                            'success': success, 'first_refutation': refutation})
    if groups[(3, 3)] != frozen['root']['actions']:
        raise ValueError('original focal evidence did not reproduce')
    replays = 0
    def replay(before, action):
        nonlocal replays
        budget.checkpoint()
        if budget.transitions >= budget.transitions_limit:
            raise RuntimeError('additivity public replay cap')
        after = apply_action(before, action, compiled)
        budget.transitions += 1; replays += 1; budget.checkpoint()
        return after
    rows = []
    for source, actions in groups.items():
        selected = [item for item in actions if item['action']['to'] == [0, 3]]
        if len(selected) != 1:
            raise ValueError('unique shared-target capture required')
        action = action_from_dict(selected[0]['action']); victim = position.board[24]
        child = replay(state, action); replies = []
        for reply in iter_semantic_public_actions(engine, child.position, checkpoint=budget.checkpoint):
            after = replay(child, reply)
            replies.append({'action': action_to_dict(reply), 'terminal': after.terminal_status.status.value,
                            'custody_delta': custody(after.position, anchors) - baseline})
        rows.append({'source': list(source), 'actions': actions, 'success': int(any(item['success'] for item in actions)),
                     'selected_capture': selected[0], 'victim': [victim.owner, victim.current_type_id, [0, 3]],
                     'capture_terminal': child.terminal_status.status.value, 'replies': replies})
    half = Fraction(1, 2)
    return {'protocol_sha256': PROTOCOL_SHA, 'input_sha256': INPUT_SHA,
            'program_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), 'complete': True,
            'scope': 'eligibility restriction on unchanged board, not physical token deletion', 'actors': rows,
            'joint_success': int(any(row['success'] for row in rows)),
            'successful_actor_count': sum(row['success'] for row in rows),
            'finite_laws': {'overlap': finite_targets(((half, (True, True)), (half, (False, False)))),
                            'disjoint': finite_targets(((half, (True, False)), (half, (False, True))))},
            'replayed_transitions': replays, 'materialized_transitions': budget.transitions,
            'elapsed_seconds': monotonic() - budget.started}


if __name__ == '__main__':
    result = audit()
    if len(sys.argv) > 1:
        Path(sys.argv[1]).write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps({**{k: v for k, v in result.items() if k != 'actors'},
                     'actors': [{k: v for k, v in row.items() if k != 'actions'} for row in result['actors']]}, indent=2))
