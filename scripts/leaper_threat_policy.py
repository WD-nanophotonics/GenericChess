"""Scoped one-writer research injection; never changes product default/source."""
from contextlib import contextmanager
from unittest.mock import patch
import generic_chess.ai.alphabeta.search as search
from scripts.leaper_threat_ordering import ThreatOrderer

@contextmanager
def threat_policy(enabled):
    orderers=[]
    if not enabled:
        yield orderers;return
    original=search._Context.__init__
    def initialize(ctx,*args,**kwargs):
        original(ctx,*args,**kwargs)
        assert not any((ctx.tuning.use_quiet_geometric_coverage,ctx.tuning.use_relative_history,ctx.tuning.use_staged_move_picker,ctx.tuning.use_ordered_qsearch))
        o=ThreatOrderer(ctx.compiled,ctx.stats);o.default_checkpoint=ctx.checkpoint;o.iteration_source=lambda:ctx.stats.completed_depth+1;ctx.orderer=o;orderers.append(o)
    with patch.object(search._Context,'__init__',initialize):yield orderers
