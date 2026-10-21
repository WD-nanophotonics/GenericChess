# TD query consumer composition — 2026-10-19

## Question

Can a cold Native search replace the query used by the existing TDLeaf trainer
while keeping its behavior policy and reducing the caller's cost?

## Evidence and scope

The saved 5x5 query panel compares the published source `TrainingSearch` on the
current Core (`302aef755b883a321a6babe06eb2c3329d61c4bf`) with Native cold D2,
q0, TT0 queries with root-window pruning off and on. Its source learner and
recorded inputs are pinned to `origin/sidemission` commit
`57696f621cda9957bbef8f10d5ff8515f8482616`. The panel contains 32 first/last
published model witnesses, 16 fixed-prefix roots across four generated rules,
three repeats, and four actually terminal roots. The completed query log has
288 nonterminal queries per method; all 288 terminal-method slots per the
three-method panel were retained as skips, and no planned slot was unexecuted.
The producer result was already present when this audit resumed; it was read and
re-analyzed here, not rerun.
The pinned `TrainingSearch` calls use `quiet=False`, so its D2 query has no
quiescence extension; path-seeded move ordering is coefficient-independent.

Across all 576 paired Native calls, mapped receipts match the source query's
raw value, PV feature vector, terminal flag, prediction, and gradient. They are
complete D2 queries with zero recorded float regret on this panel. The
`exact_optimal_signature` field means that a PV material-feature signature is
in the target's set of optimal feature signatures; it does **not** mean that
the first action is an optimal-action-set member or that two policies agree.

## Behavior-policy difference

Of 288 source/Native query triplets, 234 have the same first action in both
Native modes as in Source. In the other 54 triplets, both Native modes choose
the same action, but it differs from Source. Those are 18 model-rule contexts
repeated three times and four distinct physical roots. Replaying one recorded
disagreement per root through the current Core confirms that both actions are
legal and produce different successor positions in all four cases:

| Rule seed / root family | Source action | Native action | Immediate material vector |
| --- | --- | --- | --- |
| 356001 / 861003 | `A@e3` | `A@c3` | same |
| 356003 / 861004 | `c2-b3` | `d2-b3` | same |
| 356003 / 861002 | `a2-c3` | `d1-c3` | same |
| 356004 / 861002 | `e4-b5` | `e4-b5=A` | different; Native promotes to A |

The table is a finite action audit, not game-outcome evaluation. Matching the
search target's leaf features does not preserve the selected move, successor
state, or later trajectory. In particular, the promotion example rules out
describing every disagreement as an interchangeable tie choice.

A separate no-query reader audit replays the 32 saved first/last actual trainer
witnesses. Source actions reproduce all 32 recorded `record_after` children.
Native changes the physical child and execution history on 12 of those 32
witnesses despite equal local TD credit fields. This is a replay of saved
receipts, not new search calls or a trajectory/game evaluation; its denominator
is distinct from the 288 query triplets above.

The saved [capture-source capsule](https://github.com/WD-nanophotonics/GenericChess/blob/b942f11e50e20689d4455c5b4dc2d00ea0985b89/docs/archive/td_query_service_20261019/manifest.json)
contains 60 hashed project payloads. I executed its `reproduce.py` from the
repository root on this Core revision: all four captured-source outputs match
on non-time fields in 7.978 seconds. The script uses Python `-S`, verifies
source origins, and runs without Native, games, training, optimizer updates,
or UNKNOWN refill. This independently reproduces the captured-source checks;
it does not rerun the original Native queries or learning experiment.

## Cost and consumer contract

Measured caller seconds, including environment copy/record, search, PV mapping,
prediction, and gradient, sum to 10.0443 for Source, 0.8782 for Native with
root-window off, and 0.6329 with it on. Source counted 28,692 nodes; Native
counted 101,544 visits off and 30,174 on. These are different work currencies,
so no nodes-per-second or per-node claim follows. Setup/binding and log I/O were
recorded separately; the complete saved producer run took 15.8402 seconds.

The pinned trainer calls `td.observe(m, r)` and then advances the environment
with `e.push(r.action)` when the same search is complete. `TDLeafEpisode.observe`
uses completeness, value, PV features, terminal status, and a frozen episode
weight snapshot; it does not learn from interval bounds. Therefore a one-call
Native substitution retains the sampled target fields on these inputs but
changes the actor's move on the observed disagreement roots. Keeping the
Source-selected move while asking Native for the target requires both searches.
That duplicates a target already returned by Source here and raises the summed
caller time to 10.6772 seconds (Native window on) or 10.9225 seconds (off),
before negligible binding overhead.

## Decision

Do not add a Native-to-TD API or replace the existing trainer's query on this
evidence. The speed ratio applies to these bounded query callers, not an
end-to-end learning run. A Native actor would be a changed behavior policy and
would need a separately frozen actual-W/L evaluation; that would duplicate the
auxiliary learning lane, so PRIMARY does not launch it. Keep source/Native
target-field agreement as a scoped compatibility result, not trajectory,
strength, all-domain, or cost-per-node equivalence. Science remains OPEN.

The action replay was a four-root semantic diagnostic over already saved query
records; no new search, game, learner, optimizer, or training run was executed.
