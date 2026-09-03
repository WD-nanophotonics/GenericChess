"""Run the F49 learning experiment through persistent semantic Native search."""

from __future__ import annotations

import json
from pathlib import Path

from . import audit_f49_learning_signal_architecture as runner


def main() -> int:
    result = runner.run_measurements(
        partition_root=runner.F49_SEMANTIC_REENTRY_ROOT,
        semantic_reentry=True,
    )
    print(json.dumps({
        "status": "PASS",
        "classification": result["classification"],
        "next_boundary": result["next_boundary"],
        "transport": result["native_search_transport"],
        "control": result["control_corpus_transport"],
        "root": result["partition_root"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
