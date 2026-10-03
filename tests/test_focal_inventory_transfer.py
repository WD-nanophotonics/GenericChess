from dataclasses import replace
import hashlib
import json
from pathlib import Path

import pytest

from generic_chess.core.pieces import Piece
from generic_chess.core.transition import initial_state
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from scripts.audit_f24f_western_chess_perft import standard_engine, position_from_fen
from scripts.audit_focal_inventory_transfer import audit, inventory, vector
from scripts.audit_physical_placement_sampling import substituted


def test_symbolic_inventory_matches_actual_frozen_board_substitutions():
    result = audit(); root = Path(__file__).resolve().parents[1]
    physical = json.loads((root / 'docs/research/data/physical_placement_sampling_20261003.json').read_text())
    chess, _ = standard_engine()
    games = {'chess': chess, 'shogi': compile_ruleset_for_execution(build_standard_shogi_ruleset())}
    assert result['complete'] and len(result['rows']) == 12
    for row in result['rows']:
        compiled = games[row['game']]
        template = (position_from_fen('8/8/8/8/8/8/8/8 w - - 0 1', compiled) if row['game'] == 'chess'
                    else initial_state(compiled).position)
        frame = replace(template, board=tuple(None if p is None else Piece(*p)
                                             for p in physical['games'][row['game']]['physical_board']))
        query = substituted(frame, row['query_type'], compiled)
        assert row['query_inventory'] == vector(inventory(query))
        assert row['actual_inventory'] == vector(inventory(initial_state(compiled).position))
        if row['query_type'] == 'P':
            assert row['count_l1_distance'] == 0 and not row['disjoint_inventory_support']
            assert row['position_space_tv_if_both_laws_exist'] is None  # Equal counts do not prove equal laws.
        else:
            assert row['count_l1_distance'] == 2 and row['disjoint_inventory_support']
            assert row['position_space_tv_if_both_laws_exist'] == 1
    assert sum(row['disjoint_inventory_support'] for row in result['rows']) == 10


def test_frozen_inventory_evidence_and_source_reproduce():
    result = audit(); root = Path(__file__).resolve().parents[1]
    recorded = json.loads((root / 'docs/research/data/focal_inventory_transfer_20261004.json').read_text())
    for key in ('protocol_sha256', 'sampler_sha256', 'program_sha256', 'rows', 'scope'):
        assert result[key] == recorded[key]
    assert result['program_sha256'] == hashlib.sha256((root / 'scripts/audit_focal_inventory_transfer.py').read_bytes()).hexdigest()


def test_time_cap_is_not_a_transfer_certificate():
    with pytest.raises(TimeoutError, match='time cap'):
        audit(seconds=-1)
