from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from ai_fixtures import build_4x4_rooks
from conftest import make_state
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.cancellation import CancellationToken
from generic_chess.ai.limits import SearchLimits
from generic_chess.core.attacks import is_in_check
from generic_chess.session.session import GameSession


compiled = build_4x4_rooks()
state = make_state(compiled, ["R..K", "....", ".r..", "k..."], side_to_move=1)
assert is_in_check(state.position, 1, compiled)
session = GameSession(compiled)
# Test-fixture injection only: GameSession intentionally exposes no arbitrary
# state setter. This creates an ongoing checked root without fake history.
session._state = state
session._search_history_witnesses = (state.position,)
before = (session.state, session.history, session.to_record(), session._search_witnesses)
legal = session.legal_actions()
assert legal
token = CancellationToken()
token.cancel()
decision = AlphaBetaPlayer(
    compiled, use_disk_cache=False, tt_max_entries=1000
).choose_action(
    session,
    SearchLimits(max_depth=8, max_nodes=4096, quiescence_max_depth=0),
    cancel_token=token,
)
after = (session.state, session.history, session.to_record(), session._search_witnesses)
record = {
    "schema": "primary-checked-root-cancel-fallback-v1",
    "ruleset_fingerprint": compiled.ruleset_fingerprint,
    "root_ply": state.ply_count,
    "root_in_check": True,
    "legal_evasion_count": len(legal),
    "returned_action_legal_evasion": decision.action in legal,
    "choice_kind": decision.choice_kind,
    "termination_reason": decision.termination_reason,
    "completed_depth": decision.completed_depth,
    "principal_variation": list(decision.principal_variation),
    "nodes": decision.nodes,
    "tt_probes": decision.tt_probes,
    "result_source": decision.result_source,
    "caller_session_unchanged": before == after,
    "fixture_note": "State seeded into GameSession only inside this bounded test probe; no production state-setter is implied.",
}
assert record["returned_action_legal_evasion"]
assert record["caller_session_unchanged"]
(Path(__file__).with_name("result.json")).write_text(
    json.dumps(record, sort_keys=True, indent=2) + "\n", encoding="utf-8"
)
print(json.dumps(record, separators=(",", ":")))
