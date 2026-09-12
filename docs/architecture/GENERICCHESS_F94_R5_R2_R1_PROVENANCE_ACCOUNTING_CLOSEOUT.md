# F94-R5-R2-R1 executor provenance and accounting closeout

The R5 executor now records the actual result sandbox SHA, executor path, and
executor byte SHA-256 separately from the frozen PREP source/protocol SHA.
It validates the second compiled/checkpoint/evaluator construction before
native compilation. A tracking wrapper records actual runner invocations, and
completion fails closed unless the returned evidence totals exactly 18
invocations, 108 pairs, 216 games, 216 traces, and 72 pooled
strongest-vs-weakest games (36 per ready control); the boundary remains zero.

Focused fake-runner tests passed. No real Arena, Heavy task, or RESULT compute
was started; a separately approved exact compute plan remains required.
