"""Named SearchTuning profiles used by the benchmark (never UI defaults)."""

from __future__ import annotations

from dataclasses import dataclass

from ..alphabeta.tuning import SearchTuning


@dataclass(frozen=True, slots=True)
class BenchmarkProfile:
    name: str
    tuning: SearchTuning


PROFILES: dict[str, BenchmarkProfile] = {
    "baseline": BenchmarkProfile("baseline", SearchTuning()),
    "pvs": BenchmarkProfile("pvs", SearchTuning(use_pvs=True)),
    "pvs_aspiration": BenchmarkProfile(
        "pvs_aspiration", SearchTuning(use_pvs=True, use_aspiration=True)
    ),
    "staged_picker": BenchmarkProfile(
        "staged_picker", SearchTuning(use_staged_move_picker=True)
    ),
    "countermove": BenchmarkProfile(
        "countermove", SearchTuning(use_countermove=True)
    ),
    "mate_distance": BenchmarkProfile(
        "mate_distance", SearchTuning(use_mate_distance_pruning=True)
    ),
    "full_candidate": BenchmarkProfile(
        "full_candidate",
        SearchTuning(
            use_pvs=True,
            use_aspiration=True,
            use_staged_move_picker=True,
            use_countermove=True,
            use_mate_distance_pruning=True,
        ),
    ),
}

ALL_PROFILES: tuple[str, ...] = (
    "baseline",
    "pvs",
    "pvs_aspiration",
    "staged_picker",
    "countermove",
    "mate_distance",
    "full_candidate",
)


def profile_by_name(name: str) -> BenchmarkProfile:
    return PROFILES[name]


def all_profiles() -> list[BenchmarkProfile]:
    return [PROFILES[name] for name in ALL_PROFILES]
