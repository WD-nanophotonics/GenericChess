# Initial full-stock static search: integration, not strength

The new board-only evaluator handles all38 conserved ordinary resources using
the existing origin/custody ledger and all13 fixed board coefficients. The old
two-resource evaluator correctly rejects this root. The standard initial state
was selected by the rules before labels, not by a positive mate outcome.

One depth1/qdepth0 production run completes with30 pushes/30 pops,31 evaluations,
score0 and unchanged root. Each evaluated one-ply quiet leaf has score0: no
promotion/capture occurs and owner inventories stay balanced. All choices tie;
the first returned action is an implementation ordering artifact. There is no
new strength label, WDL certificate or informative material preference.

The evaluator refuses any held inventory. This prevents a search containing
capture from silently selecting zero/unit/midpoint held prices; such a search
must obtain an independently declared held-law scope first. Numeric safety
does not extend the old physical-constructor admission or full-game semantics.

## Enumeration accounting qualification

The raw producer counts61 semantic candidates plus960 returned actions AFTER
its instrumentation starts. Compilation's initial-position validation and
initial_state's terminal probe occur before instrumentation. Do not call1021
the measured whole-run enumeration count. Preserve this instrumentation gap.

A conservative source bound covers these TWO preflight existence probes with
no rerun. Per owner the initial stock is K1/P9/L2/N2/S2/G2/B1/R1. Counting every
ray up to8 board steps gives at most123 atom destinations. Two target families
and at most two inherited promotion choices give492 candidate upper bound per
probe. Empty hands yield no drop candidate; no extra setup is defined. The
compiler validates one standard initial setup once; initial_state probes once.
Neither probe returns an action list charged by the runtime-list counter.
Therefore a conservative whole-run charge is1021+2*492=2005, below5000.
This bound is not an exact measurement. Root construction, compilation and
search wall time are all within the recorded0.094sec/15sec limit. Pushes30<128.

The bound refers to the declared semantic candidate/list counters, not all
internal geometry arithmetic, attack tests or compiler operations. No attempt
is made to hide those operations as independent game evidence. Raw source pins
and partial evidence remain immutable; no extra production run was performed.

Evidence: `data/shogi_full_board_search_20261006.json`; protocol and producer.
Next investigate held-interval robust backup rather than force a scalar hand
price or deepen this all-tie opening merely to obtain a preference.
