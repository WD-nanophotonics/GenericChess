# Reachable history and Native trace targets — 2026-10-19

The current Native search remains correct on these finite fixtures. Its
diagnostic trace key cannot identify a unique history-conditioned target,
even within a single query. This closes the bounded history-contract question
without changing Native search, an AUX learner, or a public API.

## Actual supported alternative after the Pass refusal

The previous [trace supplement](https://github.com/WD-nanophotonics/GenericChess/blob/b942f11e50e20689d4455c5b4dc2d00ea0985b89/docs/research/data/native_trace_contract_20261018/README.md)
matched all 1506 rows on two exposed signed-source rules, with zero ambiguous
contexts. That was scoped evidence. Its next-plan first step preserved an
existing Pass/history fixture and recorded Native's explicit refusal; it did
not strip Pass or claim a Native collision.

The new [complete technical supplement](https://github.com/WD-nanophotonics/GenericChess/blob/b942f11e50e20689d4455c5b4dc2d00ea0985b89/docs/research/data/native_trace_history_20261019/README.md)
uses ordinary reversible movement and the existing repetition rule. A forced
4-cycle faithfully follows test_native_history.py. Public Sessions at plies
3, 7 and 11 share a position, but the next repetition differs. Eighteen cold
D1/D2/D4 requests in both window modes retain the full histories. Earlier roots
return -1, the late root 0, with colliding position trace keys.

A distinct two-choice fixture has two reversible tokens per player on 6x6.
One D8 request per mode uses TT0 and q0. Independent complete Core trees over
all iterative depths find real within-query transpositions. The full RuleSets,
actual action paths, state hashes, count vectors and raw returned rows are saved.

| Fixture / mode | Native calls | Retained rows | Rows with several full states | Rows with several values | Rows invalid for some matching context |
|---|---:|---:|---:|---:|---:|
| Forced cycle / False | 9 | 56 | 0 | 0 | 0 |
| Forced cycle / True | 9 | 56 | 0 | 0 | 0 |
| Branching / False | 1 | 100 | 72 | 3 | 2 |
| Branching / True | 1 | 98 | 60 | 1 | 0 |

All 20 root values agree with full Core targets. Every emitted bound has at
least one valid matching context. These counts therefore do not identify a
wrong Native execution path or establish a search defect. In particular, True
does not establish history-safe pooling: its ambiguous LOWER -2 happens to be
valid for both -2 and 0, while exact targets still differ between those states.

## Same-ply public records isolate the problem

Select the first saved branching EXACT multi-value witness, for mechanism
diagnosis only. Replay its two seven-action paths using actual Session.submit,
then search each at D1 under both modes: four additional cold requests.

The parents have the same board, side, rule, ply 7, legal-move geometry and
material inputs. Their complete histories and repetition-count maps differ.
Their correct root targets are -2 and 0. Both Native modes return these exact
values under identical position_identity, side, remaining_depth, search_ply,
ruleset_fingerprint, board/hand counts and board features.

The profile uses the existing material-only scale 1. No signed256 endpoint,
price fitting, new training, human holdout or strength claim is involved.

Totals are 24 Native requests / 1600 nodes / 0.21155 successful producer seconds.
The original 32-query count cap is respected and unused slots are closed.
The intended continuous 120-second wall cap was not enforced across staged
Agent preparation/analysis: producers tracked only their own/aggregate runtime.
The saved budget-deviation.json records the actual file-time span and this
protocol limitation; 0.21155 seconds must not be presented as total elapsed
experiment/engineering cost. No frozen fitness or reference tail is refilled. Core builds 1048 visits / 1028 edges, checks 310 retained rows / 50 PV
edges, then separately checks four witness children and both canonical records.
Producer wall excludes the Agent's preparation, reader, tests and recording.

## Consumer consequence and validation

A result-level query identity is necessary provenance, but cannot identify
an interior path removed by within-query trace deduplication. Position-key
pooling is not qualified for exact history-conditioned target reuse. An
explicit distributional approximation would be a different method, not a
claim of exact context identity.

The fixed published AUX93 consumer uses Core float/path samples with its own
credit rules. PRIMARY does not execute, migrate or rewrite it. There is no
current consumer migration requiring a new diagnostics API or Native dedup
change. The product receives a five-line explanatory comment and two regression
controls preserving actual histories, correct Core/Native values and immutable
parents. No algorithm, binary, output field or default changes.

[Source qualification](https://github.com/WD-nanophotonics/GenericChess/blob/b942f11e50e20689d4455c5b4dc2d00ea0985b89/docs/research/data/native_trace_history_20261019/qualification.json)
regenerates both Core outputs from established hash-pinned public source
capsules, Python -S, without Native: private 1.987 seconds and public-copy verification 1.928
seconds. It compares every
non-runtime output. Original producer/reader setup failures are retained in
technical form; raw command/account evidence remains private. This is finite
semantic evidence, not universal history safety, all-defense WDL, or a learner
comparison.

The next independent mainline question changes the search regime: assess the
existing root-window option in a q4-requested paid service. Retained D1 q0
reserve results must be separated from completed q4. Its newly registered
rules, games and bounded Core product-search control are separate from this
history budget and from AUX/DS work; no trace learning is launched.
