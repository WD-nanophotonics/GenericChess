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
STUDY_DIR = "profile_transform_invariance_20261018"


def _worktree_root(start: Path) -> Path:
    """Locate the checkout root whether this file runs from the private or the
    published copy.  An earlier version derived the root from ``HERE`` alone,
    which wrote a nested docs/research/docs/... tree when the published copy was
    run; the root is now found by a marker instead of by depth."""
    for candidate in (start, *start.parents):
        if (candidate / "generic_chess").is_dir() and (candidate / "docs").is_dir():
            return candidate
    raise SystemExit(f"cannot locate the worktree root above {start}")


ROOT = _worktree_root(HERE)
PRIVATE = ROOT / ".local_agent" / STUDY_DIR
# Originals preferred: the private study directory when it exists, else this one.
SOURCE = PRIVATE if (PRIVATE / "plan.json").exists() else HERE
EXTRA_DIR = ROOT / ".local_agent" / "games-leaf-terms-20261018"
DEST = ROOT / "docs" / "research" / "data" / STUDY_DIR

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
    "plan_bind_reachability_to_decisions.json",
    "results_bind_reachability_to_decisions.json",
    "results_contact_concentration.json",
    "plan_zone_promotion_disjointness.json",
    "results_zone_promotion_disjointness.json",
    "plan_zone_promotion_source_classification.json",
    "results_zone_promotion_source_classification.json",
    "verification_zone_promotion_source_classification.json",
    "plan_stage12_contact_choice.json",
    "results_stage12_contact_choice.json",
    "verification_stage12_contact_choice.json",
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
    "bind_reachability_to_decisions.py",
    "verify_bind_reachability_consistency.py",
    "analyze_contact_concentration.py",
    "scan_zone_promotion_disjointness.py",
    "verify_zone_promotion_disjointness.py",
    "scan_zone_promotion_source_classification.py",
    "verify_zone_promotion_source_classification.py",
    "scan_stage12_contact_choice.py",
    "verify_stage12_contact_choice.py",
    "make_public_evidence.py",
]

# Stage 7 lives in its own private directory because it reads stored games
# rather than generating rules; it is still part of this study's evidence.
EXTRA_SOURCES = {
    name: EXTRA_DIR / name
    for name in (
        "results_stored_games_leaf_terms.json",
        "plan_games_leaf_terms.json",
        "scan_stored_games_leaf_terms.py",
        "results_static_zone_share.json",
        "static_zone_share_boards.py",
        "plan_bind_reachability_to_decisions.json",
        "results_bind_reachability_to_decisions.json",
        "bind_reachability_to_decisions.py",
        "results_contact_concentration.json",
        "analyze_contact_concentration.py",
    )
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
        src = EXTRA_SOURCES.get(name, SOURCE / name)
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
