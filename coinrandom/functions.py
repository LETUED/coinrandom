import math
import secrets
from typing import Any, MutableSequence, Sequence

from .core import _build_seed


def _get_random_bytes(n: int) -> bytes:
    seed = _build_seed()
    # seed를 secrets.token_bytes의 추가 entropy로 혼합
    mixed = bytes(a ^ b for a, b in zip(seed[:n], secrets.token_bytes(n)))
    return mixed


def _random_float() -> float:
    raw = _get_random_bytes(8)
    val = int.from_bytes(raw, "big")
    return val / (2**64)


def random() -> float:
    return _random_float()


def uniform(a: float, b: float) -> float:
    return a + (b - a) * _random_float()


def randint(a: int, b: int) -> int:
    span = b - a + 1
    raw = _get_random_bytes(8)
    val = int.from_bytes(raw, "big")
    return a + (val % span)


def choice(seq: Sequence[Any]) -> Any:
    return seq[randint(0, len(seq) - 1)]


def choices(seq: Sequence[Any], k: int = 1) -> list[Any]:
    return [choice(seq) for _ in range(k)]


def sample(seq: Sequence[Any], k: int) -> list[Any]:
    pool = list(seq)
    result = []
    for _ in range(k):
        idx = randint(0, len(pool) - 1)
        result.append(pool.pop(idx))
    return result


def shuffle(seq: MutableSequence[Any]) -> None:
    for i in range(len(seq) - 1, 0, -1):
        j = randint(0, i)
        seq[i], seq[j] = seq[j], seq[i]


def gauss(mu: float = 0.0, sigma: float = 1.0) -> float:
    # Box-Muller transform
    u1 = _random_float()
    u2 = _random_float()
    z = math.sqrt(-2 * math.log(u1)) * math.cos(2 * math.pi * u2)
    return mu + sigma * z
