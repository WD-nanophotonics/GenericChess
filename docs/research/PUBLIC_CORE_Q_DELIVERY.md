# Public Core q delivery and the cheaper existing ordering route

Science is OPEN. This segment adds68 primary physical search rows:60 Core
calls and8 recovered Stockfish probes. Separately,484 saved AUX games were
replayed; no new AUX games or training were launched by PRIMARY. Source/results
and failures are bound by data/public_core_q_20261012.json. Base source is
b66eaad86396e6e70e0d97c759ceb7b6753ee933. Engine/default/UI code is unchanged;
only the observed operational finish loophole is repaired.

## Actual public consumer

Eight reversed D2 controls on the existing active auxiliary root1091 use
unmodified public Core q versus the earlier full logical legality/quiet probe.
Choose-action timings exclude rule/profile/player construction and are not UI
end-to-end latency. Both AB and PVS preserve exact action/PV/value/root. AB has
164main/45485q; PVS247main/25265q; value-2416. Public AB costs20.237/20.678s,
PVS11.705/11.727; combined probe AB15.670/15.588, PVS8.984/8.888.

Sixteen raw public1/16/64/256s calls keep Native semantic leaves, legality and
availability, fresh TT, lexical q, maxD12/1Mnodes/q4/hard8. All time_limit:
1s bothD1/q0/value9;16s AB retainsD1/q0 while PVS reachesD2/q4/-2416;
64s bothD2/q4;256s bothD3/q4/-230. This is supported completion, not strength.

Eight missing single-factor D2 cells isolate logical legality versus quiet
mechanical exclusion: legal-only AB19.057/19.150, PVS11.075/11.050s;
quiet-only AB17.040/17.053, PVS9.500/9.480. Decisions and work remain exact.
Four quiet-only controls using existing Core availability fallback cost
24.234/24.136 AB and13.461/13.380 PVS, with the same decision/work. Native
availability implementation matters; this is not a fallback-free deployment
claim. Cross-batch time ratios are descriptive; reversed within-batch controls
and ordinary concurrent load are retained, with no machine-exclusivity claim.

Four same-batch64s raw/quiet-only PVS controls all retainD2/q4/-2416. The next
four quiet-only/combined PVS controls give quiet-onlyD2 versus combinedD3/-230
in both orders. The SAME king move remains selected. A historical combinedD3
alone would not prove a current interface need; the paired result is stronger
completion evidence but still does not justify a private product API by itself.

## Existing q ordering avoids that interface decision

The old1006/1008 ordering controls paid an eager full logical collection tax.
Here the public consumer already owns a complete tuple, a changed cost premise.
Only the existing use_ordered_qsearch flag changes; quiet guards, PVS, Native
backends, evaluation, q inclusion and caps stay. Four D2 controls keep exact
value/action/PV and247main: q25265 becomes12263; costs9.453/9.474 become
4.799/4.814s. Four paired64s calls retain lexicalD2/q4/-2416 versus ordered
D3/q4/-230 in BOTH orders, without the private legal collection.
One ordered call stops at63.281s with qsearch_check_hard_limit during its next
unfinished iteration; the other stops at time_limit. The retainedD3 is complete,
not a claimedD4 result. Preserve hard8; do not enlarge it to rescue the trace.

Choice: retain the public tuple contract and compare existing ordering first.
Defer private iterable API and new C q4 kernel. This research quiet hook is not
silently promoted into production; neither defaults nor frozen UI policies change.
No new ordering algorithm or human-price fitting is introduced. One exposed
root does not establish whole generated-domain deployment equivalence.

## Defined decision usefulness

Eight TT-off full-window forced-root-action calls use the SAME actual parent
D2/D3 q4 context and original public Core. Earlier root iterations run normally;
at the declared final depth only one legal action is pushed, with original
negamax at ply1/depth-1. This avoids the incorrect child-root q0 phase reset.
Restricted caller completed_depth is NOT a whole-root optimization certificate.
Both orders give the D1 pawn choice-2618/-327 versus the D2 king choice
-2416/-230 at parentD2/D3, matching the existing best-root values. Conditional
regret is202/97 under these fixed search/evaluation criteria. Thus the16s
PVS D1-to-D2 move change has defined utility; the laterD2-to-D3 support adds
value refinement but does not change this selected move. No WDL/Elo claim.

## Recovered mature entry and auxiliary evidence

The original Stockfish binary55aa40c857de30b79dbe4f8e4c335ee2b23815cf2f100a6630d54761fcad3b85
executes8 existing250ms Chess probes after SAC recovery. All bestmoves and
reported principal lines replay legally; the owned process closes. Middle
reportsdepth18/seldepth24. Immediate-mate nominaldepth245 has seldepth2:
reported selective engine depth is not generic q4 depth/work equivalence.
EP's last score is an upper bound, not an exact common value. Default NNUE,
selective pruning and draw/evaluation policies make this an overall reference,
not a material-only search control. The unchanged unsupported Shogi entry is
not retried; its infrastructure remains a separate concrete next question.

PRIMARY independently replays AUX's actual four-game pilot and Task121480
records/3666 searches: legality, full history, seeded random opponents, applied
leaf weights, final positions, rewards and selection arithmetic pass; five
declared source hashes match. Three heldout means change-12.449/+24.915/+.025,
medians0/-.0333/0; one lost/two gained mates dominate the first two. Endpoints
remain dispersed. Actual ordering is per-seed freeze then its heldout, followed
by the next seed; no cross-seed feedback appears in source. Do not claim all
three endpoints frozen before any heldout, stable human ratios or independent
live-engine reproduction. The metadata correction was shared with DEV_AUX;
its separate training stays under its ownership.

## Operational correction and validation

The prior finish helper accepted arbitrary nonempty text for user_decision and
runtime_limit. It now requires a current-session diagnosed JSON report, a
specific already-sent user action for user_decision, or actual current runtime
exhaustion. Runtime evidence older than resume is rejected. All six stop flags
across rollout/advisor/slack are respected. Real stop/tool/quota paths remain;
these checks establish structure, not report truth.28 session regressions pass;
118 earlier relevant regressions pass, then the four stop-flag additions pass.
Final publisher results are reported after the tested entry executes.

Failures are preserved: Windows command-line206 corrected by bounded private
raw-write chunks; pytest default-temp WinError5 corrected with a fresh project
temp; Git/MSYS kernel-object denial in sandbox diagnosed then tests pass in the
authorized execution environment. No system security/ACL changes. The first AUX
replay backend-label assertion was corrected against the exact same binary hash;
no engine result was altered. Raw Slack/account/user data, host logs and binaries
are excluded from publication. All source/cap/exposed-data limits remain.
