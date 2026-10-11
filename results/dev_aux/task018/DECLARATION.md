# Task018: independent prelocated-index migration acceptance

Changed premise: primary working candidate locates old entry index before any
target mutation and later deletes by that exact index, replacing fallible
post-journal list.remove comparison. Earlier Task015/016 data stays frozen.
Read working source once; hash/freeze method; confirm only resolve AST changes
relative to immutable558b497. Private method/published push in own process.

Eight candidate-only cells: natural opaque3ply or nested opaque2ply+outer move,
ordinary/forcedHash0, no comparator fault/single comparator allocation fault.
Public repetition mapping remains identical; target key is ordered last to
expose comparisons when collision bucket has prior entries. Gate on actual
resolve caller and exact old imported key; one original MemoryError object.
No comparison is expected for singleton noncollision bucket, so retain
unreached injected arm as a successful control, not a false passing fault test.

Complete state/multiset/bucket/alias/frozen-parent-frame/cache/history restoration,
snapshot versus actual items/digest, exact escaping object/context/cause for
reached fault. Turn off injection, same Runtime retry/pop must match public
and restore. Preserve comparison counts and original no-fault parity.
No production editing, earlier batch rerun, full primary regression execution,
timing, global OOM guarantee or TT/UI incident. Expected under2sec;120sec fuse.
