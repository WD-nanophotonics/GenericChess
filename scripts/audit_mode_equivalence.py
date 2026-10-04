"""Frozen matched provenance controls, not a context mean or material batch."""
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
from generic_chess.core.position import Hands
from generic_chess.core.semantic_executor import semantic_engine_for, _semantic_public_action
from generic_chess.core.transition import initial_state
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from generic_chess.rules.western_chess import build_western_chess_ruleset
from scripts.audit_exchange_custody import synthetic_state
from scripts.audit_f24f_western_chess_perft import position_from_fen
from scripts.audit_resource_mode_feasibility import canonical_choice
from scripts.material_leaf_choice import material_score
from scripts.owned_service_reward import binding_reward, public_child_reward
from scripts.owned_tag_trace import trace_tag
from scripts.public_goal_intervals import PublicGame
from scripts.resource_mode_context import resource_ledger

PROTOCOL = 'docs/research/MODE_EQUIVALENCE_PROTOCOL.md'
PROTOCOL_SHA = 'd43c9875fbedbe0572d463ed1eb1482f33628f99964f027f1e3319d4760727f7'


def projection(state):
    """Current-state and corresponding short-history observations, not raw keys."""
    return {'board': [None if p is None else (p.owner, p.current_type_id) for p in state.position.board],
            'hands': [h.items() for h in state.position.hands],
            'side': state.position.side_to_move, 'aux': state.position.aux_state,
            'ply': state.ply_count, 'terminal': (state.terminal_status.status.value, state.terminal_status.winner),
            'history': [(h.actor, h.action_signature, h.gave_check) for h in state.history],
            'repetition_shape': sorted(n for _, n in state.repetition_counts)}


def rotate(position):
    return replace(position, board=tuple(None if p is None else Piece(1-p.owner, p.base_type_id,
                   p.current_type_id, p.promoted) for p in reversed(position.board)),
                   hands=tuple(reversed(position.hands)), side_to_move=1-position.side_to_move)


def audit():
    started = monotonic(); enumerated = 0; transitions = 0; rows = []; reason = None
    if hashlib.sha256((ROOT/PROTOCOL).read_bytes()).hexdigest() != PROTOCOL_SHA:
        raise ValueError('frozen mode-equivalence protocol changed')
    def checkpoint():
        if monotonic()-started >= 10:
            raise RuntimeError('10-second mode-equivalence cap')
    def choices(compiled, state):
        nonlocal enumerated
        game = PublicGame(compiled); engine = semantic_engine_for(compiled); public = {}; bindings = {}
        if game.terminal(state).is_terminal:
            raise ValueError('ongoing fixture required')
        for action in game.actions(state, checkpoint):
            checkpoint(); enumerated += 1; key = canonical_choice(action)
            if key in public:
                raise ValueError('duplicate public choice')
            public[key] = action
            if len(public) > 128 or enumerated > 5000:
                raise RuntimeError('complete-choice enumeration cap')
        for runtime, binding in engine.iter_legal_action_bindings(state.position, checkpoint=checkpoint):
            checkpoint(); enumerated += 1; key = canonical_choice(_semantic_public_action(engine, runtime))
            if key in bindings:
                raise ValueError('duplicate legal binding')
            bindings[key] = (runtime, binding)
            if len(bindings) > 128 or enumerated > 5000:
                raise RuntimeError('binding enumeration cap')
        if public.keys() != bindings.keys() or not public:
            raise ValueError('control requires complete ordinary action sets/no claims')
        return public, bindings
    def child(compiled, state, action):
        nonlocal transitions
        checkpoint()
        if transitions >= 128:
            raise RuntimeError('128 public materialization cap')
        result = PublicGame(compiled).successor(state, action); transitions += 1; checkpoint()
        return result
    try:
        chess = compile_ruleset_for_execution(build_western_chess_ruleset())
        shogi = compile_ruleset_for_execution(build_standard_shogi_ruleset())
        template = position_from_fen('8/7k/3r4/6b1/3Q4/8/8/K7 w - - 0 1', chess)
        for owner in (0, 1):
            pair = []; all_projections = []; reward_means = []; cached = []
            for base in ('Q', 'P'):
                board = list(template.board); board[27] = Piece(0, base, 'Q', base == 'P')
                position = replace(template, board=tuple(board))
                if owner:
                    position = rotate(position)
                resource_ledger(chess, position, 'chess')
                state = synthetic_state(chess, position)
                square = 27 if owner == 0 else 36
                tag = {'owner': owner, 'base': base, 'board': {square: Fraction(1)}, 'held': 0, 'lost': 0}
                table = choices(chess, state); pair.append(set(table[0]))
                projected = {}; child_cache = {}; reward_sum = Fraction(0)
                for key, action in table[0].items():
                    after = child(chess, state, action); runtime, binding = table[1][key]
                    expected = binding_reward(semantic_engine_for(chess), position, runtime, binding, tag)
                    if expected != public_child_reward(position, after.position, action, tag, chess.support.type_metadata):
                        raise AssertionError('independent tagged capture control mismatch')
                    tracked = trace_tag(semantic_engine_for(chess), position, after.position, runtime, binding, tag)
                    resource_ledger(chess, after.position, 'chess')
                    # Location/mass match after erasing only the tag's base.
                    projected[key] = {'state': projection(after), 'tag': {k: v for k, v in tracked.items() if k != 'base'},
                                      'reward': expected}
                    child_cache[key] = (after, tracked); reward_sum += expected
                all_projections.append(projected); reward_means.append(reward_sum/len(table[0]))
                cached.append((state, tag, table, child_cache))
            if pair[0] != pair[1] or all_projections[0] != all_projections[1] or reward_means[0] != reward_means[1]:
                raise AssertionError('matched Chess Queen provenance changes declared observations')
            weights = {('board', t): 1 for t, m in chess.support.type_metadata.items() if not m.is_anchor}
            scores = [material_score(s.position, weights, {'K'}, 30) for s, _, _, _ in cached]
            if scores[0] != scores[1]:
                raise AssertionError('current-type unit material changed under provenance swap')
            captured = []
            quiet_source = Square(3, 3) if owner == 0 else Square(4, 4)
            quiet_target = Square(3, 4) if owner == 0 else Square(4, 3)
            enemy_source = Square(3, 5) if owner == 0 else Square(4, 2)
            for _, _, table, child_cache in cached:
                keys = [key for key, action in table[0].items() if action_source_square(action) == quiet_source
                        and action_target_square(action) == quiet_target]
                if len(keys) != 1:
                    raise ValueError('unique frozen quiet Queen choice missing')
                after, tag = child_cache[keys[0]]; replies = choices(chess, after)
                keys = [key for key, action in replies[0].items() if action_source_square(action) == enemy_source
                        and action_target_square(action) == quiet_target]
                if len(keys) != 1:
                    raise ValueError('unique enemy Queen capture missing')
                key = keys[0]; final = child(chess, after, replies[0][key])
                runtime, binding = replies[1][key]
                lost = trace_tag(semantic_engine_for(chess), after.position, final.position, runtime, binding, tag)
                if lost['lost'] != 1 or final.position.hands != (Hands.empty(), Hands.empty()):
                    raise AssertionError('Chess provenance changes custody/loss')
                captured.append(projection(final))
            if captured[0] != captured[1]:
                raise AssertionError('post-capture Chess observations differ')
            rows.append({'game': 'chess', 'owner': owner, 'complete_root_choices': len(pair[0]),
                         'all_child_observations_equal': True, 'mean_unit_capture': str(reward_means[0]),
                         'unit_material': str(scores[0]), 'enemy_capture_loss': '1', 'hands_after_capture': [{}, {}]})
        if shogi.support.type_metadata['G'].movement_atoms != shogi.support.type_metadata['TP'].movement_atoms:
            raise AssertionError('declared Gold movement equivalence missing')
        for owner in (0, 1):
            held = []
            for base, current in (('G', 'G'), ('P', 'TP')):
                board = [None]*81; board[0] = Piece(0, 'K', 'K'); board[80] = Piece(1, 'K', 'K')
                board[40] = Piece(0, 'R', 'R'); board[49] = Piece(1, base, current, base != current)
                position = replace(initial_state(shogi).position, board=tuple(board))
                if owner:
                    position = rotate(position)
                state = synthetic_state(shogi, position); table = choices(shogi, state)
                source = Square(4, 4); target = Square(4, 5) if owner == 0 else Square(4, 3)
                keys = [key for key, action in table[0].items() if action_source_square(action) == source
                        and action_target_square(action) == target and getattr(action, 'promotion_target_id', None) is None]
                if len(keys) != 1:
                    raise ValueError('unique unpromoted Shogi capture missing')
                key = keys[0]; final = child(shogi, state, table[0][key]); victim = 49 if owner == 0 else 31
                tag = {'owner': 1-owner, 'base': base, 'board': {victim: Fraction(1)}, 'held': 0, 'lost': 0}
                runtime, binding = table[1][key]
                lost = trace_tag(semantic_engine_for(shogi), position, final.position, runtime, binding, tag)
                if lost['lost'] != 1 or final.position.hands[owner].count(base) != 1:
                    raise AssertionError('Shogi base custody conversion wrong')
                held.append(dict(final.position.hands[owner].items()))
            if held != [{'G': 1}, {'P': 1}]:
                raise AssertionError('movement-only merge loses Shogi custody distinction')
            rows.append({'game': 'shogi', 'owner': owner, 'same_gold_geometry': True,
                         'captured_hand_native_vs_promoted': held, 'scope': 'sparse synthetic semantic control'})
        checkpoint()
    except (RuntimeError, ValueError, AssertionError) as exc:
        reason = str(exc)
    paths = [PROTOCOL, 'scripts/audit_mode_equivalence.py', 'scripts/owned_service_reward.py',
             'scripts/owned_tag_trace.py', 'scripts/resource_mode_context.py', 'scripts/material_leaf_choice.py',
             'generic_chess/core/semantic_executor.py', 'generic_chess/core/transition.py',
             'generic_chess/rules/western_chess.py', 'generic_chess/rules/standard_shogi.py']
    return {'complete': len(rows) == 4 and reason is None, 'scope': 'bounded matched-origin/custody controls, no prices or outcomes',
            'controls': rows, 'public_transitions': transitions, 'enumerated_choices': enumerated,
            'stop_reason': reason, 'elapsed_seconds': monotonic()-started,
            'sha256': {p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths}}


if __name__ == '__main__':
    result = audit()
    if len(sys.argv) > 1:
        (ROOT/sys.argv[1]).write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8', newline='\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'sha256'}, indent=2))
