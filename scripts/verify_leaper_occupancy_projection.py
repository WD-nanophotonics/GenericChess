"""Offline finite witness for a plain-Leaper attack projection.

This is not a legality provider, search backend, cache or performance benchmark.
It reads published literal paths, derives static incidence from the existing IR,
and compares scratch occupancy algebra with authoritative Core pseudo-attacks.
No source capsule, Player, Native module or search entry is executed.
"""
from __future__ import annotations

import argparse
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from generic_chess.core.search_runtime import _plain_leaper_hash_patterns
from generic_chess.core.semantic_executor import semantic_engine_for
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution
from generic_chess.rules.schema import compute_fingerprint, ruleset_from_dict
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.session.session import GameSession
from scripts.verify_published_boolean_returns import diagnostic_action

INPUT_SHA = "dc471719ad6720f97be01b0a052cdc14728dfdab29dbe4b8bdb8a0785fb9dd93"


def read(path):
    raw = Path(path).read_bytes()
    return json.loads(gzip.decompress(raw) if str(path).endswith(".gz") else raw)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def incidence(compiled):
    """Forward and reverse endpoints, using distinct mechanical traversals."""
    assert _plain_leaper_hash_patterns(compiled) is not None
    assert compiled.board_shape.area <= 64
    forward = {}
    types = tuple(sorted(compiled.support.type_metadata))
    for pattern in compiled.ir.patterns:
        if pattern.target.kind != "target_enemy":
            continue
        for tid in pattern.type_ids:
            for gid in pattern.geometry_ids:
                geometry = compiled.ir.geometry[gid]
                if geometry.kind == "drop":
                    continue
                assert geometry.kind == "leap"
                if geometry.atom_source is not None and geometry.atom_source[0] != tid:
                    continue
                for owner in (0, 1):
                    for source, path in geometry.paths[str(owner)].items():
                        assert len(path) <= 1
                        if path:
                            key = owner, tid, source
                            forward[key] = forward.get(key, 0) | (1 << path[0])
    reverse = {(owner, tid, target): 0 for owner in (0, 1)
               for tid in types for target in range(compiled.board_shape.area)}
    rows = compiled._incoming_attack_paths
    assert rows is not None, "this witness does not invent an incoming-index fallback"
    duplicates = 0
    for (owner_text, target), entries in rows.items():
        owner = int(owner_text)
        for pattern, tid, source, gid, path in entries:
            assert not path
            key = owner, tid, target
            bit = 1 << source
            duplicates += bool(reverse[key] & bit)
            reverse[key] |= bit
    # Every possible source/target/type/owner relation is checked, including
    # absent edges. This checks a transpose, not runtime reachability.
    for owner in (0, 1):
        for tid in types:
            for source in range(compiled.board_shape.area):
                for target in range(compiled.board_shape.area):
                    assert bool(forward.get((owner, tid, source), 0) & (1 << target)) == bool(
                        reverse[owner, tid, target] & (1 << source))
    return types, forward, reverse, duplicates


def occupation(position, compiled, types):
    assert position.ruleset_fingerprint == compiled.ruleset_fingerprint
    assert position.board_shape == compiled.board_shape
    assert not position.aux_state and not any(h.counts for h in position.hands)
    assert type(position.side_to_move) is int and position.side_to_move in (0, 1)
    out = {(owner, tid): 0 for owner in (0, 1) for tid in types}
    anchors = [0, 0]
    for source, piece in enumerate(position.board):
        if piece is None:
            continue
        assert type(piece.owner) is int and piece.owner in (0, 1)
        assert piece.current_type_id in types
        assert piece.base_type_id == piece.current_type_id and piece.promoted is False
        out[piece.owner, piece.current_type_id] |= 1 << source
        anchors[piece.owner] += int(compiled.support.type_metadata[piece.current_type_id].is_anchor)
    assert anchors == [1, 1]
    return out


def sources(occupancy, reverse, types, owner, target):
    result = 0
    for tid in types:
        result |= occupancy[owner, tid] & reverse[owner, tid, target]
    return result


def check_position(position, compiled, types, forward, reverse, stats, witnesses):
    occ = occupation(position, compiled, types)
    engine = semantic_engine_for(compiled)
    occupied = {i: p for i, p in enumerate(position.board) if p is not None}
    for owner in (0, 1):
        for target in range(compiled.board_shape.area):
            mask = sources(occ, reverse, types, owner, target)
            actual = engine.is_square_attacked(position, target, owner)
            assert bool(mask) == actual, (owner, target, mask)
            stats["core_attack_comparisons"] += 1
            if target not in occupied:
                stats["empty_target_comparisons"] += 1
            elif occupied[target].owner == owner:
                stats["friendly_target_comparisons"] += 1
            if mask.bit_count() > 1 and "overlap" not in witnesses:
                first = (mask & -mask).bit_length() - 1
                remainder = mask & ~(1 << first)
                union = 0
                for source, piece in occupied.items():
                    if piece.owner == owner:
                        union |= forward.get((owner, piece.current_type_id, source), 0)
                naive = union ^ forward[owner, occupied[first].current_type_id, first]
                assert not (naive & (1 << target)) and remainder
                witnesses["overlap"] = dict(owner=owner, target=target, sources=mask,
                    removed_source=first, remaining_sources=remainder,
                    naive_xor_says_attacked=False, correct_says_attacked=True,
                    position_repr=repr(position))
            # A source occupancy bitset identifies the actual sources, not
            # merely the attacked union. Verify every source against IR rows.
            expected = 0
            for source, piece in occupied.items():
                if piece.owner == owner and forward.get((owner, piece.current_type_id, source), 0) & (1 << target):
                    expected |= 1 << source
            assert mask == expected
    return occ


def check_delta(parent, child, action, compiled, types, forward, reverse, stats):
    """Scratch two-cell substitutions and undo, never a Core replacement."""
    before = occupation(parent, compiled, types)
    desired = occupation(child, compiled, types)
    n = compiled.board_size
    source = action.from_square.rank * n + action.from_square.file
    target = action.to_square.rank * n + action.to_square.file
    assert source != target and action.promotion_target_id is None
    actor, victim = parent.board[source], parent.board[target]
    assert actor is not None and actor.owner == parent.side_to_move
    assert child.board[source] is None and child.board[target] == actor
    assert child.side_to_move == 1 - parent.side_to_move
    assert parent.hands == child.hands and parent.aux_state == child.aux_state == ()
    assert all(a == b for i, (a, b) in enumerate(zip(parent.board, child.board))
               if i not in (source, target))
    changes = [(actor.owner, actor.current_type_id, source, False)]
    if victim is not None:
        assert victim.owner == 1 - actor.owner
        changes.append((victim.owner, victim.current_type_id, target, False))
        stats["capture_deltas"] += 1
    else:
        stats["quiet_deltas"] += 1
    changes.append((actor.owner, actor.current_type_id, target, True))
    mutable = dict(before)
    undo = []
    # Every possible intermediate edit prefix can be rolled back with old
    # slots. This is algebraic rollback only, not a runtime abort test.
    for owner, tid, square, insert in changes:
        key = owner, tid
        undo.append((key, mutable[key]))
        bit = 1 << square
        assert bool(mutable[key] & bit) is not insert
        mutable[key] = (mutable[key] | bit) if insert else (mutable[key] & ~bit)
        rolled_back = dict(mutable)
        for old_key, old_value in reversed(undo):
            rolled_back[old_key] = old_value
        assert rolled_back == before
        stats["rollback_prefixes"] += 1
    assert mutable == desired
    for owner in (0, 1):
        for target_square in range(compiled.board_shape.area):
            # Independently update the old SOURCE set without reading the
            # child's board or recomputing its occupancy. Captures clear the
            # victim's source bit; they do not XOR an attacked-target union.
            incremental = sources(before, reverse, types, owner, target_square)
            if owner == actor.owner:
                incremental &= ~(1 << source)
                if forward.get((owner, actor.current_type_id, target), 0) & (1 << target_square):
                    incremental |= 1 << target
            elif victim is not None:
                incremental &= ~(1 << target)
            assert incremental == sources(desired, reverse, types, owner, target_square)
            stats["delta_source_comparisons"] += 1
    for key, old in reversed(undo):
        mutable[key] = old
    assert mutable == before
    stats["delta_undo_transitions"] += 1


def verify(inputs, archive, output):
    started = time.perf_counter()
    assert sha(inputs.read_bytes()) == INPUT_SHA
    packet = read(inputs)
    assert len(packet["rows"]) == 24
    frozen = read(archive / "boolean-experiment--frozen.json.gz")
    assert frozen["input_sha256"] == INPUT_SHA
    slots = read(archive / "boolean-experiment--slots.json.gz")
    # File bytes are checked against the already published manifest. Do not
    # re-audit all RAW48 fields or repeat its completed scientific question.
    manifest = read(archive / "manifest.json")
    entries = {e["file"]: e for e in manifest["files"]}
    stats, witnesses, rules, roots, seen = Counter(), {}, {}, {}, set()
    table_rows = []
    for row in packet["rows"]:
        fingerprint = row["fingerprint"]
        if fingerprint not in rules:
            rule = ruleset_from_dict(row["RuleSet"])
            assert compute_fingerprint(rule) == fingerprint
            compiled = compile_legacy_ruleset_for_semantic_execution(rule)
            types, forward, reverse, duplicates = incidence(compiled)
            rules[fingerprint] = compiled, types, forward, reverse
            table_rows.append(dict(fingerprint=fingerprint, board_area=compiled.board_shape.area,
                types=len(types), nonempty_forward_rows=len(forward),
                reverse_rows=len(reverse), duplicate_incoming_sources=duplicates,
                forward_incidence_bits=sum(x.bit_count() for x in forward.values()),
                reverse_incidence_bits=sum(x.bit_count() for x in reverse.values())))
        compiled, types, forward, reverse = rules[fingerprint]
        record = deserialize_game_record(json.dumps(row["record"]))
        session = GameSession.replay(compiled, record)
        roots[row["id"]] = compiled, record
        if session.state.position not in seen:
            check_position(session.state.position, compiled, types, forward, reverse, stats, witnesses)
            seen.add(session.state.position)
        stats["input_histories"] += 1
    for number in range(48):
        name = f"boolean-experiment--return-{number:03d}.json.gz"
        assert sha((archive / name).read_bytes()) == entries[name]["publication_sha256"]
        raw = read(archive / name)
        assert raw["slot"] == slots[number]["slot"] == number
        assert raw["case_id"] == slots[number]["case_id"]
        compiled, record = roots[raw["case_id"]]
        types, forward, reverse = rules[compiled.ruleset_fingerprint][1:]
        session = GameSession.replay(compiled, record)
        for diagnostic in raw["decision"]["principal_variation"]:
            action = diagnostic_action(diagnostic, record.ruleset_fingerprint)
            parent = session.state.position
            session.submit(action)
            child = session.state.position
            check_delta(parent, child, action, compiled, types, forward, reverse, stats)
            if child not in seen:
                check_position(child, compiled, types, forward, reverse, stats, witnesses)
                seen.add(child)
            stats["literal_path_plies"] += 1
        stats["saved_returns"] += 1
    assert stats["literal_path_plies"] == 286 and stats["saved_returns"] == 48
    result = dict(status="PASS", counts=dict(stats), distinct_positions=len(seen),
        rules=len(rules), incidence=table_rows, witnesses=witnesses,
        source_input_sha256=INPUT_SHA, script_sha256=sha(Path(__file__).read_bytes()),
        elapsed_seconds=time.perf_counter() - started,
        limits=["Finite relative-to-current-Core witness, not independent WDL or strength.",
               "Scratch Python dictionaries are not an implemented runtime/provider/cache.",
               "No whole-call benchmark, Player, search, game production or Native build.",
               "Pseudo-attacks include empty/friendly targets and pinned actors; not legal captures.",
               "Projection alone omits side/rule binding/history/clock/public action identity; base/current and promoted fields are fixed by admission.",
               "Undo prefixes establish algebra only; no integrated runtime exception claim."])
    output.mkdir(parents=True, exist_ok=False)
    (output / "verification.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    verify(args.inputs, args.archive, args.output)
