"""Audit exposure for the frozen seed-21 compound-action utility preflight."""
from __future__ import annotations
import json, random
from pathlib import Path

import semantic_generated_substrate_utility_20261020 as source
from generic_chess.ai.evaluation.config import EvaluationConfig
from generic_chess.ai.evaluation.evaluator import Evaluator
from generic_chess.ai.evaluation.profile import build_ruleset_profile
from generic_chess.session.session import GameSession
from generic_chess.session.result import SessionStatus

base, augmented, compiled = source.build_case()
config = EvaluationConfig()
candidate = build_ruleset_profile(compiled, config)
control = build_ruleset_profile(compiled._legacy_compiled, config)
rows = []
for seed in source.PREFIX_SEED_RANGE:
    rng = random.Random(seed)
    session = GameSession(compiled)
    prefix = []
    for _ in range(12):
        if session.result.status is not SessionStatus.ONGOING:
            break
        legal = sorted(session.legal_actions(), key=str)
        if not legal:
            break
        action = rng.choice(legal)
        prefix.append(str(action))
        session.submit(action)
    if session.result.status is not SessionStatus.ONGOING or len(prefix) != 12 or session.state.position.side_to_move != 0:
        rows.append({"seed": seed, "eligible_root": False, "plies": len(prefix), "status": session.result.status.value})
        continue
    pos = session.state.position
    board_p = sum(p is not None and p.current_type_id == "P" for p in pos.board)
    hand_p = sum(dict(h.counts).get("P", 0) for h in pos.hands)
    sem = [str(a) for a in session.legal_actions() if getattr(a, "pattern_id", "").startswith("sem_")]
    eval_candidate = Evaluator(compiled, candidate, config).evaluate(session.state)
    eval_control = Evaluator(compiled, control, config).evaluate(session.state)
    rows.append({
        "seed": seed, "eligible_root": True, "plies": 12, "status": "ongoing",
        "side_to_move": 0, "board_P_count": board_p, "hand_P_count": hand_p,
        "semantic_actions": sem, "legal_action_count": len(session.legal_actions()),
        "candidate_root_eval": eval_candidate, "control_root_eval": eval_control,
        "prefix": prefix,
    })
eligible = [r for r in rows if r["eligible_root"]]
result = {
    "scope": "fixed seed-21 4x4 bilateral-random generated substrate with one synthetic P compound action; 32 prescribed prefix RNG seeds; at most 12 legal plies per seed",
    "base_fingerprint": base.compiled_ruleset.ruleset_fingerprint,
    "augmented_fingerprint": compiled.ruleset_fingerprint,
    "piece_types": [t.type_id for t in augmented.piece_types],
    "initial_P_count": sum(p is not None and p.current_type_id == "P" for side in augmented.initial_position for p in side),
    "candidate_P_board": candidate.board_value_by_type.get("P"),
    "control_P_board": control.board_value_by_type.get("P"),
    "candidate_P_hand": candidate.hand_value_by_base_type.get("P"),
    "control_P_hand": control.hand_value_by_base_type.get("P"),
    "seed_range": [source.PREFIX_SEED_RANGE[0], source.PREFIX_SEED_RANGE[-1]],
    "prefixes_examined": len(rows), "eligible_roots": len(eligible),
    "eligible_roots_with_P": sum(r["board_P_count"] + r["hand_P_count"] > 0 for r in eligible),
    "eligible_roots_with_semantic_action": sum(bool(r["semantic_actions"]) for r in eligible),
    "eligible_roots_with_changed_root_eval": sum(r["candidate_root_eval"] != r["control_root_eval"] for r in eligible),
    "eligible_root_details": eligible,
    "all_attempts": rows,
    "decision": "do_not_run the proposed 16-game panel: the registered profile contrast changes only P values, but the generated start has no P and no qualifying 12-ply root exposes a P board/hand feature or the compound semantic action",
    "limitations": ["prefix exposure audit, not a utility experiment", "single generated substrate and synthetic recombination", "does not establish all reachable trajectories lack P exposure beyond tested 12-ply prefixes"]
}
out = Path("docs/research/data/semantic_generated_substrate_exposure_audit_20261020.json")
out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(json.dumps({k:v for k,v in result.items() if k not in ("eligible_root_details","all_attempts")}, indent=2))
