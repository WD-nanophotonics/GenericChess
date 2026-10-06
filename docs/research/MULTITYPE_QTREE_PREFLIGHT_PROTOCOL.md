# One candidate-neutral multi-type qtree cost preflight

ONE new synthetic initial FEN7k/8/8/8/8/8/n1b2P2/1K6 w - - 0 1:
White Kb1,Pf2; Black Kh8,Na2,Bc2. Geometry exposes two adjacent different
capture types and a real initial Bishop check. Do not filter by candidate
choices, outcomes, retained material or agreement; no replacement root.

Use pinned python-chess movement source, ALL legal root actions, ALL replies,
and ALL evasions after checking replies. Use one counted push per source edge;
determine checking from the already pushed child, never Board.gives_check
(which itself pushes) or parse_uci annotation loops. Any checking third-ply
child cannot be represented by q1/hard2 and fails admission; no hard-depth
increase. Source goals are recorded separately; their automatic draws cannot
overwrite F24F goals. Source128 pushes/5000 legal entries/15sec, no Core query.

Preflight research controller E: qualify/materialize this complete tree once,
then evaluate each frozen model on the public states with the declared q1
stand-pat/forced-evasion recursion. E deliberately uses saved public tables,
not repeated runtime search; it does not claim production integration. No
stand-pat in check. At ordinary reply depth1 cutoff; checking reply gets all
evasions to hard2 and must then be nonchecking or actually terminal.
Admission requires <=128 unique public tree edges and<=1500 five-mode score
terms for all three models,5000 returned/member entries and15sec. Public
offline qualification is charged, not free training labels. Contrast with
repeated cached-noisy runtime D cost upper(public edges+3 noisy/evasion edges),
without running or increasing D's128-event cap.

Freeze geometric_half,linear_mixture,unit before eventual E execution. Full
root ties retained; root selection is structural and does not require model
disagreement. No external requests/labels,closed trial reruns,piece-price fit,
GameState history reset during edges,production edit or human holdout read.
