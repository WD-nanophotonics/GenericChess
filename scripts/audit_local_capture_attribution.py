"""Complete local/global labels on exposed capture actions; no new prior."""
from collections import Counter
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
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from scripts.audit_exchange_custody import custody
from scripts.audit_f24f_western_chess_perft import standard_engine
from scripts.audit_post_capture_scope import state_evidence
from scripts.audit_secured_exchange_common_context import Budget, task_success
from scripts.label_joint_capability_corpus import INPUT, INPUT_SHA, load_root

REFERENCE = ROOT / 'docs/research/data/joint_capability_reference_20261004.json'
REFERENCE_SHA = '4aa2599acf41546e77de691571bb3ac2282578639a76a6a895ac42fa46455f53'
PROTOCOL = ROOT / 'docs/research/LOCAL_CAPTURE_ATTRIBUTION_PROTOCOL.md'
PROTOCOL_SHA = '4a512e6c1707e34edf4fecc703790a2b2b2022b71bcaa70746ecba4478a1adf4'


def key(action):
    return json.dumps(action, sort_keys=True)


def local_success(actor_owned, victim_retained, terminal, winner):
    if terminal == 'no_contest':
        raise ValueError('no-contest unsupported')
    return bool(actor_owned and victim_retained and (terminal == 'ongoing' or winner == 0))


def state_hash(state, compiled):
    data = json.dumps(state_evidence(state, compiled), sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(data.encode()).hexdigest()


def capture_victim(position, action, n, anchors):
    source = getattr(action, 'from_square', None); target = getattr(action, 'to_square', None)
    if source is None or target is None:
        return None
    actor = position.board[source.rank * n + source.file]
    victim = position.board[target.rank * n + target.file]
    if actor is None or actor.owner != 0 or actor.current_type_id in anchors or victim is None or victim.owner != 1 or victim.current_type_id in anchors:
        return None
    return victim


def audit(budget=None):
    for path, expected in ((INPUT, INPUT_SHA), (REFERENCE, REFERENCE_SHA), (PROTOCOL, PROTOCOL_SHA)):
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError('frozen attribution inputs changed')
    budget = budget or Budget(seconds=15, transitions_limit=10_000)
    corpus = json.loads(INPUT.read_text()); reference = json.loads(REFERENCE.read_text())
    games = {'chess': standard_engine()[0], 'shogi': compile_ruleset_for_execution(build_standard_shogi_ruleset())}
    results = {}
    for game, compiled in games.items():
        n = compiled.board_size
        anchors = {t for t, m in compiled.support.type_metadata.items() if m.is_anchor}
        roots = []
        for evidence, saved in zip(corpus['games'][game]['reference'], reference['games'][game]['labels']):
            budget.checkpoint()
            state = load_root(compiled, game, evidence)
            if any(hand.total() for hand in state.position.hands) or state.terminal_status.is_terminal:
                raise ValueError('empty-hand ongoing reference required')
            baseline = custody(state.position, anchors)
            expected = {}
            for actor in saved['actors']:
                for row in actor['actions']:
                    target = row['action']['to']; victim = evidence['physical_board'][target[1] * n + target[0]]
                    if victim and victim[0] == 1 and victim[2] not in anchors:
                        expected[key(row['action'])] = row
            actions = []
            for handle in iter_legal_successor_handles(state, compiled, checkpoint=budget.checkpoint):
                victim = capture_victim(state.position, handle.action, n, anchors)
                if victim is None:
                    continue
                action = action_to_dict(handle.action); saved_action = expected.pop(key(action))
                child = budget.child(state, handle, compiled)
                source = handle.action.from_square.rank * n + handle.action.from_square.file
                target = handle.action.to_square.rank * n + handle.action.to_square.file
                actor = child.position.board[target]
                if actor is None or actor.owner != 0 or actor.base_type_id != state.position.board[source].base_type_id:
                    raise ValueError('capture actor tracking failed')
                board = list(state.position.board); board[source] = None; board[target] = actor
                expected_hand = Counter({victim.base_type_id: 1}) if game == 'shogi' else Counter()
                if tuple(board) != child.position.board or Counter(dict(child.position.hands[0].items())) != expected_hand or child.position.hands[1].total():
                    raise ValueError('additional-effect capture outside physical tracking scope')
                if custody(child.position, anchors) - baseline != (2 if game == 'shogi' else 1):
                    raise ValueError('ordinary token capture reward drift')
                replies = []
                def flags(after, reply_action=None):
                    if after.position.hands[0] != child.position.hands[0]:
                        raise ValueError('opponent modified captured-token own hand')
                    owned = after.position.board[target] == actor
                    # In this capture/reply scope no action resurrects the removed Chess victim;
                    # the sole Shogi victim stays in the unchanged owner-zero hand.
                    retained = True
                    status = after.terminal_status.status.value
                    return {'action': reply_action, 'actor_owned': owned, 'victim_retained': retained,
                            'terminal': status, 'winner': after.terminal_status.winner,
                            'custody_delta': custody(after.position, anchors) - baseline,
                            'global_success': bool(task_success(after, anchors, baseline)),
                            'local_success': local_success(owned, retained, status, after.terminal_status.winner),
                            'state_sha256': state_hash(after, compiled)}
                if child.terminal_status.is_terminal:
                    outcome = flags(child)
                    local, global_ok = outcome['local_success'], outcome['global_success']
                else:
                    outcome = None
                    for reply in iter_legal_successor_handles(child, compiled, checkpoint=budget.checkpoint):
                        after = budget.child(child, reply, compiled)
                        reply_source = getattr(reply.action, 'from_square', None)
                        reply_target = getattr(reply.action, 'to_square', None)
                        if reply_source is None or reply_target is None:
                            raise ValueError('non-board reply outside empty-hand physical tracking')
                        s = reply_source.rank * n + reply_source.file; t = reply_target.rank * n + reply_target.file
                        if child.position.board[s] is None or child.position.board[s].owner != 1:
                            raise ValueError('reply acts on non-opponent token')
                        board = list(child.position.board); board[s] = None; board[t] = after.position.board[t]
                        if tuple(board) != after.position.board:
                            raise ValueError('additional-effect reply outside physical tracking')
                        replies.append(flags(after, action_to_dict(reply.action)))
                    if not replies:
                        raise ValueError('empty nonterminal replies; no complete diagnostic')
                    local = all(r['local_success'] for r in replies)
                    global_ok = all(r['global_success'] for r in replies)
                if len(replies) != saved_action['reply_count'] or global_ok != saved_action['success']:
                    raise ValueError('frozen complete global action evidence mismatch')
                actions.append({'action': action, 'victim_base_type': victim.base_type_id,
                                'capture_state_sha256': state_hash(child, compiled),
                                'local_success': local, 'global_success': global_ok,
                                'terminal_capture_outcome': outcome, 'replies': replies})
            if expected:
                raise ValueError('incomplete capture coverage')
            roots.append({'position_key': evidence['position_key'], 'actions': actions})
        count = sum(len(r['actions']) for r in roots)
        if len(roots) != 4 or count != (63 if game == 'chess' else 55):
            raise ValueError('frozen eight-root capture coverage changed')
        results[game] = {'roots': roots, 'capture_actions': count,
                         'secured_local_actions': sum(a['local_success'] for r in roots for a in r['actions']),
                         'global_success_actions': sum(a['global_success'] for r in roots for a in r['actions'])}
    budget.checkpoint()
    return {'protocol_sha256': PROTOCOL_SHA, 'input_sha256': INPUT_SHA, 'reference_sha256': REFERENCE_SHA,
            'program_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'complete': True, 'games': results, 'materialized_transitions': budget.transitions,
            'elapsed_seconds': monotonic() - budget.started}


if __name__ == '__main__':
    result = audit()
    Path(sys.argv[1]).write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps({**{k: v for k, v in result.items() if k != 'games'},
                      'games': {g: {k: v for k, v in row.items() if k != 'roots'} for g, row in result['games'].items()}}, indent=2))
