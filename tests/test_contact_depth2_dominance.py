import hashlib
import itertools
import json
from fractions import Fraction as F
from pathlib import Path

from scripts.material_leaf_choice import inventory_features
from scripts.native_chess_contact_intervals import _ongoing_features, native_contact_intervals
from scripts.public_goal_intervals import PublicGame
from scripts.research_record import record_value
from scripts.research_state_replay import read_game_state
from scripts.saved_action_binding import saved_board_action
from generic_chess.core.semantic_executor import semantic_engine_for
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.western_chess import build_western_chess_ruleset

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'docs/research/data'

def load(name):
    return json.loads((DATA / f'{name}_20261005.json').read_text())

def score(features, weights):
    return sum((F(n) * weights[k] for k, n in features.items()), F(0)) / 31

def test_negative_complete_branch_beats_terminal_floor_for_both_global_boxes():
    r = load('contact_depth2_dominance')
    old = load('chess_knight_interposition')
    pick = r['negative_depth2']['contact']
    assert set(r['negative_depth2'].values()) == {pick}
    rows = old['reply_tables'][pick]['rows']
    assert len(rows) == len(r['negative_leaf_features']) == 35
    for law in ('geometric_half', 'linear_mixture'):
        intervals = native_contact_intervals(law)
        for row in rows:
            features = _ongoing_features(read_game_state(row['state']).position)
            lower = sum(F(n) * intervals[k][0 if n >= 0 else 1] for k, n in features.items()) / 31
            assert lower > -1
    assert all(sum(inventory_features(read_game_state(row['state']).position, {'K'}).values()) / F(31) > -1 for row in rows)

def test_positive_global_corner_dominance_unit_tie_and_complete_zero_states():
    r = load('contact_depth2_dominance')
    old = load('chess_pinned_queen_mate')
    continued = load('chess_pinned_queen_continuation')
    children = {k: read_game_state(v) for k, v in old['children'].items()}
    candidate = r['positive_depth2']['contact']
    features = {k: _ongoing_features(v.position) for k, v in children.items()}
    game = PublicGame(compile_ruleset_for_execution(build_western_chess_ruleset()))
    reply = read_game_state(old['candidate_replies'][0]['enemy_child'])
    assert inventory_features(reply.position, {'K'}) == features[candidate]
    for law in ('geometric_half', 'linear_mixture'):
        intervals = native_contact_intervals(law)
        keys = tuple(intervals)
        for endpoints in itertools.product((0, 1), repeat=len(keys)):
            weights = {k: intervals[k][i] for k, i in zip(keys, endpoints)}
            winning = score(features[candidate], weights)
            assert winning > 0
            assert all(winning > max(0, score(v, weights)) for k, v in features.items() if k != candidate)
    rook = r['positive_depth2']['unit']
    values = {k: sum(v.values()) / F(31) for k, v in features.items()}
    assert values[rook] == max(values.values()) == F(2, 31)
    earlier = [k for k, v in values.items() if k < rook and v >= values[rook]]
    old_unit = old['selections_before_labels']['unit']['selected']
    assert earlier == [old_unit]
    counter = read_game_state(continued['baseline_counterbranches'][old_unit]['enemy_child'])
    assert sum(inventory_features(counter.position, {'K'}).values()) / F(31) == F(1, 31)
    assert r['rook_capture']['parent'] == rook and len(r['rook_capture']['all_enemy_replies']) == 1
    assert inventory_features(read_game_state(r['rook_capture']['state']).position, {'K'}) == features[rook]
    assert {row['action'] for row in r['zero_rows']} == set(r['zero_all_replies'])
    assert len(r['zero_rows']) == 14 and sum(row['reused'] for row in r['zero_rows']) == 1
    for encoded in [r['rook_capture']['state']] + [row['state'] for row in r['zero_rows']]:
        state = read_game_state(encoded)
        assert record_value(state) == encoded
        assert state.ply_count == 2 and len(state.history) == 3
        assert not (game.terminal(state).is_terminal and game.terminal(state).winner == 1)

def test_frozen_sources_and_saved_binding_remain_exact_without_reapplying_events():
    r = load('contact_depth2_dominance')
    assert r['complete'] and r['source_hashes_unchanged']
    assert r['public_transitions'] == 14 and r['enumerated'] == 184 and r['source_queries'] == 0
    for name, pin in r['source_sha256'].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == pin
    old = load('chess_pinned_queen_mate')
    engine = semantic_engine_for(compile_ruleset_for_execution(build_western_chess_ruleset()))
    state = read_game_state(old['children'][r['rook_capture']['parent']])
    key = r['rook_capture']['all_enemy_replies'][0]
    assert str(saved_board_action(engine, state, key)) == key
