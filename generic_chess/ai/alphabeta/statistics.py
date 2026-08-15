"""Mutable search statistics (hot-path counters)."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class SearchStatistics:
    nodes: int = 0
    qnodes: int = 0
    tt_probes: int = 0
    tt_hits: int = 0
    tt_cutoffs: int = 0
    tt_stores: int = 0
    tt_eligible_nodes: int = 0
    tt_skipped_ineligible_nodes: int = 0
    beta_cutoffs: int = 0
    completed_depth: int = 0
    selective_depth: int = 0
    termination_reason: str = ""
    time_to_first_legal_action: float | None = None
    time_to_first_completed_iteration: float | None = None
    # Quiescence truncation reasons and qsearch classification counts.
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
    # PVS.
    pvs_null_window_searches: int = 0
    pvs_researches: int = 0
    # Aspiration windows.
    aspiration_fail_low: int = 0
    aspiration_fail_high: int = 0
    aspiration_researches: int = 0
    # Root tactical scan.
    root_scan_nodes: int = 0
    root_scan_seconds: float = 0.0
    root_scan_used_fallback: bool = False
    # Staged move picker.
    move_picker_generated: int = 0
    move_picker_yielded: int = 0
    move_picker_yielded_by_stage: dict[str, int] = field(default_factory=dict)
    # Ordering / movegen / evaluation timing.
    ordering_calls: int = 0
    ordered_moves: int = 0
    ordering_seconds: float = 0.0
    legal_generation_calls: int = 0
    legal_generation_seconds: float = 0.0
    evaluation_calls: int = 0
    evaluation_seconds: float = 0.0
    # Countermove heuristic.
    countermove_hits: int = 0
    # Mate-distance pruning.
    mate_pruning_cutoffs: int = 0
    # Lazy successor experiment.
    legal_actions_generated: int = 0
    successor_handles_created: int = 0
    successors_materialized: int = 0
    successors_searched: int = 0
    terminal_results_computed: int = 0
    terminal_cache_hits: int = 0
    position_keys_computed: int = 0
    position_key_cache_hits: int = 0
    # F2 Core-owned search-path runtime instrumentation.
    runtime_pushes: int = 0
    runtime_pops: int = 0
    runtime_hash_updates: int = 0
    # ``runtime_exact_key_computations`` counts root/import boundary SHA work;
    # child external-key work is tracked separately and must remain zero in
    # normal runtime searches.
    runtime_exact_key_computations: int = 0
    runtime_child_external_key_computations: int = 0
    runtime_exact_position_comparisons: int = 0
    runtime_legacy_incremental_updates: int = 0
    runtime_semantic_full_diff_fallbacks: int = 0
    runtime_snapshot_exact_comparisons: int = 0
    runtime_collision_checks: int = 0
    runtime_collision_fallbacks: int = 0
    # History identity bridge instrumentation. Reconstruction is one-time
    # root/import work; opaque-history child keys are conditional fallback work.
    runtime_history_reconstruction_attempts: int = 0
    runtime_history_reconstruction_key_computations: int = 0
    runtime_history_witness_hits: int = 0
    runtime_history_witness_misses: int = 0
    runtime_opaque_history_child_external_key_computations: int = 0
    runtime_history_context_updates: int = 0
    runtime_history_context_exact_comparisons: int = 0
    runtime_tt_eligible: int = 0
    runtime_snapshot_updates: int = 0
    runtime_snapshot_entry_digest_calls: int = 0
    runtime_search_key_calls: int = 0
    runtime_history_tuple_copies: int = 0
    runtime_repetition_tuple_copies: int = 0
    runtime_root_imports: int = 0
    runtime_peak_depth: int = 0
    runtime_depth_balanced: bool = True
    # Optional Native semantic legality provider observability.  These are
    # populated through the Core-neutral SearchPathRuntime callback boundary.
    native_legality_enabled: int = 0
    native_legality_calls: int = 0
    native_legality_actions: int = 0
    native_legality_seconds: float = 0.0
    native_legality_payload_seconds: float = 0.0
    native_legality_decode_binding_seconds: float = 0.0
    native_legality_fallbacks: int = 0
    native_legality_operational_failures: int = 0
