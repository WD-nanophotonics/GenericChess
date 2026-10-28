"""Finite event-algebra check, explicitly NOT a game/reachability experiment.

The comparator calls only Core's existing history classification predicate on
abstract records. No RuleSet, Position, runtime search, Player, solver or Native
object is created. A match is a source-predicate fact, not a legal-game result.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
from itertools import product
import json
from pathlib import Path
import sys
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from generic_chess.core.terminal import _runtime_perpetual_check_result


def prefix_checker(records, occurrences, limit, complete=True):
    """Exact prefix differences for the current queried repeat window only."""
    if not records or not complete:
        return None
    limit = max(1, int(limit))
    if len(occurrences) < limit:
        return None
    begin, end = occurrences[-limit], occurrences[-1]
    if begin == end:
        return None
    moves = [0, 0]
    nonchecks = [0, 0]
    at_begin = None
    at_end = None
    for index, record in enumerate(records):
        if record.actor in (0, 1):
            moves[record.actor] += 1
            nonchecks[record.actor] += not bool(record.gave_check)
        if index == begin:
            at_begin = tuple(moves), tuple(nonchecks)
        if index == end:
            at_end = tuple(moves), tuple(nonchecks)
    dm = [at_end[0][p] - at_begin[0][p] for p in (0, 1)]
    db = [at_end[1][p] - at_begin[1][p] for p in (0, 1)]
    if not all(dm):
        return None
    checking = [p for p in (0, 1) if db[p] == 0]
    return checking[0] if len(checking) == 1 else None


def source_checker(records, occurrences, limit, complete=True):
    # A data-only predicate stub, not a constructed SearchPathRuntime or a
    # claim that these opaque identities/check events are physically reachable.
    state = SimpleNamespace(history=records, _history_complete=complete,
                            current_identity=records[-1].identity if records else "q", runtime_hash=None,
                            compiled=SimpleNamespace(repetition_limit=limit,
                                support=SimpleNamespace(repetition_limit=limit)),
                            occurrence_count=lambda *_: len(occurrences),
                            history_occurrences=lambda _: occurrences)
    result = _runtime_perpetual_check_result(state)
    return None if result is None else 1 - result.winner


def make_records(identities, actors, checks):
    return tuple(SimpleNamespace(identity=identity, actor=actor, gave_check=check)
                 for identity, actor, check in zip(identities, actors, checks))


def append_summary(summary, identity, actor, check, limit):
    """Pure mathematical fold; no persistent runtime object or hash cache."""
    moves, nonchecks, count_map, windows = summary
    moves, nonchecks = list(moves), list(nonchecks)
    if actor in (0, 1):
        moves[actor] += 1
        nonchecks[actor] += not bool(check)
    count_map = dict(count_map)
    count_map[identity] = count_map.get(identity, 0) + 1
    windows = dict(windows)
    snapshot = tuple(moves), tuple(nonchecks)
    windows[identity] = (*windows.get(identity, ()), snapshot)[-max(1, int(limit)):]
    return tuple(moves), tuple(nonchecks), count_map, windows


def summary_checker(summary, identity, limit):
    _, _, counts, windows = summary
    limit = max(1, int(limit))
    if counts.get(identity, 0) < limit or len(windows.get(identity, ())) < limit:
        return None
    begin, end = windows[identity][-limit], windows[identity][-1]
    moves = [end[0][p] - begin[0][p] for p in (0, 1)]
    nonchecks = [end[1][p] - begin[1][p] for p in (0, 1)]
    if not all(moves):
        return None
    checking = [p for p in (0, 1) if nonchecks[p] == 0]
    return checking[0] if len(checking) == 1 else None


def run(output, max_plies=8):
    tally, decisions = Counter(), Counter()
    for plies in range(max_plies + 1):
        # Initial identity and current identity are q. Intermediate identities
        # are opaque q/r tokens. There is no game graph behind these tokens.
        for mask in range(1 << max(0, plies - 1)):
            identities = ["q"] + ["q" if mask & (1 << (i - 1)) else "r"
                                   for i in range(1, plies)]
            if plies:
                identities.append("q")
            occurrences = [i for i, key in enumerate(identities) if key == "q"]
            actors = [-1] + [(i - 1) % 2 for i in range(1, plies + 1)]
            for bits in product((False, True), repeat=plies):
                records = make_records(identities, actors, [False, *bits])
                for limit in (1, 2, 3, 4):
                    expected = source_checker(records, occurrences, limit)
                    actual = prefix_checker(records, occurrences, limit)
                    assert actual == expected, (plies, mask, bits, limit)
                    tally["abstract_predicate_comparisons"] += 1
                    decisions[str(expected)] += 1
                    if plies <= 6:
                        summary = ((0, 0), (0, 0), {}, {})
                        for record in records:
                            summary = append_summary(summary, record.identity,
                                                     record.actor, record.gave_check, limit)
                        assert summary_checker(summary, "q", limit) == expected
                        tally["summary_fold_comparisons"] += 1
                        # Check transition closure, not just the current label:
                        # each possible next identity/actor/check event is tested.
                        for next_identity, next_actor, next_check in product(("q", "r"), (0, 1), (False, True)):
                            next_records = (*records, SimpleNamespace(identity=next_identity,
                                actor=next_actor, gave_check=next_check))
                            next_occ = [i for i, r in enumerate(next_records) if r.identity == next_identity]
                            wanted = source_checker(next_records, next_occ, limit)
                            next_summary = append_summary(summary, next_identity,
                                next_actor, next_check, limit)
                            assert summary_checker(next_summary, next_identity, limit) == wanted
                            tally["summary_extension_comparisons"] += 1
    controls = {}
    for name, actors, checks, complete in [
        ("only_actor0", [-1, 0, 0], [False, True, True], True),
        ("mutual_all_checks", [-1, 0, 1], [False, True, True], True),
        ("neither_all_checks", [-1, 0, 1], [False, False, False], True),
        ("incomplete", [-1, 0, 1], [False, True, False], False),
        ("checker0", [-1, 0, 1], [False, True, False], True),
        ("checker1", [-1, 0, 1], [False, False, True], True),
    ]:
        records = make_records(["q", "r", "q"], actors, checks)
        a, b = source_checker(records, [0, 2], 2, complete), prefix_checker(records, [0, 2], 2, complete)
        assert a == b
        controls[name] = a
    assert controls == dict(only_actor0=None, mutual_all_checks=None,
                           neither_all_checks=None, incomplete=None,
                           checker0=0, checker1=1)
    # Same global move/check counts need not imply equal current-window facts.
    # This is an abstract event-source counterexample, NOT two proved legal
    # histories. Swap opaque a/b events before/inside the queried window.
    ids = ["q", "a", "q", "b", "c", "d", "q"]
    actor = [-1, 0, 1, 0, 1, 0, 1]
    a = make_records(ids, actor, [False, False, False, True, False, True, False])
    b = make_records(["q", "b", "q", "a", "c", "d", "q"], actor,
                     [False, True, False, False, False, True, False])
    totals = lambda records: [(sum(r.actor == p for r in records),
                              sum(r.actor == p and bool(r.gave_check) for r in records))
                             for p in (0, 1)]
    assert totals(a) == totals(b)
    assert source_checker(a, [0, 2, 6], 2) == prefix_checker(a, [0, 2, 6], 2) == 0
    assert source_checker(b, [0, 2, 6], 2) == prefix_checker(b, [0, 2, 6], 2) is None
    result = dict(status="PASS", max_abstract_plies=max_plies, counts=dict(tally),
                  predicate_results=dict(decisions), controls=controls,
                  global_count_counterexample=dict(scope="ABSTRACT_EVENT_MODEL_ONLY",
                      same_global_actor_move_check_counts=totals(a), same_identity_multiplicities=True,
                      q_occurrences=[0, 2, 6], limit=2, checker_a=0, checker_b=None),
                  script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  limits=["No RuleSet, Position, legal game, runtime, search or Native execution.",
                          "Abstract histories do not establish physical reachability, WDL or a product defect.",
                          "Prefix predicate and abstract append closure are checked; no physical continuation or TT implementation is certified.",
                          "The functional summary is a research data model; no production history cache/replacement or cost gain is implemented."])
    output.mkdir(parents=True, exist_ok=False)
    (output / "events.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    run(args.output)
