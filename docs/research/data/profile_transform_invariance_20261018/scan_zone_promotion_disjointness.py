"""Which rulesets have a promotion zone that is disjoint from every promotion source?

Structural question only. For each seed that ever pays the in-zone bonus in the
stored Stage 8 corpus, this script regenerates the seeded ruleset and asks
whether the evaluator promotion zone of any positively-valued base type
intersects the squares that appear as ``from_square`` in that type's compiled
``promotion_allowed`` pairs.

Why the answer is structural rather than behavioural: ``generic_chess/core/
movegen.py`` only builds a promotion variant when
``(from_square, to_square) in compiled.promotion_allowed[base_type_id][side]``.
A square that is not a promotion source therefore cannot carry a promotion
action at all, so a seed whose zone is disjoint from every source cannot
contribute to the in-zone contact column *by construction*. This artifact
records that partition and deliberately records no contact count and no rate
contrast; an apparent "0 contacts" group would be definitional, not evidence
about search behaviour.

Read-only with respect to the corpus: no search and no game replay, only
ruleset regeneration.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from generic_chess.ai.evaluation.config import EvaluationConfig  # noqa: E402
from generic_chess.ai.evaluation.evaluator import Evaluator  # noqa: E402
from generic_chess.ai.evaluation.profile import build_ruleset_profile  # noqa: E402
from generic_chess.core.coordinates import square_to_index  # noqa: E402
from generic_chess.generation.config import GeneratorConfig  # noqa: E402
from generic_chess.generation.generator import generate_game  # noqa: E402

HERE = Path(__file__).resolve().parent
STAGE8 = HERE / "results_bind_reachability_to_decisions.json"
PLAN = HERE / "plan_zone_promotion_disjointness.json"
OUT = HERE / "results_zone_promotion_disjointness.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def per_seed_opportunity() -> dict[int, int]:
    """In-zone paid observations per seed, read from the published Stage 8 file."""
    stage8 = json.loads(STAGE8.read_text(encoding="utf-8"))
    counts: dict[int, int] = {}
    for game in stage8["per_game"]:
        seed = game["seed"]
        counts[seed] = counts.get(seed, 0) + game["in_zone_at_start"] + game["in_zone_during_play"]
    return counts


def geometry(seed: int) -> dict:
    compiled = generate_game(
        GeneratorConfig(seed=seed, board_size=4, setup_preset="classic_like")
    ).compiled_ruleset
    config = EvaluationConfig()
    evaluator = Evaluator(compiled, build_ruleset_profile(compiled, config), config)
    zones = 0
    sources = 0
    intersection = 0
    pairs_with_zone = 0
    for base, gain in evaluator._profile.promotion_gain_by_type.items():
        if gain <= 0:
            continue
        for side in (0, 1):
            zone = evaluator._zones.get((base, side))
            if not zone:
                continue
            pairs_with_zone += 1
            allowed = compiled.promotion_allowed.get(base, ((), ()))[side]
            source_set = {square_to_index(src, compiled.board_size) for src, _dst in allowed}
            zones += len(zone)
            sources += len(source_set)
            intersection += len(zone & source_set)
    return {
        "seed": seed,
        "base_type_side_pairs_with_a_zone": pairs_with_zone,
        "zone_squares": zones,
        "promotion_source_squares": sources,
        "zone_squares_that_are_promotion_sources": intersection,
        "zone_disjoint_from_every_promotion_source": intersection == 0,
    }


def main() -> int:
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    opportunity = per_seed_opportunity()
    seeds = sorted(opportunity)
    rows = []
    for seed in seeds:
        row = geometry(seed)
        row["in_zone_paid_observations"] = opportunity[seed]
        row["can_contribute_an_in_zone_contact"] = not row["zone_disjoint_from_every_promotion_source"]
        rows.append(row)
    opportunity_seeds = [row for row in rows if row["in_zone_paid_observations"] > 0]
    disjoint_all = [row["seed"] for row in rows if row["zone_disjoint_from_every_promotion_source"]]
    disjoint_opportunity = [
        row["seed"] for row in opportunity_seeds if row["zone_disjoint_from_every_promotion_source"]
    ]
    payload = {
        "role": "DEEPSEEK_AUX",
        "session": "3d8dc073-5fcc-456e-933c-a7b6646296e5",
        "question": plan["question"],
        "plan": PLAN.name,
        "source": STAGE8.name,
        "source_sha256": sha256(STAGE8),
        "design": {
            "seeds": "every seed that appears in the stored Stage 8 per-game records",
            "zone": "evaluator._zones[(base_type_id, side)] for base types with a positive promotion gain",
            "promotion_sources": "from_square of compiled.promotion_allowed[base_type_id][side]",
            "counting": "per (base type, side) pair, so one square can be counted for more than one pair",
        },
        "seeds_examined": len(rows),
        "seeds_with_an_in_zone_paid_observation": len(opportunity_seeds),
        "seeds_whose_zone_is_disjoint_from_every_promotion_source": disjoint_all,
        "disjoint_seed_count": len(disjoint_all),
        "opportunity_seeds_whose_zone_is_disjoint": disjoint_opportunity,
        "opportunity_disjoint_seed_count": len(disjoint_opportunity),
        "structural_statement": (
            "For these seeds the evaluator promotion zone contains no square from which any "
            "positively-valued base type can promote, so no in-zone paid square in them can "
            "carry a legal promotion action. This follows from the contact definition plus "
            "compiled.promotion_allowed and is not evidence about how search chooses moves. "
            "The opportunity list restricts this to seeds that actually pay the in-zone bonus "
            "in the stored corpus."
        ),
        "per_seed": rows,
        "nonclaims": [
            "no contact count and no contact rate are recorded here; the withdrawn 0-vs-53 rate contrast is not reproduced",
            "no search-time or strength claim",
            "the partition depends on the served evaluator's zone definition and the compiled promotion pairs",
            "seeds that intersect yet show no contact are not explained by this artifact",
        ],
    }
    OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"seeds_examined={payload['seeds_examined']}")
    print(f"seeds_with_an_in_zone_paid_observation={len(opportunity_seeds)}")
    print(f"disjoint_seed_count={len(disjoint_all)}")
    print(f"opportunity_disjoint_seed_count={len(disjoint_opportunity)} seeds={disjoint_opportunity}")
    print("zone_disjointness_recorded")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

