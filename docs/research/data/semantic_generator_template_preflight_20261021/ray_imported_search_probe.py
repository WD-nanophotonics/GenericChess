"""One fixed ray candidate through serialized-rule import and public search."""
from __future__ import annotations

import json
import re
import sys
import tempfile
from contextlib import redirect_stdout
from dataclasses import replace
from io import StringIO
from pathlib import Path
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from ray_spread_setup import eligible_pairs, layout_for_seed  # noqa: E402
from generic_chess.ai.alphabeta import AlphaBetaPlayer, SearchTuning  # noqa: E402
from generic_chess.ai.cli.benchmark_alphabeta import main as benchmark_main  # noqa: E402
from generic_chess.ai.limits import SearchLimits  # noqa: E402
from generic_chess.generation.config import GeneratorConfig  # noqa: E402
from generic_chess.generation.generator import generate_game  # noqa: E402
from generic_chess.cli.play import _load_ruleset  # noqa: E402
from generic_chess.rules.schema import (  # noqa: E402
    RuleActionEffect, RuleGeometrySpec, RuleInvariant, RuleSemanticAction,
    RuleSquareRef, compute_fingerprint,
)
from generic_chess.rules.serialization import serialize_ruleset  # noqa: E402
from generic_chess.session.session import GameSession  # noqa: E402


def main() -> None:
    seed = 202610431
    base = generate_game(GeneratorConfig(seed=seed, board_size=6,
                                         setup_preset="classic_like"))
    fixture = layout_for_seed(base, seed)
    ruleset = fixture["ruleset"]
    if ruleset is None or fixture["attempt"] != 0:
        raise RuntimeError("prespecified deterministic three-rank fixture changed")
    pair = next((type_id, direction) for type_id, direction in eligible_pairs(base)
                if direction == (1, 0) and type_id == "X")
    type_id, direction = pair
    action = RuleSemanticAction(
        name="horizontal_ray_import_probe", type_ids=(type_id,),
        geometry=RuleGeometrySpec(kind="ray", direction=direction,
                                  min_steps=1, max_steps=3),
        target_relation="empty", composition="augment",
        effects=(RuleActionEffect("move", from_ref=RuleSquareRef("source"),
                                  to_ref=RuleSquareRef("target")),),
        invariants=(RuleInvariant("own_anchor_safe"),),
    )
    authored = replace(ruleset, semantic_actions=(action,))
    serialized = serialize_ruleset(authored)
    with tempfile.TemporaryDirectory(
            prefix="genericchess-ray-import-probe-",
            dir=HERE.parents[3] / ".local_agent") as directory:
        ruleset_path = Path(directory) / "fixture.json"
        ruleset_path.write_text(serialized, encoding="utf-8")
        compiled, imported = _load_ruleset(SimpleNamespace(
            ruleset=str(ruleset_path), builtin_ruleset=None, seed=None,
            board_size=None, preset=None, hybrid=False))
        benchmark_output = StringIO()
        with redirect_stdout(benchmark_output):
            benchmark_exit = benchmark_main([
                "--ruleset", str(ruleset_path), "--nodes", "64",
                "--max-depth", "1", "--repeat", "1", "--fresh-tt",
                "--no-disk",
            ])
        run_line = next(line for line in benchmark_output.getvalue().splitlines()
                        if line.startswith("run 1:"))
        match = re.search(
            r"run 1: action=(.*?) score=(-?\d+) depth=(\d+) nodes=(\d+) "
            r"qnodes=(\d+).*result_source=(\S+) reason=(\S+)$", run_line)
        if benchmark_exit != 0 or match is None:
            raise RuntimeError("benchmark AlphaBeta CLI failed to produce a run record")
    session = GameSession(compiled)
    before = session.state
    legal = session.legal_actions()
    pattern_id = next(p.pattern_id for p in compiled.ir.patterns
                      if p.pattern_id.endswith("horizontal_ray_import_probe"))
    ray_actions = tuple(a for a in legal if a.pattern_id == pattern_id)
    player = AlphaBetaPlayer(
        compiled, use_disk_cache=False, use_tt=False,
        use_native_semantic_legality=False,
        tuning=SearchTuning(use_root_tactical=False),
    )
    decision = player.choose_action(
        session, SearchLimits(max_depth=1, quiescence_max_depth=0))
    after = session.state
    if decision.nodes != len(legal) + 1 or decision.qnodes != 0:
        raise RuntimeError("fixed depth-1/qdepth-0 traversal did not account for root and each child")
    result = {
        "question": "Can one exposed unfamiliar ray rule survive RuleSet serialization/import and the public AlphaBeta consumer?",
        "scope": "One fixed seed/layout/type/direction through the actual CLI --ruleset loader; depth 1, qdepth 0, no games or outcomes.",
        "fixture": {"seed": seed, "layout_attempt": fixture["attempt"],
                    "opening_legal_actions": fixture["opening_count"],
                    "type_id": type_id, "direction": list(direction),
                    "max_steps": 3},
        "serialized_round_trip_equal": imported == authored,
        "compiled_ruleset_fingerprint_preserved": compiled.ruleset_fingerprint == compute_fingerprint(imported),
        "import_route": "generic_chess.cli.play._load_ruleset (--ruleset path)",
        "search_cli": {
            "entrypoint": "generic_chess.ai.cli.benchmark_alphabeta --ruleset",
            "exit_code": benchmark_exit,
            "action": match.group(1), "score": int(match.group(2)),
            "depth": int(match.group(3)), "nodes": int(match.group(4)),
            "qnodes": int(match.group(5)), "result_source": match.group(6),
            "termination_reason": match.group(7),
            "run_output_without_machine_timing": run_line.split(" elapsed=")[0],
        },
        "root": {"legal_action_count": len(legal),
                 "matching_ray_action_count": len(ray_actions),
                 "matching_ray_actions": [str(a) for a in ray_actions]},
        "public_search": {"choice_kind": decision.choice_kind,
                           "action": None if decision.action is None else str(decision.action),
                           "selected_ray_action": decision.action in ray_actions,
                           "selected_action_legal": decision.action in legal,
                           "root_child_nodes": decision.nodes - 1,
                           "all_root_legal_actions_received_one_child_node": decision.nodes - 1 == len(legal),
                           "completed_depth": decision.completed_depth,
                           "termination_reason": decision.termination_reason,
                           "nodes": decision.nodes, "qnodes": decision.qnodes,
                           "pv": [str(a) for a in decision.principal_variation]},
        "caller_state_unchanged": session.state == before == after,
        "limitations": ["single synthetic fixture", "no utility/outcome claim",
                        "does not establish a population or justify a generator default"],
    }
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
