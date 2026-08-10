from __future__ import annotations

import threading
import time
from dataclasses import dataclass


@dataclass
class KeyLease:
    slot: int
    key: str


class NvidiaKeyPool:
    """Work-conserving key scheduler. Keys are never exposed outside this module."""
    def __init__(self, keys: tuple[str, ...], per_key_limit: int, cooldown_sec: float):
        self._keys = tuple(dict.fromkeys(key for key in keys if key))
        self._limit = per_key_limit
        self._cooldown_sec = cooldown_sec
        self._active = [0] * len(self._keys)
        self._cooldown_until = [0.0] * len(self._keys)
        self._next_slot = 0
        self._condition = threading.Condition()

    @property
    def size(self) -> int:
        return len(self._keys)

    def acquire(self, timeout: float) -> KeyLease:
        deadline = time.monotonic() + timeout
        with self._condition:
            while True:
                now = time.monotonic()
                eligible = [i for i in range(self.size) if self._active[i] < self._limit and self._cooldown_until[i] <= now]
                if eligible:
                    # Start new work across the configured keys before reusing the
                    # lowest-numbered slot. Once a request completes, its slot is
                    # immediately eligible again, so the pool remains work-conserving.
                    slot = min(
                        eligible,
                        key=lambda i: (
                            self._active[i],
                            (i - self._next_slot) % max(1, self.size),
                        ),
                    )
                    self._active[slot] += 1
                    self._next_slot = (slot + 1) % max(1, self.size)
                    return KeyLease(slot=slot, key=self._keys[slot])
                remaining = deadline - now
                if remaining <= 0:
                    raise TimeoutError("No NVIDIA API key became available before timeout")
                wake_at = min((value for value in self._cooldown_until if value > now), default=deadline)
                self._condition.wait(min(remaining, max(0.01, wake_at - now)))

    def release(self, lease: KeyLease, retryable_failure: bool = False) -> None:
        with self._condition:
            self._active[lease.slot] = max(0, self._active[lease.slot] - 1)
            if retryable_failure:
                self._cooldown_until[lease.slot] = time.monotonic() + self._cooldown_sec
            self._condition.notify_all()


_pools: dict[tuple[tuple[str, ...], int, float], NvidiaKeyPool] = {}
_pools_lock = threading.Lock()


def get_nvidia_key_pool(settings) -> NvidiaKeyPool:
    keys = tuple(getattr(settings, "nvidia_api_keys", ()) or ((settings.nvidia_api_key,) if settings.nvidia_api_key else ()))
    identity = (keys, settings.llm_max_in_flight_per_key, settings.llm_cooldown_sec)
    with _pools_lock:
        return _pools.setdefault(identity, NvidiaKeyPool(*identity))


def is_retryable_error(error: Exception) -> bool:
    message = str(error).lower()
    return any(marker in message for marker in ("403", "forbidden", "authorization", "429", "rate limit", "quota", "timeout", "timed out", "500", "502", "503", "504"))
