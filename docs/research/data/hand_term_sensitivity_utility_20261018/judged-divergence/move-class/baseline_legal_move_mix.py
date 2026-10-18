"""Zero-search legal-move baseline for the judged first-divergence positions.

Reconstructs each stored divergence position from the frozen game files,
counts legal actions by class (drop / promotion / quiet), and compares the
observed first-divergence choices with that availability. No search is run.
"""

from __future__ import annotations

import hashlib
import json
import random
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
JUDGED_DIR = HERE.parent
EVIDENCE = JUDGED_DIR.parent
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from generic_chess.core.actions import (  # noqa: E402
    BoardMove,
    DropMove,
    SemanticBoardMove,
    SemanticDropMove,
)
from generic_chess.core.coordinates import Square  # noqa: E402
from generic_chess.core.movegen import legal_actions  # noqa: E402
from generic_chess.core.transition import (  # noqa: E402
    apply_action,
    initial_state,
    legal_successors,
)
from generic_chess.generation.config import GeneratorConfig  # noqa: E402
from generic_chess.generation.generator import generate_game  # noqa: E402

PRIMARY = JUDGED_DIR / "results_judged_divergence.json"
PLAN = HERE / "plan-legal-move-baseline.json"
RESULT = HERE / "results_move_class_baseline.json"
EXPECTED_PRIMARY_SHA256 = (
    "444CDA2632E59ABBB06A2C747AA22A0488385C38C7E987E1B3B70B3434882979"
)
START_PLY = 8
MIN_START_ACTIONS = 6

BOARD_RE = re.compile(
    r"BoardMove\(from_square=Square\(file=(\d), rank=(\d)\), "
    r"to_square=Square\(file=(\d), rank=(\d)\), "
    r"promotion_target_id=(None|'([^']+)')\)$"
)
DROP_RE = re.compile(
    r"DropMove\(base_type_id='([^']+)', "
    r"to_square=Square\(file=(\d), rank=(\d)\)\)$"
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def parse_action(text: str):
    board = BOARD_RE.match(text)
    if board:
        target = board.group(6) if board.group(5) != "None" else None
        return BoardMove(
            Square(int(board.group(1)), int(board.group(2))),
            Square(int(board.group(3)), int(board.group(4))),
            target,
        )
    drop = DROP_RE.match(text)
    if drop:
        return DropMove(drop.group(1), Square(int(drop.group(2)), int(drop.group(3))))
    raise ValueError(f"unparseable action {text!r}")


def class_of(action) -> str:
    if isinstance(action, (DropMove, SemanticDropMove)):
        return "drop"
    if isinstance(action, (BoardMove, SemanticBoardMove)):
        return "quiet" if action.promotion_target_id is None else "promotion"
    return "other"


def generated_compiled(size: int, seed: int):
    game = generate_game(
        GeneratorConfig(seed=seed, board_size=size, setup_preset="classic_like")
    )
    return game.compiled_ruleset


def sample_start(compiled, seed: int):
    for offset in range(4):
        rng = random.Random(seed * 1009 + offset)
        state = initial_state(compiled)
        while state.ply_count < 60:
            if state.terminal_status.is_terminal:
                break
            if state.ply_count >= START_PLY:
                actions = legal_actions(state, compiled)
                children = legal_successors(state, compiled)
                if (len(actions) >= MIN_START_ACTIONS
                        and not any(c.terminal_status.is_terminal for _, c in children)):
                    return state
            children = legal_successors(state, compiled)
            if not children:
                break
            _, state = rng.choice(children)
    return None


def load_games() -> dict[tuple[int, int], list[dict]]:
    games: dict[tuple[int, int], list[dict]] = defaultdict(list)
    for depth in (2, 3):
        for path in sorted(EVIDENCE.glob(
                f"results_hand_term_match_served-blind_d{depth}_*.json")):
            data = json.loads(path.read_text(encoding="utf-8"))
            for game in data["games"]:
                games[(depth, game["seed"])].append(game)
    return games


def position_key(record: dict) -> tuple:
    moves = record["saved_moves_at_divergence"]
    return (
        record["seed"],
        record["first_diff_ply"],
        record["divergence_side"],
        moves.get("served"),
        moves.get("blind"),
    )


def main() -> int:
    if RESULT.exists():
        print(f"refusing to overwrite existing result: {RESULT}")
        return 1
    actual_sha = sha256(PRIMARY)
    if actual_sha != EXPECTED_PRIMARY_SHA256:
        print(f"primary hash mismatch: {actual_sha}")
        return 1

    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    data = json.loads(PRIMARY.read_text(encoding="utf-8"))
    judged = [r for r in data["records"] if r.get("status") == "judged"]
    if len(judged) != 45:
        print(f"expected 45 judged cells, found {len(judged)}")
        return 1

    games = load_games()
    cells = []
    seen: dict[tuple, dict] = {}
    for record in sorted(judged, key=lambda r: (r["depth"], r["seed"])):
        key = (record["depth"], record["seed"])
        both = games.get(key, [])
        if len(both) != 2:
            print(f"expected 2 games for {key}, found {len(both)}")
            return 1
        g0, g1 = sorted(both, key=lambda g: g["served_side"])
        index = record["first_diff_ply"]
        prefix = g0["moves"][:index]
        if g1["moves"][:index] != prefix:
            print(f"prefix disagreement at {key}")
            return 1
        compiled = generated_compiled(4, record["seed"])
        state = sample_start(compiled, record["seed"])
        if state is None or state.ply_count != g0["start_ply"]:
            print(f"start mismatch at {key}")
            return 1
        for ply, text in enumerate(prefix):
            action = parse_action(text)
            if repr(action) != text:
                print(f"repr round-trip mismatch at {key} ply {ply}")
                return 1
            state = apply_action(state, action, compiled)
        if state.position.side_to_move != record["divergence_side"]:
            print(f"side mismatch at {key}")
            return 1

        actions = legal_actions(state, compiled)
        mix = Counter(class_of(a) for a in actions)
        if mix.get("other"):
            print(f"unclassified legal action at {key}")
            return 1
        chosen = {
            arm: parse_action(record["saved_moves_at_divergence"][arm])
            for arm in ("served", "blind")
        }
        legal_set = set(actions)
        if any(action not in legal_set for action in chosen.values()):
            print(f"chosen action not legal at {key}")
            return 1
        row = {
            "seed": record["seed"],
            "depth": record["depth"],
            "verdict": record["verdict"],
            "pair_kind": record["pair_kind"],
            "legal_actions": len(actions),
            "legal_drop": mix.get("drop", 0),
            "legal_promotion": mix.get("promotion", 0),
            "legal_quiet": mix.get("quiet", 0),
            "served_class": class_of(chosen["served"]),
            "blind_class": class_of(chosen["blind"]),
        }
        row["position_key"] = list(position_key(record))
        cells.append(row)
        seen.setdefault(position_key(record), row)

    if len(seen) != 35:
        print(f"distinct positions {len(seen)} != 35")
        return 1

    def observed(arm: str) -> Counter:
        return Counter(row[f"{arm}_class"] for row in cells)

    served_obs = observed("served")
    blind_obs = observed("blind")
    avail = Counter()
    for row in seen.values():
        avail["drop"] += row["legal_drop"]
        avail["promotion"] += row["legal_promotion"]
        avail["quiet"] += row["legal_quiet"]
    total_avail = sum(avail.values())
    share = {k: avail[k] / total_avail for k in ("drop", "promotion", "quiet")}
    n = len(cells)
    obs_share = {
        "served": {k: served_obs.get(k, 0) / n for k in ("drop", "promotion", "quiet")},
        "blind": {k: blind_obs.get(k, 0) / n for k in ("drop", "promotion", "quiet")},
    }

    def over(row: dict) -> str:
        return "over_represented" if row["delta_points"] >= 10 else "consistent_with_availability"

    deltas = {}
    for arm in ("served", "blind"):
        deltas[arm] = {
            cls: {
                "observed_share": obs_share[arm][cls],
                "availability_share": share[cls],
                "delta_points": round(
                    (obs_share[arm][cls] - share[cls]) * 100, 1
                ),
            }
            for cls in ("drop", "promotion", "quiet")
        }
        for cls in ("drop", "promotion", "quiet"):
            deltas[arm][cls]["assessment"] = over(deltas[arm][cls])

    quiet_quiet = [r for r in cells if r["served_class"] == r["blind_class"] == "quiet"]
    quiet_quiet_drop_avail = sum(r["legal_drop"] > 0 for r in quiet_quiet)

    result = {
        "question": plan["question"],
        "owner": "DEEPSEEK_AUX",
        "input": {
            "results_judged_divergence.json": actual_sha,
            "plan_sha256": sha256(PLAN),
        },
        "zero_new_search": True,
        "checks": {
            "judged_cells": len(cells),
            "distinct_positions": len(seen),
            "prefix_mismatches": 0,
            "repr_round_trip_failures": 0,
            "chosen_not_legal": 0,
        },
        "availability_distinct_positions": {
            "positions": len(seen),
            "legal_action_instances": total_avail,
            "actions_by_class": dict(sorted(avail.items())),
            "share_by_class": {k: round(v, 4) for k, v in share.items()},
        },
        "observed_choices_45_cells": {
            "served": dict(sorted(served_obs.items())),
            "blind": dict(sorted(blind_obs.items())),
            "comparison": deltas,
        },
        "quiet_vs_quiet_cells": {
            "cells": len(quiet_quiet),
            "cells_with_a_legal_drop": quiet_quiet_drop_avail,
        },
        "cells": cells,
        "limits": plan["limits_to_state"],
    }
    RESULT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "checks": result["checks"],
        "availability": result["availability_distinct_positions"],
        "observed": result["observed_choices_45_cells"],
        "quiet_quiet": result["quiet_vs_quiet_cells"],
    }, indent=2))
    print(f"\nwritten: {RESULT}")
    print(f"sha256: {sha256(RESULT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
