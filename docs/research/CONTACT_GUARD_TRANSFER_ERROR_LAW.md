# Guard-only transfer needs whole-path evidence

The random-hand prototype omits dynamic safety and Pawn-drop postconditions.
A useful next validation target is their EFFECT on a named task, not an
unmotivated success coefficient or claim that no royals makes them satisfied.
No new game observation is made here.

Scope clarification after dot's full reply: the monotonic comparison below
holds for OPTIMIZED strategies or a FIXED random deployment law with rejected
attempts counted as zero. Uniform resampling over the filtered legal drop set
changes the action distribution and has no monotone mean direction. It is not
covered by Vguard<=Vvirtual for the original random-hand prototype.

Suppose two tasks use exactly the same world law, physical pieces, information,
source-only actions, target reward and deadline. The second ONLY restricts
actions by additional guards. Then its optimum Vguard<=Vvirtual. For a fixed
canonical virtual witness route p(w) with length t(w), let C(w) certify ALL
its guards at EVERY step. Executing certified routes gives

    E[C(w) m(t(w))] <= Vguard <= Vvirtual.

This is a strategy lower, not a statement that every successful shortest route
must be certified. If Lroute=E[m(t(w))] for the selected successful witnesses,
its lost contribution is exactly E[(1-C(w))m(t(w))]. With failed witness mass
eta and all hand completions at total time>=2, the loss is <=eta*m(2), provided
guards/worlds do not change the shared deadline law. At fixed gamma it is
<=eta*gamma^2; under the mixture use m2=1/6, not squared mean gamma1/9.
The bound can be loose/zero and requires measured or proved eta, not a guessed
rate. A finer bound retains actual route lengths and failed context weights.

FIRST-drop acceptance alone is insufficient. Two equally weighted virtual
worlds have route lengths2 and4; all drops pass, but a later guard rejects the
only length4 path in world2. First-drop rejection mass is0 while the true
loss is m4/2>0. Thus an audit of drop masks/nifu cannot be called an error
bound for royal safety along quiet promotion and later capture. It must bind
actual complete route states and any alternative retained legal strategy.

The restriction premise is essential: adding Kings changes occupied squares
and may change the world law; adding active opponent replies or enabling
support-piece moves changes task/actions, not just guards. In particular,
the source-only virtual score is not automatically an upper bound on full
official game utility. A lift to explicit royal worlds must specify its law,
all invalid-state mass, unchanged information and allowed resources BEFORE
observations. There is no proved small eta for that lift at present.

Decision: next smallest semantic check should qualify ONE predeclared complete
route and guarded-world lifting premise before attempting a guard-frequency
batch. Independent use still needs actual source-covered selected children;
these two qualifications answer different questions. Neither expands budgets
or permits human-reference tuning.

## Conditional resampling is a separate two-sided error

At one world let legal L be a nonempty subset of masked A, with removed
fraction delta. Uniform(A) and uniform(L) have total variation delta. For
unchanged continuation reward in[0,m2], their mean difference has absolute
value<=delta*m2, in EITHER direction. Two equal masked actions with rewards
m2 and0 attain both signs when retaining only one action. Empty L needs an
explicit failure convention, not removal of the world. Later-path guard loss
is an additional effect and still needs full-route evidence. This refinement
is adopted from dot's algebra and independently checked locally.
