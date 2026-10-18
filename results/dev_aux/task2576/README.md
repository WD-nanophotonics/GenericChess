# Matched candidate TRAIN / DEPLOY search contexts

Only TD_plain and TD_q2 arms in plan.json execute. The training driver reuses the
prior episode-TD implementation and retains unused TC/WDL helper branches.
Those branches were not activated; comparisons.jsonl is deliberately zero bytes.
No new WDL finite-grid or TC training is claimed. Prior97 paid WDL remains a
historical method control, not new99 computation.

Candidate TRAIN search changes between plainD2 and approximate boundedq2; actual
uniform opponent stays plainD2 in every arm. Same eta.05/lambda.95, episode-frozen
weights, all four random initializations and1.5M BOTH-actor/failed nodes per arm.
New TRAIN roots and all576 main deployment slots were registered before training.
Independent192-slot fixedq2-opponent panel was registered before main fitness,
using prior98 headroom evidence, retaining ALL models regardless of main result.
None of the old frozen experiment caps was extended.

UNKNOWN leaves a trajectory censored; completed bootstrap transitions remain
eligible, the unavailable terminal transition is omitted. Actual rule W/L/D,
not a theoretical material/proof reward, evaluates strength. Bounds from pruned
interior search nodes are not exact TD labels; only completed root/PV receipts
enter this TD learner. P fixed1; free finite signed coefficients remain unclipped.

Internal theta-minimax is not an exact actual fixed-nu opponent policy critic.
q2 can leave noncheck captures unresolved, and all forced check evasions continue
until quiet/terminal/resource limits. It is not a full quiet or generic WDL prover.
Losses change their trajectories/targets, so lower TRAIN loss does not prove
better calibrated predictions or higher playing strength.

The first-target diagnostic uses ONE common full initial TRAIN root under four
initial coefficient sets, not four independent inputs. Selected deterministically
during training, not selected for favorable outcome. Full histories, all failed
queries, raw paid costs, signed prices and negative deployment cells are retained.

Exact raw code/data/pins are in DELTA_REPRO_20261019_99.zip after closure.
DirectGit LF/EOF-only projection is disclosed separately. Use the raw extraction
for exact pinned reproduction; external dependencies python-chess/pytest and the
actual own-role stop path remain explicit. Fresh reconstruction reruns real tests
and regenerates derived evidence; it does not retrain or refill old missing slots.
