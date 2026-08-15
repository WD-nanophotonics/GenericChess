# F22 Evidence — Post-F21 Production Re-Baseline + Bounded Strength Audit

Status: `F22_RESULT = AUDIT_PASS`.

The audit ran only on `sandbox` at the locked F21 baseline `f8cf111ccc985a58cfaac1c763080a8b06d4d4a1`. `master` and `chat` remained unchanged. The complete Gmail task is persisted at `inbox/2026-08-15_GenericChess-F22_Post-F21_Production_Re-Baseline_Bounded_AlphaSho_Strength_Evaluator_Re-Entry_Audit.md`.

## Runtime re-baseline

H22A used the default-on Native legality route on the four frozen F20/F21 semantic prefixes, with five formal runs per case. Profile A median elapsed time was 0.905487 s; Profile B was 2.196248 s. Native fallbacks and operational failures were zero. The focused F21 health gate passed.

AuditRecorder and cProfile evidence are separated into inclusive and exclusive/runtime reports. The post-F21 ranking does not identify a unique new hotspot meeting the 15%/8% two-profile gate; `POST_F21_RUNTIME_SINGLE_WINNER = false`.

## Bounded AlphaSho re-entry

The preserved Round5 corpus contains ten fixed Standard Shogi positions and ten read-only AlphaSho reference moves. Historical evidence remains unchanged: 2 agreements, 8 disagreements, zero legal/budget failures, paired score 0.0, and the old long rollout sealed as `ABORTED_FOR_RUNTIME`.

Generic LOW/HIGH agreement was 2/10 at both 0.5 s and 1.0 s. The node ladder used 128, 256, 512, 1024, and 2048 where safe; unsafe per-position paths were stopped at the five-second cap and recorded. Maximum safe observed budget was 2048; max-node agreement remained 2/10. All eight initial disagreements remained persistent; none were resolved by depth. One-ply evaluator ranking put all eight persistent AlphaSho moves outside the current evaluator top-3.

Fixed-node Native ON/OFF parity was re-run without a wall-clock cap at 128 and 256 nodes: 20/20 exact rows, including logical stats. Wall-time capacity evidence is separate and does not claim fixed-time correctness from move differences.

## Evaluator audit and decision

The current evaluator remains generic-v1: rule-derived capability profile, board/hand material, promotion potential, mobility, anchor escape, and check penalty. `_legacy_compiled` is used only as evaluation/inspection metadata, not semantic execution. The profile and component decomposition are descriptive; no values or `EvaluationConfig` were changed. Component sums matched `Evaluator.evaluate` for all 280 audited child rows.

The selected next boundary is `RULE_DERIVED_EVALUATOR_V2`. It was selected because persistent disagreements were material and the current generic feature vocabulary is semantically shallower; no Shogi-specific hand-authored table was introduced. F22 implements no next-phase boundary.

## Regression/build/integrity

Focused F21/F13/F14/native semantic regressions passed. Full `python -m pytest -q -p no:cacheprovider` passed. Final Native O2 build passed at 338,432 bytes with SHA-256 recorded in `artifacts/f22_post_f21_rebaseline_strength/final_native_build.txt`. Before/after SHA-256 manifests for F4–F21 evidence and ADR-022–038 are identical. No production behavior changed and F23 was not started.

All machine-readable evidence is under `artifacts/f22_post_f21_rebaseline_strength/`; `manifest.json` is the final file manifest.
