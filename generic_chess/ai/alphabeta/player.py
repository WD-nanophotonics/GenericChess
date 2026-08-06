"""AlphaBetaPlayer: the public AI player interface."""

from __future__ import annotations

import time

from ...rules.compiled import CompiledRuleSet
from ...session.session import GameSession
from ..cancellation import CancellationToken
from ..decision import PlayerDecision
from ..evaluation.cache import EvaluationProfileCache
from ..evaluation.config import EvaluationConfig
from ..evaluation.evaluator import Evaluator
from ..limits import SearchLimits
from .search import run_root_search
from .statistics import SearchStatistics
from .transposition import TranspositionTable
from .tuning import SearchTuning


class AlphaBetaPlayer:
    """Deterministic, rule-derived alpha-beta player for any GenericChess RuleSet.

    The evaluation profile is built once per RuleSet (cached); the
    transposition table is kept across moves for the same RuleSet and cleared
    when a different RuleSet is loaded.
    """

    def __init__(
        self,
        compiled: CompiledRuleSet,
        *,
        evaluation_config: EvaluationConfig | None = None,
        tt_max_entries: int = 250_000,
        profile_cache: EvaluationProfileCache | None = None,
        use_disk_cache: bool = True,
        disk_cache_dir: str | None = None,
        use_tt: bool = True,
        use_ordering: bool = True,
        tuning: SearchTuning = SearchTuning(),
    ) -> None:
        self._compiled = compiled
        self._config = evaluation_config if evaluation_config is not None else EvaluationConfig()
        self._profile_cache = profile_cache or EvaluationProfileCache(
            use_disk=use_disk_cache, disk_dir=disk_cache_dir
        )
        self._profile, self._profile_cache_hit = self._profile_cache.get_or_build(
            compiled, self._config
        )
        self._evaluator = Evaluator(compiled, self._profile, self._config)
        self._tt = TranspositionTable(max_entries=tt_max_entries)
        self._use_tt = use_tt
        self._use_ordering = use_ordering
        self._tuning = tuning

    @property
    def compiled(self) -> CompiledRuleSet:
        return self._compiled

    @property
    def evaluation_profile(self):
        return self._profile

    @property
    def evaluation_profile_cache_hit(self) -> bool:
        return self._profile_cache_hit

    def reset(self) -> None:
        """Clear search state (e.g., after loading a different RuleSet)."""
        self._tt.clear()

    def choose_action(
        self,
        session: GameSession,
        limits: SearchLimits,
        *,
        cancel_token: CancellationToken | None = None,
        progress_callback=None,
        recorder=None,
    ) -> PlayerDecision:
        state = session.state
        started = time.monotonic()
        stats = SearchStatistics()
        action, score, pv, reason = run_root_search(
            state,
            self._compiled,
            self._evaluator,
            self._tt,
            limits,
            cancel_token,
            stats,
            use_tt=self._use_tt,
            use_ordering=self._use_ordering,
            tuning=self._tuning,
            recorder=recorder,
            progress_callback=progress_callback,
        )
        elapsed = time.monotonic() - started
        return PlayerDecision(
            action=action,
            score=score,
            principal_variation=pv,
            completed_depth=stats.completed_depth,
            selective_depth=stats.selective_depth,
            nodes=stats.nodes,
            qnodes=stats.qnodes,
            elapsed_seconds=elapsed,
            tt_probes=stats.tt_probes,
            tt_hits=stats.tt_hits,
            tt_cutoffs=stats.tt_cutoffs,
            beta_cutoffs=stats.beta_cutoffs,
            evaluation_profile_cache_hit=self._profile_cache_hit,
            termination_reason=reason,
            qdepth_cutoffs=stats.qdepth_cutoffs,
            qsearch_budget_aborts=stats.qsearch_budget_aborts,
            qsearch_check_hard_limit_aborts=stats.qsearch_check_hard_limit_aborts,
            in_check_qnodes=stats.in_check_qnodes,
            stand_pat_cutoffs=stats.stand_pat_cutoffs,
            capture_qactions=stats.capture_qactions,
            promotion_qactions=stats.promotion_qactions,
            checking_move_qactions=stats.checking_move_qactions,
            checking_drop_qactions=stats.checking_drop_qactions,
            nonchecking_drop_excluded=stats.nonchecking_drop_excluded,
            pvs_null_window_searches=stats.pvs_null_window_searches,
            pvs_researches=stats.pvs_researches,
            aspiration_fail_low=stats.aspiration_fail_low,
            aspiration_fail_high=stats.aspiration_fail_high,
            aspiration_researches=stats.aspiration_researches,
            root_scan_nodes=stats.root_scan_nodes,
            root_scan_used_fallback=stats.root_scan_used_fallback,
            move_picker_generated=stats.move_picker_generated,
            move_picker_yielded=stats.move_picker_yielded,
            move_picker_yielded_by_stage=dict(stats.move_picker_yielded_by_stage),
            ordering_calls=stats.ordering_calls,
            ordered_moves=stats.ordered_moves,
            ordering_seconds=stats.ordering_seconds,
            legal_generation_calls=stats.legal_generation_calls,
            legal_generation_seconds=stats.legal_generation_seconds,
            evaluation_calls=stats.evaluation_calls,
            evaluation_seconds=stats.evaluation_seconds,
            countermove_hits=stats.countermove_hits,
            mate_pruning_cutoffs=stats.mate_pruning_cutoffs,
            legal_actions_generated=stats.legal_actions_generated,
            successor_handles_created=stats.successor_handles_created,
            successors_materialized=stats.successors_materialized,
            successors_searched=stats.successors_searched,
            terminal_results_computed=stats.terminal_results_computed,
            terminal_cache_hits=stats.terminal_cache_hits,
            position_keys_computed=stats.position_keys_computed,
            position_key_cache_hits=stats.position_key_cache_hits,
        )
