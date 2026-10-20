"""Bounded legal-history search for material-feature aliasing in a guarded rule."""
from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from pathlib import Path
import random
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
TASK = ROOT / "results/dev_aux/task2628"
INPUTS = ROOT / "results/dev_aux/task2411/inputs.json"
OUTPUT = TASK / "feature-context-alias-v2.json"
DROP_PATTERN = "sem_00_drop_zone_capacity_guard"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> dict:
    if OUTPUT.exists():
        raise FileExistsError("context alias witness is write-once")
    from generic_chess.rules.compiler import compile_ruleset_for_execution
    from generic_chess.rules.schema import ruleset_from_dict
    from generic_chess.session.serialization import deserialize_game_record
    from generic_chess.session.session import GameSession
    from results.dev_aux.task2511.generic import NonScoringTerminal
    from results.dev_aux.task2621.fixed_scale import FixedScaleSessionEnv

    cases = json.loads(INPUTS.read_text(encoding="utf-8"))
    source_hash = sha(INPUTS)
    witness = None
    examined = 0
    bound = {"trials_per_case": 120, "max_plies": 50, "total_state_cap": 12_000}
    for case_index, case in enumerate(cases):
        rules_path = ROOT / case["rules"]
        rules = json.loads(rules_path.read_text(encoding="utf-8"))
        compiled = compile_ruleset_for_execution(ruleset_from_dict(rules))
        guard = next(g for action in rules["semantic_actions"]
                     for g in action.get("state_guards", [])
                     if g.get("spatial", {}).get("kind") == "zone")
        zone = [tuple(square) for square in guard["spatial"]["zone_squares"]]
        seen: dict[tuple[tuple[int, ...], int], dict[int, dict]] = defaultdict(dict)
        for trial in range(bound["trials_per_case"]):
            env = FixedScaleSessionEnv(GameSession.replay(compiled,
                deserialize_game_record(json.dumps(case["record"]))))
            rng = random.Random(2_411_000 + case_index * 1000 + trial)
            for ply in range(bound["max_plies"]):
                examined += 1
                if examined > bound["total_state_cap"]:
                    break
                try:
                    terminal = env.terminal()
                except NonScoringTerminal:
                    break
                if terminal is not None:
                    break
                actions = env.actions()
                drop_actions = [a for a in actions if getattr(getattr(a, "action", None), "pattern_id", None) == DROP_PATTERN]
                key = (tuple(env.features()), env.player())
                position = env.session.state.position
                hand_types = [type_id for type_id, count in position.hands[position.side_to_move].counts if count]
                if "R" in hand_types:
                    zone_count = sum(
                        1 for file, rank in zone
                        if (piece := position.board[rank * rules["board_size"] + file]) is not None
                        and piece.owner == position.side_to_move and piece.current_type_id == "R"
                    )
                    guard_open = zone_count < guard["value"]
                    seen[key].setdefault(guard_open, {
                        "record": env.record(), "zone_count": zone_count,
                        "hand_R": position.hands[position.side_to_move].count("R"),
                        "guard_open": guard_open,
                        "legal_guarded_drop_count": len(drop_actions),
                    })
                    if (len(seen[key]) > 1
                            and len({state["legal_guarded_drop_count"] for state in seen[key].values()}) > 1):
                        statuses = sorted(seen[key])
                        witness = {
                            "rule_path": case["rules"], "rule_sha256": sha(rules_path),
                            "case_index": case_index, "trial": trial, "ply": ply,
                            "features": list(key[0]), "side_to_move": key[1],
                            "guard_zone": [list(square) for square in zone],
                            "guard_comparison": f"current self R count < {guard['value']}",
                            "states": [seen[key][status] for status in statuses],
                            "states_examined": examined,
                        }
                        break
                if not actions:
                    break
                env.push(rng.choice(actions))
            if witness or examined > bound["total_state_cap"]:
                break

    if witness is None:
        result = {"status": "NO_ALIAS_FOUND_WITHIN_BOUND", "search_bound": bound,
                  "states_examined": examined, "inputs_sha256": source_hash}
    else:
        if witness["states"][0]["guard_open"] == witness["states"][1]["guard_open"]:
            raise AssertionError("witness does not cross the registered zone-guard threshold")
        if witness["states"][0]["legal_guarded_drop_count"] == witness["states"][1]["legal_guarded_drop_count"]:
            raise AssertionError("witness does not differ in guarded action availability")
        result = {
            "status": "PASS_LEGAL_MATERIAL_FEATURE_ALIAS_WITNESS",
            "search_bound": bound, "inputs_sha256": source_hash,
            "fixed_scale_source_sha256": sha(ROOT / "results/dev_aux/task2621/fixed_scale.py"),
            "witness": witness,
            "interpretation": "Two legal full-history states share the same signed global board-current/hand-base feature vector and player to move, while the count in the exact guard zone crosses the rule's threshold and guarded drop availability differs. This shows the fixed material-only leaf representation aliases a rule-relevant distinction; search still has full GameSession legality. It is a scoped representation witness, not a learner-strength or population result.",
            "no_outcomes_used": True,
        }
    with OUTPUT.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2, sort_keys=True))
    return result


if __name__ == "__main__":
    main()
