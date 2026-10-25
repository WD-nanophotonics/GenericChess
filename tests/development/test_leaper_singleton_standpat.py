"""Separate no-stand-pat from a larger q tree; all boundaries use real Core."""
from test_leaper_forced_quiet_q import context,call
from scripts.leaper_singleton_standpat import SingletonStandPat

def test_q4_singleton_draw_requires_move_without_extending_qdepth():
    _,ctx=context();ctx.qdepth_limit=4
    with SingletonStandPat()as p:assert call(ctx)==0 and p.counts['forced']==1 and not p.counts['beyond_ordinary']
    ctx.runtime.assert_balanced()

def test_explicit_q0_and_first_reserve_unchanged():
    for first in [None,False]:
        _,ctx=context(first=first)
        with SingletonStandPat()as p:assert call(ctx)==4242 and not p.counts
        ctx.runtime.assert_balanced()

def test_ordinary_depth_boundary_keeps_original_standpat():
    from generic_chess.ai.alphabeta import search as S
    _,ctx=context();ctx.qdepth_limit=4
    with SingletonStandPat()as p:assert S.quiescence(ctx.runtime.state,-S.INF,S.INF,0,4,ctx)==4242 and not p.counts
    ctx.runtime.assert_balanced()
