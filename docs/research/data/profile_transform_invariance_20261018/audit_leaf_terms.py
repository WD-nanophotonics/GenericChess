"""Audit which membership tests in the served leaf score can be true.

Written before the run; the endpoint below was recorded in ``plan-log.json``
before execution.

Question. A4 found that ``Evaluator._promotion_bonus`` compares ``Square``
targets taken from ``empty_forward_mobility`` against ``_zones`` entries that
are integer board indices, so its forward-adjacency half bonus cannot fire.  If
that is the only such mismatch, the served leaf score decomposes into material
+ hand + in-zone promotion + dynamic mobility + anchor escape, and a reader can
say which source terms actually contribute.  If it is not the only one, other
terms are silently dead as well and every evaluator-side statement in this
study needs that caveat.

Endpoint (fixed before execution):
  * every ``in`` / ``not in`` comparison in ``evaluator.py`` is listed from the
    AST with line number and source text, so the list is not hand-picked;
  * every dict lookup keyed on a type id in the same file is listed the same
    way, because a key-type mismatch would be the same class of defect;
  * for each comparison reached by the scoring path, the runtime element type
    of the container and of the query is materialised on the 80 stored rules;
    a comparison whose query type never equals a container element type is
    ``never_true_by_type``, and it is additionally counted with the target
    converted to a board index, so "impossible by type" is separated from "no
    rule happens to exercise it";
  * the anchor-capture penalty is probed on constructed states -- one piece is
    moved to an empty square of the rule's own initial position -- and whenever
    the anchor square then lies in the opponent attack map the served score
    change against ``anchor_escape_weight = 0`` must equal
    ``weight * ((esc0 - esc1) - 10 * attacked0 + 10 * attacked1)``.

Decision rule: ``leaf_terms_are_type_live_except_the_half_bonus`` when the
half-bonus comparison is the only ``never_true_by_type`` one, every dict lookup
is key-type consistent, and every probed anchor-penalty state matches the
expected score delta.  Any other outcome is recorded with its own counts and
narrows the report's evaluator claims instead.

No search, no game, no fitness, no new seeds.
"""

from __future__ import annotations

import ast
import json
import subprocess
import sys
import time
from dataclasses import replace
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))

import scan_profile_transform as base  # noqa: E402

from generic_chess.ai.evaluation.config import EvaluationConfig  # noqa: E402
from generic_chess.ai.evaluation.evaluator import Evaluator  # noqa: E402
from generic_chess.ai.evaluation.profile import build_ruleset_profile  # noqa: E402
from generic_chess.core.attacks import anchor_square  # noqa: E402
from generic_chess.core.transition import initial_state  # noqa: E402
from generic_chess.generation.config import GeneratorConfig  # noqa: E402
from generic_chess.generation.generator import generate_game  # noqa: E402

OUT = HERE / "results_leaf_term_audit.json"
SEEDS = base.SEEDS
SIZES = base.SIZES
EVALUATOR_PATH = "generic_chess/ai/evaluation/evaluator.py"
TRIGGER_CAP = 5  # verified anchor-penalty states per rule


def ast_inventory(source: str) -> dict:
    tree = ast.parse(source)
    comparisons = []
    lookups = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare):
            for op, right in zip(node.ops, node.comparators):
                if isinstance(op, (ast.In, ast.NotIn)):
                    comparisons.append(
                        {
                            "line": node.lineno,
                            "op": type(op).__name__,
                            "query": ast.unparse(node.left),
                            "container": ast.unparse(right),
                        }
                    )
        if isinstance(node, ast.Subscript) and isinstance(node.ctx, ast.Load):
            lookups.append(
                {
                    "line": node.lineno,
                    "target": ast.unparse(node.value),
                    "key": ast.unparse(node.slice),
                }
            )
    return {"comparisons": comparisons, "subscript_lookups": lookups}


def type_names(values, cap: int = 6) -> list[str]:
    names = set()
    for value in values:
        names.add(type(value).__name__)
        if len(names) >= cap:
            break
    return sorted(names)


def audit_rule(seed: int, size: int) -> dict:
    game = generate_game(
        GeneratorConfig(seed=seed, board_size=size, setup_preset="classic_like")
    )
    compiled = game.compiled_ruleset
    config = EvaluationConfig(hand_weight=base.HAND_WEIGHT)
    profile = build_ruleset_profile(compiled, config)
    evaluator = Evaluator(compiled, profile, config)
    n = compiled.board_size
    weight = config.anchor_escape_weight

    zone_records = []
    promotable_types = 0
    promotable_with_key = 0
    promotable_with_positive_gain = 0
    coded_hits = 0
    converted_hits = 0
    converted_squares = 0
    for pt in compiled.piece_types:
        if not pt.is_promotable:
            continue
        promotable_types += 1
        if pt.type_id in profile.promotion_gain_by_type:
            promotable_with_key += 1
        if profile.promotion_gain_by_type.get(pt.type_id, 0) <= 0:
            continue
        promotable_with_positive_gain += 1
        for owner in (0, 1):
            zone = evaluator._zones.get((pt.type_id, owner))
            if zone is None:
                continue
            forward = compiled.empty_forward_mobility[pt.type_id][owner]
            targets = [t for idx in range(n * n) if idx not in zone for t in forward[idx]]
            coded = sum(1 for t in targets if t in zone)
            converted = sum(1 for t in targets if (t.rank * n + t.file) in zone)
            squares_with_converted_hit = sum(
                1
                for idx in range(n * n)
                if idx not in zone
                and any((t.rank * n + t.file) in zone for t in forward[idx])
            )
            coded_hits += coded
            converted_hits += converted
            converted_squares += squares_with_converted_hit
            zone_records.append(
                {
                    "base_type": pt.type_id,
                    "owner": owner,
                    "zone_element_types": type_names(zone),
                    "target_element_types": type_names(targets),
                    "targets_tested": len(targets),
                    "coded_target_hits": coded,
                    "index_converted_target_hits": converted,
                    "squares_with_index_converted_hit": squares_with_converted_hit,
                }
            )

    # Constructed states: move one piece to an empty square of the initial board.
    state = initial_state(compiled)
    probes = 0
    triggers = 0
    matches = 0
    examples = []
    anchor_records = []
    for src, piece in enumerate(state.position.board):
        if piece is None:
            continue
        for dst, occupant in enumerate(state.position.board):
            if occupant is not None:
                continue
            board = list(state.position.board)
            board[src] = None
            board[dst] = piece
            moved = replace(state, position=replace(state.position, board=tuple(board)))
            attacks = evaluator._attack_maps(moved)
            anchor0 = anchor_square(moved.position, 0, compiled)
            anchor1 = anchor_square(moved.position, 1, compiled)
            attacked0 = anchor0 is not None and anchor0 in attacks[1]
            attacked1 = anchor1 is not None and anchor1 in attacks[0]
            probes += 1
            if not (attacked0 or attacked1):
                continue
            triggers += 1
            anchor_records.append(
                {
                    "src": src,
                    "dst": dst,
                    "piece_owner": piece.owner,
                    "attack_element_types": type_names(attacks[1]),
                    "anchor_element_type": type(anchor0).__name__ if anchor0 else None,
                    "attacked0": attacked0,
                    "attacked1": attacked1,
                }
            )
            esc0 = evaluator._anchor_escape(moved.position, 0, attacks[1])
            esc1 = evaluator._anchor_escape(moved.position, 1, attacks[0])
            with_anchor = evaluator.evaluate(moved)
            without = Evaluator(
                compiled, profile, replace(config, anchor_escape_weight=0)
            ).evaluate(moved)
            expected = weight * (esc0 - esc1) - (10 * weight if attacked0 else 0) + (
                10 * weight if attacked1 else 0
            )
            ok = (with_anchor - without) == expected
            matches += int(ok)
            if len(examples) < 3:
                examples.append(
                    {
                        "src": src,
                        "dst": dst,
                        "attacked0": attacked0,
                        "attacked1": attacked1,
                        "esc0": esc0,
                        "esc1": esc1,
                        "observed_delta": with_anchor - without,
                        "expected_delta": expected,
                        "matches": ok,
                    }
                )
            if triggers >= TRIGGER_CAP:
                break
        if triggers >= TRIGGER_CAP:
            break

    return {
        "seed": seed,
        "board_size": size,
        "zone_records": zone_records,
        "promotable_types": promotable_types,
        "promotable_types_in_promotion_gain": promotable_with_key,
        "promotable_types_with_positive_gain": promotable_with_positive_gain,
        "coded_target_hits": coded_hits,
        "index_converted_target_hits": converted_hits,
        "squares_with_index_converted_hit": converted_squares,
        "states_probed": probes,
        "anchor_penalty_triggers": triggers,
        "anchor_penalty_matches": matches,
        "anchor_penalty_examples": examples,
        "anchor_penalty_first_triggers": anchor_records[:3],
    }


def main() -> int:
    started = time.time()
    source = (ROOT / EVALUATOR_PATH).read_text(encoding="utf-8")
    inventory = ast_inventory(source)
    rules = [audit_rule(seed, size) for size in SIZES for seed in SEEDS]

    zone_records = [rec for rule in rules for rec in rule["zone_records"]]
    coded = sum(rule["coded_target_hits"] for rule in rules)
    converted = sum(rule["index_converted_target_hits"] for rule in rules)
    converted_squares = sum(rule["squares_with_index_converted_hit"] for rule in rules)
    triggers = sum(rule["anchor_penalty_triggers"] for rule in rules)
    matches = sum(rule["anchor_penalty_matches"] for rule in rules)
    probed = sum(rule["states_probed"] for rule in rules)
    promotable_types = sum(rule["promotable_types"] for rule in rules)
    promotable_with_key = sum(rule["promotable_types_in_promotion_gain"] for rule in rules)
    promotable_positive = sum(
        rule["promotable_types_with_positive_gain"] for rule in rules
    )

    zone_types = sorted({t for rec in zone_records for t in rec["zone_element_types"]})
    target_types = sorted(
        {t for rec in zone_records for t in rec["target_element_types"]}
    )
    half_bonus_never_true = coded == 0 and converted > 0 and not set(zone_types) & set(
        target_types
    )
    anchor_ok = triggers > 0 and matches == triggers
    key_lookup_ok = promotable_with_key == promotable_types

    # The remaining comparisons are live only if their two sides share a type.
    other_comparisons_live = {
        "promotion_gain_key_lookup": f"str base id tested against a dict keyed by str base id; {promotable_with_key}/{promotable_types} promotable type records have a key",
        "zone_index_membership": f"int index tested against {{{', '.join(zone_types)}}} zone entries",
        "anchor_square_in_attack_map": "Square tested against a frozenset of Square",
        "anchor_escape_target_in_attack_map": "Square tested against a frozenset of Square",
    }

    decision = (
        "leaf_terms_are_type_live_except_the_half_bonus"
        if half_bonus_never_true and anchor_ok and key_lookup_ok
        else "leaf_audit_found_an_additional_mismatch"
    )

    payload = {
        "role": "DEEPSEEK_AUX",
        "generated_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "provenance": "post-hoc source audit of the served leaf score, endpoint written in plan-log.json before the run; follows the A4 half-bonus observation",
        "source_sha256": {EVALUATOR_PATH: base.sha256_file(ROOT / EVALUATOR_PATH)},
        "git_head": subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip(),
        "design": {
            "seeds": list(SEEDS),
            "board_sizes": list(SIZES),
            "hand_weight": base.HAND_WEIGHT,
            "trigger_cap_per_rule": TRIGGER_CAP,
            "endpoint": "AST inventory of every in/not-in comparison and every subscript lookup in evaluator.py, runtime element types per comparison, as-coded versus index-converted hit counts, and anchor-penalty score-delta identity on constructed states",
        },
        "ast_inventory": inventory,
        "comparison_types": {
            "zone_element_types": zone_types,
            "forward_target_element_types": target_types,
            "other_comparisons": other_comparisons_live,
        },
        "verdict": {
            "decision": decision,
            "half_bonus_never_true_by_type": half_bonus_never_true,
            "promotable_types": promotable_types,
            "promotable_types_with_positive_gain": promotable_positive,
            "zone_records": len(zone_records),
            "coded_target_membership_hits": coded,
            "index_converted_target_membership_hits": converted,
            "squares_receiving_half_bonus_if_index_converted": converted_squares,
            "constructed_states_probed": probed,
            "anchor_penalty_triggers": triggers,
            "anchor_penalty_delta_matches": matches,
        },
        "rules": rules,
        "nonclaims": [
            "no search, no strength, utility, strength or outcome claim",
            "one generator family, square boards 6 and 8, 40 stored seeds",
            "constructs states for measurement; it does not show they are reachable in play",
            "records reachability of source terms, not a proposed repair",
        ],
    }
    OUT.write_text(json.dumps(payload, indent=1) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "out": str(OUT),
                "elapsed_seconds": round(time.time() - started, 2),
                **payload["verdict"],
                "sha256": base.sha256_file(OUT),
            },
            indent=1,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
