"""Report representative TT usefulness counters for F3 closure evidence."""

from __future__ import annotations

import json
import sys
import time
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from ai_fixtures import build_4x4_rooks  # noqa: E402
from generic_chess.ai.alphabeta.search import run_root_search  # noqa: E402
from generic_chess.ai.alphabeta.statistics import SearchStatistics  # noqa: E402
from generic_chess.ai.alphabeta.transposition import TranspositionTable  # noqa: E402
from generic_chess.ai.alphabeta.tuning import SearchTuning  # noqa: E402
from generic_chess.ai.evaluation.config import EvaluationConfig  # noqa: E402
from generic_chess.ai.evaluation.evaluator import Evaluator  # noqa: E402
from generic_chess.ai.evaluation.profile import build_ruleset_profile  # noqa: E402
from generic_chess.ai.limits import SearchLimits  # noqa: E402
from generic_chess.session.session import GameSession  # noqa: E402
from test_f3_corrective_r1 import _semantic_shogi, _session_from_texts, _session_with_seed  # noqa: E402


def run_case(label, session, compiled, depth):
    legacy = getattr(compiled, "_legacy_compiled", compiled)
    config = EvaluationConfig()
    evaluator = Evaluator(legacy, build_ruleset_profile(legacy, config), config)
    stats = SearchStatistics()
    started = time.perf_counter()
    result = run_root_search(
        session.state,
        compiled,
        evaluator,
        TranspositionTable(),
        SearchLimits(max_depth=depth, max_nodes=1200, quiescence_max_depth=0),
        None,
        stats,
        use_tt=True,
        use_ordering=False,
        tuning=SearchTuning(use_root_tactical=False),
        _history_witnesses=session._search_witnesses,
    )
    return {
        "case": label,
        "depth_limit": depth,
        "elapsed_ms": round((time.perf_counter() - started) * 1000, 3),
        "action": str(result[0]) if result[0] is not None else None,
        "score": result[1],
        "nodes": stats.nodes,
        "qnodes": stats.qnodes,
        "completed_depth": stats.completed_depth,
        "tt_eligible_nodes": stats.tt_eligible_nodes,
        "tt_skipped_ineligible_nodes": stats.tt_skipped_ineligible_nodes,
        "tt_probes": stats.tt_probes,
        "tt_hits": stats.tt_hits,
        "tt_cutoffs": stats.tt_cutoffs,
        "tt_stores": stats.tt_stores,
    }


def main() -> int:
    legacy = build_4x4_rooks()
    continuous = replace(legacy, repetition_policy="continuous_check_loss")
    cases = [
        run_case("legacy-draw-root", GameSession(legacy), legacy, 2),
        run_case(
            "continuous-check-prefix",
            _session_from_texts(continuous, ("a1-a2", "b3-b2", "a2-a1", "b2-b3")),
            continuous,
            3,
        ),
    ]
    semantic = _semantic_shogi()
    cases.append(run_case("semantic-shogi-prefix", _session_with_seed(semantic, 1, 1), semantic, 2))
    print(json.dumps(cases, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
