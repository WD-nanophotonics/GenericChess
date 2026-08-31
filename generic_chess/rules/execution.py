"""Generic execution-boundary adapters for compiled RuleSets."""

from __future__ import annotations

from .ir import CompiledSemanticRuleset


class ExecutableSemanticRuleset(CompiledSemanticRuleset):
    """Semantic executable with read-only generic geometry compatibility.

    Core semantic legality remains owned by ``ir`` and ``support``.  The
    existing generic evaluator/rendering boundary also reads legacy-shaped
    movement metadata; semantic compilation already retains that metadata as
    an inspection handle, so this adapter exposes it without changing the
    semantic executor or introducing a game-specific branch.
    """

    __slots__ = ()

    def __getattr__(self, name: str):
        try:
            return getattr(self._legacy_compiled, name)
        except AttributeError:
            raise AttributeError(name) from None

