# Selected Queen child: actual local all-defense win certificate

The exposed promotion development control's b7b8q child is now a locally
verified White win, beyond an external DTM label. Source-guided construction
uses196 complete position nodes,242 strategy edges,40 DAG reuses. Black nodes
cover every legal action; White nodes choose one legal action. Ranks strictly
decrease from14 to0; rank0 leaves are actual local White checkmate terminals.
Full current-piece/Pawn-origin metadata, rights/EP, actor and representative
history are checked.3276 local transitions,3264 author pushes,2477 outer DTM
calls,6528 combined legal entries take2.328seconds. All table bytes unchanged.

More decisively, a separate **source-free** verifier unfolds EVERY strategy
path, so it does not assume merged DAG paths have the same history. It replays
692 actual local transitions/693 visits with full history, checks10048 legal
entries and167 actual White mate leaves, maximum absolute ply15, in1.000second.
No tablebase import/probe or source-board outcome is used by that verifier.
Every actual history-dependent terminal and complete Black legal set is checked;
missing defenses, nondecreasing edges and false leaf winners are rejected.
Positive transfer thus no longer depends on a generic source/local WDL bridge
or on the constructor's short-history DAG justification alone.

Raw: data/promoted_queen_strategy_20261006.json and
data/promoted_queen_verification_20261006.json. Producer/verification code and
rule/history inputs are pinned. Construction is guided by independent source
DTM, but the accepted proof is the actual local strategy replay. It is adaptive
development evidence for this exact Pawn-origin Queen child only; the other
eleven root choices' eventual local utilities remain unproved. Unit can choose
this same winning child, so no strict tie-independent unit loss or global
formula/strength claim. Queen dominance in this case does not identify detailed
contact prices. No future source queries, heavier search or repeated positive
promotion fixtures are required to confirm this particular certificate.

Budget lesson: useful all-defense certification and verification cost about
3.3seconds, although both legal-list counts exceed the old universal5000.
Its task-specific finite fuses and predeclared question protected resources;
the observed information gain was an actual local win certificate. An arbitrary
5000 stop would have blocked this evidence without a demonstrated cost benefit.
This does not turn every cap extension or every large proof into good value.
