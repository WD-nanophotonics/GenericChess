"""Refresh H22A inclusive/exclusive AuditRecorder attribution only."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import scripts.audit_f22_post_f21 as audit  # noqa: E402

audit.load_native(sys.argv[1])
audit.m = audit.imports()
_semantic, compiled = audit.compile_context(audit.m)
positions = audit.frozen_rebaseline_positions(audit.m)
audit.run_attribution(audit.m, compiled, positions)
print("attribution refreshed")
