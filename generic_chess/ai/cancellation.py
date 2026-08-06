"""Cooperative cancellation token."""

from __future__ import annotations

import threading
from typing import Callable


class CancellationToken:
    """Cooperative cancellation flag with thread-safe callbacks.

    ``cancel()`` flips the flag once (false -> true) and invokes every
    registered callback outside the lock; callbacks registered after
    cancellation are invoked immediately.  ``unregister`` is idempotent and a
    raising callback never blocks the other callbacks.
    """

    def __init__(self) -> None:
        self._cancelled = False
        self._lock = threading.Lock()
        self._callbacks: list[Callable[[], None]] = []

    def cancel(self) -> None:
        with self._lock:
            if self._cancelled:
                return
            self._cancelled = True
            callbacks = list(self._callbacks)
        for callback in callbacks:
            try:
                callback()
            except Exception:
                pass

    def is_cancelled(self) -> bool:
        with self._lock:
            return self._cancelled

    def register_callback(
        self, callback: Callable[[], None]
    ) -> Callable[[], None]:
        """Register a callback; returns an idempotent unregister function."""
        with self._lock:
            if self._cancelled:
                cancelled_now = True
            else:
                cancelled_now = False
                self._callbacks.append(callback)

        def unregister() -> None:
            with self._lock:
                for i, cb in enumerate(self._callbacks):
                    if cb is callback:
                        del self._callbacks[i]
                        break

        if cancelled_now:
            try:
                callback()
            except Exception:
                pass
        return unregister
