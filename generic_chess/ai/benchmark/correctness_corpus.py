"""Versioned correctness corpus for future Python/native differential testing."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from ...core.actions import action_to_dict
from ...core.keys import position_key
from ...core.transition import legal_successors
from .audit_schema import write_json
from .audit_suite import (
    RuleSetFixtureSpec,
    build_compiled,
    build_session,
    smoke_ruleset_specs,
    standard_ruleset_specs,
)
from .position_mining import mine_suite

CORPUS_SCHEMA_VERSION = 1
CORPUS_VERSION = "v1"


def _canonical_actions_hash(actions) -> str:
    payload = json.dumps(
        sorted((action_to_dict(a) for a in actions), key=json.dumps),
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def perft(compiled, state, depth: int) -> int:
    if depth <= 0:
        return 1
    total = 0
    for _action, child in legal_successors(state, compiled):
        total += perft(compiled, child, depth - 1)
    return total


def _corpus_specs() -> tuple[RuleSetFixtureSpec, ...]:
    small = [
        s
        for s in standard_ruleset_specs()
        if s.board_size in (4, 6) and s.fixture_id.startswith("gen_")
    ]
    picked = small[:6]
    return tuple(smoke_ruleset_specs() + tuple(picked))


def build_corpus(
    *,
    commit: str = "",
    max_fixtures: int = 12,
    perft_depth: int = 3,
) -> dict:
    specs = _corpus_specs()
    positions = mine_suite(specs, playout_seed=1, max_games=2, max_plies=40, max_positions=2)
    fixtures = []
    for pos in positions[:max_fixtures]:
        spec = next(s for s in specs if s.fixture_id == pos.ruleset_fixture_id)
        compiled = build_compiled(spec)
        _, session = build_session(spec, pos.action_prefix)
        state = session.state
        actions = session.legal_actions()
        children = legal_successors(state, compiled)
        child_keys = [position_key(c.position, compiled) for _a, c in children]
        depths = {}
        for d in range(1, perft_depth + 1):
            depths[str(d)] = perft(compiled, state, d)
        fixtures.append(
            {
                "fixture_id": pos.fixture_id,
                "ruleset_fixture_id": spec.fixture_id,
                "board_size": compiled.board_size,
                "ruleset_fingerprint": compiled.ruleset_fingerprint,
                "action_prefix": [dict(a) for a in pos.action_prefix],
                "position_key": position_key(state.position, compiled),
                "terminal": {
                    "status": state.terminal_status.status.value,
                    "winner": state.terminal_status.winner,
                },
                "legal_action_count": len(actions),
                "legal_action_hash": _canonical_actions_hash(actions),
                "legal_actions": [action_to_dict(a) for a in actions],
                "child_keys": child_keys,
                "perft": depths,
            }
        )
    return {
        "schema_version": CORPUS_SCHEMA_VERSION,
        "corpus_version": CORPUS_VERSION,
        "commit": commit,
        "fixtures": fixtures,
    }


def write_corpus(path: str | Path, *, commit: str = "") -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    write_json(target, build_corpus(commit=commit))
    return target
