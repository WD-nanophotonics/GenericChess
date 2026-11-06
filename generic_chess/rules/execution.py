"""Generic execution-boundary adapters for compiled RuleSets."""

from __future__ import annotations

from dataclasses import fields

from .ir import CompiledSemanticRuleset


class ExecutableSemanticRuleset(CompiledSemanticRuleset):
    """Semantic executable with read-only generic geometry compatibility.

    Core semantic legality remains owned by ``ir`` and ``support``.  The
    existing generic evaluator/rendering boundary also reads legacy-shaped
    movement metadata; semantic compilation already retains that metadata as
    an inspection handle, so this adapter exposes it without changing the
    semantic executor or introducing a game-specific branch.

    Exposing metadata does not synthesize movement atoms from semantic actions.
    Static evaluators reading those atoms can omit semantic-only movement or
    retain geometry replaced by semantic rules; execution support is not a
    claim of complete semantic valuation.
    """

    __slots__ = ()

    @classmethod
    def from_compiled(cls, compiled: CompiledSemanticRuleset):
        """Expose the same compiled product, retaining its derived execution data.

        No IR/support override is accepted. Ordinary construction and
        dataclasses.replace still rebuild indices for changed rule products.
        """
        if not isinstance(compiled, CompiledSemanticRuleset):
            raise TypeError("expected a compiled semantic ruleset")
        result = object.__new__(cls)
        for item in fields(CompiledSemanticRuleset):
            object.__setattr__(result, item.name, getattr(compiled, item.name))
        return result

    def __getattr__(self, name: str):
        try:
            return getattr(self._legacy_compiled, name)
        except AttributeError:
            raise AttributeError(name) from None

