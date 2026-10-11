# Task057: independently reproduced actor-relative victim-filter mismatch

Five predeclared actual-provider controls independently reproduce a semantic error remaining after the current any-wildcard normalization. Existing F24C fixture, B0 actor at(1,1), A0 opponent victim at(2,1), anchors at(0,0)/(6,6), no hands. Only capture_B0_A0_leap remove.piece_type_ref changes; guards, action selector, effects/order and target geometry stay fixed.

|Filter|Core legal count|Actual strict Native count|Capture accepted by Core transition|
|---|---:|---:|---|
|any|3|3|yes|
|action_base|2|3|no: remove victim type mismatch|
|action_current|2|3|no: remove victim type mismatch|
|explicit B0|2|2|capture absent|
|explicit A0|3|3|yes|

Both dynamic-filter cases have exactly one Native-only public capture, sem_03_capture_B0_A0_leap; Core-only is empty. The same semantic action/binding returned by the Native provider raises RuntimeError in Core `_transition`. This is an actual frontier/transition discrepancy, without search, evaluator, TT or budget confounds. It does not prove a particular game outcome or measured timing loss.

Source pin d4a588fe50a5f90c0ad5026f28f02905ee86ed65. Core `_resolve_type_id` uses binding.actor_base/current. C runtime apply_effect for move/shift/remove supplies the affected piece base/current to resolve_type, so the dynamic filter can match that piece trivially. Only remove is dynamically exercised here; move/shift and set_current_type are source-level scope questions, not additional executed counterexamples.

The own checkout product remains b4108a68a7ee06327be39cb3a222939644085a52. To exclude its old any-wildcard bug, the exact fixed `_sem_effect` function is AST-loaded into a copy of compiler globals and installed only during this isolated process, then restored in finally. No file/product/default/UI source change or DLL build. Other relevant modules are required to match the fixed pin after CRLF normalization; both raw checkout and fixed Git source hashes are recorded. Two initial assertions compared raw checkout bytes to Git LF and failed BEFORE any frontier call; harness_failure.json preserves them. Matching installed binary SHA2f97cfb8816bc963163207095bf40ac990169284cd0cfb2e7b545f0a6bf07bf1 is actual runtime identity, not proof that tracked C source built the binary.

Reject a general static replacement with pattern actor type: `_make_binding` takes actual source base/current, pattern.type_ids selects current types, a promoted actor may have different base and current, and patterns can select several current types. Conditional constant lowering would require an independent constant-binding proof and original filter comparison semantics; preserving a rule fingerprint alone does not provide it.

Dot reviewed the pinned public source and endorsed provider capability refusal plus existing Core fallback, leaving compile-only corpus and raw APIs distinct. Full reply was saved before exact-payload reconcile/adoption. Dot did not execute these controls or read an unpublished fix. Recovery discovered PRIMARY independently reported the reversed A0/B0 case and already owns the provider repair. This auxiliary evidence is an independent corroboration, not a novel primary defect or second repair. No implementation or old32/24/8 cohort rerun follows. Primary's completion-strategy experiment remains its task.

Validation: probe.py ran the original five declarations in0.070seconds of observed local process work; result.json has complete frontiers, exact inputs/rule fingerprints, same public action, Core errors and positive-control children. validate_result assertions require all five outcomes, executable providers and unchanged roots. Scientific work remains OPEN. Follow-up is to audit the published provider fix at a new fixed revision and distinguish actual fallback from still-unguarded raw Native calls.

Provider closure supplement: captured unpublished primary source SHA f12de8f7fa8581a32600eaae1f217ab16d3008299c96e79df1f8bcefb2564709, with exact AST snapshots of try_create and supports_position. Same five declared fixtures now pass actual SearchPathRuntime frontiers: action_base/current decline provider, return Core2 actions, enabled/calls/fallback/operational failures all0. The other three create a provider and make one actual Native call, retaining Core3/2/3 actions. Public position, ply, terminal, identity, hash, snapshot, history and context restore; this does not assert a separate complete occurrence-multiset audit. Constructor capability refusal is Core execution even when the runtime fallback counter is zero. Requested Native plus zero fallback alone cannot certify actual Native execution.

First closure attempt stopped before output on the own checkout's older supports_position accessing missing compiled.max_ply. The exact same primary draft uses compiled.support.max_ply; this dependency is now captured, installed only in the auxiliary process, and both methods restored in finally. fallback-harness-failure.json preserves the failure. This is draft-function closure, not published primary regression certification, whole-domain coverage, raw Native API repair or a default change.

Published-source follow-up: PRIMARY now published bebe3d98ebb0832207e112ca0755fa9837cef3e7. Both tested try_create and supports_position AST hashes match that fixed source exactly. Full raw file hashes differ between captured Windows draft and Git source; no complete byte-identity claim follows. published_binding.json pins actual published source/AST evidence. The five earlier tests are reused without rerun; primary32/2086 regression counts remain its published evidence, not independently executed here.
