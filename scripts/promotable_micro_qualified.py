"""Use the exact old declared mask sets with their public typed envelope."""
from dataclasses import replace
from generic_chess.core.coordinates import Square
from scripts.audit_promotable_cube_micro import build as raw_build
def qualified_build(*args,**kwargs):
    rules=raw_build(*args,**kwargs)
    allowed={t:tuple(frozenset((Square(*source),Square(*target)) for source,target in mask) for mask in owners) for t,owners in rules.promotion_allowed.items()}
    forced={t:tuple(frozenset(Square(*square) for square in mask) for mask in owners) for t,owners in rules.promotion_forced.items()}
    return replace(rules,promotion_allowed=allowed,promotion_forced=forced)
