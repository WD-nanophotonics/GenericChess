from functools import lru_cache

import pytest

from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.western_chess import build_western_chess_ruleset
from scripts.audit_f24f_western_chess_perft import position_from_fen
from scripts.audit_signed_exposure_choices import exposure_changes
from scripts.intrinsic_action_events import collect_intrinsic_board_events


def test_signed_tracking_reports_moved_actor_separately_and_fails_bad_mapping():
    compiled = compile_ruleset_for_execution(build_western_chess_ruleset())
    before = position_from_fen('3r3k/8/8/8/8/3R4/8/K2N4 w - - 0 1', compiled)
    after = position_from_fen('3r3k/8/8/8/8/4R3/8/K2N4 b - - 1 1', compiled)
    @lru_cache(maxsize=None)
    def ledger(type_id):
        return collect_intrinsic_board_events(compiled, type_id, max_candidates=100_000)
    changes = exposure_changes(compiled, before, after, 0,
                               {'protected': (3, 3), 'actor': (19, 20)}, ledger)
    assert changes['protected']['before_sources'] == []
    assert changes['protected']['after_sources'] == [59]
    assert changes['actor']['before_sources'] == [59]
    assert changes['actor']['after_sources'] == []
    assert changes['protected']['signed_delta'] == -1
    assert changes['actor']['signed_delta'] == 1
    for tracked, match in (({'a': (3, 3), 'b': (3, 3)}, 'distinct'),
                           ({'a': (19, 19)}, 'surviving'),
                           ({'a': (3, 20)}, 'surviving'),
                           ({'a': (0, 0)}, 'ordinary'),
                           ({'a': (3, 64)}, 'board-only')):
        with pytest.raises(ValueError, match=match):
            exposure_changes(compiled, before, after, 0, tracked, ledger)
    with pytest.raises(ValueError, match='unsupported'):
        exposure_changes(compiled, before, after, 0, {'a': (3, 3)},
                         lambda _: {'coverage_complete': False})
    with pytest.raises(ValueError, match='owner'):
        exposure_changes(compiled, before, after, True, {'a': (3, 3)}, ledger)
