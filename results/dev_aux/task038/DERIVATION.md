# Ranked-stream retrieval derivation

For ordered nonempty groups with unique ranks, let k be their count and let p be the number of globally ordered rows yielded before the caller returns. For p=0 no merge work is entered. For p>=1, merge first retrieves one row from every nonempty group. Requesting each later yield advances the group that supplied the preceding yield. Therefore successful row retrievals are:

`R = k + sum(has_successor_in_same_group(rank) for rank in first p-1 yielded ranks)`.

Exhausted next attempts are separate operations. The formula counts retrieved references, not guard evaluations, new IR row construction, allocation bytes or elapsed time. The compiler already owns all row tuples. Full consumption retrieves n rows; singleton groups retrieve all k=n at the first answer. A single nonempty group retrieves p rows.

The same n, k and p need not determine R. The two declared six-row/three-group layouts have prefix [0,1,2]. With groups [0,1]/[2,3]/[4,5], the second request retrieves 1 and the third discovers that its group is exhausted: R=4. With [0,3]/[1,4]/[2,5], both resumed groups have successors: R=5. This is a structural contrast, not a declaration that both layouts occur in the frozen builtin cohort.

Task037's isolated public targets provide a changed premise: six rows in one active source group and success at row one or four. Their structural merge retrieval count is one or four. The source scan and guards remain identical in the actual semantic checks. This gives a possible reference-handling saving, not evidence that a search workload uses it enough to overcome generator/heap costs. Keep performance/deployment deferred.

The original compiler assigns ranks in pattern/type/source/geometry/path order (`generic_chess/rules/ir.py`), then partitions by source/current type. Ranks are unique within each owner/target key; they need not be contiguous within a source group. A future cost record should retain group-rank layout or actual retrieval counts when k>1, rather than infer cost from aggregate n/k/p. Guard count is generally insufficient to identify p if path or eligibility checks bypass guards. The Task037 selected targets explicitly isolate guard-bearing eligible rows.

The declaration and runner were written during the resource window; execution status belongs to retrieval_law.json and REPORT.md after the window. This derivation supplies no new timing, engine or caller claim.
