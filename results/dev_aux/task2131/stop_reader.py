"""Opt-in stop reader: fresh bytes every poll; memoize only JSON decoding.

No freshness/mtime cache, polling delay, held descriptor, thread or flag writer.
Actual content changes (even same size and mtime), read errors and invalid JSON
are observed on that same call. Path order/truthiness/exception match task109.
"""
from pathlib import Path
import json
from results.dev_aux.task109.adapter import PersistentStop

class ParsedStopReader:
    def __init__(self, root):
        root = Path(root)
        states = (root / '.local_agent', root.resolve().parent / 'GenericChess 2' / '.local_agent')
        self.paths = tuple(state / name for state in states
                           for name in ('rollout.json', 'advisor.json', 'slack.json'))
        self._cache = {}
        self.reads = self.parses = self.bytes_read = 0

    def __call__(self):
        for path in self.paths:
            raw = path.read_bytes()  # Deliberately fresh on EVERY poll.
            self.reads += 1
            self.bytes_read += len(raw)
            previous = self._cache.get(path)
            if previous is None or previous[0] != raw:
                value = json.loads(raw)  # Preserve original error/truthiness.
                stopped = bool(value.get('user_paused') or value.get('stopped'))
                self._cache[path] = (raw, stopped)
                self.parses += 1
            else:
                stopped = previous[1]
            if stopped:
                raise PersistentStop('persistent user stop')
