from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("coinrandom")
except PackageNotFoundError:
    __version__ = "unknown"

from .light import (
    random, uniform, randint, choice, choices, sample, shuffle, gauss
)

__all__ = [
    "__version__",
    "random", "uniform", "randint", "choice", "choices", "sample", "shuffle", "gauss",
]
