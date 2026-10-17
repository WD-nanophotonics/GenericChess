# Incremental material learning — research entry

The main candidate is TD-Leaf with episode-frozen weights and backward eligibility
(`episode.py`), using the same alpha-beta engine as the online smoke comparison.
Standard Chess is the first chosen environment, not a restriction on the final
GenericChess domain. `SessionEnv` already runs the same search/model over real
GameSession choices, history, board-current and hand-base features; its qsearch
is deliberately unsupported. No product/default/UI integration occurs.

The learner has five Chess material features P/N/B/R/Q, fixes P=1 and initializes
other weights randomly without a supplied ordering. Scores use a fixed white
perspective. Search uses only these coefficients, legal actions, actual terminal
outcomes, and coefficient-independent seeded action permutations. There is no
SEE, material ordering, nullmove, futility, evaluation engine or WIN Prover.
The prediction transform is tanh(material/10); this is a chosen learning scale,
not a calibrated probability. Actual terminal targets are +1/0/-1.

`learning.py` also retains an online TD approximation, optional temporal
coherence, and a one-sided TreeStrap variant. These are distinct update rules.
TreeStrap averages the frozen per-search gradient batch and uses transformed
bounds; it is NOT a literal reproduction of the original linear/summed algorithm.
The first smoke used D2/q0. The optional bounded capture/evasion qsearch does
not use SEE; exhausting its cap in check rejects that whole query/training batch.
Unknown game endings never receive a draw or material-count terminal label.

Run from the DEV_AUX clone with its existing Python environment:

```text
python -m pytest -q results/dev_aux/task2492/test_learning.py results/dev_aux/task2492/test_episode.py --import-mode=importlib
```

Experiments are frozen one-shot producers (`run.py`/task2495/task2497), not commands
to rerun inside their occupied output directory. Use a NEW directory/plan and
patch the small producer's OUT for a new registered run; never delete receipts.
The existing dependency is python-chess/chess1.11.2, used only as Chess rule
and legal move authority. It is GPL-3.0+; no dependency source is bundled.

The original2492 smoke predates a terminal-eligibility correction and runner
reason correction. `executed_smoke_v1_learning.py.txt` and
`executed_smoke_v1_run.py.txt` are exact original bytes in the immutable86 ZIP (direct Git text may normalize LF). To reconstruct that run,
extract the86 ZIP and overlay those files at their original `.py` names in an isolated copy. The original8test snapshot is also included and hash verified. Original
results stay original; newer code must not be called its executed source.

Evidence needed before success: multiple random initializations, actual terminal
heldout games versus initialization, stable repeated gains and total-cost curves.
Parameter movement, more tree samples, or lower bootstrap loss alone is not
success. Whole-method WDL-grid equal-cost comparison and a faithful Beal-Smith
replication remain pending; no human reference prices are used for selection.

Primary references read: [TDLeaf Figure3](https://arxiv.org/pdf/cs/9901002),
[TreeStrap algorithms1/2](https://cgi.cse.unsw.edu.au/~blair/pubs/2009VenessSilverUtherBlairNIPS.pdf),
[temporal coherence, IJCAI1999](https://www.ijcai.org/Proceedings/99-1/Papers/081.pdf).
Beal-Smith1997's [publisher abstract](https://journals.sagepub.com/doi/10.3233/ICG-1997-20302)
was accessible; full text was not obtained, so no exact-method claim is made.
