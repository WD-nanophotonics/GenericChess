"""Post-capture board-actor labels retaining check, hands and GameState."""
from collections import Counter
from dataclasses import asdict, replace
import hashlib
import json
from pathlib import Path
import sys
from time import monotonic

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from generic_chess.core.actions import action_to_dict
from generic_chess.core.identity import repetition_identity_key
from generic_chess.core.lazy_transitions import iter_legal_successor_handles
from generic_chess.core.pieces import Piece
from generic_chess.core.semantic_executor import semantic_engine_for
from generic_chess.core.transition import initial_state
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from scripts.audit_exchange_custody import custody, synthetic_state
from scripts.audit_f24f_western_chess_perft import standard_engine, position_from_fen
from scripts.audit_physical_placement_sampling import serialize_board
from scripts.audit_secured_exchange_common_context import Budget, task_success

PROTOCOL = ROOT / 'docs/research/POST_CAPTURE_VALIDATION_CONTRACT.md'
PROTOCOL_SHA = 'fff96751a4350ef45a538874f6db6a2a689a4945f82e00332ce14eb39cf963c6'
INPUT = ROOT / 'docs/research/data/actual_inventory_sampling_20261004.json'
INPUT_SHA = '38612248817cd69947957c51169098895672ef7ca77425f72102e2926068d87a'


def state_evidence(state, compiled):
    evidence = {'physical_board': serialize_board(state.position),
            'hands': [list(hand.items()) for hand in state.position.hands],
            'side_to_move': state.position.side_to_move, 'aux_state': state.position.aux_state,
            'position_key': repetition_identity_key(state.position, compiled),
            'ply_count': state.ply_count, 'repetition_counts': state.repetition_counts,
            'history': [asdict(record) for record in state.history],
            'terminal': state.terminal_status.status.value}
    return json.loads(json.dumps(evidence))


def capture_key(action):
    """Physical move identity within this board-capture/promotion scope."""
    return json.dumps({key: action[key] for key in
                       ('actor_type_id', 'from', 'to', 'promotion_target_id')}, sort_keys=True)


def board_actor_labels(compiled, state, budget):
    """No quiet/initial-inventory/empty-opponent-hand filter on deployment."""
    if state.position.side_to_move != 0 or state.terminal_status.is_terminal:
        raise ValueError('ongoing owner-zero deployment required')
    if state.position.hands[0].total():
        raise ValueError('own hand actors outside this narrow deployment contract')
    anchors = {tid for tid, item in compiled.support.type_metadata.items() if item.is_anchor}
    baseline = custody(state.position, anchors)
    rows = {square: {'source': [square % compiled.board_size, square // compiled.board_size],
                      'type': p.current_type_id, 'actions': []}
            for square, p in enumerate(state.position.board)
            if p and p.owner == 0 and p.current_type_id not in anchors}
    for handle in iter_legal_successor_handles(state, compiled, checkpoint=budget.checkpoint):
        source = getattr(handle.action, 'from_square', None)
        square = None if source is None else source.rank * compiled.board_size + source.file
        if square not in rows:
            continue
        child = budget.child(state, handle, compiled)
        count = 0; success = True; refutation = None; drops = 0
        if child.terminal_status.is_terminal:
            success = task_success(child, anchors, baseline)
        else:
            for reply in iter_legal_successor_handles(child, compiled, checkpoint=budget.checkpoint):
                after = budget.child(child, reply, compiled); count += 1
                drops += int(getattr(reply.action, 'from_square', None) is None)
                if not task_success(after, anchors, baseline):
                    success = False
                    if refutation is None:
                        refutation = {'action': action_to_dict(reply.action),
                                      'custody_delta': custody(after.position, anchors) - baseline,
                                      'terminal': after.terminal_status.status.value}
            if count == 0:
                raise ValueError('empty nonterminal replies; incomplete deployment label')
        rows[square]['actions'].append({'action': action_to_dict(handle.action), 'reply_count': count,
                                       'opponent_drop_replies': drops, 'success': success,
                                       'first_refutation': refutation})
    result = list(rows.values())
    for row in result:
        row['success'] = int(any(a['success'] for a in row['actions']))
    budget.checkpoint()
    return {'actors': result, 'counts': dict(Counter(r['type'] for r in result)),
            'actor_success_count': sum(r['success'] for r in result),
            'opponent_drop_replies': sum(a['opponent_drop_replies'] for r in result for a in r['actions'])}


def audit(budget=None):
    if hashlib.sha256(PROTOCOL.read_bytes()).hexdigest() != PROTOCOL_SHA:
        raise ValueError('frozen post-capture contract changed')
    if hashlib.sha256(INPUT.read_bytes()).hexdigest() != INPUT_SHA:
        raise ValueError('frozen admitted-board input changed')
    budget = budget or Budget(seconds=15, transitions_limit=10_000)
    data = json.loads(INPUT.read_text())
    chess, _ = standard_engine()
    shogi = compile_ruleset_for_execution(build_standard_shogi_ruleset())
    roots = []
    for game, compiled in (('chess', chess), ('shogi', shogi)):
        frozen = data['games'][game]['physical_board']
        template = position_from_fen('8/8/8/8/8/8/8/8 b - - 0 1', compiled) if game == 'chess' else initial_state(compiled).position
        position = replace(template, board=tuple(None if p is None else Piece(*p) for p in frozen), side_to_move=1)
        parent = synthetic_state(compiled, position)
        if parent.terminal_status.is_terminal:
            raise ValueError('terminal owner-one parent; scope incomplete')
        anchors = {tid for tid, item in compiled.support.type_metadata.items() if item.is_anchor}
        captures = []; children = {}; action_count = 0
        engine = semantic_engine_for(compiled)
        for handle in iter_legal_successor_handles(parent, compiled, checkpoint=budget.checkpoint):
            action_count += 1
            target = getattr(handle.action, 'to_square', None)
            victim = None if target is None else position.board[target.rank * compiled.board_size + target.file]
            if victim is None or victim.owner != 0 or victim.current_type_id in anchors:
                continue
            child = budget.child(parent, handle, compiled)
            action = action_to_dict(handle.action); key = capture_key(action)
            if key in children:
                raise ValueError('duplicate physical capture; deployment weights undefined')
            children[key] = child
            captures.append({'action': action, 'key': key, 'victim_type': victim.current_type_id,
                             'terminal': child.terminal_status.status.value,
                             'own_check': engine.in_check(child.position, 0, checkpoint=budget.checkpoint),
                             'opponent_hand': [list(item) for item in child.position.hands[1].items()]})
        ongoing = sorted((r for r in captures if r['terminal'] == 'ongoing'), key=lambda r: r['key'])
        preferred = [r for r in ongoing if r['own_check'] or r['opponent_hand']]
        if not ongoing:
            raise ValueError('no ongoing capture; scope incomplete')
        selected = (preferred or ongoing)[0]
        child = children[selected['key']]
        label = board_actor_labels(compiled, child, budget)
        roots.append({'game': game, 'parent': state_evidence(parent, compiled),
                      'legal_parent_actions': action_count, 'captures': captures,
                      'ongoing_victim_types': sorted({r['victim_type'] for r in ongoing}),
                      'selected_capture': selected, 'child': state_evidence(child, compiled), **label})
    budget.checkpoint()
    return {'protocol_sha256': PROTOCOL_SHA, 'input_sha256': INPUT_SHA,
            'program_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'complete': True, 'scope': 'two deployment scope fixtures, no coefficients or validation risk',
            'roots': roots, 'materialized_transitions': budget.transitions,
            'elapsed_seconds': monotonic() - budget.started}


if __name__ == '__main__':
    result = audit()
    if len(sys.argv) > 1:
        Path(sys.argv[1]).write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps({**{k: v for k, v in result.items() if k != 'roots'},
                      'roots': [{k: v for k, v in r.items() if k not in ('parent', 'child', 'actors', 'captures')}
                                for r in result['roots']]}, indent=2))
