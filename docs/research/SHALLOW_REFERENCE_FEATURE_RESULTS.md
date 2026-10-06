# Price-ratio tuning cannot repair this shallow quiet-move miss

Complete saved32-action table has exactly two immediate feature classes:
30 quiet choices preserve root signed inventory(-1 Pawn,other modes0),
two captures add one Pawn. Advertised c2-c3 belongs to the quiet class.
160 mode/action terms,0 new events/labels/source queries; all paths retained.

Therefore EVERY depth1 linear material-only operator with positive Pawn
weight ranks both captures strictly above ALL quiet choices. Altering
N/B/R/Q ratios cannot select the advertised quiet answer, because those
components do not change. Actual fixed quantized Pawn weights17417/24329/
100000 are strictly positive, so the result applies without rounding caveat.
Setting Pawn0 would tie classes without supplying a reason to prefer c2-c3;
negative Pawn pricing would abandon the declared positive material model.

This separates a feature/horizon limitation from coefficient-quality evidence.
The single external reference disagreement cannot establish worse pricing
than unit, and it should NOT be used to fit a positional bonus or a duration
law. The advertised engine answer remains a reference, not independently
proved unique/WDL. No solution rollout, deeper retry, replacement sample or
claim of natural performance. Future work needs a frozen richer controller
on another prospective source rather than trying to repair this label.
