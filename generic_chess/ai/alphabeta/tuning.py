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
    # Experimental: stable quiet-slot preference for unconditional enemy leap
    # geometry. Main search only; no legality/pruning/evaluation shortcut.
    use_quiet_geometric_coverage: bool = False
    # Experimental opportunity-normalized history, main quiet slots only.
    use_relative_history: bool = False
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
    # ordinary qsearch. Actual captures/material changes/terminals and all
    # evasions stay; legacy promotion metadata retains its historical shortcut.
    use_capture_only_qsearch: bool = False

    # Opt-in output contract: validate a complete cached principal line or
    # replay its nodes. Non-principal TT cutoffs remain available.
    require_full_pv: bool = False

    # Scope of opt-in q ordering. False preserves lexical check evasions while
    # ordinary q actions use the existing orderer. Ignored when q ordering is off.
    # True retains the historical all-q behavior; defaults do not enable ordering.
    use_ordered_qsearch_in_check: bool = True

    # Opt-in objective for callers that need any completed root win (e.g. a
    # shallow playability screen), not the shortest mate or a full iteration.
    # The result keeps its actual source, last complete depth and stop reason.
    stop_after_root_win: bool = False

    # Opt-in exact component hashing for certified plain-Leaper semantic moves.
    # Core transition, history, terminal and TT guards retain their full semantics.
    use_plain_leaper_local_hash: bool = False

    # Opt-in lazy Python identity-hash memo for the same admitted Leaper scope.
    # Exact position/history equality is unchanged; external identities stay SHA.
    use_cached_position_identity_hash: bool = False

    # Experimental: spend at most one main-search ply on a positive-depth
    # checked node per path; qsearch policy is unchanged. Default OFF.
    use_one_check_extension: bool = False
