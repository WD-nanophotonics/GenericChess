# Completion record envelope

The first zero-observation completion attempt failed before compiling its
control because the saved census has `total`, not `worlds`. Its output and
producer remain frozen. This separate wrapper changes only that field lookup,
checks histogram plus unreachable mass independently, and charges its recorded
time. It invokes the declared acyclic rejection control and saved-result checks;
no world/action observations or completed-population reruns are introduced.
