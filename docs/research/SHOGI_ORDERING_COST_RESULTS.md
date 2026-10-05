# Same static leaf result with fewer runtime searches on the fixed tree

One prospective ordering intervention, exact same frozen quantized evaluator:
score130057 and unique promoted-capture choice unchanged. Production legacy
ordering completes depth2, qnodes0, no fallback,27 nodes/25 pushes/20 leaf
evaluations versus saved no-ordering51 nodes/49 pushes/44 evaluations. Seven
ordering calls. ALL visited physical states match the frozen reference tree;
25 pops balance. This is a useful local integration/cost result, not evidence
that these material coefficients improve WDL or general search speed.

The intervention includes capture/promotion and ordinary killer/history
ordering; capture hint uses board CURRENT plus captured BASE hand minus mover
CURRENT. No new leaf evaluation, game query or goal label. Canonical root ties
and search semantics remain fixed. No coefficient/scale/orderer variants tried
after observation; baseline reused, never rerun.

New cost88 candidates/213 conservatively returned actions; paired74 pushes,
conservative1431 enumeration including old whole1130,0.235sec cumulative.
The old candidate counter combined two laws, so we cannot give a precise
per-run candidate reduction. Wall time is one short measurement, not a robust
speedup estimate. Full caps128/5000/15sec hold;0 public events/source queries.

First wrapper's added pins shifted a positional input: preserved0-search
AssertionError. Separate qualified wrapper binds the tree's explicit path,
retains original source/pins/output and all intervention rules. No completed
search rerun or reset of old goal budgets. Source hashes unchanged.
