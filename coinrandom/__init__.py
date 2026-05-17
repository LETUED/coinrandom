import asyncio
import functools
from importlib.metadata import version, PackageNotFoundError
from typing import Any, MutableSequence, Sequence

try:
    __version__ = version("coinrandom")
except PackageNotFoundError:
    __version__ = "unknown"

from .light import (
    random, uniform, randint, choice, choices, sample, shuffle, gauss
)

# ── Async API (Light) ─────────────────────────────────────

def _run(fn, *args, **kwargs):
    loop = asyncio.get_running_loop()
    return loop.run_in_executor(None, functools.partial(fn, *args, **kwargs))


async def arandom() -> float:
    return await _run(random)

async def auniform(a: float, b: float) -> float:
    return await _run(uniform, a, b)

async def arandint(a: int, b: int) -> int:
    return await _run(randint, a, b)

async def achoice(seq: Sequence[Any]) -> Any:
    return await _run(choice, seq)

async def achoices(seq: Sequence[Any], k: int = 1) -> list[Any]:
    return await _run(choices, seq, k=k)

async def asample(seq: Sequence[Any], k: int) -> list[Any]:
    return await _run(sample, seq, k)

async def ashuffle(seq: MutableSequence[Any]) -> None:
    return await _run(shuffle, seq)

async def agauss(mu: float = 0.0, sigma: float = 1.0) -> float:
    return await _run(gauss, mu, sigma)


__all__ = [
    "__version__",
    # sync
    "random", "uniform", "randint", "choice", "choices", "sample", "shuffle", "gauss",
    # async
    "arandom", "auniform", "arandint", "achoice", "achoices", "asample", "ashuffle", "agauss",
]
