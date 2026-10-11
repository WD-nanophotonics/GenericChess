# Task013: typed support boundary for published Native capability gate

Question: does the other product change in published558b497 preserve the
declared Native capability boundary while removing legacy-handle dependence?
Source baseline b4108a68; only supports_position method from immutable published
blob installed in a private process arm. No product changes or old reruns.

32 frozen direct frontier cells: Chess/Shogi built-ins; max_ply1/default;
ExecutableSemanticRuleset compatibility carrier/pure CompiledSemanticRuleset
with same IR/support and no legacy handle; original/published method;
strict False/True. Create fresh provider/Runtime each cell. Observe exceptions,
accepted counts, Core fallback/operational failures, active status and exact
legal action set versus public Core. At Shogi max1 the declared S4 reply probe
requires normal Core fallback, even for published method; this is expected,
not repair failure. At ordinary pure carrier original legacy read may fail;
record rather than hide that negative. Wrapped carriers are unchanged controls.

No root search, timing, evaluator, generated-domain or terminal precedence proof.
Single batch expected under5sec,120sec outer between-cell guard, own stops
checked each cell. This task tests finite method/context compatibility only;
Tasks007–010 remain independent Runtime evidence, unchanged.
