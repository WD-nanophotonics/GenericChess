"""Scoped secured-capture actor counts; not material/WDL utility."""
from collections import Counter

from generic_chess.core.actions import action_to_dict
from generic_chess.core.lazy_transitions import iter_legal_successor_handles
from scripts.audit_local_capture_attribution import capture_victim, local_success


def service_labels(compiled, state, budget):
    budget.checkpoint()
    if state.position.side_to_move != 0 or state.terminal_status.is_terminal or state.position.hands[0].total():
        raise ValueError('ongoing owner-zero board actors with empty own hand required')
    anchors = {t for t, m in compiled.support.type_metadata.items() if m.is_anchor}
    n = compiled.board_size
    actors = {s: {'source': [s % n, s // n], 'type': p.current_type_id, 'actions': []}
              for s, p in enumerate(state.position.board) if p and p.owner == 0 and p.current_type_id not in anchors}
    if any(state.position.board[s].promoted for s in actors):
        raise ValueError('own promoted prior types outside finite scope')
    for handle in iter_legal_successor_handles(state, compiled, checkpoint=budget.checkpoint):
        victim = capture_victim(state.position, handle.action, n, anchors)
        if victim is None:
            continue
        source = handle.action.from_square.rank * n + handle.action.from_square.file
        target = handle.action.to_square.rank * n + handle.action.to_square.file
        child = budget.child(state, handle, compiled)
        actor = child.position.board[target]
        if actor is None or actor.owner != 0 or actor.base_type_id != state.position.board[source].base_type_id:
            raise ValueError('capture actor identity drift')
        board = list(state.position.board); board[source] = None; board[target] = actor
        victim_hand = Counter({victim.base_type_id: 1}) if n == 9 else Counter()
        if n not in (8, 9) or tuple(board) != child.position.board or Counter(dict(child.position.hands[0].items())) != victim_hand or child.position.hands[1] != state.position.hands[1]:
            raise ValueError('additional capture effects outside scoped token tracking')
        def evaluate(after):
            if after.position.hands[0] != child.position.hands[0]:
                raise ValueError('captured victim left own hand during opponent reply')
            owned = after.position.board[target] == actor
            return local_success(owned, True, after.terminal_status.status.value, after.terminal_status.winner), owned
        replies = 0; drops = 0; success = True; first_refutation = None
        if child.terminal_status.is_terminal:
            success, _ = evaluate(child)
        else:
            for reply in iter_legal_successor_handles(child, compiled, checkpoint=budget.checkpoint):
                after = budget.child(child, reply, compiled)
                src = getattr(reply.action, 'from_square', None); dst = getattr(reply.action, 'to_square', None)
                if dst is None:
                    raise ValueError('non-board/drop reply outside physical tracking')
                t = dst.rank * n + dst.file
                board = list(child.position.board)
                if src is None:
                    if child.position.board[t] is not None or after.position.board[t] is None or after.position.board[t].owner != 1:
                        raise ValueError('invalid opponent hand-drop trajectory')
                    drops += 1
                else:
                    s = src.rank * n + src.file
                    if child.position.board[s] is None or child.position.board[s].owner != 1:
                        raise ValueError('reply moved wrong owner')
                    board[s] = None
                board[t] = after.position.board[t]
                if tuple(board) != after.position.board:
                    raise ValueError('additional-effect reply outside scoped token tracking')
                ok, owned = evaluate(after); replies += 1
                if not ok:
                    success = False
                    if first_refutation is None:
                        first_refutation = {'action': action_to_dict(reply.action), 'actor_owned': owned,
                                            'terminal': after.terminal_status.status.value,
                                            'winner': after.terminal_status.winner}
            if not replies:
                raise ValueError('empty nonterminal replies')
        actors[source]['actions'].append({'action': action_to_dict(handle.action), 'reply_count': replies,
                                         'opponent_drop_replies': drops, 'success': success,
                                         'first_refutation': first_refutation})
    rows = list(actors.values())
    for row in rows:
        row['success'] = int(any(a['success'] for a in row['actions']))
    types = {t: {'count': sum(r['type'] == t for r in rows),
                 'successful': sum(r['success'] for r in rows if r['type'] == t)} for t in sorted({r['type'] for r in rows})}
    budget.checkpoint()
    return {'actors': rows, 'types': types, 'counts': dict(Counter(r['type'] for r in rows)),
            'actor_success_count': sum(r['success'] for r in rows),
            'opponent_drop_replies': sum(a['opponent_drop_replies'] for r in rows for a in r['actions'])}
