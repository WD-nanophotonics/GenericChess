# Persistent search-key integrity after the same fault

Two predeclared original/candidate controls completed with ordinary high-limit
Chess. Both retries remain ONGOING; this extends the diagnostic to a nonterminal
case without changing Task007's preserved limit2 false-repetition witness.

Original fault restores root search_key equality while actual multiset differs.
On real same-action retry, actual occurrence count2 enters snapshot.items
correctly, but snapshot.digest differs from rebuilding the exact actual table.
The updater XOR-removes previous_count1 even though the restored parent snapshot
never contained that failed child. A clean same-action runtime has count1 and a
different search key. After pop, stale private data still remains.

Candidate fault restores both root key and actual counts. Retry count1, snapshot
items/digest, clean search_key and final actual multiset all agree. No TT search
or probe was run; there is no evidence of an actual wrong cutoff, hash collision,
natural failure frequency or production user impact.

Decision: a restored key or snapshot-field equality cannot replace direct
mutable-table restoration checking. A multiplicity-preserving table oracle and
finite snapshot/table consistency diagnostic are sufficient for this mechanism;
do not expand into all TT soundness or more unrelated game runs. Product source
stays pinned and unchanged; primary integrates its independently owned repair.
