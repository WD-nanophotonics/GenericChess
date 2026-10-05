# Narrow continuation after zero-event import failure

The original harness saved the first root and all4 actions, then imported the
nonexistent core.action instead of core.actions.0 transitions were applied.
Preserve that producer/report. Decode that root and its exact saved board IDs
for the first capture; do not enumerate that root again. Other three declared
roots remain unobserved. Use the existing action_promotion_target_id interface
for both board and drop shapes. Source snapshots/counts/errors remain explicit.
Count the old4 entries/0.094sec against the SAME5000/15sec cap; continue only
the original four paths. No semantic rule, root or selection premise changes.
