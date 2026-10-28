# Autonomous round-continuation correction

The prior PRIMARY session ended at1492.285151effective seconds by calling two
finite subtask closures scientific_complete, despite further pure-Leaper work.
That ending is rejected and superseded by latest direct USER correction. Its
original bytes/quality receipt remain private and its ledger/start/UUID remain.
No gap or workflow repair is credited; no published history is rewritten.

Observed causes: scientific_complete was in HARD_REASONS, so self-declared
whole_current_objective/COMPLETE text bypassed duration and matching review.
final-check then allowed that hard reason while returning research_completed=false.
A regression test explicitly permitted this old behavior. Current USER contract
changes the requirement; this is not changing an expectation to match a failure.

Fix: scientific_complete is a normal duration/quality-gated reason. Both final
modes reject old premature scientific endings. start automatically resumes the
latest owned rejected ending with the same UUID/start/work intervals, records
superseded_endings and updates only the resume window. Stop/foreign-thread
protection remains.48 workflow regressions pass, including24.87minute false
whole-goal claims,missing quality,automatic recovery,gap exclusion,foreign identity
and user stop controls. No self-written finite scope or bounded mode substitutes
for60 effective minutes. At milestones choose AND BEGIN useful next research
under standing authorization without waiting for a new user start.

AGENTS and LOCAL_AGENT are updated; NEXT_WORK/current Main are executable.
No AUX file/session/branch,existing schedule,worker or goal was modified. This
structural guard cannot force App uptime or prevent a model from failing to
invoke checks; correct execution and honest concrete interruption reports remain
required. No claim of an absolute runtime guarantee is made.
