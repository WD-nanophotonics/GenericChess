# Semantic search interface smoke check — 2026-10-20

## Question and scope

Do five existing semantic-rule fixtures complete through the unfamiliar-rule
search interface, repeat deterministically, and agree with the bounded plain
Core reference at depth 1? This is an initial-root interface smoke check only;
it is not evidence that the listed semantic mechanisms are searched correctly.

## Result

All five calls completed. For each fixture, plain Python and the public bundle
completed twice, repeated identically, and matched the completed reference
score. The public bundle used its Native provider without a fallback. Each
search visited four nodes and selected a legacy King action.

Inspection of `tests/rule_semantics_ir_fixtures.py` shows why this does not test
the named mechanisms: `weird_rulesets()` builds each root using the default
`_semantic_ruleset` position, which places only the two Kings and gives no
pieces to either hand. The semantic actor is `R`; therefore the screen-count,
zone-guarded drop, expiring auxiliary/promotion, compound-shift and S3-reply
actions cannot be exercised from these roots. The recorded reference actions
are legacy King moves (`legacy_018` or `legacy_020`), and the four-node search
does not establish behavior after a target action.

## Decision

Treat the output as evidence that the interface dispatches and returns stable
depth-1 results for these initial positions only. Do not cite it as mechanism,
legality, PV, Native-parity or unfamiliar-rule coverage. The earlier checkpoint
overstated the experiment's scope; this report corrects that interpretation.
An immediate follow-up first put the adjacent R at file 3/rank 2 instead of
file 2/rank 3, so that probe was invalid. After correcting the coordinate, Core
generated exactly one compound action, its multi-piece transition matched the
declared effects, and depth-1 plain/public-bundle searches matched the completed
Core reference. A separate prepared two-screen root generated a semantic
capture whose transition and selected depth-1 PV also matched the reference.
An additional guarded-drop root reached after a real capture and opponent reply
produced one legal guarded drop among 78 root actions; depth-1 plain/public
scores matched the 78-leaf Core reference, though the drop was not selected in
the PV. A separate direct transition check confirmed the R was placed at the
target and removed from hand; no search rerun was done.
The compact evidence and limits are recorded in
`SEMANTIC_SEARCH_MECHANISM_PROBES_20261020.md` and its JSON. These local probes
correct the setup error and sample three mechanism paths; they do not prove
broad mechanism coverage or utility.

Exact private run records remain in ignored `.local_agent/semantic-search-interface-20261020/`.
