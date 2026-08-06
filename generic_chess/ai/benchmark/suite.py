"""Fixed-seed ruleset suite with deterministic opening positions."""

from __future__ import annotations

import random
from dataclasses import dataclass

from ...core.actions import Action
from ...generation.config import GeneratorConfig
from ...generation.generator import generate_game
from ...rules.compiled import CompiledRuleSet
from ...session.result import SessionStatus
from ...session.session import GameSession


@dataclass(frozen=True, slots=True)
class SuitePosition:
    """One benchmark entry: a generated RuleSet plus a deterministic opening."""

    key: str
    config: GeneratorConfig
    opening_plies: int


DEFAULT_SUITE: tuple[SuitePosition, ...] = (
    SuitePosition(
        "classic8_ply0",
        GeneratorConfig(seed=42, board_size=8, setup_preset="classic_like"),
        0,
    ),
    SuitePosition(
        "classic8_ply24",
        GeneratorConfig(seed=42, board_size=8, setup_preset="classic_like"),
        24,
    ),
    SuitePosition(
        "classic6_ply0",
        GeneratorConfig(seed=7, board_size=6, setup_preset="classic_like"),
        0,
    ),
    SuitePosition(
        "classic6_ply16",
        GeneratorConfig(seed=7, board_size=6, setup_preset="classic_like"),
        16,
    ),
    SuitePosition(
        "bilateral8_ply0",
        GeneratorConfig(seed=2026, board_size=8, setup_preset="bilateral_random"),
        0,
    ),
    SuitePosition(
        "bilateral8_ply20",
        GeneratorConfig(seed=2026, board_size=8, setup_preset="bilateral_random"),
        20,
    ),
    SuitePosition(
        "free8_ply0",
        GeneratorConfig(seed=11, board_size=8, setup_preset="free_random"),
        0,
    ),
    SuitePosition(
        "free8_ply12",
        GeneratorConfig(seed=11, board_size=8, setup_preset="free_random"),
        12,
    ),
)


def build_position(
    pos: SuitePosition,
) -> tuple[CompiledRuleSet, tuple[Action, ...]]:
    """Generate the ruleset and deterministically replay the opening.

    The opening walk picks from sorted legal actions with a PRNG seeded by
    ``(ruleset_seed, opening_plies)`` so every run reproduces the same
    position without storing artifacts.
    """
    game = generate_game(pos.config)
    compiled = game.compiled_ruleset
    session = GameSession(compiled)
    rng = random.Random(f"{pos.config.seed}:{pos.opening_plies}")
    opening: list[Action] = []
    for _ in range(pos.opening_plies):
        if session.result.status is not SessionStatus.ONGOING:
            break
        actions = list(session.legal_actions())
        if not actions:
            break
        action = rng.choice(sorted(actions, key=str))
        session.submit(action)
        opening.append(action)
    return compiled, tuple(opening)
