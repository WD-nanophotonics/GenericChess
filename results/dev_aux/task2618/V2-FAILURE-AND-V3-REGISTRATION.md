# task2618 v2 failure and v3 recovery

Science remains **OPEN**. The v2 launch failed before training completed, so it
supports no learner-strength conclusion and did not open evaluation.

## v2 failure

The one-shot registered run used plan SHA256
`2e2701ace560e65cd13376f1fa48d208efe8efea687249a8088758f2854b131f`. It exited
with code 1 after 132.545 seconds. The concrete exception was
`KeyError: 'active'` in `train_learners.py` while serializing a TDLeaf query.
TreeStrap statistics include `active`; TDLeaf statistics do not. The runner
unconditionally indexed that TreeStrap-only field even when `tree=None`.

Before the exception, the TreeStrap seed-0 arm completed its 1,000,000 paid-node
budget: 52 games started, 50 actual terminals, 2 UNKNOWN, and 68 of 120 roots
unstarted. Its arm-progress record was fsynced. The subsequent TDLeaf arm failed
while recording its first query. There is no complete training-result receipt,
no eligible model panel and no evaluation. The run is preserved unchanged and
will not be retried or topped up.

The fix serializes `stats.get("active", 0)` for the TreeStrap-only telemetry
field and adds a TDLeaf regression test covering the actual stats shape. The
complete task2618 test suite passes after the fix.

Exact v2 stderr and JSONL/receipt originals are preserved in Git-ignored
`.local_agent/task2618-v2-failure/`. Key private SHA256s: stderr
`fa8746d9d7e6353521f813cb7ecddfd68ffb546792d83c5d0490c6d225f9aa79`, games
`87860ee1e14894e7261bc93fa50e05bf0bf537d0d64029a142351b78ace9f41b`, queries
`294dcd11afd66b6d78cffa579fc9ba578d044f91d0e22c0f38c99e72108824d0`, and
arm-progress `4a953a6ba9467be64705c65b11b61323c03332f16327480e5a0290e919c69e99`.
The raw stderr's local Windows path stays private.

## v3 attempt (aborted; selection flaw)

Because a plan cannot reuse trainer source that changed after failure, v3 is a
new write-once registration. Its outcome-blind selector excludes all 120
families from the v2 registered panel (not just the 52 that started), leaving
360 eligible roots; it selected 120 under a fixed namespace, with zero exact
overlap against the frozen 32 evaluation roots. The same training panel is
paired across all four seeds/methods. No outcomes were read for selection.

Root-selection SHA256:
`ea1ce1059d30943de166977fec921b26c615ed7d960da65dee3e56ee872e5b61`.
Registered plan SHA256:
`43c7c690a15f4e820fa7776a3e2632c304f8198610742796805466f13dd002ca`.
No-search preflight passed: 12 arms, 480 seed-root manifest rows, 32 evaluation
roots and 1,024 evaluation slots. All registered source hashes matched and the
one-shot output set was absent before launch.

An independent post-registration audit found that this selector excluded the
v2 panel but omitted v1's 51 started training families. The selected v3 panel
therefore intersected 18 v1-exposed families. This invalidated its intended
fresh-root condition. The issue was caught before completion, and the training
process was stopped after exact PID/command-line verification; v3 will not be
continued or topped up. Its complete TreeStrap seed-0 arm reached 1,000,000
nodes (40 roots started, 33 actual terminals, 7 UNKNOWN, 80 unstarted). No
training-result or evaluation receipt exists. The remaining files are partial
evidence only, not a strength result.

The interrupted v3 plan SHA remains
`43c7c690a15f4e820fa7776a3e2632c304f8198610742796805466f13dd002ca`; selector
SHA remains
`ea1ce1059d30943de166977fec921b26c615ed7d960da65dee3e56ee872e5b61`. The exact
v1/v3 family intersection was
`[810033,810034,810035,810036,810037,810042,810043,810049,810051,810057,810058,810060,810064,810073,810078,810081,810082,810083]`.
The stopped process receipt records 187.518 seconds and return code
4294967295. Exact v3 artifacts are preserved privately in
`.local_agent/task2618-v3-aborted/`; the 60,613,095-byte query log SHA256 is
`649e4d388b7ec649f5049505bc699fa8ba0a6d1e38e85b4133661ec149c29e87`, games log
SHA256 is `8ea5627c988c07bfba9586c7767f754cc427f1a359ce16e49117ed9239e1772d`,
and exit receipt SHA256 is
`4c24ab00448c4ca9f8c23a63daa081ceb2fac993a35b8e59b1b67ed82820ce7f`.

The next registration must exclude the union of all 51 v1-started families,
the 120 v2-registered families and the 120 v3-registered families. Those panels
overlap in 18 v1-exposed roots; the union leaves 207 eligible roots, enough for
a new deterministic 120-root panel. No further training/evaluation has started.
The cost-only projection remains below two hours, but recompute and source-bind
the estimate for the corrected selector before any new run. Preserve all prior
registrations and failed partials. Science remains OPEN.

## v4 outcome-blind preparation

A separate selector now excludes the union of v1-started exposure and every
registered v2/v3 family. It reads only `(family, unstarted)` from v1 game rows;
the selector ignores all labels, weights, TD traces and terminal outcomes. It
also pins the two registered plan hashes and exact training/evaluation root
sources. Audit results: 51 v1 exposed, 120 each in v2/v3 registrations, pairwise
overlaps `(v1,v2)=0`, `(v1,v3)=18`, `(v2,v3)=0`, union 273, and 207 eligible roots
from the audited 480-root pool. The fixed v4 namespace selected 120; exact
record overlap with the frozen evaluation panel is zero.

The first v4 root-selection artifact (`a2399218...`) used the local v1 game log
directly and is superseded by an outcome-free projection so collaborators can
audit the exposure input without receiving labels or weights. The published
projection is `results/dev_aux/task2618/learner-comparison-v4-prep/v1-exposure-projection.json`,
SHA256 `b3b4fab40269c4b020d8447b64db2295bf98dca3cf4204cd4277fef6c7e63ab0`;
it carries only 120 `(family, unstarted)` rows and the private source's digest.
The verified preparation artifact is
`results/dev_aux/task2618/learner-comparison-v4-prep-verified/root-selection.json`,
SHA256 `38b8daea46817c12230b488da91ad0e1239d26f2d8673a033a67b5417ef57216`.
Selector: `reselect_training_roots_v4.py`; focused exposure/selector tests: 6
passed, including mutation invariance and overlap/count rejection. No
registration, search or training occurred. The existing source-bound
cost-only calculator passes unchanged at 95.768 minutes with a 110-minute
all-in cap and 25% margin plus 15-minute setup reserve; this is a planning
estimate, not a guarantee. Rebind this estimate to the eventual v4 registration
sources before launch. Exact v1/v3 stopped evidence remains in ignored
`.local_agent`; science remains OPEN.

## v4 write-once registration

After the sanitized projection and fresh-root panel passed, revision 4 was
registered without search. The no-search preflight passed with 12 arms, 480
seed/root rows, 32 fixed evaluation roots and 1,024 evaluation slots. Plan
SHA256 `5ddc6b6bcbaec3cea17254dbf0b563bf3ea481b2a292f8fa6092ab31c38aeeda`;
the root panel remains SHA256
`38b8daea46817c12230b488da91ad0e1239d26f2d8673a033a67b5417ef57216`.
All selected roots exclude the 273-family prior-exposure union and evaluation
overlap is zero. The plan binds the current selector/projection and all runner,
cost, and evaluation source hashes. No training, evaluation or terminal outcome
was generated by registration. The existing source-bound 95.768-minute estimate
and 110-minute all-in cap remain unchanged; verify the plan's pinned feasibility
and current source hashes immediately before a one-shot launch. No prior Chat
assessment is required for the registered <120-minute run. Preserve all v1-v3
partial/failure records; science remains OPEN.
