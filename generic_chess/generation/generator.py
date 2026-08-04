"""Top-level generator: produce a compiled, filtered GeneratedGame."""

from __future__ import annotations

import random
from dataclasses import replace

from ..core.coordinates import Square, index_to_square
from ..core.movegen import legal_actions_from_position
from ..rules.compiler import compile_ruleset
from ..rules.schema import RuleSet
from ..rules.validation import RuleValidationError
from .config import GenerationError, GeneratorConfig
from .drop_derivation import derive_drop_mask
from .filters import run_soft_filters
from .piece_generator import generate_ordinary_types, make_anchor_type, ordinary_type_ids
from .promotion_derivation import derive_promotion_data
from .report import GeneratedGame, GenerationReport, PieceTypeReport
from .setup_generator import build_initial_setup


def _try_generate(rng: random.Random, cfg: GeneratorConfig) -> GeneratedGame:
    n = cfg.board_size
    anchor = make_anchor_type()
    ids = ordinary_type_ids(n)
    force_promotable = frozenset({"P"}) if cfg.setup_preset == "classic_like" else frozenset()
    ordinary = generate_ordinary_types(rng, cfg, ids, force_promotable)

    target_ids = tuple(t.type_id for t in ordinary if not t.is_promotable)
    ordinary = tuple(
        replace(t, promotion_target_ids=target_ids) if t.is_promotable else t for t in ordinary
    )
    types = (anchor,) + ordinary
    types_by_id = {t.type_id: t for t in types}

    promotion_allowed: dict[str, tuple[frozenset[tuple[Square, Square]], ...]] = {}
    promotion_forced: dict[str, tuple[frozenset[Square], ...]] = {}
    for t in ordinary:
        if not t.is_promotable:
            continue
        pa0, pf0 = derive_promotion_data(n, 0, t.movement_atoms)
        pa1, pf1 = derive_promotion_data(n, 1, t.movement_atoms)
        promotion_allowed[t.type_id] = (pa0, pa1)
        promotion_forced[t.type_id] = (pf0, pf1)

    drop_allowed = {
        t.type_id: (
            derive_drop_mask(n, 0, t.movement_atoms),
            derive_drop_mask(n, 1, t.movement_atoms),
        )
        for t in ordinary
    }

    initial_position = build_initial_setup(rng, cfg.setup_preset, n, ids)
    ruleset = RuleSet(
        schema_version=1,
        board_size=n,
        piece_types=types,
        initial_position=initial_position,
        drop_allowed=drop_allowed,
        promotion_allowed=promotion_allowed,
        promotion_forced=promotion_forced,
        repetition_limit=4,
        max_ply=512,
        stalemate_result="draw",
        metadata={
            "seed": cfg.seed,
            "setup_preset": cfg.setup_preset,
            "movement_symmetry": cfg.movement_symmetry,
            "generator": "generic_chess.generation",
        },
    )

    compiled = compile_ruleset(ruleset)
    filter_results = run_soft_filters(cfg, compiled, types_by_id)
    if not all(f.passed for f in filter_results):
        failed = ", ".join(f.name for f in filter_results if not f.passed)
        raise GenerationError(f"soft filters rejected: {failed}")

    opening_count = len(legal_actions_from_position(compiled.initial_position, compiled))
    reports: list[PieceTypeReport] = []
    for t in types:
        if t.is_anchor:
            continue
        mobilities = [len(compiled.empty_mobility[t.type_id][0][idx]) for idx in range(n * n)]
        zone = tuple(
            index_to_square(idx, n)
            for idx in range(n * n)
            if not compiled.empty_forward_mobility[t.type_id][0][idx]
        )
        mandatory = tuple(
            index_to_square(idx, n)
            for idx in range(n * n)
            if not compiled.empty_mobility[t.type_id][0][idx]
        )
        reports.append(
            PieceTypeReport(
                type_id=t.type_id,
                name=t.name,
                movement_atoms=tuple(str(a) for a in t.movement_atoms),
                is_promotable=t.is_promotable,
                promotion_target_ids=t.promotion_target_ids,
                promotion_zone=zone,
                mandatory_promotion=mandatory,
                drop_mask=compiled.drop_allowed[t.type_id][0],
                average_mobility=sum(mobilities) / (n * n),
            )
        )

    return GeneratedGame(
        ruleset=ruleset,
        compiled_ruleset=compiled,
        generation_report=GenerationReport(
            seed=cfg.seed,
            preset=cfg.setup_preset,
            board_size=n,
            generation_attempts=1,
            opening_legal_move_count=opening_count,
            piece_type_reports=tuple(reports),
            filter_results=filter_results,
        ),
    )


def generate_game(config: GeneratorConfig | dict | None = None) -> GeneratedGame:
    """Generate a compiled game from ``config`` (a GeneratorConfig or dict)."""
    if config is None:
        raise GenerationError("generate_game requires a config with a seed")
    cfg = config if isinstance(config, GeneratorConfig) else GeneratorConfig(**config)
    rng = random.Random(cfg.seed)
    last_error: Exception | None = None
    for attempt in range(cfg.max_generation_attempts):
        try:
            game = _try_generate(rng, cfg)
            report = replace(
                game.generation_report,
                generation_attempts=attempt + 1,
            )
            return GeneratedGame(game.ruleset, game.compiled_ruleset, report)
        except (RuleValidationError, GenerationError) as exc:  # pragma: no cover - exercised
            last_error = exc
            continue
    raise GenerationError(
        f"no valid game generated after {cfg.max_generation_attempts} attempts; last error: {last_error}"
    )
