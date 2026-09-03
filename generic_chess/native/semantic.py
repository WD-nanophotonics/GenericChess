"""Python boundary for the independent Native semantic position state."""

from __future__ import annotations

from collections.abc import Mapping
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json

from ..core.actions import SemanticBoardMove, SemanticDropMove
from ..core.coordinates import Square, index_to_square
from ..core.pieces import Piece
from ..core.position import Hands, Position
from ..core.declarations import DeclarationAssessment
from . import _module, native_available


def _require_executable(native_rules):
    if not getattr(native_rules, "native_executable", False):
        raise ValueError("Native semantic attack/check requires an executable rules capsule")


def pack_position(native_rules, payload):
    """Pack an independent semantic position.

    ``history`` entries with four 64-bit words are the exact SHA-256
    repetition authority. Two-word entries remain accepted only as an
    explicit legacy transport projection and are not terminal-eligible.
    """
    if not native_available():
        raise RuntimeError("native extension is not built")
    normalized = dict(payload)
    # Keep aux transport explicit and numeric at the C boundary.
    normalized["aux"] = [
        [slot, owner, list(value) if isinstance(value, tuple) else value]
        for (slot, owner), value in payload.get("aux_state", ())
    ]
    if "history" in payload:
        normalized["history"] = [
            [int(word) for word in words] for words in payload["history"]
        ]
    return _module().semantic_pack_position(native_rules.capsule, normalized)


def is_square_attacked(native_rules, position, square: int, by_owner: int) -> bool:
    """Query semantic pseudo-attack on an already-packed Native position."""
    if not native_available():
        raise RuntimeError("native extension is not built")
    _require_executable(native_rules)
    if not isinstance(square, int) or isinstance(square, bool):
        raise TypeError("square must be an integer board index")
    if not isinstance(by_owner, int) or isinstance(by_owner, bool) or by_owner not in (0, 1):
        raise ValueError("by_owner must be 0 or 1")
    return bool(_module().semantic_is_square_attacked(
        native_rules.capsule, position, int(square), int(by_owner)
    ))


def in_check(native_rules, position, side: int) -> bool:
    """Query semantic check on an already-packed Native position."""
    if not native_available():
        raise RuntimeError("native extension is not built")
    _require_executable(native_rules)
    if not isinstance(side, int) or isinstance(side, bool) or side not in (0, 1):
        raise ValueError("side must be 0 or 1")
    return bool(_module().semantic_in_check(native_rules.capsule, position, int(side)))


def snapshot(native_rules, position):
    if not native_available():
        raise RuntimeError("native extension is not built")
    out = dict(_module().semantic_position_snapshot(native_rules.capsule, position))
    out["aux_state"] = tuple(
        ((int(entry[0]), int(entry[1])),
         tuple(entry[2]) if isinstance(entry[2], (list, tuple)) else entry[2])
        for entry in out.get("aux_state", ())
    )
    out["history"] = tuple(tuple(int(word) for word in entry) for entry in out.get("history", ()))
    out["history_events"] = tuple(
        (int(event[0]), bool(event[1])) for event in out.get("history_events", ())
    )
    out["history_exact"] = bool(out.get("history_exact", False))
    out["history_events_exact"] = bool(out.get("history_events_exact", False))
    out["history_occurrences"] = int(out.get("history_occurrences", 0))
    return out


def position_key(native_rules, position) -> str:
    """Canonical semantic position identity computed by the Native kernel."""
    if not native_available():
        raise RuntimeError("native extension is not built")
    return str(_module().semantic_position_key(native_rules.capsule, position))


def pack_action(fields: dict) -> int:
    """Pack an exact semantic action using the frozen Native bit layout."""
    if not native_available():
        raise RuntimeError("native extension is not built")
    return int(_module().semantic_action_pack(dict(fields)))


def unpack_action(action: int) -> dict:
    """Unpack and validate an exact semantic action."""
    if not native_available():
        raise RuntimeError("native extension is not built")
    return {key: int(value) for key, value in _module().semantic_action_unpack(int(action)).items()}


def public_action(native_rules, action: int):
    """Decode an exact packed action without reducing semantic identity.

    The returned object retains pattern, geometry, actor type, coordinates,
    and promotion identity, so packing it again is lossless.
    """
    fields = unpack_action(action)
    n = int(native_rules.report.board_squares ** 0.5)
    pattern = int(fields["pattern"])
    geometry = int(fields["geometry"])
    if pattern >= len(native_rules.pattern_ids) or geometry >= len(native_rules.geometry_ids):
        raise ValueError("packed semantic action is outside this ruleset mapping")
    to_square = index_to_square(int(fields["to"]), n)
    if fields["kind"] == 2:
        source = int(fields["from"])
        promotion = int(fields["promotion"])
        if source >= n * n or int(fields["actor_current"]) >= len(native_rules.type_ids):
            raise ValueError("packed semantic board action is outside board/type mapping")
        if promotion != 255 and promotion >= len(native_rules.type_ids):
            raise ValueError("packed promotion type is outside mapping")
        return SemanticBoardMove(
            pattern_id=native_rules.pattern_ids[pattern],
            geometry_id=native_rules.geometry_ids[geometry],
            actor_type_id=native_rules.type_ids[int(fields["actor_current"])],
            from_square=index_to_square(source, n),
            to_square=to_square,
            promotion_target_id=(
                None if promotion == 255 else native_rules.type_ids[promotion]
            ),
        )
    base = int(fields["base"])
    if base >= len(native_rules.type_ids):
        raise ValueError("packed semantic drop action type is outside mapping")
    return SemanticDropMove(
        pattern_id=native_rules.pattern_ids[pattern],
        geometry_id=native_rules.geometry_ids[geometry],
        base_type_id=native_rules.type_ids[base],
        to_square=to_square,
    )


def assess_declaration(native_rules, position, declaration_id: str):
    """Assess one generic declaration against the exact Native position."""
    if not native_available():
        raise RuntimeError("native extension is not built")
    raw = dict(_module().semantic_assess_declaration(
        native_rules.capsule, position, str(declaration_id)
    ))
    return DeclarationAssessment(
        str(raw["declaration_id"]), int(raw["actor"]), str(raw["outcome"]),
        None if raw.get("weighted_score") is None else int(raw["weighted_score"]),
    )


def available_declarations(native_rules, position):
    """Return non-losing declaration assessments for the side to move."""
    if not native_available():
        raise RuntimeError("native extension is not built")
    return tuple(
        DeclarationAssessment(
            str(raw["declaration_id"]), int(raw["actor"]), str(raw["outcome"]),
            None if raw.get("weighted_score") is None else int(raw["weighted_score"]),
        )
        for raw in _module().semantic_available_declarations(
            native_rules.capsule, position
        )
    )


def candidate_actions(native_rules, position) -> tuple[int, ...]:
    """Enumerate deterministic S0 geometry candidates (not yet S1-S4 legal)."""
    if not native_available():
        raise RuntimeError("native extension is not built")
    return tuple(int(action) for action in _module().semantic_candidate_actions(native_rules.capsule, position))


def guarded_actions(native_rules, position) -> tuple[int, ...]:
    """Return exact actions surviving Native S0-S4 checks currently implemented."""
    if not native_available():
        raise RuntimeError("native extension is not built")
    return tuple(int(action) for action in _module().semantic_guarded_actions(native_rules.capsule, position))


def guarded_actions_audit(native_rules, position) -> dict:
    """Test-only baseline counters for the exact guarded-action path."""
    if not native_available():
        raise RuntimeError("native extension is not built")
    raw = dict(_module().semantic_guarded_actions_audit(native_rules.capsule, position))
    raw["actions"] = tuple(int(action) for action in raw.get("actions", ()))
    for key in (
        "candidate_count", "s3_trial_count", "s4_count", "nested_reply_count",
        "child_canonical_key_computations", "history_appends", "attack_check_calls",
    ):
        raw[key] = int(raw.get(key, 0))
    return raw


def transient_legal_actions(native_rules, position) -> tuple[int, ...]:
    """Return ordered S0-S4 actions without child key/history authority."""
    if not native_available():
        raise RuntimeError("native extension is not built")
    return tuple(int(action) for action in _module().semantic_transient_legal_actions(
        native_rules.capsule, position
    ))


def transient_legal_actions_audit(native_rules, position) -> dict:
    """Test-only transient legality counters and ordered action set."""
    if not native_available():
        raise RuntimeError("native extension is not built")
    raw = dict(_module().semantic_transient_legal_actions_audit(
        native_rules.capsule, position
    ))
    raw["actions"] = tuple(int(action) for action in raw.get("actions", ()))
    for key in (
        "candidate_count", "s3_trial_count", "s4_count", "nested_reply_count",
        "child_canonical_key_computations", "history_appends", "attack_check_calls",
    ):
        raw[key] = int(raw.get(key, 0))
    return raw


def history_occurrences(position, lo: int, hi: int) -> int:
    if not native_available():
        raise RuntimeError("native extension is not built")
    return int(_module().semantic_history_occurrences(position, int(lo), int(hi)))


def make_checked(native_rules, position, action: int):
    """Apply an exact semantic candidate in Native and return its child capsule."""
    if not native_available():
        raise RuntimeError("native extension is not built")
    return _module().semantic_make_checked(native_rules.capsule, position, int(action))


def make_unmake_roundtrip(native_rules, position, action: int) -> dict:
    if not native_available():
        raise RuntimeError("native extension is not built")
    return dict(_module().semantic_make_unmake_roundtrip(native_rules.capsule, position, int(action)))


def candidate_perft(native_rules, position, depth: int) -> int:
    if not native_available():
        raise RuntimeError("native extension is not built")
    return int(_module().semantic_candidate_perft(native_rules.capsule, position, int(depth)))


def terminal_status(native_rules, position) -> dict:
    """Return the exact Native semantic terminal status and winner."""
    if not native_available():
        raise RuntimeError("native extension is not built")
    raw = dict(_module().semantic_terminal(native_rules.capsule, position))
    raw["status"] = str(raw["status"])
    raw["winner"] = None if raw.get("winner") is None else int(raw["winner"])
    return raw


def search_runtime_sizes() -> dict:
    """Return Native semantic search-state byte sizes for performance planning."""
    if not native_available():
        raise RuntimeError("native extension is not built")
    return {
        key: int(value)
        for key, value in _module().semantic_search_runtime_sizes().items()
    }


def _run_search(native_rules, position, depth: int, *, board_values=None, hand_values=None, entrypoint: str) -> dict:
    args = (native_rules.capsule, position, int(depth))
    if (board_values is None) != (hand_values is None):
        raise ValueError("board_values and hand_values must be supplied together")
    if isinstance(board_values, Mapping) or isinstance(hand_values, Mapping):
        if not isinstance(board_values, Mapping) or not isinstance(hand_values, Mapping):
            raise ValueError("board_values and hand_values must use the same profile form")
        expected = tuple(native_rules.type_ids)
        if set(board_values) != set(expected) or set(hand_values) != set(expected):
            raise ValueError("semantic profile mappings must cover exactly native type IDs")
        board_values = tuple(int(board_values[type_id]) for type_id in expected)
        hand_values = tuple(int(hand_values[type_id]) for type_id in expected)
    if board_values is not None:
        args += (tuple(int(value) for value in board_values), tuple(int(value) for value in hand_values))
    raw = dict(getattr(_module(), entrypoint)(*args))
    raw["best_action"] = None if raw.get("best_action") is None else int(raw["best_action"])
    raw["principal_variation"] = tuple(int(value) for value in raw.get("principal_variation", ()))
    raw["score"] = int(raw["score"])
    raw["nodes"] = int(raw["nodes"])
    return raw


def fixed_depth_search(native_rules, position, depth: int, *, board_values=None, hand_values=None) -> dict:
    """Run production fixed-depth semantic AlphaBeta over guarded actions.

    ``board_values`` and ``hand_values`` are optional evaluator profiles; when
    supplied they must be paired.  A
    sequence is interpreted in ``native_rules.type_ids`` order, while a
    mapping must cover those stable type IDs exactly.  Board values are
    applied to each piece's current type and hand values to held base types,
    with the side-to-move perspective determining the sign.  Omitting both
    profiles retains the deterministic ``type_index + 1`` fallback.
    """
    if not native_available():
        raise RuntimeError("native extension is not built")
    return _run_search(native_rules, position, depth, board_values=board_values, hand_values=hand_values, entrypoint="semantic_fixed_depth_search")


def probe_search(native_rules, position, depth: int, *, board_values=None, hand_values=None) -> dict:
    """Run the lower-level compatibility AlphaBeta probe."""
    if not native_available():
        raise RuntimeError("native extension is not built")
    return _run_search(native_rules, position, depth, board_values=board_values, hand_values=hand_values, entrypoint="semantic_probe_search")


def semantic_iterative_search(
    native_rules,
    position,
    max_depth: int,
    *,
    max_nodes: int | None = None,
    max_time_seconds: float | None = None,
    cancel_token=None,
    board_values=None,
    hand_values=None,
    _root_ply_offset: int = 0,
) -> dict:
    """Run deterministic no-TT iterative search on a semantic position.

    The Native entrypoint owns the recursive semantic state stack and checks
    node, monotonic-time, and cooperative-cancellation budgets.  Evaluator
    tables are an immutable call binding; they are not part of the RuleSet
    fingerprint and may be changed between searches.
    """
    if not native_available():
        raise RuntimeError("native extension is not built")
    if _root_ply_offset not in (0, 1):
        raise ValueError("_root_ply_offset must be 0 or 1")
    if (board_values is None) != (hand_values is None):
        raise ValueError("board_values and hand_values must be supplied together")
    expected = tuple(native_rules.type_ids)
    if isinstance(board_values, Mapping) or isinstance(hand_values, Mapping):
        if not isinstance(board_values, Mapping) or not isinstance(hand_values, Mapping):
            raise ValueError("board_values and hand_values must use the same profile form")
        if set(board_values) != set(expected) or set(hand_values) != set(expected):
            raise ValueError("semantic evaluator profile must cover exactly native type IDs")
        board_values = tuple(int(board_values[type_id]) for type_id in expected)
        hand_values = tuple(int(hand_values[type_id]) for type_id in expected)
    if board_values is not None:
        board_values = tuple(int(value) for value in board_values)
        hand_values = tuple(int(value) for value in hand_values)
    flag = None
    unregister = None
    if cancel_token is not None:
        flag = _module().create_cancel_flag()
        unregister = cancel_token.register_callback(lambda: _module().request_cancel(flag))
    try:
        raw = dict(_module().semantic_iterative_search(
            native_rules.capsule,
            position,
            int(max_depth),
            None if max_nodes is None else int(max_nodes),
            None if max_time_seconds is None else float(max_time_seconds),
            flag,
            board_values,
            hand_values,
            int(_root_ply_offset),
        ))
    finally:
        if unregister is not None:
            unregister()
    raw["best_action"] = None if raw.get("best_action") is None else int(raw["best_action"])
    raw["principal_variation"] = tuple(int(value) for value in raw.get("principal_variation", ()))
    for key in ("score", "nodes", "completed_depth", "selective_depth", "qnodes", "elapsed_nanoseconds", "legal_generation_count", "transition_count", "beta_cutoffs", "tt_probes", "tt_hits", "tt_stores", "tt_cutoffs"):
        raw[key] = int(raw.get(key, 0))
    raw["used_fallback"] = bool(raw.get("used_fallback", False))
    raw["elapsed_seconds"] = raw["elapsed_nanoseconds"] / 1e9
    raw["ruleset_fingerprint"] = str(native_rules.fingerprint)
    raw["tt_status"] = "NOT_STARTED"
    raw["evaluator_config_hash"] = hashlib.sha256(json.dumps({
        "ruleset_fingerprint": native_rules.fingerprint,
        "board_values": board_values,
        "hand_values": hand_values,
    }, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
    return raw


def root_parallel_search(native_rules, position, max_depth: int, *, workers: int = 1,
                         board_values=None, hand_values=None) -> dict:
    """Experimental deterministic root split for one semantic search position.

    Each root child is an isolated Native position and each worker invokes the
    accepted GIL-free iterative engine.  There is deliberately no shared TT or
    mutable state.  This mode is for latency experiments; budgets remain owned
    by the single-thread entrypoint.
    """
    if max_depth < 1:
        return semantic_iterative_search(
            native_rules, position, max_depth, board_values=board_values,
            hand_values=hand_values,
        )
    actions = guarded_actions(native_rules, position)
    if not actions:
        return semantic_iterative_search(
            native_rules, position, max_depth, board_values=board_values,
            hand_values=hand_values,
        )

    def evaluate(action):
        child = make_checked(native_rules, position, action)
        reply = semantic_iterative_search(
            native_rules, child, max_depth - 1, board_values=board_values,
            hand_values=hand_values,
            _root_ply_offset=1,
        )
        return -reply["score"], action, (action, *reply["principal_variation"]), reply

    with ThreadPoolExecutor(max_workers=max(1, int(workers))) as pool:
        rows = list(pool.map(evaluate, actions))
    score, action, pv, _reply = max(rows, key=lambda row: (row[0], -row[1]))
    return {
        "score": score,
        "best_action": action,
        "principal_variation": pv,
        "root_actions": len(actions),
        "workers": max(1, int(workers)),
        "mode": "ROOT_PARALLEL_EXPERIMENTAL",
    }


iterative_search = semantic_iterative_search
