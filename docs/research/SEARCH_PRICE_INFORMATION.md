# Price information in a fixed finite search tree

This is an independent derivation about a declared material-only controller,
not an outcome calibration theorem. It explains why successful capture-aware
integration can have zero information about relative piece prices.

## A sufficient no-information certificate

Consider a finite, fixed, complete tree with weight-independent legal actions
and cutoff policy. All leaves are ongoing states scored from the same root
perspective by w dot f. Interior operations are min or max, including an
explicit stand-pat leaf when the controller permits that approximation.
Suppose every leaf vector has form c+t*d, with the SAME c,d throughout the
tree. For all parameter vectors under consideration, w dot d has the same
strict sign. Then every node is w dot c+(w dot d)*s, where s is computed by
the same scalar min/max tree (operations reverse if the sign is negative).
Thus all full maximizing root tie sets and the fixed canonical tie choice
are independent of w throughout that sign region.

Proof is induction: min/max commute with adding a common number and multiplying
by a positive number; a negative multiplier swaps the operation. At a leaf,
s=t. At root comparisons the common offset cancels. This applies to both
saved q1-root controls: c=0,d=P and t is0 or-1, with w_P>0. A deeper fixed
controller can still be coefficient-blind if its complete features stay on
the same positive ray. w_P=0 collapses all values to a tie; it does not select
a strategically correct quiet action.

Do not apply this to fixed terminal mate constants mixed with material leaves,
history-dependent declarations, unfinished searches or price-dependent branch
admission/budgets. Exact alpha-beta on a complete fixed tree preserves the
mathematical result; budget-truncated execution need not. Integer quantization
also means arbitrary scaling of real input coefficients need not scale their
rounded evaluator weights. Here the admitted integer coefficients are fixed
and strictly positive, so the saved controls meet the premise directly.

## Rank is a diagnostic, not a usefulness label

Affine feature rank>=2 is necessary to escape the above positive-ray case when
all admissible directions have the same projection sign. It is not generally
necessary for sensitivity: on d=N-B, a rank1 tree can switch when w_N-w_B
changes sign. Nor is rank>=2 sufficient: an action with f=(1,1) can dominate
other leaves(1,0),(0,1) throughout strictly positive weights; the tree has
rank2 yet the same action always wins. The relevant evidence is an actual
decision boundary within the declared parameter region, not rank alone.

For a fixed finite linear-leaf min/max tree, each node value equals some leaf
linear form. Partition parameter space by all pairwise leaf-equality
hyperplanes w dot(f_i-f_j)=0. In each open cell, leaf order is fixed, hence all
min/max choices and full root ties are fixed. Boundaries require explicit tie
analysis. This supplies a finite decision-sensitivity problem without claiming
a probability law over prices or an independently correct cell.

## Prospective sampling decision

Use candidate-neutral multi-type exchange geometry and a predeclared root
sequence for a future small outcome experiment. Record every rejected proposal
and the cost/support gate before labels. Do NOT sample until contact wins,
discard ties after observing outcomes or silently replace failures.
An experiment deliberately conditioned on model disagreement is a different
population: useful for adversarial mechanism diagnosis if disclosed, but not
an unbiased natural-game performance estimate. Dot's existing advice instead
uses candidate-neutral structural exchange risk; adopt that default.

A price-independent outcome source is still necessary after finding sensitivity.
Exact agreement with the same material leaves only tests implementation. A new
reference must expose information beyond those leaves and keep its goal,
history and rule contract explicit. Current external GET failed before labels;
do not turn rank or qsearch improvement into an outcome surrogate.
