"""RuleSet schema, validation, compiler and serialization."""

from .catalog import (
    build_builtin_ruleset,
    builtin_ruleset_names,
    resolve_builtin_ruleset_by_fingerprint,
)
from .compiler import compile_ruleset, compile_ruleset_for_execution
from .western_chess import build_western_chess_ruleset
from .standard_shogi import build_standard_shogi_ruleset
from .schema import (
    RuleAutomaticAdjudication,
    RuleDeclaration,
    RuleDeclarationOutcomeBand,
    RuleWeightedMaterialMetric,
)

__all__ = [
    "build_builtin_ruleset",
    "builtin_ruleset_names",
    "resolve_builtin_ruleset_by_fingerprint",
    "build_western_chess_ruleset",
    "build_standard_shogi_ruleset",
    "compile_ruleset",
    "compile_ruleset_for_execution",
    "RuleDeclaration",
    "RuleAutomaticAdjudication",
    "RuleDeclarationOutcomeBand",
    "RuleWeightedMaterialMetric",
]
