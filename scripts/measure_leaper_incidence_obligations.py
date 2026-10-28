"""Logical edit census on existing literal paths, not a runtime benchmark.

Counts, source-set masks and union bits are scratch mathematical projections.
No provider/backend is installed and no search decision or new trajectory is made.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.session.session import GameSession
from scripts import verify_leaper_occupancy_projection as projection
from scripts.verify_published_boolean_returns import diagnostic_action


def counts(occupancy, types, reverse, area):
    return {(owner, target): sum((occupancy[owner, tid] & reverse[owner, tid, target]).bit_count()
                                for tid in types)
            for owner in (0, 1) for target in range(area)}


def mask_targets(mask):
    while mask:
        bit = mask & -mask
        yield bit.bit_length() - 1
        mask ^= bit


def obligation(parent, child, action, compiled, types, forward, reverse):
    area, width = compiled.board_shape.area, compiled.board_shape.width
    old = projection.occupation(parent, compiled, types)
    new = projection.occupation(child, compiled, types)
    old_counts, new_counts = counts(old, types, reverse, area), counts(new, types, reverse, area)
    s = action.from_square.rank * width + action.from_square.file
    t = action.to_square.rank * width + action.to_square.file
    actor, victim = parent.board[s], parent.board[t]
    edits = [(actor.owner, actor.current_type_id, s, -1),
             (actor.owner, actor.current_type_id, t, 1)]
    if victim is not None:
        edits.append((victim.owner, victim.current_type_id, t, -1))
    delta = Counter()
    sequential = 0
    for owner, tid, source, sign in edits:
        for target in mask_targets(forward.get((owner, tid, source), 0)):
            delta[owner, target] += sign
            sequential += 1
    predicted = {key: value + delta[key] for key, value in old_counts.items()}
    assert predicted == new_counts
    assert all(value >= 0 for value in predicted.values())
    changed_sources = changed_counts = union_flips = 0
    for owner in (0, 1):
        for target in range(area):
            old_sources = projection.sources(old, reverse, types, owner, target)
            new_sources = projection.sources(new, reverse, types, owner, target)
            assert old_counts[owner, target] == old_sources.bit_count()
            assert new_counts[owner, target] == new_sources.bit_count()
            changed_sources += old_sources != new_sources
            changed_counts += old_counts[owner, target] != new_counts[owner, target]
            union_flips += bool(old_sources) != bool(new_sources)
    return dict(source_contribution_edits=len(edits), sequential_incidence_edits=sequential,
                net_nonzero_count_rows=sum(value != 0 for value in delta.values()),
                source_set_rows_changed=changed_sources, count_rows_changed=changed_counts,
                attack_union_bits_changed=union_flips, captured=victim is not None)


def run(inputs, archive, output):
    assert projection.sha(inputs.read_bytes()) == projection.INPUT_SHA
    packet = projection.read(inputs)
    by_id = {row["id"]: row for row in packet["rows"]}
    compiled_cache, rows, unique = {}, [], {}
    manifest = projection.read(archive / "manifest.json")
    entries = {entry["file"]: entry for entry in manifest["files"]}
    for number in range(48):
        raw = projection.read(archive / f"boolean-experiment--return-{number:03d}.json.gz")
        # Rely on the earlier byte-bound input/return verifier, then bind this
        # census to its exact data digest rather than silently trust filenames.
        entry = entries[f"boolean-experiment--return-{number:03d}.json.gz"]
        assert projection.sha((archive / entry["file"]).read_bytes()) == entry["publication_sha256"]
        source = by_id[raw["case_id"]]
        fp = source["fingerprint"]
        if fp not in compiled_cache:
            compiled = compile_legacy_ruleset_for_semantic_execution(ruleset_from_dict(source["RuleSet"]))
            types, forward, reverse, _ = projection.incidence(compiled)
            compiled_cache[fp] = compiled, types, forward, reverse
        compiled, types, forward, reverse = compiled_cache[fp]
        session = GameSession.replay(compiled, deserialize_game_record(json.dumps(source["record"])))
        for ply, diagnostic in enumerate(raw["decision"]["principal_variation"]):
            action = diagnostic_action(diagnostic, fp)
            parent = session.state.position
            session.submit(action)
            child = session.state.position
            measured = obligation(parent, child, action, compiled, types, forward, reverse)
            key = parent, action, child
            if key not in unique:
                unique[key] = dict(id=len(unique), case=raw["case_id"], parent_repr=repr(parent),
                                   action_repr=repr(action), child_repr=repr(child), **measured)
            rows.append(dict(slot=number, pv_index=ply, unique_transition=unique[key]["id"],
                             case=raw["case_id"], **measured))
    assert len(rows) == 286
    # Explicit list avoids confusing identifiers/strata with edit quantities.
    keys = ["source_contribution_edits", "sequential_incidence_edits", "net_nonzero_count_rows",
            "source_set_rows_changed", "count_rows_changed", "attack_union_bits_changed"]
    totals = {key: sum(row[key] for row in rows) for key in keys}
    distinct = list(unique.values())
    unique_totals = {key: sum(row[key] for row in distinct) for key in keys}
    result = dict(status="PASS", source_input_sha256=projection.INPUT_SHA,
                  paths=48, path_occurrences=len(rows), distinct_transitions=len(distinct),
                  occurrence_totals=totals, unique_transition_totals=unique_totals,
                  rows=rows, distinct_transition_witnesses=distinct,
                  script_sha256=projection.sha(Path(__file__).read_bytes()),
                  conclusions=["Counts+typed occupancy+fixed forward/reverse incidence suffice for exact restricted attacks.",
                               "No dynamic source-bitset cache is semantically mandatory for these attack consumers.",
                               "Net count changes may cancel while source identities change; counts are not a source list.",
                               "These are set/incidence obligations, not CPU operations, byte writes, time or speedup.",
                               "History, public actions, terminal, integration/abort and runtime cost remain outside this census."])
    output.mkdir(parents=True, exist_ok=False)
    (output / "counts.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in result.items()
                      if key not in {"rows", "distinct_transition_witnesses"}}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    run(args.inputs, args.archive, args.output)
