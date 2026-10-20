from __future__ import annotations

import hashlib
import json
import time
from collections import Counter
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
PLAN = HERE / "promotion-order-preflight-plan.json"
GAMES = HERE / "utility-run" / "games.jsonl"
OUT = HERE / "promotion-order-preflight.json"

import sys
sys.path.insert(0, str(ROOT))

from generic_chess.ai.alphabeta.ordering import MoveOrderer, StagedMovePicker
from generic_chess.ai.alphabeta.statistics import SearchStatistics
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.ai.evaluation.config import EvaluationConfig
from generic_chess.ai.evaluation.evaluator import Evaluator
from generic_chess.ai.evaluation.profile import build_ruleset_profile
from generic_chess.core.actions import action_from_dict, action_promotion_target_id
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.session.session import GameSession


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


class TargetValueOnly:
    def __init__(self, unit: Evaluator, static_values: dict[str, int]):
        self.unit = unit
        self.static_values = static_values

    def evaluate(self, state):
        return self.unit.evaluate(state)

    def capture_order_value(self, moving_piece, captured_piece):
        return self.unit.capture_order_value(moving_piece, captured_piece)

    def type_value(self, type_id: str) -> int:
        return self.static_values[type_id]


def main() -> None:
    if OUT.exists():
        raise RuntimeError("NO_OVERWRITE")
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    lines = [line for line in GAMES.read_text(encoding="utf-8").splitlines() if line]
    games = [json.loads(line) for line in lines]
    rules_by_seed: dict[int, dict] = {}
    for g in games:
        seed = int(g["root_id"].split("-")[0])
        if seed not in rules_by_seed:
            p = HERE / "utility-run" / f"rule-{seed}.json"
            rules_by_seed[seed] = json.loads(p.read_text(encoding="utf-8"))

    caches = {}
    events = []
    tallies = Counter()
    start = time.perf_counter()
    for game in games:
        seed = int(game["root_id"].split("-")[0])
        if seed not in caches:
            compiled = compile_legacy_ruleset_for_semantic_execution(
                ruleset_from_dict(rules_by_seed[seed])
            )
            profile = build_ruleset_profile(compiled, EvaluationConfig())
            unit_values = {
                pt.type_id: (0 if pt.is_anchor else 1000)
                for pt in compiled.piece_types
            }
            unit_profile = replace(
                profile,
                board_value_by_type=unit_values,
                hand_value_by_base_type={
                    pt.type_id: (0 if pt.is_anchor else 900)
                    for pt in compiled.piece_types
                },
                promotion_gain_by_type={},
            )
            cfg = EvaluationConfig(promotion_potential_weight=0)
            unit = Evaluator(compiled, unit_profile, cfg)
            static = TargetValueOnly(unit, profile.board_value_by_type)
            caches[seed] = compiled, unit, static
        compiled, unit, static = caches[seed]
        session = GameSession(compiled)
        actions = [action_from_dict(a) for a in game["full_record"]["actions"]]
        for ply, chosen in enumerate(actions):
            legal = session.legal_actions()
            if chosen not in legal:
                raise RuntimeError(f"ILLEGAL_REPLAY:{game['game_id']}:{ply}")
            promotions = [a for a in legal if action_promotion_target_id(a) is not None]
            if len(promotions) >= 2:
                orderings = []
                for ev in (unit, static):
                    picker = StagedMovePicker(
                        session.state, legal, ev, 1, None, None,
                        MoveOrderer(), SearchTuning(use_staged_move_picker=True),
                        SearchStatistics(),
                    )
                    ordered = [a for a in picker if action_promotion_target_id(a) is not None]
                    orderings.append(ordered)
                targets = [action_promotion_target_id(a) for a in promotions]
                changed = orderings[0] != orderings[1]
                tallies["multi_promotion_states"] += 1
                tallies["order_changed_states"] += int(changed)
                tallies["distinct_target_states"] += int(len(set(targets)) > 1)
                tallies[f"owner_{game['candidate_owner']}_states"] += 1
                tallies[f"parity_{ply % 2}_states"] += 1
                if changed:
                    events.append({
                        "game_id": game["game_id"], "root_id": game["root_id"],
                        "seed": seed, "candidate_owner": game["candidate_owner"],
                        "ply": ply, "prefix_parity": ply % 2,
                        "targets": targets,
                        "unit_order": [action_promotion_target_id(a) for a in orderings[0]],
                        "static_order": [action_promotion_target_id(a) for a in orderings[1]],
                    })
            session.submit(chosen)
        replayed = GameSession.replay(compiled, session.to_record())
        if (replayed.state, replayed.history, replayed._search_witnesses, replayed.result) != (
            session.state, session.history, session._search_witnesses, session.result
        ):
            raise RuntimeError(f"FINAL_REPLAY_MISMATCH:{game['game_id']}")
        tallies["complete_replays"] += 1

    out = {
        "status": "COMPLETE",
        "question": plan["question"],
        "plan_sha256": sha(PLAN.read_bytes()),
        "games_sha256": sha(GAMES.read_bytes()),
        "games": len(games),
        "rules": len(rules_by_seed),
        "tallies": dict(sorted(tallies.items())),
        "changed_examples": events[:12],
        "elapsed_seconds": time.perf_counter() - start,
        "started_at_utc": utc(),
        "limits": "Exposed retained records only; mechanism reachability, not utility, population frequency, or default validation.",
    }
    print(json.dumps(out, sort_keys=True))
    OUT.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k: out[k] for k in ("status", "games", "rules", "tallies", "elapsed_seconds", "plan_sha256", "games_sha256")}, sort_keys=True))


if __name__ == "__main__":
    main()
