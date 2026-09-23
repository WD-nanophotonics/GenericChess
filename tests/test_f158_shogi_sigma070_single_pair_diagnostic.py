import json
from pathlib import Path

from scripts import f153_shogi_material_mutation_root_sensitivity as f153
from scripts import f158_shogi_sigma070_single_pair_diagnostic as diagnostic
from scripts.f144_shogi_material_only_arena_evolution import GEN0_SEED, gen0_vector


def test_f158_resource_ceiling_is_one_pair_and_bounded():
    assert diagnostic.MAX_GAMES == 2
    assert diagnostic.MAX_CONCURRENT_GAMES == 1
    assert diagnostic.OPENING_COUNT == 1
    assert diagnostic.MAX_TOTAL_PLIES_PER_GAME == 128
    assert diagnostic.MAX_TOTAL_PLIES_PER_GAME * diagnostic.MAX_GAMES == 256
    assert diagnostic.MAX_TOTAL_NODES == 224_000
    assert diagnostic.MAX_WALL_SECONDS == 14 * 60


def test_heavy_envelope_matches_executable_hard_caps():
    root = Path(diagnostic.__file__).resolve().parents[1]
    envelope = json.loads((root / ".generic_chess_flow/f158-sigma070-single-pair-envelope.json").read_text(encoding="utf-8"))
    assert envelope["maximum_games"] == diagnostic.MAX_GAMES
    assert envelope["maximum_concurrent_games"] == diagnostic.MAX_CONCURRENT_GAMES
    assert envelope["maximum_plies"] == diagnostic.MAX_GAMES * diagnostic.MAX_TOTAL_PLIES_PER_GAME
    assert envelope["maximum_nodes"] == diagnostic.MAX_TOTAL_NODES
    assert envelope["hard_wall_minutes"] * 60 > diagnostic.MAX_WALL_SECONDS


def test_mutant_is_the_f153_sigma070_root_divergent_direction():
    gen0 = tuple(gen0_vector(GEN0_SEED))
    sigma070_stage = f153.mutation_vectors_at_sigma(gen0, diagnostic.SIGMA)
    mutant = sigma070_stage[diagnostic.MUTANT_INDEX]
    assert mutant != gen0
    assert len(sigma070_stage) == 6
    assert diagnostic.SIGMA == 0.70


def test_f158_has_fixed_single_opening_and_role_swapped_game_order():
    assert diagnostic.OPENING_SEED not in {1_510_101, 1_530_101}
    assert diagnostic.HISTORICAL_OPENING_IDS == {
        "5738e1f589b8096372ce9c369692937123c13a383f70ceb44ec4f6a19a9bfd2b",
        "742b4fc33ad8a8e9e57369f74b7544245622932fe16d99326f82a9163c1b801c",
        "b046dec8bd8675adfbbc6dc1c0d439ffbd878c8b08a433ab84abb200b119160b",
    }
    assert diagnostic.ROLE_ORDER == (0, 1)
    assert diagnostic.PRIOR_ROOT_DIVERGENCE["source"].startswith("F153 sigma .70")
import json
from pathlib import Path
