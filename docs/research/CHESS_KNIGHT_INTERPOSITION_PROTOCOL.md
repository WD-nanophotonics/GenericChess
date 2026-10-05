# Changed premise: single Queen check, Knight capture alternative

The prior B d7 construction was invalid: Bishop d7 ALSO checks King c8, so a
Pawn interposition cannot evade its double check. The analytical-import harness
rejects unsafe promotion children before any reply/event/query, preserving that
zero-event report. Do not relabel either prior root as a successful use sample.

NEW explicit hypothesis: a Knight on d7 is not an additional checker, allowing
all interpositions. Own K c8/P e7; enemy K a1/Q h8/N d7/N a5/N d5. This is a
different single-check premise, not a replacement inside either frozen experiment.
Full root expected Kxd7 and P e8=Q/R/B/N. Freeze exact full action/child table
and original two-law contact/unit/zero choices before new reply labels. No
coefficient or tie changes. Candidate expected e8=Q; unit/zero Kxd7.

After e8=Q, Qxe8 is expected to mate: Queen both checks King c8 and guards
Knight d7; Knights a5/d5 guard b7/c7, and Queen guards b8/d8. After Kxd7,
enumerate all replies and classify whether any is actual checkmate. This is
an independent full-history one-reply safety criterion, not eventual-WDL gain
or a withheld human-value test. Nonmate does not mean nonloss.

128 actual transitions/5000 enumerated actions/128 choices per node/15sec
cooperative cumulative limit. Charge prior original unknown0..5 events and1sec
plus imported-child0 events/0.046sec. Persist initial evidence and ALL action
lists before processing; serialize terminal enums correctly. No old reruns.
Do not replace this root if failed. No further depth or source downloads.
