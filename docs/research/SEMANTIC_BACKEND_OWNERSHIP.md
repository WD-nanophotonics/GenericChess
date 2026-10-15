# Semantic backend ownership

Science OPEN. Existing semantic rules and engine capsules previously followed
the mutable default Native module on later calls. Four real-C regressions fail
before this change at state packing, q capability checks, one-shot search and
cancellation. Rules now retain the module captured once at compilation; semantic
state/action wrappers, the mirror, legality payload builder and persistent engine
use that owner. Capability tests and cancellation create/request use the same
owner. New engines and evaluator rebinding from existing rules also retain it.
Stateless codec/history/runtime-size helpers keep the old default API and accept
an optional native_rules binding. Legacy Native paths are outside this change.

Product V1 payload/codec, size<=16 admission, Core fallback, defaults and UI remain.
This is ownership plumbing, not an automatically installed wide backend. The
constructor's explicit backend_module supports an already-created capsule owner;
it does not renegotiate payload layouts or certify an arbitrary external module.
Raw capsule/version validation is still enforced by the underlying kernel.

A private actual V1/V2 experiment never changes native._MODULE:35roots/54contexts,
5354 complete legal-action checks,280 checked children,166 search/cancel/reuse
calls;57 same retained-policy score pairs agree.114 mixed version capsule/engine
calls reject,16 genuine V1 wide-capacity refusals remain. V2 uses a private
public-dictionary sentinel adapter and distinct raw layout/capsule names; it is
not injected into the V1-only legality provider. Full hands/auxiliary/current/base
and SHA256 history/event checks remain. Two driver preparation errors are kept;
36 completed queries were resumed without rerun. The9 ownership regressions pass.
Actual full2580 tests pass, plus4 later new tests separately pass; exact final
2584-node coverage is verified, not mislabeled as one2584-case full invocation.

Four new32 preparation seeds have one success (two played roots) and three45s
censors.32 same-budget calls yield8deeper q0 pairs and8equal q4 pairs, but NONE of
the16 requestedq4 calls retains actualq4: faster execution is not stronger play.
A counter-only148-call control has74 identical non-time results: q inventory/
enemy scans take1.57% and checked transitions61.9% of measured kernel time.
Do not optimize the small scan merely because its loops look redundant.

The completed follow-on is OWNED_BACKENDS_AND_MAIN_FRONTIER.md. It rejects the
serializer on measured kernel cost, repairs a real32-board rule-price recursion
failure, and selects a cheap main hint only for exact-root canonical-replay mode.
Complete evidence and cooperation limits accompany that report.
