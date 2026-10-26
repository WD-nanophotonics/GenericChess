"""Player decision result."""

from __future__ import annotations

from dataclasses import dataclass, field

from ..core.actions import Action


@dataclass(frozen=True, slots=True)
class PlayerDecision:
    """Result of one ``Player.choose_action`` call.

    ``action`` is ``None`` for terminal positions or already finished sessions.
    A selected declaration is represented separately. Scores are always in
    the side-to-move perspective of the root position. If a bounded search is
    interrupted before a full iteration completes, ``action`` can still hold a
    legal root fallback while ``principal_variation`` is empty. Otherwise the
    variation is the line from the last completed iteration (or a separately
    completed root proof).
    """

    action: Action | None
    score: int
    principal_variation: tuple[Action, ...]
    completed_depth: int
    selective_depth: int
    nodes: int
    qnodes: int
    elapsed_seconds: float
    tt_probes: int
    tt_hits: int
    tt_cutoffs: int
    beta_cutoffs: int
    evaluation_profile_cache_hit: bool
    termination_reason: str
    choice_kind: str = "ACTION"
    declaration: object | None = None
    time_to_first_legal_action: float | None = None
    time_to_first_completed_iteration: float | None = None
    # Fine-grained diagnostics (0.6.0 search lab).
    qdepth_cutoffs: int = 0
    qsearch_budget_aborts: int = 0
    qsearch_check_hard_limit_aborts: int = 0
    in_check_qnodes: int = 0
    stand_pat_cutoffs: int = 0
    capture_qactions: int = 0
    promotion_qactions: int = 0
    checking_move_qactions: int = 0
    checking_drop_qactions: int = 0
    nonchecking_drop_excluded: int = 0
    pvs_null_window_searches: int = 0
    pvs_researches: int = 0
    aspiration_fail_low: int = 0
    aspiration_fail_high: int = 0
    aspiration_researches: int = 0
    root_scan_nodes: int = 0
    root_scan_used_fallback: bool = False
    move_picker_generated: int = 0
    move_picker_yielded: int = 0
    move_picker_yielded_by_stage: dict[str, int] = field(default_factory=dict)
    ordering_calls: int = 0
    ordered_moves: int = 0
    ordering_seconds: float = 0.0
    legal_generation_calls: int = 0
    legal_generation_seconds: float = 0.0
    evaluation_calls: int = 0
    evaluation_seconds: float = 0.0
    countermove_hits: int = 0
    mate_pruning_cutoffs: int = 0
    legal_actions_generated: int = 0
    successor_handles_created: int = 0
    successors_materialized: int = 0
    successors_searched: int = 0
    terminal_results_computed: int = 0
    terminal_cache_hits: int = 0
    position_keys_computed: int = 0
    position_key_cache_hits: int = 0
    declaration_checks: int = 0
    declaration_win_options: int = 0
    declaration_restart_options: int = 0
    declaration_root_selected: bool = False
    # Successful Native legality calls and operational fallback evidence.
    # Provider availability alone does not establish the route actually used.
    native_legality_calls: int = 0
    native_legality_fallbacks: int = 0
    native_legality_operational_failures: int = 0
    # Appended to preserve existing optional positional argument order.
    material_change_qactions: int = 0

    # Source of the retained result, independent of why the search stopped.
    # Q fields describe its iteration policy, not a uniform leaf/horizon proof:
    # check extensions and selective TT reuse retain their existing semantics.
    result_source: str = "unknown"
    result_ordinary_qdepth: int | None = None
    result_check_hard_qdepth: int | None = None

    # Completed Core search-runtime pushes include q-action classification and
    # root probes as well as searched successors. They exclude failed pushes
    # and S3 candidate trials; nodes/qnodes keep their existing budget meaning.
    # None means this player/result did not report a Core runtime observation.
    # Append optional fields to preserve existing positional constructors.
    runtime_pushes: int | None = None
    runtime_pops: int | None = None
    runtime_depth_balanced: bool | None = None
    runtime_semantic_local_hash_updates: int | None = None
    runtime_position_identity_hash_cached: bool | None = None
    runtime_semantic_full_diff_fallbacks: int | None = None
