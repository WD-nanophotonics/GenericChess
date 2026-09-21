"""Gate 3 R1: measure local leverage of a material-contrast mutation.

This is a benchmark-only diagnostic.  It freezes the F86Q F/V5-3 ruleset,
replays F86O policy tapes to three published roots, proves Gen0 checkpoint
parity, and then measures deterministic 1000-node action changes for the two
requested symmetric contrast mutations.  Wider mutations are run only when
both primary mutants leave all three root actions unchanged.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.evaluation.config import EvaluationConfig
from generic_chess.ai.evaluation.evaluator import Evaluator
from generic_chess.ai.evaluation.profile import build_ruleset_profile
from generic_chess.ai.limits import SearchLimits
from generic_chess.core.actions import action_to_dict
from generic_chess.core.identity import position_identity_key
from generic_chess.learning.features import (
    dynamic_features,
    linear_value,
    material_features,
    non_anchor_type_ids,
)
from generic_chess.learning.material import LearnableMaterialCheckpoint
from generic_chess.rules.compiler import compile_ruleset
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.session.session import GameSession
from scripts import f86q_check_forcing_depth3_probe as f86q
from scripts.gate2_r1_rule_prior_forced_win_microbench import (
    ROOT_DIGEST,
    SOURCE_FINGERPRINT,
    _replay_target_root,
)


ROOT = Path(__file__).resolve().parents[1]
SOURCE_ARM = "F"
SOURCE_SAMPLE = "V5-3"
SELECTED_ROOT_ORDER = "artifacts/f86q_check_forcing_depth3_probe/summary.json"
EXPECTED_FIRST_DIFFERENT_ROOT = "0d3d1f1d40190e526e2f8d60cafb5817734d8aa558572a9d753f1366a7035472"
EXPECTED_NEXT_DIFFERENT_ROOT = "2904701542900474233a19ca2796b391bceda73235aeaeae20cad4adaa658fe9"
PRIMARY_MUTATIONS = (0.75, 1.25)
WIDE_MUTATIONS = (0.50, 1.50)
MAX_NODES = 1000


def _canonical_json(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _action_digest(action) -> str:
    return hashlib.sha256(_canonical_json(action_to_dict(action))).hexdigest()


def _session_at(compiled, state, witnesses):
    session = GameSession(compiled)
    session._state = state
    session._search_history_witnesses = witnesses
    return session


class CheckpointEvaluator:
    """Adapter exposing a checkpoint through the production evaluator API."""

    def __init__(self, compiled, checkpoint: LearnableMaterialCheckpoint):
        checkpoint.validate_ruleset(compiled)
        checkpoint.ensure_within_limits()
        self._compiled = compiled
        self._checkpoint = checkpoint
        self._type_ids = non_anchor_type_ids(compiled)

    def evaluate(self, state) -> int:
        position = state.position
        material = material_features(position, self._type_ids, perspective=0)
        dynamic = dynamic_features(position, self._compiled)
        value = linear_value(
            material,
            self._checkpoint.board_weights,
            self._checkpoint.hand_weights,
            dynamic,
            self._checkpoint.dynamic_weights,
        )
        if position.side_to_move == 1:
            value = -value
        return value


def _source_entry(root: Path):
    manifest = f86q._f86o_manifest(root)
    entries = [
        entry for entry in manifest["rulesets"]
        if entry["arm"] == SOURCE_ARM and entry["sample_id"] == SOURCE_SAMPLE
    ]
    if len(entries) != 1:
        raise AssertionError("F86O source entry is not unique")
    entry = entries[0]
    compiled = compile_ruleset(ruleset_from_dict(entry["ruleset"]))
    if compiled.ruleset_fingerprint != SOURCE_FINGERPRINT:
        raise AssertionError("frozen ruleset fingerprint drift")
    return manifest, compiled


def _replay_root(root: Path, root_digest: str):
    manifest, compiled = _source_entry(root)
    tapes = f86q._load_tapes(manifest)[SOURCE_SAMPLE]
    for seats in (("A", "B"), ("B", "A")):
        session = GameSession(compiled)
        consumed = {"A": 0, "B": 0}
        prefix = []
        while session.result.status.value == "ongoing" and len(session.history) < f86q.MAX_PLY:
            if position_identity_key(session.state.position, compiled) == root_digest:
                return compiled, session.state, session._search_witnesses, {
                    "arm": SOURCE_ARM,
                    "sample_id": SOURCE_SAMPLE,
                    "seat_assignment": {"player0": seats[0], "player1": seats[1]},
                    "root_position_digest": root_digest,
                    "root_actor": session.state.position.side_to_move,
                    "prefix_plies": len(prefix),
                    "prefix_action_sequence_sha256": hashlib.sha256(_canonical_json(prefix)).hexdigest(),
                }
            successors = f86q._canonical_successors(session.state, compiled)
            if not successors:
                break
            actor = session.state.position.side_to_move
            tape = tapes[seats[actor]]
            action, _child = successors[tape.choose_index(consumed[seats[actor]], len(successors))]
            prefix.append({"actor": actor, "action": action_to_dict(action), "legal_action_count": len(successors)})
            consumed[seats[actor]] += 1
            session.submit(action)
    raise AssertionError(f"F86Q root digest was not reconstructed: {root_digest}")


def _load_root_digests(root: Path) -> tuple[str, str, str]:
    selected = json.loads((root / SELECTED_ROOT_ORDER).read_text(encoding="utf-8"))["selected_roots"]
    f_rows = [row for row in selected if row["arm"] == SOURCE_ARM and row["sample_id"] == SOURCE_SAMPLE]
    different = [row["root_position_digest"] for row in f_rows if row["root_position_digest"] != ROOT_DIGEST]
    if different[:2] != [EXPECTED_FIRST_DIFFERENT_ROOT, EXPECTED_NEXT_DIFFERENT_ROOT]:
        raise AssertionError("published F86Q selected-root order drift")
    return ROOT_DIGEST, different[0], different[1]


def _gen0(compiled):
    config = EvaluationConfig()
    profile = build_ruleset_profile(compiled, config)
    checkpoint = LearnableMaterialCheckpoint.from_profile(
        compiled,
        profile,
        generation=0,
        training_seed=None,
        dynamic_weights={
            "mobility": 2,
            "anchor_safety": 5,
            "promotion_potential": 0,
        },
    )
    checkpoint = replace(
        checkpoint,
        created_at="1970-01-01T00:00:00Z",
        training_config_hash="gate3-r1-gen0",
        training_seed=None,
    )
    return config, profile, checkpoint


def _mutant_checkpoint(gen0: LearnableMaterialCheckpoint, contrast: float):
    median = gen0.reference_median
    board = {
        type_id: median + contrast * (value - median)
        for type_id, value in gen0.board_weights.items()
    }
    hand = {
        type_id: board[type_id] * gen0.hand_weights[type_id] / gen0.board_weights[type_id]
        for type_id in gen0.hand_weights
    }
    return replace(
        gen0,
        generation=1,
        parent_checkpoint_id=gen0.checkpoint_id,
        created_at="1970-01-01T00:00:00Z",
        training_config_hash=f"gate3-r1-material-contrast-{contrast:.2f}",
        board_weights=board,
        hand_weights=hand,
    )


def _parity_row(compiled, state, checkpoint, production):
    adapter = CheckpointEvaluator(compiled, checkpoint)
    production_value = production.evaluate(state)
    checkpoint_value = adapter.evaluate(state)
    return {
        "production": production_value,
        "checkpoint": checkpoint_value,
        "exact": production_value == checkpoint_value,
    }


def _search(compiled, state, witnesses, config, profile, checkpoint, production=False):
    evaluator = Evaluator(compiled, profile, config) if production else CheckpointEvaluator(compiled, checkpoint)
    player = AlphaBetaPlayer(
        compiled,
        evaluation_config=config,
        evaluator_override=evaluator,
        use_disk_cache=False,
        use_tt=False,
        use_ordering=False,
        use_native_semantic_legality=False,
    )
    decision = player.choose_action(
        _session_at(compiled, state, witnesses),
        SearchLimits(max_nodes=MAX_NODES, quiescence_max_depth=0, quiescence_hard_max_depth=0),
    )
    return {
        "action_digest": None if decision.action is None else _action_digest(decision.action),
        "action": None if decision.action is None else action_to_dict(decision.action),
        "score": decision.score,
        "completed_depth": decision.completed_depth,
        "nodes": decision.nodes + decision.qnodes,
        "termination_reason": decision.termination_reason,
    }


def run_gate3(root: Path = ROOT):
    root_digests = _load_root_digests(root)
    roots = []
    for digest in root_digests:
        compiled, state, witnesses, replay = (
            _replay_target_root(root) if digest == ROOT_DIGEST else _replay_root(root, digest)
        )
        if compiled.ruleset_fingerprint != SOURCE_FINGERPRINT:
            raise AssertionError("ruleset fingerprint drift")
        roots.append({"digest": digest, "compiled": compiled, "state": state, "witnesses": witnesses, "replay": replay})

    config, profile, gen0 = _gen0(roots[0]["compiled"])
    production = Evaluator(roots[0]["compiled"], profile, config)
    parity = []
    for root_row in roots:
        row = {"root_position_digest": root_row["digest"], "root": _parity_row(root_row["compiled"], root_row["state"], gen0, production)}
        children = []
        for _action, child in f86q._canonical_successors(root_row["state"], root_row["compiled"]):
            children.append(_parity_row(root_row["compiled"], child, gen0, production))
        row["children"] = children
        parity.append(row)
    parity_exact = all(row["root"]["exact"] and all(child["exact"] for child in row["children"]) for row in parity)
    if not parity_exact:
        return {
            "status": "GATE3_GEN0_CHECKPOINT_PARITY_FAILURE",
            "classification": "GATE3_GEN0_CHECKPOINT_PARITY_FAILURE",
            "root_position_digests": list(root_digests),
            "parity": parity,
            "searches": [],
        }

    checkpoints = {"0": gen0}
    for contrast in PRIMARY_MUTATIONS + WIDE_MUTATIONS:
        checkpoints[f"{contrast:.2f}"] = _mutant_checkpoint(gen0, contrast)
    search_rows = []
    gen0_decisions = {}
    for root_row in roots:
        digest = root_row["digest"]
        decision = _search(root_row["compiled"], root_row["state"], root_row["witnesses"], config, profile, gen0, production=True)
        gen0_decisions[digest] = decision
        search_rows.append({"root_position_digest": digest, "evaluator": "gen0", "contrast": 1.0, **decision})

    def run_mutants(mutations):
        for contrast in mutations:
            checkpoint = checkpoints[f"{contrast:.2f}"]
            for root_row in roots:
                decision = _search(root_row["compiled"], root_row["state"], root_row["witnesses"], config, profile, checkpoint)
                gen0_action = gen0_decisions[root_row["digest"]]["action_digest"]
                search_rows.append({
                    "root_position_digest": root_row["digest"],
                    "evaluator": f"mutant_{contrast:.2f}",
                    "contrast": contrast,
                    "changed_from_gen0": decision["action_digest"] != gen0_action,
                    **decision,
                })

    run_mutants(PRIMARY_MUTATIONS)
    primary_changes = [row for row in search_rows if row["evaluator"].startswith("mutant_") and row["contrast"] in PRIMARY_MUTATIONS and row["changed_from_gen0"]]
    tested_mutations = list(PRIMARY_MUTATIONS)
    if not primary_changes:
        run_mutants(WIDE_MUTATIONS)
        tested_mutations.extend(WIDE_MUTATIONS)
    changed = [row for row in search_rows if row["evaluator"].startswith("mutant_") and row["changed_from_gen0"]]
    if primary_changes:
        band = "0.75/1.25"
        classification = "GATE3_RULE_PRIOR_CONTRAST_HAS_LOCAL_LEVERAGE"
    elif changed:
        band = "0.50/1.50"
        classification = "GATE3_RULE_PRIOR_CONTRAST_HAS_LOCAL_LEVERAGE"
    else:
        band = None
        classification = "GATE3_RULE_PRIOR_CONTRAST_NO_LOCAL_LEVERAGE"
    return {
        "status": "PASS",
        "classification": classification,
        "smallest_tested_leverage_band": band,
        "source_ruleset_fingerprint": SOURCE_FINGERPRINT,
        "root_position_digests": list(root_digests),
        "gen0": {
            "checkpoint_id": gen0.checkpoint_id,
            "reference_median": gen0.reference_median,
            "dynamic_weights": gen0.dynamic_weights,
        },
        "mutations_tested": tested_mutations,
        "parity": parity,
        "searches": search_rows,
        "compute": {"root_count": 3, "search_count": len(search_rows), "max_nodes": MAX_NODES},
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = run_gate3()
    text = json.dumps(result, indent=2, sort_keys=True)
    if args.output:
        args.output.write_text(text + "\n", encoding="utf-8")
    print(json.dumps({key: result.get(key) for key in ("status", "classification", "smallest_tested_leverage_band", "mutations_tested", "compute")}, sort_keys=True))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
