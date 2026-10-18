"""Check the owner-mirror-fairness claim on the frozen rules and roots.

Reads only the frozen rules.json/roots.json and recomputes legal actions with
the same compiled executor. No search, no game outcome, no new rule.

For every rule, the initial position and every frozen root P are mapped to
M(P): rotate the board 180 degrees and swap piece/hand owners and side to move.
The visible legal action set of P, mapped by the same rotation, must equal the
legal action set of M(P). Two negative controls (180 rotation without owner
swap; left-right mirror without owner swap) show that the comparison is not
vacuous.
"""
from collections import Counter
from dataclasses import replace
from pathlib import Path
import json

from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution
from generic_chess.core.position import GameState
from generic_chess.core.actions import SemanticBoardMove, SemanticDropMove, Square
from generic_chess.core.movegen import legal_actions
from generic_chess.core.terminal import TerminalResult, TerminalStatus
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record

D = Path('.local_agent/asymmetric-static-20261018')
RULES = json.loads((D / 'rules.json').read_bytes())
ROOTS = json.loads((D / 'roots.json').read_bytes())
TABLE_FAILURES = Counter()
TABLE_SAMPLES = []


def note(kind, seed, type_id, index=None, atom=None, extra=None):
    TABLE_FAILURES[kind] += 1
    if len(TABLE_SAMPLES) < 6:
        TABLE_SAMPLES.append(dict(kind=kind, rule=int(seed), type=type_id,
                                  square=index, atom=atom, extra=extra))


def mirror_square(sq: Square, n: int) -> Square:
    return Square(file=n - 1 - sq.file, rank=n - 1 - sq.rank)


def visible_key(action):
    if isinstance(action, SemanticBoardMove):
        return ('board', action.actor_type_id, action.from_square,
                action.to_square, action.promotion_target_id)
    if isinstance(action, SemanticDropMove):
        return ('drop', action.base_type_id, action.to_square)
    return ('other', str(action))


def mirrored_key(key, n):
    if key[0] == 'board':
        return ('board', key[1], mirror_square(key[2], n),
                mirror_square(key[3], n), key[4])
    if key[0] == 'drop':
        return ('drop', key[1], mirror_square(key[2], n))
    return key


def mirror_position(position, n, *, swap_owners=True, left_right=False):
    board = [None] * len(position.board)
    for index, piece in enumerate(position.board):
        if piece is None:
            continue
        row, col = divmod(index, n)
        if left_right:
            target = row * n + (n - 1 - col)
        else:
            target = len(position.board) - 1 - index
        if swap_owners:
            piece = replace(piece, owner=1 - piece.owner)
        board[target] = piece
    hands = position.hands
    side = position.side_to_move
    if swap_owners:
        hands = (position.hands[1], position.hands[0])
        side = 1 - side
    return replace(position, board=tuple(board), hands=hands,
                   side_to_move=side, aux_state=position.aux_state)


def action_counter(state, compiled, position=None):
    probe = state if position is None else replace(state, position=position)
    return Counter(visible_key(a) for a in legal_actions(probe, compiled))


def mirrored_counter(counter, n):
    return Counter({mirrored_key(k, n): v for k, v in counter.items()})


rows = []
for seed in sorted(RULES['rules'], key=int):
    rule = ruleset_from_dict(json.loads(json.dumps(RULES['rules'][seed])))
    compiled = compile_legacy_ruleset_for_semantic_execution(rule)
    n = compiled.board_size
    legacy = compiled._legacy_compiled
    aux_slots = len(compiled.ir.aux_slots)

    # Initial position: owner 1 half must be the 180-degree owner-swapped copy.
    init = legacy.initial_position
    init_ok = all(
        (init.board[i] is None) == (init.board[len(init.board) - 1 - i] is None)
        and (init.board[i] is None or (
            init.board[i].base_type_id
            == init.board[len(init.board) - 1 - i].base_type_id
            and init.board[i].owner != init.board[len(init.board) - 1 - i].owner))
        for i in range(len(init.board)))

    # Compiled move/drop/promotion tables must be exact owner mirrors.
    tables_ok = True
    r = lambda i: n * n - 1 - i  # noqa: E731
    for type_id in compiled.types_by_id:
        atom_count = len(legacy.leap_targets[type_id][0][0])
        ray_count = len(legacy.ray_paths[type_id][0][0])
        if (atom_count != len(legacy.leap_targets[type_id][1][0])
                or ray_count != len(legacy.ray_paths[type_id][1][0])):
            tables_ok = False
        for i in range(n * n):
            for atom in range(atom_count):
                lo = set(legacy.leap_targets[type_id][0][i][atom])
                l1 = set(legacy.leap_targets[type_id][1][r(i)][atom])
                if {mirror_square(t, n) for t in lo} != l1:
                    tables_ok = False
                    note('leap', seed, type_id, i, atom,
                         dict(o0=sorted(map(repr, lo)), o1=sorted(map(repr, l1))))
            for atom in range(ray_count):
                paths0 = legacy.ray_paths[type_id][0][i][atom]
                paths1 = legacy.ray_paths[type_id][1][r(i)][atom]
                rotated = tuple(mirror_square(s, n) for s in paths0)
                if rotated != paths1:
                    tables_ok = False
                    note('ray', seed, type_id, i, atom,
                         dict(o0=repr(paths0), o1=repr(paths1)))
            if type_id in legacy.drop_allowed:
                if (legacy.drop_allowed[type_id][0][i]
                        != legacy.drop_allowed[type_id][1][r(i)]):
                    tables_ok = False
                    note('drop', seed, type_id, i)
        if type_id in legacy.promotion_forced:
            forced0 = {mirror_square(s, n)
                       for s in legacy.promotion_forced[type_id][0]}
            if forced0 != set(legacy.promotion_forced[type_id][1]):
                tables_ok = False
                note('promotion_forced', seed, type_id)
        if type_id in legacy.promotion_allowed:
            allowed0 = {(mirror_square(a, n), mirror_square(b, n))
                        for a, b in legacy.promotion_allowed[type_id][0]}
            if allowed0 != set(legacy.promotion_allowed[type_id][1]):
                tables_ok = False
                note('promotion_allowed', seed, type_id)  

    root_rows = [row for row in ROOTS['rows'] if int(row['rule']) == int(seed)]
    mirrored_ok = 0
    duplicate_bindings = 0
    rotate_control_diff = 0
    left_right_control_diff = 0
    replay_count_mismatch = 0
    aux_nonempty = 0
    for row in root_rows:
        session = GameSession.replay(
            compiled, deserialize_game_record(json.dumps(row['record'])))
        state = session.state
        if len(session.legal_actions()) != row['legal_root_actions']:
            replay_count_mismatch += 1
        if state.position.aux_state:
            aux_nonempty += 1
        base = action_counter(state, compiled)
        duplicate_bindings += sum(1 for value in base.values() if value > 1)
        mirrored = action_counter(
            state, compiled,
            position=mirror_position(state.position, n, swap_owners=True))
        if mirrored_counter(base, n) == mirrored:
            mirrored_ok += 1
        rotate_same_owner = action_counter(
            state, compiled,
            position=mirror_position(state.position, n, swap_owners=False))
        if base != rotate_same_owner:
            rotate_control_diff += 1
        left_right = action_counter(
            state, compiled,
            position=mirror_position(state.position, n, swap_owners=False,
                                     left_right=True))
        if base != left_right:
            left_right_control_diff += 1

    # The same invariance on the initial position itself.
    init_state = GameState(position=init, ply_count=0, repetition_counts=(),
                           terminal_status=TerminalResult(TerminalStatus.ONGOING))
    init_base = action_counter(init_state, compiled)
    init_mirror = action_counter(
        init_state, compiled,
        position=mirror_position(init, n, swap_owners=True))
    init_ok = init_ok and mirrored_counter(init_base, n) == init_mirror

    rows.append(dict(
        rule=int(seed), board_size=n, aux_slots=aux_slots,
        initial_position_mirror=init_ok,
        compiled_tables_owner_mirror=tables_ok,
        roots=len(root_rows), roots_mirror_exact=mirrored_ok,
        replay_legal_count_mismatches=replay_count_mismatch,
        nonempty_aux_root_states=aux_nonempty,
        duplicate_visible_bindings=duplicate_bindings,
        control_rotate_without_owner_swap_differs=rotate_control_diff,
        control_left_right_without_owner_swap_differs=left_right_control_diff))

out = dict(
    rules=rows,
    all_initial_positions_mirror=all(r['initial_position_mirror'] for r in rows),
    all_compiled_tables_mirror=all(r['compiled_tables_owner_mirror'] for r in rows),
    total_roots=sum(r['roots'] for r in rows),
    total_roots_mirror_exact=sum(r['roots_mirror_exact'] for r in rows),
    table_failure_counts=dict(TABLE_FAILURES),
    table_failure_samples=TABLE_SAMPLES,
    scope='Frozen rules.json and roots.json read-only; legal actions recomputed '
          'with the same compiled executor; no search, eval, or game outcome. '
          'Mirror map: 180-degree board rotation + owner swap + side swap. '
          'Visible action key ignores pattern_id/geometry_id because a mirrored '
          'binding may name the mirrored geometry. Aux-state mirroring is only '
          'the identity here; all six rules report aux_slots=0.')

# Explicit gates: a regression must fail loudly, not only appear in the JSON.
checks = {
    'six_rules': len(rows) == 6,
    'all_initial_positions_mirror': out['all_initial_positions_mirror'],
    'all_compiled_tables_mirror': out['all_compiled_tables_mirror'],
    'no_table_failures': not TABLE_FAILURES,
    'all_192_roots_mirror_exact': (out['total_roots'] == 192
                                   and out['total_roots_mirror_exact'] == 192),
    'no_replay_legal_count_mismatch': all(
        r['replay_legal_count_mismatches'] == 0 for r in rows),
    'no_duplicate_visible_bindings': all(
        r['duplicate_visible_bindings'] == 0 for r in rows),
    'all_aux_slots_zero': all(r['aux_slots'] == 0 for r in rows),
    'no_nonempty_aux_roots': all(
        r['nonempty_aux_root_states'] == 0 for r in rows),
    'rotate_control_differs_32_of_32': all(
        r['control_rotate_without_owner_swap_differs'] == r['roots'] == 32
        for r in rows),
    'left_right_control_differs_32_of_32': all(
        r['control_left_right_without_owner_swap_differs'] == r['roots'] == 32
        for r in rows),
}
out['checks'] = checks
out['status'] = 'PASS' if all(checks.values()) else 'FAIL'
failed = sorted(name for name, ok in checks.items() if not ok)
if failed:
    raise SystemExit('owner_mirror_check FAILED: ' + ', '.join(failed))

(D / 'owner_mirror_check.json').write_text(json.dumps(out, indent=1, sort_keys=True))
print(json.dumps(out, indent=1, sort_keys=True))
