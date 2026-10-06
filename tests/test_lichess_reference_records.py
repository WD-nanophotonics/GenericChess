import hashlib
import json
from pathlib import Path
from fractions import Fraction as F

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT/'docs/research/data'


def load(name): return json.loads((DATA/f'{name}_20261006.json').read_text())


def pins(r):
    assert r['source_hashes_unchanged']
    for path, digest in r['source_sha256'].items():
        assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest() == digest


def test_exact_single_daily_response_and_before_acquisition_frozen_inputs():
    r = load('lichess_daily_source'); pins(r)
    assert r['complete'] and r['http_requests'] == 1 and r['http_status'] == 200
    body = (DATA/'lichess_daily_source_20261006.response').read_bytes()
    assert len(body) == r['bytes'] == 730
    assert hashlib.sha256(body).hexdigest() == r['response_sha256']
    assert json.loads(body) == r['payload']
    assert r['payload']['puzzle']['id'] == 'WYC4q'


def test_preserved_ep_ingestion_failure_and_nonreplayed_view():
    old = load('lichess_daily_preflight'); pins(old)
    view = load('lichess_ep_view'); pins(view)
    assert not old['complete'] and not old['history_qualified']
    assert old['error'] == 'ValueError: advertised root/complete PGN mismatch'
    assert old['author_pushes'] == old['board_checks'] == len(old['history']) == 52
    assert old['author_legal_entries'] == 3836
    assert view['complete'] and view['author_pushes'] == view['public_transitions'] == 0
    assert view['ep_target'] == 'a6' and not view['has_legal_en_passant']
    assert view['snapshot_stack_length'] == 0 and view['full_saved_ancestry_length'] == 52
    assert not view['full_history_terminal_view_qualified']
    assert view['required_three_model_events'] == 180 > 128
    assert view['required_pure_child_events'] == 84 < 128
    assert view['forced_ep_fen'].split()[:3] == view['api_display_fen'].split()[:3]
    assert view['forced_ep_fen'].split()[3] == 'a6' and view['api_display_fen'].split()[3] == '-'


def test_complete_native_history_and_public_child_table_with_original_caps():
    r = load('lichess_complete_children'); pins(r)
    assert r['complete'] and r['prefix_checks'] == 52 and r['ancestor_count'] == 53
    assert r['public_transitions'] == 84 and r['enumerated_entries'] == 3932
    assert r['runtime_pushes'] == 0 and r['cumulative_author_pushes'] == 84
    assert r['cumulative_author_legal_entries'] == 3900 and r['seconds'] < 30
    assert len(r['all_root_actions']) == len(r['children']) == len(r['source_checks']) == 32
    assert set(r['all_root_actions']) == set(r['children']) == set(r['source_checks'])
    assert r['root']['ply_count'] == 52 and len(r['root']['history']) == 53
    for key, child in r['children'].items():
        assert child['ply_count'] == 53 and len(child['history']) == 54
        assert child['terminal_status'] == {'status': 'ongoing', 'winner': None}
        check = r['source_checks'][key]
        assert check['author_stack_length'] == 1
        assert check['full_ancestry_occurrence_count'] < 5 and check['author_halfmove_clock'] < 150
        assert check['automatic_terminal'] is None


def test_precomparison_record_not_falsely_called_unseen_labels():
    r = load('lichess_complete_children')
    path = DATA/'lichess_complete_children_20261006.selections.json'
    assert hashlib.sha256(path.read_bytes()).hexdigest() == r['precomparison_sha256']
    pre = json.loads(path.read_text())
    assert pre['policies'] == r['policies'] and pre['children'] == r['children']
    assert 'reference_comparison' not in pre
    for law, p in r['policies'].items():
        best = max(p['scores'].values())
        assert p['tie_set'] == sorted(k for k, v in p['scores'].items() if v == best)
        assert p['selected'] == p['tie_set'][0]
        c = r['reference_comparison'][law]
        assert c['advertised_answer'] == 'c2c3' and c['selected_uci'] == 'g4g7'
        assert not c['canonical_matches'] and not c['answer_in_full_ties']


def test_immediate_feature_partition_preserves_all_actions_and_explains_miss():
    r = load('shallow_reference_features'); pins(r)
    assert r['complete'] and r['mode_terms'] == 160
    assert r['public_transitions'] == r['runtime_pushes'] == r['source_queries'] == 0
    assert r['quiet_count'] == 30 and r['capture_count'] == 2
    assert r['positive_pawn_price_cannot_select_reference_proved']
    assert set(p for group in r['feature_groups'].values() for p in group) == set(r['action_deltas'])
    assert r['reference_delta'] == dict.fromkeys('PNBRQ', 0)
    assert all(v > 0 for v in r['actual_quantized_pawn_weights'].values())
    for price in (F(1, 1000), F(1, 2), F(1)):
        scores = {k: price*row['P'] for k, row in r['action_deltas'].items()}
        assert scores[r['reference_action']] < max(scores.values())
