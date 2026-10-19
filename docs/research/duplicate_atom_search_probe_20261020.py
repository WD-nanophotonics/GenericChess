"""Reproduce the narrow duplicate legacy-ray profile/search probe.

This is one synthetic 5x5 legacy ruleset. It asks whether adding an exact
duplicate RayAtom changes the built-in profile, legal visible actions, or
public bounded AlphaBeta result. It is not a generated-domain invariance test.
"""
from __future__ import annotations

import json
from pathlib import Path
import random
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tests"))

from conftest import T, king_type, make_ruleset  # noqa: E402
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer  # noqa: E402
from generic_chess.ai.alphabeta.tuning import SearchTuning  # noqa: E402
from generic_chess.ai.evaluation.config import EvaluationConfig  # noqa: E402
from generic_chess.ai.evaluation.cache import (  # noqa: E402
    EvaluationProfileCache,
    MovementCapabilityCache,
)
from generic_chess.ai.limits import SearchLimits  # noqa: E402
from generic_chess.core.movegen import legal_actions  # noqa: E402
from generic_chess.core.movement import RayAtom  # noqa: E402
from generic_chess.generation.config import GeneratorConfig  # noqa: E402
from generic_chess.generation.piece_generator import generate_ordinary_types  # noqa: E402
from generic_chess.rules.compiler import compile_ruleset  # noqa: E402
from generic_chess.session.session import GameSession  # noqa: E402


def main() -> None:
    class CountingCapabilityCache(MovementCapabilityCache):
        def __init__(self) -> None:
            super().__init__()
            self.build_count = 0

        def get_or_build(self, n, atoms, config):
            profile, hit = super().get_or_build(n, atoms, config)
            if not hit:
                self.build_count += 1
            return profile, hit

    atom = RayAtom((0, 1))
    common = [king_type(), T("R", atom)]
    duplicated = [king_type(), T("R", atom, atom)]
    rows = ["....k", ".....", "..R..", ".....", "K...."]
    config = EvaluationConfig()
    capability_cache = CountingCapabilityCache()
    profile_cache = EvaluationProfileCache(
        use_disk=False, capability_cache=capability_cache
    )
    controls = {}
    for label, types in (("single", common), ("duplicate", duplicated)):
        compiled = compile_ruleset(make_ruleset(5, types, rows))
        profile, profile_cache_hit = profile_cache.get_or_build(compiled, config)
        repeated_profile, repeated_cache_hit = profile_cache.get_or_build(compiled, config)
        session = GameSession(compiled)
        legal = sorted(str(action) for action in legal_actions(session.state, compiled))
        player = AlphaBetaPlayer(
            compiled,
            evaluation_config=config,
            use_disk_cache=False,
            use_tt=False,
            use_ordering=False,
            tuning=SearchTuning(use_root_tactical=False),
        )
        results = {}
        for cap in (12, 16, 20, 24, 32, 48):
            decision = player.choose_action(
                session,
                SearchLimits(max_depth=8, max_nodes=cap, quiescence_max_depth=0),
            )
            results[str(cap)] = {
                "action": str(decision.action) if decision.action is not None else None,
                "score": decision.score,
                "depth": decision.completed_depth,
                "nodes": decision.nodes + decision.qnodes,
                "stop": decision.termination_reason,
                "pv": [str(action) for action in decision.principal_variation],
            }
        controls[label] = {
            "fingerprint": compiled.ruleset_fingerprint,
            "profile_cache_hit_on_first_lookup": profile_cache_hit,
            "profile_cache_hit_on_repeat_lookup": repeated_cache_hit,
            "repeat_returns_same_profile_object": repeated_profile is profile,
            "capability_cache_build_count": capability_cache.build_count,
            "movement_signature": profile.piece_profiles["R"].movement_signature,
            "raw_score": profile.piece_profiles["R"].raw_capability_score,
            "board_value": profile.board_value_by_type["R"],
            "hand_value": profile.hand_value_by_base_type["R"],
            "legal_count": len(legal),
            "unique_visible_action_count": len(set(legal)),
            "legal_actions": legal,
            "search": results,
        }

    a, b = controls["single"], controls["duplicate"]
    comparable = {
        "fingerprints_differ": a["fingerprint"] != b["fingerprint"],
        "profile_inputs_and_values_equal": all(
            a[k] == b[k] for k in ("movement_signature", "raw_score", "board_value", "hand_value")
        ),
        "legal_action_lists_equal": a["legal_actions"] == b["legal_actions"],
        "bounded_results_equal": a["search"] == b["search"],
    }
    generator_scan = {"configurations": 0, "piece_types": 0, "types_with_duplicate_atoms": 0}
    for board_size in (4, 8):
        for symmetry in ("none", "bilateral"):
            for allow_hybrid in (False, True):
                for seed in range(16):
                    cfg = GeneratorConfig(
                        seed=seed,
                        board_size=board_size,
                        movement_symmetry=symmetry,
                        allow_hybrid=allow_hybrid,
                        require_promotable_type=False,
                        require_nonpromotable_type=False,
                    )
                    types = generate_ordinary_types(
                        random.Random(seed), cfg, ("P", "N", "B", "R", "Q")
                    )
                    generator_scan["configurations"] += 1
                    for piece_type in types:
                        generator_scan["piece_types"] += 1
                        if len(piece_type.movement_atoms) != len(set(piece_type.movement_atoms)):
                            generator_scan["types_with_duplicate_atoms"] += 1
    print(json.dumps({"controls": controls, "comparison": comparable,
                      "generator_scan": generator_scan}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
