# Finite allocation arithmetic and its boundaries

2026-10-05. resource_coalition_intervals.py allocates supplied binary-task
coalition value intervals; it does not compute legal-game values or prices.
Six tests independently enumerate every resource order for all256 three-resource
binary utility tables, plus missing-value, identity and nonmonotonicity controls.
No actual Chess/Shogi game transition or fresh external goal label is observed.

The exposed R/P pin unanimity table assigns P=R=1/2. This is a mathematically
specified allocation of joint task1, not an intrinsic equality of Pawn/Rook.
Adding an interchangeable second Pawn in an INDEPENDENT toy coalition game
with value1 iff R and at least one Pawn are present gives P1=P2=1/6,R=2/3.
This is not a sampled n=2 Shogi pin result. Averaging uniform resource orders
therefore changes allocations when physical multiplicities change, even while
total pooled task stays1. Static mode prototypes require a separate context law.

Unknown coalition values remain[0,1]. With known empty0/joint1 and two unknown
singletons, each resource allocation is[0,1], but their EXACT shared-variable
sum is1. Summing component interval boxes instead gives[0,2], losing dependence.
No caller may interpret component boxes as independently realizable joint
allocations. The implementation collects each signed coalition coefficient
before evaluating a rectangular uncertainty set; additional legal-game
constraints can tighten bounds but are not guessed by this arithmetic.

Signed allocations are intentional. A toy task F(a)=1,F(b)=F(ab)=F(empty)=0
allocates a=1/2,b=-1/2; adding a physical resource has not been proven to
preserve original action/payoff subtrees in Chess/Shogi. Do not clip negative
allocations or add an epsilon to pass a positive-material gate. Optional-action
monotonicity is a different assumption, as previous real R/Q evidence shows.

The seven-resource input limit bounds this arithmetic to128 supplied coalition
variables. It is a local qualification limit, NOT a proof that128 transitions
compute their legal task values. At the initial own ordinary inventory, Chess
n=15 needs32768 coalition roots and Shogi n=19 needs524288, before game trees.
Full-stock Shogi ownership changes can raise own n further. Anonymous type
grouping does not automatically remove physical multiplicity or context effects.
The sparse two-resource restriction is cheap structurally but omits real support
and represents a different approximate model, which must be declared.

Primary attribution precedent and limits are documented in
RESOURCE_MARGINAL_CONSTRUCTION_HYPOTHESIS.md. Neither allocation efficiency nor
additivity across utility games establishes exact inventory additivity or a
useful static material prior. The future common law/candidate remains unfilled;
no independent generator or Xiangqi holdout has been opened.
