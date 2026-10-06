# Fresh complete-root admission; external outcome transport failed

The prospectively frozen synthetic root admits all5 actions and22 replies.
Author trees are generated first and reused; unlike the first q1-root control,
reply annotations reuse enumerated Move objects instead of parse_uci scans.
27 source pushes,76 fully charged source entries,27 public transitions and
66 runtime push/pop pairs total93 state events,426 local entries,21 qnodes,
one compile and0.109sec. Full synthetic histories, actor, board, effective
rights and forced EP state agree. Every saved node is ongoing/nonchecking.
No natural-game sampling or original puzzle deepening occurred.

All frozen formulae select [a1a2,a1b1,a1b2]. Static full ties include all5;
c2c3 and c2c4 each receive minus their own positive Pawn coefficient, ordinary
capture and en-passant respectively. This demonstrates complete shallow
capture-risk integration. With only P features, every positive coefficient
gives these same ties; it is intrinsically uninformative about relative prices.

After local policies were persisted and hashed, exactly one unauthenticated
GET was attempted to the documented public tablebase endpoint for this FEN.
It failed with local WinError10013 (socket access permissions). No response,
label, successful external root reference or source WDL comparison exists.
No automatic retry, escalation rerun, alternative endpoint or replacement root
was attempted. The one-shot acquisition is closed; its complete=false record
and original source pins remain evidence. This is an observed transport limit,
not a theoretical reason to stop independent research.

Pre-acquisition primary-source orientation audit:
[tablebases.rs](https://github.com/lichess-org/lila-tablebase/blob/main/src/tablebases.rs)
probes every legal child after applying its move, and negates the best child's
category for the parent. [response.rs](https://github.com/lichess-org/lila-tablebase/blob/main/src/response.rs)
uses child clocks with DTZ to form categories and explicitly swaps win/loss
under negation. This supports the planned orientation, not any actual label
for this root. DTZ is not a local mate distance. Service50-rule outcomes would
remain a distinct independent contract from F24F's max-ply/repetition goal.

Next selection must distinguish price sensitivity from capture-awareness:
inspect joint feature contrasts under the declared complete controller before
acquiring outcome labels. At least one multi-type contrast is needed to
distinguish price formulae; future selection must record its conditional
population and avoid tuning against already exposed labels.

Evidence: CHESS_Q1_REFERENCE_PREFLIGHT.md,
data/chess_q1_reference_local_20261006.json,
data/chess_q1_reference_external_20261006.json. No response file was created.
