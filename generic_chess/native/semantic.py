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


def _backend(native_rules=None):
    if native_rules is not None:
        return native_rules.backend_module
    if not native_available():
        raise RuntimeError("native extension is not built")
    return _module()


def _require_executable(native_rules):
    if not getattr(native_rules, "native_executable", False):
        raise ValueError("Native semantic attack/check requires an executable rules capsule")


def pack_position(native_rules, payload):
    """Pack an independent semantic position.

    ``history`` entries with four 64-bit words are the exact SHA-256
    repetition authority. Two-word entries remain accepted only as an
    explicit legacy transport projection and are not terminal-eligible.

    An unpromoted piece must have equal base/current types. Explicit promotion
    to the same type can legally set promoted=True; the converse is not required.
    Explicit semantic type changes need not appear in legacy promotion metadata.
    Packing checks representation, not legal reachability or history authenticity.
    Continuous-check adjudication at repetition also requires actor/check events
    (six-word history records); digest-only imports cannot decide that result.
    """
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
    return _backend(native_rules).semantic_pack_position(native_rules.capsule, normalized)


def pack_current_position(native_rules, position, *, ply_count: int):
    """Pack current board/hand/aux state, without importing historical claims.

    Suitable for attacks and transient legality, not repetition adjudication.
    """
    if position.ruleset_fingerprint != native_rules.fingerprint:
        raise ValueError("Native/Python position ruleset fingerprint mismatch")
    type_map = {tid: i for i, tid in enumerate(native_rules.type_ids)}
    board = [None if piece is None else [
        type_map[piece.base_type_id], type_map[piece.current_type_id],
        int(piece.owner), int(bool(piece.promoted)),
    ] for piece in position.board]
    hands = []
    for hand in position.hands:
        counts = [0] * len(type_map)
        for tid, count in hand.counts:
            counts[type_map[tid]] = count
        hands.append(counts)
    return pack_position(native_rules, {
        "board": board, "hands": hands, "side": position.side_to_move,
        "ply": ply_count, "aux_state": position.aux_state,
    })


def is_square_attacked(native_rules, position, square: int, by_owner: int) -> bool:
    """Query semantic pseudo-attack on an already-packed Native position."""
    _require_executable(native_rules)
    if not isinstance(square, int) or isinstance(square, bool):
        raise TypeError("square must be an integer board index")
    if not isinstance(by_owner, int) or isinstance(by_owner, bool) or by_owner not in (0, 1):
        raise ValueError("by_owner must be 0 or 1")
    return bool(_backend(native_rules).semantic_is_square_attacked(
        native_rules.capsule, position, int(square), int(by_owner)
    ))


def attacked_squares(native_rules, position, by_owner: int) -> frozenset[int]:
    """Collect scalar-authority pseudo-attacks, not legal-action counts."""
    _require_executable(native_rules)
    if not isinstance(by_owner, int) or isinstance(by_owner, bool) or by_owner not in (0, 1):
        raise ValueError("by_owner must be 0 or 1")
    return frozenset(_backend(native_rules).semantic_attacked_squares(
        native_rules.capsule, position, by_owner
    ))


def in_check(native_rules, position, side: int) -> bool:
    """Query semantic check on an already-packed Native position."""
    _require_executable(native_rules)
    if not isinstance(side, int) or isinstance(side, bool) or side not in (0, 1):
        raise ValueError("side must be 0 or 1")
    return bool(_backend(native_rules).semantic_in_check(native_rules.capsule, position, int(side)))


def snapshot(native_rules, position):
    out = dict(_backend(native_rules).semantic_position_snapshot(native_rules.capsule, position))
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
    return str(_backend(native_rules).semantic_position_key(native_rules.capsule, position))


def pack_action(fields: dict, *, native_rules=None) -> int:
    """Pack an exact semantic action using the frozen Native bit layout."""
    return int(_backend(native_rules).semantic_action_pack(dict(fields)))


def unpack_action(action: int, *, native_rules=None) -> dict:
    """Unpack and validate an exact semantic action."""
    return {key: int(value) for key, value in _backend(native_rules).semantic_action_unpack(int(action)).items()}


def public_action(native_rules, action: int):
    """Decode an exact packed action without reducing semantic identity.

    The returned object retains pattern, geometry, actor type, coordinates,
    and promotion identity, so packing it again is lossless.
    """
    fields = unpack_action(action, native_rules=native_rules)
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
    raw = dict(_backend(native_rules).semantic_assess_declaration(
        native_rules.capsule, position, str(declaration_id)
    ))
    return DeclarationAssessment(
        str(raw["declaration_id"]), int(raw["actor"]), str(raw["outcome"]),
        None if raw.get("weighted_score") is None else int(raw["weighted_score"]),
    )


def available_declarations(native_rules, position):
    """Return non-losing declaration assessments for the side to move."""
    return tuple(
        DeclarationAssessment(
            str(raw["declaration_id"]), int(raw["actor"]), str(raw["outcome"]),
            None if raw.get("weighted_score") is None else int(raw["weighted_score"]),
        )
        for raw in _backend(native_rules).semantic_available_declarations(
            native_rules.capsule, position
        )
    )


def candidate_actions(native_rules, position) -> tuple[int, ...]:
    """Enumerate deterministic S0 geometry candidates (not yet S1-S4 legal)."""
    return tuple(int(action) for action in _backend(native_rules).semantic_candidate_actions(native_rules.capsule, position))


def guarded_actions(native_rules, position) -> tuple[int, ...]:
    """Return exact actions surviving Native S0-S4 checks currently implemented."""
    return tuple(int(action) for action in _backend(native_rules).semantic_guarded_actions(native_rules.capsule, position))


def guarded_actions_audit(native_rules, position) -> dict:
    """Test-only baseline counters for the exact guarded-action path."""
    raw = dict(_backend(native_rules).semantic_guarded_actions_audit(native_rules.capsule, position))
    raw["actions"] = tuple(int(action) for action in raw.get("actions", ()))
    for key in (
        "candidate_count", "s3_trial_count", "s4_count", "nested_reply_count",
        "child_canonical_key_computations", "history_appends", "attack_check_calls",
    ):
        raw[key] = int(raw.get(key, 0))
    return raw


def material_summary(native_rules, position):
    """Read actual side/ply, owner board totals and board-current/hand-base counts.

    Inventory is owner-major in native_rules.type_ids order. This read-only
    projection is neither evaluation, terminal adjudication nor TT identity.
    Older extensions report the missing entry instead of changing semantics.
    """
    entry = getattr(_backend(native_rules), "semantic_material_summary", None)
    if entry is None:
        raise RuntimeError("native extension lacks semantic material summary; rebuild required")
    return entry(native_rules.capsule, position)


def transient_legal_actions(native_rules, position) -> tuple[int, ...]:
    """Return ordered S0-S4 actions without child key/history authority."""
    return tuple(int(action) for action in _backend(native_rules).semantic_transient_legal_actions(
        native_rules.capsule, position
    ))


def transient_legal_subset(native_rules, position, candidates) -> tuple[int, ...]:
    """Readonly exact legality for a caller-ordered candidate chunk.

    Does not infer a complete action set or terminal result. Core retains state,
    history and adjudication authority; consumers must preserve full coverage.
    """
    operation = getattr(_backend(native_rules), "semantic_transient_legal_subset", None)
    if operation is None:
        raise RuntimeError("installed Native extension lacks candidate chunk legality")
    return tuple(operation(native_rules.capsule, position, candidates))


def transient_legal_actions_audit(native_rules, position) -> dict:
    """Test-only transient legality counters and ordered action set."""
    raw = dict(_backend(native_rules).semantic_transient_legal_actions_audit(
        native_rules.capsule, position
    ))
    raw["actions"] = tuple(int(action) for action in raw.get("actions", ()))
    for key in (
        "candidate_count", "s3_trial_count", "s4_count", "nested_reply_count",
        "child_canonical_key_computations", "history_appends", "attack_check_calls",
    ):
        raw[key] = int(raw.get(key, 0))
    return raw


def policy_logits(native_rules, position, policy) -> dict:
    """Return checked semantic actions and frozen Policy-v1 logits."""
    payload = policy.native_payload() if hasattr(policy, "native_payload") else dict(policy)
    raw = dict(_backend(native_rules).semantic_policy_logits(
        native_rules.capsule, position, payload
    ))
    return {
        "actions": tuple(int(value) for value in raw["actions"]),
        "logits": tuple(float(value) for value in raw["logits"]),
    }


def history_occurrences(position, lo: int, hi: int, *, native_rules=None) -> int:
    return int(_backend(native_rules).semantic_history_occurrences(position, int(lo), int(hi)))


def make_checked(native_rules, position, action: int):
    """Apply an exact semantic candidate in Native and return its child capsule."""
    if native_rules.automatic_adjudications:
        native_rules.require_terminal_policy_support()
    return _backend(native_rules).semantic_make_checked(native_rules.capsule, position, int(action))


def make_unmake_roundtrip(native_rules, position, action: int) -> dict:
    return dict(_backend(native_rules).semantic_make_unmake_roundtrip(native_rules.capsule, position, int(action)))


def candidate_perft(native_rules, position, depth: int) -> int:
    return int(_backend(native_rules).semantic_candidate_perft(native_rules.capsule, position, int(depth)))


def has_legal_action(native_rules, position) -> bool:
    """Read S0-S4 availability independently of terminal history/adjudication.

    Uses the existing terminal availability probe's zero-ply, empty-history
    semantics. This boolean is not a full legal set or terminal verdict.
    """
    _require_executable(native_rules)
    entry = getattr(_backend(native_rules), "semantic_has_legal_action", None)
    if entry is None:
        raise RuntimeError("native extension lacks semantic availability; rebuild required")
    return bool(entry(native_rules.capsule, position))


def terminal_status(native_rules, position) -> dict:
    """Return the exact Native semantic terminal status and winner."""
    native_rules.require_terminal_policy_support()
    raw = dict(_backend(native_rules).semantic_terminal(native_rules.capsule, position))
    raw["status"] = str(raw["status"])
    raw["winner"] = None if raw.get("winner") is None else int(raw["winner"])
    return raw


def dynamic_features(native_rules, position) -> tuple[int, int, int]:
    """Return the Native semantic evaluator's generic dynamic feature vector."""
    return tuple(
        int(value) for value in _backend(native_rules).semantic_dynamic_features(
            native_rules.capsule, position
        )
    )


def spatial_features(native_rules, position) -> dict:
    """Return Native 3x3 occupancy and localized-control feature vectors."""
    raw = dict(_backend(native_rules).semantic_spatial_features(native_rules.capsule, position))
    return {
        "occupancy": tuple(int(value) for value in raw["occupancy"]),
        "localized_control": tuple(int(value) for value in raw["localized_control"]),
    }


def evaluate(
    native_rules,
    position,
    *,
    board_values=None,
    hand_values=None,
    dynamic_values=None,
    spatial_occupancy_values=None,
    localized_control_values=None,
    compact_values=None,
    evaluator_scale: int = 1,
) -> int:
    """Evaluate one packed leaf with the exact Native fixed-point profile."""
    return int(_backend(native_rules).semantic_evaluate(
        native_rules.capsule,
        position,
        board_values,
        hand_values,
        dynamic_values,
        spatial_occupancy_values,
        localized_control_values,
        compact_values,
        int(evaluator_scale),
    ))


def search_runtime_sizes(*, native_rules=None) -> dict:
    """Return Native semantic search-state byte sizes for performance planning."""
    return {
        key: int(value)
        for key, value in _backend(native_rules).semantic_search_runtime_sizes().items()
    }


def _run_search(native_rules, position, depth: int, *, board_values=None, hand_values=None, entrypoint: str) -> dict:
    native_rules.require_terminal_policy_support()
    # The executor now shares the exact terminal/winner authority. Payload
    # version describes rule encoding, not this installed search capability.
    # Older kernels retain the explicit rejection until rebuilt.
    if (native_rules.repetition_policy == "continuous_check_loss"
            and not _backend(native_rules).native_capabilities().get(
                "semantic_fixed_depth_terminal_winners", False)):
        from .compiler import NativeUnsupportedRuleError
        raise NativeUnsupportedRuleError(
            "Native fixed/probe search does not score continuous-check winners; "
            "use semantic iterative search or Core"
        )
    if not _backend(native_rules).native_capabilities().get(
            "semantic_fixed_depth_terminal_dominance", False):
        from .compiler import NativeUnsupportedRuleError
        raise NativeUnsupportedRuleError(
            "Native fixed/probe terminal score band requires a rebuilt kernel; "
            "use semantic iterative search or Core"
        )
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
    raw = dict(getattr(_backend(native_rules), entrypoint)(*args))
    raw["best_action"] = None if raw.get("best_action") is None else int(raw["best_action"])
    raw["principal_variation"] = tuple(int(value) for value in raw.get("principal_variation", ()))
    raw["score"] = int(raw["score"])
    raw["nodes"] = int(raw["nodes"])
    return raw


def fixed_depth_search(native_rules, position, depth: int, *, board_values=None, hand_values=None) -> dict:
    """Run fixed-depth semantic AlphaBeta over guarded board/drop actions.

    This finite board-action reference retains terminal winner/history rules.
    Optional declarations are not searched; use persistent search for them.

    ``board_values`` and ``hand_values`` are optional evaluator profiles; when
    supplied they must be paired.  A
    sequence is interpreted in ``native_rules.type_ids`` order, while a
    mapping must cover those stable type IDs exactly.  Board values are
    applied to each piece's current type and hand values to held base types,
    with the side-to-move perspective determining the sign.  Omitting both
    profiles retains the deterministic ``type_index + 1`` fallback.
    Ordinary scores retain the existing +/-90,000,000 saturation. Rule wins
    and losses score +/-100,000,000, strictly beyond that band; this corrects
    older kernels whose +/-1,000,000 terminals could lose to accepted profiles.
    These compatibility scores have no mate-distance adjustment. Iterative
    and persistent search keep their existing root-relative mate scores.
    """
    return _run_search(native_rules, position, depth, board_values=board_values, hand_values=hand_values, entrypoint="semantic_fixed_depth_search")


def probe_search(native_rules, position, depth: int, *, board_values=None, hand_values=None) -> dict:
    """Run the lower-level compatibility AlphaBeta probe."""
    return _run_search(native_rules, position, depth, board_values=board_values, hand_values=hand_values, entrypoint="semantic_probe_search")


def _require_root_window_support(enabled: bool, native_rules=None) -> None:
    if enabled and not _backend(native_rules).native_capabilities().get("semantic_exact_root_windows", False):
        from .compiler import NativeUnsupportedRuleError
        raise NativeUnsupportedRuleError(
            "Native root-window pruning can select an inexact tied bound; "
            "use full-root windows until exact tie selection is verified"
        )


def _require_immediate_win_support(enabled: bool, native_rules) -> None:
    if not isinstance(enabled, bool):
        raise TypeError("stop_on_immediate_win must be a bool")
    if enabled and not _backend(native_rules).native_capabilities().get(
        "semantic_immediate_win_goal", False
    ):
        from .compiler import NativeUnsupportedRuleError
        raise NativeUnsupportedRuleError(
            "Native immediate-win decision goal requires a rebuilt kernel"
        )


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
    dynamic_values=None,
    spatial_occupancy_values=None,
    localized_control_values=None,
    compact_values=None,
    _root_ply_offset: int = 0,
    tt_megabytes: int = 0,
    root_window_pruning: bool = False,
    stop_on_immediate_win: bool = False,
) -> dict:
    """Run deterministic iterative search on a semantic position.

    The Native entrypoint owns the recursive semantic state stack and checks
    node, monotonic-time, and cooperative-cancellation budgets.  Evaluator
    tables are an immutable call binding; they are not part of the RuleSet
    fingerprint and may be changed between searches.

    stop_on_immediate_win opts into a verified physical root-child decision.
    A prefix win reports completed_depth0, no completed q policy and source
    verified_root_child. Its checked edge is included in search-loop counters.
    False preserves finite analysis and old-kernel call compatibility.
    """
    native_rules.require_terminal_policy_support()
    if _root_ply_offset not in (0, 1):
        raise ValueError("_root_ply_offset must be 0 or 1")
    if isinstance(tt_megabytes, bool) or not isinstance(tt_megabytes, int) or not 0 <= tt_megabytes <= 1024:
        raise ValueError("tt_megabytes must be an integer in [0, 1024]")
    if not isinstance(root_window_pruning, bool):
        raise TypeError("root_window_pruning must be a bool")
    _require_root_window_support(root_window_pruning, native_rules)
    _require_immediate_win_support(stop_on_immediate_win, native_rules)
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
    if dynamic_values is not None:
        if isinstance(dynamic_values, Mapping):
            if set(dynamic_values) != {"mobility", "promotion_potential", "anchor_safety"}:
                raise ValueError("semantic dynamic evaluator profile must cover exactly the dynamic feature names")
            dynamic_values = tuple(int(dynamic_values[name]) for name in (
                "mobility", "promotion_potential", "anchor_safety"
            ))
        else:
            dynamic_values = tuple(int(value) for value in dynamic_values)
        if len(dynamic_values) != 3:
            raise ValueError("semantic dynamic evaluator profile must contain three values")
    if spatial_occupancy_values is not None:
        if isinstance(spatial_occupancy_values, Mapping):
            spatial_keys = {
                f"{owner}:{type_id}" for owner in (0, 1) for type_id in expected
            }
            if set(spatial_occupancy_values) != spatial_keys:
                raise ValueError("semantic spatial evaluator profile must cover every owner/current type")
            rows = [tuple(spatial_occupancy_values[f"{owner}:{type_id}"])
                    for owner in (0, 1) for type_id in expected]
            if any(len(row) != 9 for row in rows):
                raise ValueError("each spatial owner/type mapping row must contain nine values")
            spatial_occupancy_values = tuple(int(value) for row in rows for value in row)
        else:
            spatial_occupancy_values = tuple(int(value) for value in spatial_occupancy_values)
        if len(spatial_occupancy_values) != 2 * len(expected) * 9:
            raise ValueError("semantic spatial evaluator profile length must match 2 * type_count * 9")
        if any(sum(spatial_occupancy_values[i:i + 9]) != 0 for i in range(0, len(spatial_occupancy_values), 9)):
            raise ValueError("semantic spatial evaluator rows must have zero sum")
    if localized_control_values is not None:
        localized_control_values = tuple(int(value) for value in localized_control_values)
        if len(localized_control_values) != 9 or sum(localized_control_values) != 0:
            raise ValueError("semantic localized control profile must contain nine values with zero sum")
    goal_args = ((None,) * 6 + (1, -1, 1, None, False, 0, 0, None, True)
                 if stop_on_immediate_win else ())
    flag = None
    unregister = None
    if cancel_token is not None:
        flag = _backend(native_rules).create_cancel_flag()
        unregister = cancel_token.register_callback(lambda: _backend(native_rules).request_cancel(flag))
    try:
        raw = dict(_backend(native_rules).semantic_iterative_search(
            native_rules.capsule,
            position,
            int(max_depth),
            None if max_nodes is None else int(max_nodes),
            None if max_time_seconds is None else float(max_time_seconds),
            flag,
            board_values,
            hand_values,
            dynamic_values,
            spatial_occupancy_values,
            localized_control_values,
            compact_values,
            int(_root_ply_offset),
            int(tt_megabytes),
            None,
            1,
            None,
            root_window_pruning,
            *goal_args,
        ))
    finally:
        if unregister is not None:
            unregister()
    raw["best_action"] = None if raw.get("best_action") is None else int(raw["best_action"])
    raw["principal_variation"] = tuple(int(value) for value in raw.get("principal_variation", ()))
    for key in ("score", "nodes", "completed_depth", "selective_depth", "qnodes", "elapsed_nanoseconds", "legal_generation_count", "transition_count", "beta_cutoffs", "tt_probes", "tt_hits", "tt_exact_hits", "tt_stores", "tt_replacements", "tt_collisions", "tt_cutoffs", "tt_previous_iteration_hits", "tt_current_iteration_hits", "tt_allocated_bytes", "tt_occupied_entries", "tt_entry_bytes"):
        raw[key] = int(raw.get(key, 0))
    raw["immediate_win"] = bool(raw.get("immediate_win", False))
    raw["result_source"] = str(raw.get("result_source",
        "fallback" if raw.get("used_fallback", False) else "main_iteration"))
    raw["used_fallback"] = bool(raw.get("used_fallback", False))
    raw["declaration_id"] = (
        None if raw.get("declaration_id") is None else str(raw["declaration_id"])
    )
    raw["tt_status"] = "ENABLED" if tt_megabytes else "NOT_STARTED"
    raw["elapsed_seconds"] = raw["elapsed_nanoseconds"] / 1e9
    raw["ruleset_fingerprint"] = str(native_rules.fingerprint)
    raw["evaluator_config_hash"] = hashlib.sha256(json.dumps({
        "ruleset_fingerprint": native_rules.fingerprint,
        "board_values": board_values,
        "hand_values": hand_values,
        "dynamic_values": dynamic_values,
        "spatial_occupancy_values": spatial_occupancy_values,
        "localized_control_values": localized_control_values,
        "compact_values": compact_values,
        "evaluator_scale": 1,
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
    native_rules.require_terminal_policy_support()
    if max_depth < 1:
        return semantic_iterative_search(
            native_rules, position, max_depth, board_values=board_values,
            hand_values=hand_values,
        )
    if native_rules.declarations and any(
        item.outcome != "LOSS" for item in available_declarations(native_rules, position)
    ):
        # Declaration decisions are out-of-band public actions.  Keep the
        # experimental root splitter from silently dropping one.
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
