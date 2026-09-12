"""Qualification-only Western control derived from the production ruleset.

This module is intentionally outside the public built-in catalog.  The
control exists only to make the unreachable production repetition threshold a
bounded qualification variable; it must never replace or mutate
``build_western_chess_ruleset``.
"""

from __future__ import annotations

from dataclasses import replace

from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.rules.western_chess import build_western_chess_ruleset


QUALIFICATION_CONTROL_NAME = "western_chess_qualification_control_v1"
PRODUCTION_RULESET_FINGERPRINT = (
    "7bc6cf3179f4eaea30b205576b9032dca47a16803e9cc8b3e29405cb1e820b35"
)
QUALIFICATION_RULESET_FINGERPRINT = (
    "314729d06f8a47fc653779fe5b1eab6e6b9f2e923436c1c79a6f06cd12812e14"
)
QUALIFICATION_CHECKPOINT_ID = (
    "9ff9facc235577e3631c499cee549916935153d47ef12dd2a6bfc18409ba9b74"
)
EVALUATOR_IDENTITY = "learnable-material-v1"
QUALIFICATION_REPETITION_LIMIT = 5


def build_western_chess_qualification_control():
    """Derive the qualification control with exactly one gameplay delta."""
    production = build_western_chess_ruleset()
    control = replace(production, repetition_limit=QUALIFICATION_REPETITION_LIMIT)
    return control


def compile_western_chess_qualification_control():
    """Compile the non-public control through the semantic execution path."""
    return compile_semantic_ruleset(build_western_chess_qualification_control())


__all__ = [
    "QUALIFICATION_CONTROL_NAME",
    "PRODUCTION_RULESET_FINGERPRINT",
    "QUALIFICATION_RULESET_FINGERPRINT",
    "QUALIFICATION_CHECKPOINT_ID",
    "EVALUATOR_IDENTITY",
    "QUALIFICATION_REPETITION_LIMIT",
    "build_western_chess_qualification_control",
    "compile_western_chess_qualification_control",
]
