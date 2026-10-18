"""Build the public evidence copy for the profile-transform study.

The private results carry compiler tracebacks with absolute checkout paths.
This script writes a publication copy in which the checkout root is replaced
by ``<repo>``.  Nothing else is altered: no number, decision, record or
nonclaim changes.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.resolve().parents[1]
DEST = ROOT / "docs" / "research" / "data" / "profile_transform_invariance_20261018"

JSON_FILES = [
    "plan.json",
    "plan_a3.json",
    "plan_evaluator_equivariance.json",
    "plan_a4.json",
    "plan_a5.json",
    "plan-log.json",
    "results_profile_transform.json",
    "results_profile_transform_a3.json",
    "results_a3_verification.json",
    "results_evaluator_equivariance.json",
    "results_promotion_zone_equivariance.json",
    "results_half_bonus_branch.json",
    "results_zone_mechanism.json",
    "results_zone_mechanism_heldout.json",
    "results_promotion_cancellation.json",
    "results_promotion_zone_equivariance_heldout.json",
    "results_zone_effect_heldout.json",
    "results_zone_effect_heldout_first.json",
    "results_leaf_term_audit.json",
    "results_stored_games_leaf_terms.json",
    "plan_games_leaf_terms.json",
    "results_static_zone_share.json",
]

PY_FILES = [
    "scan_profile_transform.py",
    "scan_profile_transform_a3.py",
    "verify_a3_results.py",
    "scan_evaluator_equivariance.py",
    "scan_promotion_zone_equivariance.py",
    "scan_zone_mechanism.py",
    "verify_zone_mechanism_heldout.py",
    "verify_half_bonus_branch.py",
    "verify_promotion_cancellation.py",
    "verify_zone_effect_heldout.py",
    "verify_public_copy_rebuild.py",
    "audit_leaf_terms.py",
    "scan_stored_games_leaf_terms.py",
    "static_zone_share_boards.py",
    "make_public_evidence.py",
]

# Stage 7 lives in its own private directory because it reads stored games
# rather than generating rules; it is still part of this study's evidence.
EXTRA_SOURCES = {
    "results_stored_games_leaf_terms.json": HERE.parent / "games-leaf-terms-20261018" / "results_stored_games_leaf_terms.json",
    "plan_games_leaf_terms.json": HERE.parent / "games-leaf-terms-20261018" / "plan_games_leaf_terms.json",
    "scan_stored_games_leaf_terms.py": HERE.parent / "games-leaf-terms-20261018" / "scan_stored_games_leaf_terms.py",
    "results_static_zone_share.json": HERE.parent / "games-leaf-terms-20261018" / "results_static_zone_share.json",
    "static_zone_share_boards.py": HERE.parent / "games-leaf-terms-20261018" / "static_zone_share_boards.py",
}

_HOME = re.compile(r"[A-Za-z]:\\\\?Users\\\\?[^\\\\\"]+", re.IGNORECASE)


def sanitize(text: str) -> str:
    text = text.replace(str(ROOT), "<repo>")
    text = text.replace(str(ROOT).replace("\\", "\\\\"), "<repo>")
    text = _HOME.sub("<home>", text)
    return text


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    DEST.mkdir(parents=True, exist_ok=True)
    written = []
    for name in JSON_FILES + PY_FILES:
        src = EXTRA_SOURCES.get(name, HERE / name)
        if not src.exists():
            raise SystemExit(f"missing {name}")
        text = sanitize(src.read_text(encoding="utf-8"))
        if name.endswith(".json"):
            parsed = json.loads(text)  # fail loudly if sanitizing broke JSON
            text = json.dumps(parsed, indent=1) + "\n"
        out = DEST / name
        out.write_text(text, encoding="utf-8")
        written.append({"file": name, "bytes": out.stat().st_size, "sha256": sha256(out)})
    manifest = {"role": "DEEPSEEK_AUX", "sanitized": "<repo>/<home>", "files": written}
    (DEST / "manifest.json").write_text(json.dumps(manifest, indent=1) + "\n", encoding="utf-8")
    for entry in written:
        print(f"{entry['file']} {entry['bytes']} {entry['sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
