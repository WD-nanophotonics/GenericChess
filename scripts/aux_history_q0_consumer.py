"""Closed 2026-10-31 consumer probe; five actual calls exceeded frozen four.
Exact executed producers and raw returns are preserved under artifacts.
No further dispatch or refill is permitted. Offline analysis only.
"""

def run(*args, **kwargs):
    raise RuntimeError("CLOSED_CAP_EXCEEDED: use preserved evidence, never dispatch Player")
