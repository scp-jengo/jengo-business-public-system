"""
In-memory rate limiter.

Default: 60 requests per minute per client_id.
Uses a sliding-window (token bucket approximation) approach:
  - Keeps a deque of timestamps per client.
  - On each check(), prunes timestamps older than the window.
  - If the remaining count >= limit → deny.
"""

from __future__ import annotations

from collections import deque
from datetime import datetime, timezone
from threading import Lock


def _now_ts() -> float:
    return datetime.now(timezone.utc).timestamp()


class RateLimiter:
    """
    Simple in-memory sliding-window rate limiter.

    Parameters
    ----------
    max_requests:
        Maximum number of requests allowed in the window.  Default: 60.
    window_seconds:
        Length of the sliding window in seconds.  Default: 60 (1 minute).
    """

    def __init__(self, max_requests: int = 60, window_seconds: int = 60) -> None:
        if max_requests <= 0:
            raise ValueError("max_requests must be > 0")
        if window_seconds <= 0:
            raise ValueError("window_seconds must be > 0")

        self._max = max_requests
        self._window = float(window_seconds)
        self._clients: dict[str, deque[float]] = {}
        self._lock = Lock()

    def check(self, client_id: str) -> bool:
        """
        Check whether client_id is within its rate limit.

        Records the current timestamp if allowed.

        Parameters
        ----------
        client_id:
            A string identifying the client (e.g. IP address, API token).

        Returns
        -------
        True  — request is allowed.
        False — rate limit exceeded.
        """
        with self._lock:
            now = _now_ts()
            cutoff = now - self._window

            if client_id not in self._clients:
                self._clients[client_id] = deque()

            window = self._clients[client_id]

            # Prune old timestamps
            while window and window[0] < cutoff:
                window.popleft()

            if len(window) >= self._max:
                return False

            window.append(now)
            return True

    def remaining(self, client_id: str) -> int:
        """Return the number of requests remaining in the current window."""
        with self._lock:
            now = _now_ts()
            cutoff = now - self._window
            window = self._clients.get(client_id, deque())
            active = sum(1 for ts in window if ts >= cutoff)
            return max(0, self._max - active)

    def reset(self, client_id: str) -> None:
        """Clear all recorded timestamps for client_id."""
        with self._lock:
            self._clients.pop(client_id, None)

    def clear_all(self) -> None:
        """Clear state for all clients (used in tests)."""
        with self._lock:
            self._clients.clear()
