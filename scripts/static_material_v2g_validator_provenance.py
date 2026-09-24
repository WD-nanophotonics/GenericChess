"""Fail-closed version check for the post-freeze V2G human validator."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

FROZEN_VALIDATOR_SHA256 = "93359e03ca5b7a0a3bf3e7c3c1c433e570fab221b48d8c8701970cba47f93a2f"
REVIEWED_CURRENT_VALIDATOR_SHA256 = "266c5dadd135fcd19bcd22c96eb7625bdd3aa5e2085bb493c8b6998502919192"
VALIDATOR_RELATIVE_PATH = "scripts/validate_static_material_v2g_redeployment_throughput.py"


def check_validator_version(freeze: dict[str, Any], validator_path: Path) -> dict[str, Any]:
    """Accept only the exact pre-reference validator and its reviewed correction."""
    frozen = freeze.get("sha256", {}).get(VALIDATOR_RELATIVE_PATH)
    current = hashlib.sha256(validator_path.read_bytes()).hexdigest()
    approved = (
        frozen == FROZEN_VALIDATOR_SHA256
        and current == REVIEWED_CURRENT_VALIDATOR_SHA256
    )
    return {
        "approved": approved,
        "pre_reference_frozen_sha256": frozen,
        "expected_pre_reference_sha256": FROZEN_VALIDATOR_SHA256,
        "current_sha256": current,
        "expected_reviewed_current_sha256": REVIEWED_CURRENT_VALIDATOR_SHA256,
        "allowed_versions": [FROZEN_VALIDATOR_SHA256, REVIEWED_CURRENT_VALIDATOR_SHA256],
        "correction_scope": "V2C ledger field name plus bounded validator-version check; candidate formula/data/gates unchanged.",
    }
