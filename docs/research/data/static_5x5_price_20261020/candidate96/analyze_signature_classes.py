from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from pathlib import Path


BASE = Path(__file__).resolve().parent
INPUTS = [BASE / f"profile-{seed}.json" for seed in range(522001, 522009)]


def signature_key(signature: str) -> str:
    atoms = json.loads(signature)
    direct = sorted(tuple(atom) for atom in atoms)
    file_reflected = sorted((atom[0], -atom[1], *atom[2:]) for atom in atoms)
    return json.dumps(min(direct, file_reflected), separators=(",", ":"))


groups: dict[str, list[dict[str, object]]] = defaultdict(list)
input_hashes = []
king_signatures = set()
for path in INPUTS:
    raw = path.read_bytes()
    input_hashes.append({"file": path.name, "sha256": hashlib.sha256(raw).hexdigest()})
    data = json.loads(raw)
    for type_id, profile in data["piece_profiles"].items():
        key = signature_key(profile["movement_signature"])
        if type_id == "K":
            king_signatures.add(key)
            continue
        groups[key].append(
            {
                "seed": path.stem.removeprefix("profile-"),
                "type_id": type_id,
                "promotable": bool(profile["is_promotable"]),
                "normalized_board_value": int(profile["normalized_board_value"]),
                "normalized_hand_value": int(profile["normalized_hand_value"]),
            }
        )

repeated = [
    {"movement_signature": json.loads(key), "members": members}
    for key, members in sorted(groups.items())
    if len(members) > 1
]
result = {
    "schema": "primary-candidate96-signature-class-audit-v1",
    "inputs": input_hashes,
    "equivalence": "Exact ordered movement atoms, modulo horizontal file reflection only; forward direction is preserved because promotion makes vertical reflection non-equivalent.",
    "king_signature_classes": len(king_signatures),
    "nonking_type_entries": sum(map(len, groups.values())),
    "nonking_signature_classes": len(groups),
    "repeated_nonking_classes": repeated,
    "scope": "Eight frozen candidate96 5x5 profile JSONs only; no games, search, training, vertical reflection, or cross-signature similarity model.",
    "interpretation": "No repeated non-king movement class is available to estimate a signature-conditioned cross-rule price spread. This is absence of support in these eight profiles, not evidence that transferable prices do or do not exist.",
}
(BASE / "signature_class_summary.json").write_text(
    json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
)
