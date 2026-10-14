# Complete Native semantic qsearch

Science is OPEN. This adds requested nonzero q search to the complete semantic
Native engine; it does not change UI/backend selection or downgrade q policy.
The initial implementation is bounded development evidence, not a generic
strength or universal equivalence theorem.

## Capability and observed checks

The previous engine rejected nonzero q depth. The new kernel advertises
SEMANTIC_QSEARCH_VERSION=1 and accepts ordinary/hard q depths and a separate
q-node budget through SearchLimits. Older binaries explicitly require rebuilding
for nonzero q; old q0 calls keep their original argument shape. Main-plus-hard
depth is bounded by the existing semantic stack limit. Legacy Native engine
capabilities remain separate.

Nonchecking q inclusion uses actual enemy removal, board-current plus hand-base
inventory changes, actual terminal outcomes, and checks. It retains off-target
captures, type/ownership effects and checking drops without relying on explicit
promotion metadata. Quiet inventory-conserving nonchecking drops stay excluded
under the existing Core q policy. All actual recursive children use complete
checked transitions with auxiliary state and relevant history. In-check nodes
search all legal evasions and abort at the hard limit, never stand pat.
Terminal adjudication precedes WIN and neutral declarations; available neutral
claims retain their zero floor. Q suffixes are not advertised as returned main PV.

The first full main iteration reserves ordinary q depth0 while mandatory checks
still extend to the configured hard limit. Later iterations use requested q
depth. Returned result_ordinary_qdepth/result_check_hard_qdepth describe the
retained iteration; they are absent/None for no completed iteration. A q-hard,
q-node, total-node, time or cancellation abort preserves its actual reason and
last complete result. Total-node budget includes main plus q visits; result
nodes and qnodes report them separately. These work counts are not unique states.

Persistent TT contexts distinguish requested q policy, hard depth and the
first-iteration reserve. A deliberately unsafe private ablation that removes
this distinction fails both real cold/warm objective-change regression modes,
while the supported candidate passes. The frozen4x4 played fixture actually
distinguishes q0 material200 from a q-extended mate estimate. No static-payload,
position or history cache is introduced.

## Finite validation and ongoing comparisons

Eight initial private q1/hard4 smoke calls and144 fixed calls retain68 supported
D1/D2 paired scores after existing100M/1B terminal-unit normalization.
The bounded q4/hard8 candidate adds144 fixed calls:60 completed supported
pairs match; eight paired cases are censored, not extended. Unsupported18-board
cells remain explicit. Both stages keep full played transform/drop/aux/history
fixtures and checked neutral declarations. Different comparators can choose
different equal-value actions; matching scores alone is not a maxset/strength proof.

The candidate passes2555 active tests in one complete private-image run.
The rebuilt installed image then passes56 focused tests, including12 new
semantic q, real warm-cache policy changes, total/q/hard budgets,
pre-cancellation, actual state restoration and old-capability rejection checks.
One first test fixture did not distinguish q objectives; its failed assumption
is preserved privately, then replaced with the frozen distinguishing fixture.
The shipped q implementation is tested code; caller usefulness comparisons
on four builtin Chess/Shogi roots and16 prospectively generated rules continue
in the same segment and will be reported without changing their budgets.

## Interruption and interpretation

The first q4 producer stopped after29 durable rows at08:29UTC. At recovery
around12:58UTC its process and tool handle were gone, with no retained exit code.
No matching Python crash event was found in the queried window; that does not
establish the cause. A separately bounded pending Native call exits0 and
completesD2; only remaining predeclared cells were resumed, preserving the29 rows
and original declaration. The unknown gap is not counted as effective work.
No Smart App Control diagnosis or process-crash claim is inferred.

The earlier neutral fallback concern was already fixed:12 actual node1/D1/
pre-cancel queries and27 existing tests confirm current behavior. No redundant
patch was made. Saved ordering adverse cases were attributed without rerunning
their speed curve:38 literal Core children certify all12 retained2505 choices
as actual mate-in-one; depth5 versus4 does not lose that root decision.
The6.813 caller outlier retains equal490 search visits and recorded0.204s setup
versus ordinary0.006s; a scheduler cause remains unproved.

Raw Slack/account/receipts, host logs and binaries remain private and ignored.
Research sources/rows and current limitations will be delivered as reviewed
Agent evidence; the original archives and prior validation status stay frozen.
