"""Diagnostic TT override must preserve stored data/hash move and restore."""
import pytest
from generic_chess.ai.alphabeta.transposition import TranspositionTable,BoundType
from scripts.leaper_tt_score_counterfactual import NoTTScoreReuse


def test_ineligible_copy_preserves_real_entry_and_hash_move():
    table=TranspositionTable();table.store('key',4,23,BoundType.UPPER,'hash-action')
    original=table.probe('key')
    with NoTTScoreReuse()as diag:
        copy=table.probe('key')
        assert copy is not original and copy.depth==-1
        assert(copy.key,copy.score,copy.bound,copy.best_action,copy.generation)==(original.key,original.score,original.bound,original.best_action,original.generation)
        assert original.depth==4 and table.probe('missing')is None
    assert table.probe('key')is original and original.depth==4
    assert diag.probes==2 and diag.masked_hits==1


def test_counterfactual_restores_after_exception():
    original=TranspositionTable.probe
    with pytest.raises(RuntimeError):
        with NoTTScoreReuse():raise RuntimeError('diagnostic abort')
    assert TranspositionTable.probe is original
