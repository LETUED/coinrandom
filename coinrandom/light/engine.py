import hashlib
import math
import os
import threading
import time
from typing import Any, MutableSequence, Sequence

from argon2.low_level import hash_secret_raw, Type

from ..core import fetch_binance_entropy, mix_entropy

LIGHT_SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
RESEED_CALLS = 1000
RESEED_SECONDS = 60

ARGON2_TIME_COST = 1
ARGON2_MEMORY_COST = 8192  # 8MB
ARGON2_PARALLELISM = 1
ARGON2_HASH_LEN = 64


class HashDRBG:
    """SHA-512 카운터 기반 결정론적 난수 생성기. stdlib random 미사용."""

    def __init__(self):
        self._state = b""
        self._counter = 0

    def seed(self, data: bytes) -> None:
        self._state = hashlib.sha512(data).digest()
        self._counter = 0

    def _next_block(self) -> bytes:
        self._counter += 1
        return hashlib.sha512(
            self._state + self._counter.to_bytes(8, "big")
        ).digest()

    def random(self) -> float:
        val = int.from_bytes(self._next_block()[:8], "big")
        return val / (2**64)

    def randint(self, a: int, b: int) -> int:
        span = b - a + 1
        threshold = (2**64) - (2**64 % span)
        while True:
            val = int.from_bytes(self._next_block()[:8], "big")
            if val < threshold:
                return a + (val % span)


class LightEngine:
    def __init__(self):
        self._rng = HashDRBG()
        self._lock = threading.Lock()
        self._call_count = 0
        self._last_seed_time = 0.0
        self._seeded = False

    def _maybe_reseed(self) -> None:
        now = time.time()
        if (
            not self._seeded
            or self._call_count >= RESEED_CALLS
            or now - self._last_seed_time >= RESEED_SECONDS
        ):
            coin = fetch_binance_entropy(LIGHT_SYMBOLS)
            mixed = mix_entropy(coin)
            salt = os.urandom(16)
            stretched = hash_secret_raw(
                secret=mixed,
                salt=salt,
                time_cost=ARGON2_TIME_COST,
                memory_cost=ARGON2_MEMORY_COST,
                parallelism=ARGON2_PARALLELISM,
                hash_len=ARGON2_HASH_LEN,
                type=Type.ID,
            )
            self._rng.seed(stretched)
            self._call_count = 0
            self._last_seed_time = now
            self._seeded = True

    def random(self) -> float:
        with self._lock:
            self._maybe_reseed()
            self._call_count += 1
            return self._rng.random()

    def uniform(self, a: float, b: float) -> float:
        return a + (b - a) * self.random()

    def randint(self, a: int, b: int) -> int:
        with self._lock:
            self._maybe_reseed()
            self._call_count += 1
            return self._rng.randint(a, b)

    def choice(self, seq: Sequence[Any]) -> Any:
        return seq[self.randint(0, len(seq) - 1)]

    def choices(self, seq: Sequence[Any], k: int = 1) -> list[Any]:
        return [self.choice(seq) for _ in range(k)]

    def sample(self, seq: Sequence[Any], k: int) -> list[Any]:
        pool = list(seq)
        result = []
        for _ in range(k):
            idx = self.randint(0, len(pool) - 1)
            result.append(pool.pop(idx))
        return result

    def shuffle(self, seq: MutableSequence[Any]) -> None:
        for i in range(len(seq) - 1, 0, -1):
            j = self.randint(0, i)
            seq[i], seq[j] = seq[j], seq[i]

    def gauss(self, mu: float = 0.0, sigma: float = 1.0) -> float:
        u1 = self.random()
        while u1 == 0.0:
            u1 = self.random()
        u2 = self.random()
        z = math.sqrt(-2 * math.log(u1)) * math.cos(2 * math.pi * u2)
        return mu + sigma * z


_engine = LightEngine()


def _reseed_after_fork() -> None:
    _engine._seeded = False


try:
    os.register_at_fork(after_in_child=_reseed_after_fork)
except AttributeError:
    pass  # Windows does not support fork
