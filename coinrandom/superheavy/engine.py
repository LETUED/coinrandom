import asyncio
import functools
import hashlib
import math
import os
from datetime import datetime, timezone
from typing import Any, MutableSequence, Sequence

from ..core import mix_entropy, bytes_to_float
from ..heavy.engine import _collect_entropy, _argon2_stretch, ARGON2_TIME_COST, ARGON2_MEMORY_COST, ARGON2_PARALLELISM, ARGON2_HASH_LEN
from ..proof import SuperProof
from .optimizer import select_min_correlation_symbols


class SuperHeavyEngine:
    def __init__(self):
        self._argon2_params = {
            "time_cost": ARGON2_TIME_COST,
            "memory_cost_kb": ARGON2_MEMORY_COST,
            "parallelism": ARGON2_PARALLELISM,
            "hash_len": ARGON2_HASH_LEN,
        }

    def _generate(self) -> tuple[bytes, list[str], dict, dict, list[dict], str, str]:
        # 1단계: 역 포트폴리오 최적화로 최소 상관 코인 선정
        selected, corr_matrix, opt_result = select_min_correlation_symbols()

        # 2단계: 선정된 코인으로 3거래소 병렬 수집 + ETH 블록 해시
        raw, records, block_hash = _collect_entropy(selected)

        # 3단계: Argon2 스트레칭
        mixed = mix_entropy(raw)
        salt = os.urandom(16)
        stretched = _argon2_stretch(mixed, salt)
        final_hash = hashlib.sha256(stretched).hexdigest()

        return stretched, selected, corr_matrix, opt_result, records, block_hash, final_hash

    def random(self) -> float:
        seed, *_ = self._generate()
        return bytes_to_float(seed)

    def uniform(self, a: float, b: float) -> float:
        return a + (b - a) * self.random()

    def randint(self, a: int, b: int) -> int:
        span = b - a + 1
        threshold = (2**64) - (2**64 % span)
        while True:
            seed, *_ = self._generate()
            val = int.from_bytes(seed[:8], "big")
            if val < threshold:
                return a + (val % span)

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
        u1, u2 = self.random(), self.random()
        z = math.sqrt(-2 * math.log(u1)) * math.cos(2 * math.pi * u2)
        return mu + sigma * z

    def random_with_proof(self) -> SuperProof:
        seed, selected, corr_matrix, opt_result, records, block_hash, final_hash = self._generate()
        return SuperProof(
            value=bytes_to_float(seed),
            timestamp=datetime.now(timezone.utc).isoformat(),
            exchanges=records,
            block_hash=block_hash,
            argon2_params=self._argon2_params,
            candidate_count=len(corr_matrix),
            selected_symbols=selected,
            correlation_matrix=corr_matrix,
            optimization_result=opt_result,
            final_hash=final_hash,
        )

    # ── Async API ─────────────────────────────────────────

    def _run(self, fn, *args, **kwargs):
        loop = asyncio.get_running_loop()
        return loop.run_in_executor(None, functools.partial(fn, *args, **kwargs))

    async def arandom(self) -> float:
        return await self._run(self.random)

    async def auniform(self, a: float, b: float) -> float:
        return await self._run(self.uniform, a, b)

    async def arandint(self, a: int, b: int) -> int:
        return await self._run(self.randint, a, b)

    async def achoice(self, seq: Sequence[Any]) -> Any:
        return await self._run(self.choice, seq)

    async def achoices(self, seq: Sequence[Any], k: int = 1) -> list[Any]:
        return await self._run(self.choices, seq, k=k)

    async def asample(self, seq: Sequence[Any], k: int) -> list[Any]:
        return await self._run(self.sample, seq, k)

    async def ashuffle(self, seq: MutableSequence[Any]) -> None:
        return await self._run(self.shuffle, seq)

    async def agauss(self, mu: float = 0.0, sigma: float = 1.0) -> float:
        return await self._run(self.gauss, mu, sigma)

    async def arandom_with_proof(self) -> SuperProof:
        return await self._run(self.random_with_proof)
