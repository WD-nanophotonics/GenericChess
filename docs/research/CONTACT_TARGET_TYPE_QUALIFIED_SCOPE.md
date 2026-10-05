# Correct dataclass field at the unchanged execution boundary

The second zero-observation producer used nonexistent PieceType.movement.
The actual frozen schema field is movement_atoms; a separately named producer
changes only this invocation. Preserve both failed raw records and scripts.
No completed enumeration/events are repeated and the intended eight controls,
geometry, guard and resource caps remain unchanged. These were avoidable harness
errors, not scientific failures or evidence against the guard hypothesis.
