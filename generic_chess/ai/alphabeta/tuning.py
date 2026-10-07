"""Ablation switches for the generic alpha-beta search (benchmark-driven)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SearchTuning:
    """Per-feature switches for the generic alpha-beta search.

    Advanced features default to OFF so the desktop UI keeps the well-tested
    baseline; benchmark profiles enable them one at a time so each can be
    measured in isolation.  ``use_root_tactical`` is on by default because it
    only improves the fallback path (never a full-iteration result).

    SEE / LMR / lazy-full-evaluation / mate-probe switches are intentionally
    absent: they belong to later phases and would otherwise be dead config.
    """

    use_pvs: bool = False
    use_aspiration: bool = False
    use_staged_move_picker: bool = False
    use_countermove: bool = False
    use_mate_distance_pruning: bool = False
    use_root_tactical: bool = True
    # Experimental: lazily materialize child states only when searched.
    # Default OFF; baseline path remains the default.
    use_lazy_successors: bool = False

    aspiration_delta: int = 50
    aspiration_start_depth: int = 4
    history_max: int = 2**16
    quiet_buckets: int = 8

    # Opt-in: at a static qdepth=0 leaf, search mandatory check evasions only.
    # Nonchecking leaves keep static evaluation; ordinary captures are not added.
    use_check_only_qsearch: bool = False

    # Opt-in reuse of the existing move orderer inside qsearch only.
    # Preserves all noisy actions/evasions; changes neither evaluation nor depth.
    use_ordered_qsearch: bool = False

    # Development hypothesis: outside check, omit quiet checking actions from
    # ordinary qsearch. Captures/promotions/terminal actions and all evasions stay.
    use_capture_only_qsearch: bool = False

    # Opt-in output contract: validate a complete cached principal line or
    # replay its nodes. Non-principal TT cutoffs remain available.
    require_full_pv: bool = False
