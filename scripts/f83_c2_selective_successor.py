"""F83 C2 successor: selective correction with parent-decision retention."""

from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from generic_chess.learning.nonlinear import CompactNonlinearResidual
from generic_chess.learning.serialization import stable_sha256
from scripts import f78_parent_anchored_full_residual_arena2 as f78
from scripts import f82_c2_parent_anchored_repeatability as c2

LABEL = c2.LABEL
WORK_ORDER = "GENERICCHESS-F83-C2-SELECTIVE-CORRECTION-SUCCESSOR"
ALLOCATION = ROOT / "artifacts/f82_c2_repeatability/c2_allocation_manifest.json"
C2_ARTIFACT = ROOT / "artifacts/f82_c2_repeatability/c2_candidate_result.json"
EVIDENCE = ROOT / "artifacts/f85_c2_train_teacher_evidence/training_evidence.json"
OUT = ROOT / "artifacts/f83_c2_selective_successor"
ARTIFACT = OUT / "successor_candidate_result.json"
DESCRIPTOR = OUT / "successor_candidate_descriptor.json"
ALPHAS = (1.0, 0.5, 0.25, 0.125, 0.0625, 0.03125, 0.015625)


def _rows(parent_model):
    evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    roots = []
    for root in evidence["roots"]:
        rows = root["teacher_rows"]
        keys = [row["action_key"] for row in rows]
        target = root["root_metadata"]["root_80k"]["action_key"]
        if target not in keys:
            raise RuntimeError(f"teacher target absent for {root['root_id']}")
        features = np.asarray([row["features"] for row in rows], dtype=float)
        base = np.asarray([row["base_q"] for row in rows], dtype=float)
        prediction = parent_model.predict(features)
        order = sorted(range(len(keys)), key=lambda i: (-float(base[i] + prediction[i]), keys[i]))
        disagreement = keys[order[0]] != target
        roots.append({
            "root_id": root["root_id"],
            "features": features,
            "base": base,
            "target": keys.index(target),
            "keys": keys,
            "target_key": target,
            "parent_top_key": keys[order[0]],
            "parent_top_index": order[0],
            "disagreement": disagreement,
        })
    return roots


def _metrics(roots, parent_model, candidate_model):
    preserved = [row for row in roots if not row["disagreement"]]
    corrected = [row for row in roots if row["disagreement"]]
    retained = True
    parent_loss_rows = []
    candidate_loss_rows = []
    margins = []
    for row in roots:
        p = row["base"] + parent_model.predict(row["features"])
        c = row["base"] + candidate_model.predict(row["features"])
        po = sorted(range(len(p)), key=lambda i: (-float(p[i]), row["keys"][i]))
        co = sorted(range(len(c)), key=lambda i: (-float(c[i]), row["keys"][i]))
        if not row["disagreement"]:
            parent_margin = float(p[po[0]] - p[po[1]])
            candidate_margin = float(c[co[0]] - c[co[1]])
            retained = retained and co[0] == po[0] and candidate_margin >= 0.75 * parent_margin
        margins.append({"root_id": row["root_id"], "parent": float(p[po[0]] - p[po[1]]), "candidate": float(c[co[0]] - c[co[1]])})
        parent_loss_rows.append({"features": row["features"], "base": row["base"], "target": row["target"], "keys": row["keys"]})
        candidate_loss_rows.append(parent_loss_rows[-1])
    def loss(model, rows):
        return f78._pairwise_loss(model, rows)
    return {
        "preserved_root_count": len(preserved),
        "corrected_root_count": len(corrected),
        "preserved_decisions_and_margins": retained,
        "parent_objective_all_roots": loss(parent_model, parent_loss_rows),
        "candidate_objective_all_roots": loss(candidate_model, candidate_loss_rows),
        "corrected_root_ids": [row["root_id"] for row in corrected],
        "margin_rows": margins,
    }


def build() -> dict:
    allocation = json.loads(ALLOCATION.read_text(encoding="utf-8"))
    artifact, descriptor, compiled, _native, _c1, c2_parent = c2._load_verified_arena2_candidate(allocation, C2_ARTIFACT)
    parent_model = CompactNonlinearResidual.from_dict(c2_parent.compact_nonlinear)
    roots = _rows(parent_model)
    # Preserve roots where C2 already agrees with the deep target by training
    # their existing top action as an explicit retention target; only roots
    # whose top action disagrees use the deep teacher target.
    fit_data = [{"root_index": row["root_id"], "features": row["features"], "base": row["base"], "target": row["target"] if row["disagreement"] else row["parent_top_index"], "keys": row["keys"]} for row in roots]
    if not fit_data:
        raise RuntimeError("selective successor has no parent/teacher disagreement roots")
    raw_model, fit_summary = f78._adam_fit(parent_model, fit_data)
    chosen = None
    chosen_model = None
    attempts = []
    for alpha in ALPHAS:
        candidate_model = f78._interpolate(parent_model, raw_model, alpha)
        metrics = _metrics(roots, parent_model, candidate_model)
        metrics["alpha"] = alpha
        metrics["finite"] = all(np.isfinite(value) for row in roots for value in candidate_model.predict(row["features"]))
        metrics["corrected_objective"] = f78._pairwise_loss(candidate_model, fit_data)
        metrics["safe"] = metrics["preserved_decisions_and_margins"] and metrics["finite"] and metrics["corrected_objective"] < f78._pairwise_loss(parent_model, fit_data)
        attempts.append(metrics)
        if chosen is None and metrics["safe"]:
            chosen = alpha
            chosen_model = candidate_model
    if chosen_model is None:
        print(json.dumps({"attempts": [{"alpha": row["alpha"], "retained": row["preserved_decisions_and_margins"], "corrected_objective": row["corrected_objective"], "finite": row["finite"]} for row in attempts]}, sort_keys=True))
        raise RuntimeError("no safe selective successor alpha")
    identity = {
        "work_order": WORK_ORDER,
        "parent_checkpoint_id": c2_parent.checkpoint_id,
        "parent_model_sha256": stable_sha256(c2_parent.compact_nonlinear),
        "c2_candidate_descriptor_sha256": descriptor["descriptor_sha256"],
        "allocation_sha256": allocation["allocation_sha256"],
        "teacher_evidence_sha256": c2.TEACHER_EVIDENCE_SHA,
        "objective": "selective_pairwise_correction_on_parent_teacher_disagreement_roots_with_margin_retention",
        "corrected_root_count": len(fit_data),
        "alpha": chosen,
    }
    successor, training_hash = f78._make_candidate(c2_parent, chosen_model, identity)
    successor.validate_ruleset(compiled)
    model_sha = stable_sha256(chosen_model.to_dict())
    descriptor_payload = {
        "schema": "generic-chess-f83-c2-selective-successor-descriptor-v1",
        "work_order": WORK_ORDER,
        "ruleset": LABEL,
        "parent_checkpoint_id": c2_parent.checkpoint_id,
        "parent_model_sha256": stable_sha256(c2_parent.compact_nonlinear),
        "source_c2_candidate_descriptor_sha256": descriptor["descriptor_sha256"],
        "allocation_sha256": allocation["allocation_sha256"],
        "teacher_evidence_sha256": c2.TEACHER_EVIDENCE_SHA,
        "candidate_checkpoint_id": successor.checkpoint_id,
        "candidate_model_sha256": model_sha,
        "training_config_hash": training_hash,
        "chosen_alpha": chosen,
        "candidate_checkpoint": successor.to_dict(),
        "compact_model": chosen_model.to_dict(),
        "fit_summary": fit_summary,
        "selection": {"attempts": attempts, "corrected_root_ids": [row["root_id"] for row in roots if row["disagreement"]]},
    }
    descriptor_payload["descriptor_sha256"] = stable_sha256(descriptor_payload)
    result = {
        "schema": "generic-chess-f83-c2-selective-successor-v1",
        "status": "SUCCESSOR_READY_FOR_APPROVED_ARENA",
        "work_order": WORK_ORDER,
        "parent_checkpoint_id": c2_parent.checkpoint_id,
        "parent_model_sha256": stable_sha256(c2_parent.compact_nonlinear),
        "candidate_checkpoint_id": successor.checkpoint_id,
        "candidate_model_sha256": model_sha,
        "candidate_descriptor_path": str(DESCRIPTOR.relative_to(ROOT)).replace("\\", "/"),
        "candidate_descriptor_sha256": descriptor_payload["descriptor_sha256"],
        "allocation_sha256": allocation["allocation_sha256"],
        "teacher_evidence_sha256": c2.TEACHER_EVIDENCE_SHA,
        "selection": _metrics(roots, parent_model, chosen_model),
        "chosen_alpha": chosen,
        "training_config_hash": training_hash,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    DESCRIPTOR.write_text(json.dumps(descriptor_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    ARTIFACT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    print(json.dumps(build(), indent=2, sort_keys=True))
